import pymupdf
import json
import sys
import re
from pathlib import Path

TOLERANCE = 5


def fix_amount(text: str) -> str:
    # דפוס: '6660\n.' או '550000\n, .' - ספרות + שורה חדשה + פיסוק
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return text.strip()
    has_decimal = "." in text
    has_thousands = "," in text
    if has_decimal and has_thousands:
        # X,XXX.XX - שתי ספרות אחרונות הן עשרוניות
        integer, decimal = digits[:-2], digits[-2:]
    elif has_decimal and not has_thousands:
        # XX.XX - שתי ספרות אחרונות הן עשרוניות
        integer, decimal = digits[:-2], digits[-2:]
    else:
        return digits
    integer = integer.lstrip("0") or "0"
    integer_fmt = ",".join(re.findall(r"\d{1,3}(?=(?:\d{3})*$)", integer))
    return f"{integer_fmt}.{decimal}"


def is_reversed_hebrew(text: str) -> bool:
    # בודק אם המילה הראשונה מתחילה באות סיום (סימן להיפוך)
    FINAL_LETTERS = set('\u05dd\u05df\u05e3\u05da\u05e5')  # ם ן ף ך ץ
    words = text.strip().split()
    if not words:
        return False
    first_word = words[0]
    if not re.search(r'[\u0590-\u05FF]', first_word):
        return False
    # אם האות הראשונה היא אות סיום - זה הפוך
    return first_word[0] in FINAL_LETTERS


def fix_cell(text: str, is_amount: bool = False) -> str:
    if not text:
        return ""
    if is_amount and re.match(r"^[\d\s.,\n]+$", text):
        return fix_amount(text)
    if re.search(r"[\u0590-\u05FF]", text):
        if is_reversed_hebrew(text):
            words = re.split(r"\s+", text.strip())
            return " ".join(w[::-1] for w in words if w)
        return text.strip()
    return text.strip()


def cell_text_from_words(words: list, bbox: tuple) -> str:
    x0, y0, x1, y1 = bbox
    in_cell = [
        w for w in words
        if w[0] >= x0 - TOLERANCE and w[2] <= x1 + TOLERANCE
        and w[1] >= y0 - TOLERANCE and w[3] <= y1 + TOLERANCE
    ]
    # מיין משמאל לימין (סדר קריאה עברית)
    in_cell.sort(key=lambda w: -w[0])
    return " ".join(w[4] for w in in_cell)


def extract_extra_columns(words: list, table, grid: list, n_rows: int) -> dict[int, str]:
    """מחפש מילים מחוץ לגבול הטבלה ומשייך אותן לשורות לפי y"""
    extra = {}
    table_x0 = table.bbox[0]
    outside_words = [w for w in words if w[2] < table_x0 - 2]
    if not outside_words:
        return extra
    for row_idx in range(1, n_rows):  # מדלג על שורת כותרת
        cell_y0 = grid[row_idx][0][1]
        cell_y1 = grid[row_idx][0][3]
        row_words = [
            w for w in outside_words
            if w[1] >= cell_y0 - TOLERANCE and w[3] <= cell_y1 + TOLERANCE
        ]
        row_words.sort(key=lambda w: -w[0])
        extra[row_idx] = fix_cell(" ".join(w[4] for w in row_words))
    return extra


def extract_tables(pdf_path: str) -> list[list[dict]]:
    doc = pymupdf.open(pdf_path)
    all_tables = []
    for page in doc:
        words = page.get_text("words")
        for table in page.find_tables().tables:
            n_cols = table.col_count
            # cells מסודרים לפי עמודה - נארגן לפי שורות
            n_rows = len(table.cells) // n_cols
            grid = [
                [table.cells[col * n_rows + row] for col in range(n_cols)]
                for row in range(n_rows)
            ]
            rows_text = [
                [fix_cell(cell_text_from_words(words, cell)) for cell in row]
                for row in grid
            ]
            if len(rows_text) < 2:
                continue
            raw_headers = [cell_text_from_words(words, table.cells[col * n_rows]) for col in range(n_cols)]
            headers = [fix_cell(h) or f"col_{i}" for i, h in enumerate(raw_headers)]
            # זיהוי עמודות סכום לפי הכותרת
            amount_cols = {i for i, h in enumerate(headers) if h in ("חובה", "זכות", "יתרה", "סכום")}
            # חילוץ עמודות מחוץ לגבול הטבלה (כמו הערות)
            extra_col = extract_extra_columns(words, table, grid, n_rows)
            # זיהוי כותרת העמודה החיצונית
            extra_header_words = [w for w in words if w[2] < table.bbox[0] - 2 and w[1] >= table.bbox[1] - TOLERANCE and w[3] <= grid[1][0][1] + TOLERANCE]
            extra_header = fix_cell(" ".join(w[4] for w in sorted(extra_header_words, key=lambda w: -w[0]))) or "הערות"
            records = [
                {**{headers[i]: fix_cell(v, is_amount=(i in amount_cols)) for i, v in enumerate(row)},
                 **({extra_header: extra_col[row_idx + 1]} if extra_col else {})}
                for row_idx, row in enumerate(rows_text[1:])
            ]
            all_tables.append(records)
    return all_tables


def pdf_to_json(pdf_path: str) -> str:
    tables = extract_tables(pdf_path)
    if not tables:
        return json.dumps({"error": "No tables found", "file": pdf_path}, ensure_ascii=False)
    all_records = [record for table in tables for record in table]
    return json.dumps(
        {"file": Path(pdf_path).name, "count": len(all_records), "records": all_records},
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"
    sys.stdout.reconfigure(encoding="utf-8")
    print(pdf_to_json(path))
