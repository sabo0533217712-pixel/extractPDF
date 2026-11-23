import tempfile
import os
from flask import Flask, request, jsonify
from pdf_to_json import extract_tables

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/extract", methods=["POST"])
def extract():
    file = request.files.get("file") or next(iter(request.files.values()), None)
    if not file:
        return jsonify({"error": "No file provided"}), 400

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file.save(tmp.name)
        try:
            tables = extract_tables(tmp.name)
        finally:
            os.unlink(tmp.name)

    if not tables:
        return jsonify({"error": "No tables found"}), 404

    all_records = [record for table in tables for record in table]
    return jsonify({"file": file.filename, "count": len(all_records), "records": all_records})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
