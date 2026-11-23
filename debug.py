import pymupdf, sys
sys.stdout.reconfigure(encoding="utf-8")

doc = pymupdf.open("sample.pdf")
page = doc[0]
words = page.get_text("words")
table = page.find_tables().tables[0]
n_rows = len(table.cells) // table.col_count

# גבולות X של כל עמודה
col_ranges = sorted(set((round(table.cells[col*n_rows][0],1), round(table.cells[col*n_rows][2],1)) for col in range(table.col_count)))
print("col x ranges:", col_ranges)
print("table x0:", round(table.bbox[0],1))

# מילים שנמצאות שמאלה לעמודה הראשונה (הכי שמאלית)
leftmost_col_x0 = min(c[0] for c in col_ranges)
print("leftmost col x0:", leftmost_col_x0)

outside_left = [w for w in words if w[2] < leftmost_col_x0 + 5 and w[1] > table.bbox[1] and w[3] < table.bbox[3]]
print("\nwords left of all columns (הערות area):")
for w in sorted(outside_left, key=lambda w: w[1])[:15]:
    print(f"  x0={round(w[0],1)} x1={round(w[2],1)} y={round(w[1],1)} text={repr(w[4])}")
