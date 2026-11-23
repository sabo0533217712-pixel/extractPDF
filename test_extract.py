from pdf_to_json import pdf_to_json
import json

result = json.loads(pdf_to_json("sample.pdf"))

print(f"File: {result.get('file')}")
print(f"Tables found: {result.get('tables_count', 0)}")

for i, table in enumerate(result.get("tables", [])):
    print(f"\n{'=' * 50}")
    print(f"TABLE {i + 1}  ({len(table)} rows)")
    print("=" * 50)
    for row in table:
        print(row)
