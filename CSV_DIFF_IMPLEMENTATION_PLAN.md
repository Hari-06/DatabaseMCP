# CSV Comparison Tool — Implementation Plan
### Comparing two 1.5M-row × 85-column CSVs for cell-level discrepancies

---

## 1. Goal

Given two CSV files (`file_a.csv`, `file_b.csv`) representing the same dataset at two points in time / from two sources, identify:
- Rows present in one file but not the other (by unique ID)
- Cells where the value differs between the two files for matching IDs
- Produce a human-reviewable output (Excel, highlighted) plus a full machine-readable diff (CSV/Parquet)

Target scale: ~1.5,000,000 rows × 85 columns per file (~127M cells per file).

---

## 2. Tech Stack

| Component | Choice | Why |
|---|---|---|
| Data engine | **Polars** (not pandas) | Multi-threaded, columnar, lazy execution, handles 1.5M×85 in ~hundreds of MB–1GB RAM |
| Output (highlighted) | **openpyxl** or **xlsxwriter** | Conditional formatting / cell fill for mismatches |
| Output (full diff) | CSV or **Parquet** | Parquet is far smaller/faster for 1.5M-row diff logs |
| Language | Python 3.10+ | Ecosystem fit |

Install:
```bash
pip install polars openpyxl xlsxwriter pyarrow --break-system-packages
```

---

## 3. High-Level Architecture

```
file_a.csv ─┐
            ├─► [1. Ingest (raw, as-is)] ─► [2. Outer Join on ID]
file_b.csv ─┘                                        │
                                                      ▼
                               ┌──────────────────────────────────┐
                               │ 3. Vectorized column-wise compare │
                               └──────────────────────────────────┘
                                                      │
                  ┌───────────────────────────────────┼───────────────────────────┐
                  ▼                                   ▼                           ▼
         [4a. Only-in-A IDs]                [4b. Only-in-B IDs]         [4c. Mismatched cells]
                  │                                   │                           │
                  └───────────────────────────────────┴───────────────────────────┘
                                                      ▼
                                        [5. Tidy long-format diff table]
                                                      ▼
                               ┌──────────────────────────────────┐
                               │ 6. Outputs: xlsx (highlighted) +  │
                               │    full diff (csv/parquet) +      │
                               │    per-column summary             │
                               └──────────────────────────────────┘
```

**Note:** This pipeline does an **exact, as-is comparison** — no whitespace trimming, no type coercion, no case-folding, no float tolerance. If `"100"` vs `100.0` or `"Yes"` vs `"yes"` exist in your data, they will show as mismatches. See §6 for details.

---

## 4. Step-by-Step Implementation

### Step 1 — Ingest (raw, exact as-is)
```python
import polars as pl

ID_COL = "id"  # replace with actual unique ID column name

# Read every column as a string (Utf8) — this guarantees Polars does not
# silently reinterpret "100" as 100, "2024-01-05" as a date, etc.
# You get a byte-for-byte-faithful comparison of what's actually in the file.
df_a = pl.read_csv("file_a.csv", infer_schema=False)
df_b = pl.read_csv("file_b.csv", infer_schema=False)
```
- `infer_schema=False` forces every column to be read as a plain string, so nothing gets coerced, trimmed, or reformatted before comparison — this is what "exact as it is" requires.
- If either file is too large for comfortable RAM, use `pl.scan_csv()` (lazy, same `infer_schema=False` option) and keep the pipeline lazy until the final `.collect()`.

### Step 2 — Outer join on ID
```python
joined = df_a.join(df_b, on=ID_COL, how="full", suffix="_b")
```
- `how="full"` (outer join) surfaces rows that exist in only one file.
- Rows where all `_b` columns are null → only in A.
- Rows where all `_a` (original) columns are null → only in B.

### Step 3 — Vectorized comparison (exact match)
Build the list of compare columns (all columns except the ID):
```python
compare_cols = [c for c in df_a.columns if c != ID_COL]

mismatch_exprs = [
    (
        (pl.col(c).is_null() & pl.col(f"{c}_b").is_null()).not_()
        & (pl.col(c) != pl.col(f"{c}_b"))
    ).alias(f"{c}__mismatch")
    for c in compare_cols
]

flagged = joined.with_columns(mismatch_exprs)
```
This is a **single columnar pass** — no per-row Python loop — and is where the speed comes from. On 1.5M rows this should run in low single-digit seconds on a modern machine. Since everything is read as raw strings, `!=` here is a byte-for-byte exact comparison — no coercion, no tolerance.

### Step 4 — Split into categories
```python
only_in_a = joined.filter(pl.col(f"{compare_cols[0]}_b").is_null())
only_in_b = joined.filter(pl.col(compare_cols[0]).is_null())

both_present = joined.filter(
    pl.col(compare_cols[0]).is_not_null() & pl.col(f"{compare_cols[0]}_b").is_not_null()
)
```

### Step 5 — Reshape mismatches into a tidy long table
Rather than carrying a wide 85-column boolean grid, melt only the flagged mismatches:
```python
mismatch_flags = [c for c in flagged.columns if c.endswith("__mismatch")]

long_diff = (
    flagged
    .select([ID_COL] + compare_cols + [f"{c}_b" for c in compare_cols] + mismatch_flags)
    .unpivot(index=[ID_COL], on=mismatch_flags, variable_name="column", value_name="is_mismatch")
    .filter(pl.col("is_mismatch"))
    .with_columns(pl.col("column").str.replace("__mismatch", ""))
)
```
Then join back to pull the actual `value_a` / `value_b` for each flagged (id, column) pair — gives you a clean table:

| id | column | value_a | value_b |
|---|---|---|---|

This table is your **single source of truth** for every discrepancy — small, filterable, sortable.

### Step 6 — Outputs

**(a) Full diff — CSV or Parquet**
```python
long_diff.write_csv("full_diff.csv")
# or, for large diff volumes:
long_diff.write_parquet("full_diff.parquet")
```

**(b) Per-column summary (quick human overview)**
```python
summary = (
    long_diff.group_by("column")
    .agg(pl.len().alias("mismatch_count"))
    .sort("mismatch_count", descending=True)
)
summary.write_csv("mismatch_summary.csv")
```

**(c) Highlighted Excel spreadsheet**
- ⚠️ Excel hard limit: **1,048,576 rows per sheet**. Do NOT dump all 1.5M rows — only rows that have ≥1 mismatch.
```python
import xlsxwriter

wb = xlsxwriter.Workbook("diff_highlighted.xlsx")
ws = wb.add_worksheet("mismatches")
highlight_fmt = wb.add_format({"bg_color": "#FFC7CE"})

# Write header
headers = [ID_COL] + compare_cols
ws.write_row(0, 0, headers)

# Get IDs that have at least one mismatch
mismatched_ids = long_diff.select(ID_COL).unique().to_series().to_list()
subset = both_present.filter(pl.col(ID_COL).is_in(mismatched_ids))

for row_idx, row in enumerate(subset.iter_rows(named=True), start=1):
    ws.write(row_idx, 0, row[ID_COL])
    for col_idx, c in enumerate(compare_cols, start=1):
        val_a, val_b = row[c], row[f"{c}_b"]
        cell_value = val_a  # show file A's value; could show "A / B" string instead
        if val_a != val_b:
            ws.write(row_idx, col_idx, cell_value, highlight_fmt)
        else:
            ws.write(row_idx, col_idx, cell_value)

wb.close()
```
- If mismatched-row count is still huge (hundreds of thousands), consider:
  - Splitting across multiple sheets (Excel per-sheet row cap), or
  - Producing the Excel output only for a sampled/filtered subset (e.g., top N columns by mismatch frequency), with the full data living in `full_diff.parquet`/`csv`.

---

## 5. Performance Expectations

| Step | Expected time (1.5M rows × 85 cols, modern laptop) |
|---|---|
| CSV read (×2, as strings, no inference) | 2–8s each — actually slightly faster than type-inferring reads |
| Outer join | 1–5s |
| Vectorized compare (85 cols) | 2–8s |
| Melt/reshape mismatches | 1–5s |
| Excel write (mismatched rows only) | depends heavily on mismatch row count — 10K rows ≈ few seconds, 500K+ rows ≈ much slower, since xlsx writing is inherently row-by-row |

Total for the Polars-side pipeline: **under a minute** in most cases. The Excel write step is the one part that doesn't vectorize (Excel format is inherently row-oriented) — if mismatches are numerous, prefer CSV/Parquet as primary output and treat Excel as a secondary, filtered view.

---

## 6. Known Consequences of Exact, As-Is Comparison

Since this pipeline intentionally does **no normalization**, be aware it will flag all of the following as mismatches — by design:

- Trailing/leading whitespace differences (`"abc "` vs `"abc"`)
- `""` (empty string) vs `null`/missing value
- Numeric formatting differences (`"100"` vs `"100.0"` vs `"100.00"`)
- Case differences (`"Yes"` vs `"yes"`)
- Date/time format differences (`"2024-01-05"` vs `"01/05/2024"`) even if they represent the same date
- Floating-point representation differences (`"1.0"` vs `"1.00000001"`)

If any of these turn out to be noise rather than genuine discrepancies once you see the output, that's a normalization step we can add back in selectively — but nothing is applied by default here.

- [ ] Duplicate IDs within a single file (join will fan out — decide dedup strategy upfront)
- [ ] Column name mismatches/reordering between the two files (this pipeline aligns by column **name**, not position, so reordered columns are handled correctly)

---

## 7. Next Steps

1. Confirm the unique ID column name.
2. Run the pipeline once files are available.
3. Review `mismatch_summary.csv` first to sanity-check scope (e.g., if one column shows 100% mismatch, it's likely a formatting artifact, not real data drift) before generating the full highlighted Excel.
