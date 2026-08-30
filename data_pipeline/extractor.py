# extractor.py
import re

import pdfplumber


def extract_structured_text(pdf_path: str) -> dict:
    """
    Extracts text page by page, and separately extracts tables,
    since regulatory PDFs often have inline tables that break
    naive text extraction.
    """
    pages_text = []
    all_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_text.append({"page": page_num + 1, "text": text})

            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                all_tables.append(
                    {"page": page_num + 1, "table_index": t_idx, "rows": table}
                )

    full_text = "\n\n".join(str(p["text"]) for p in pages_text)
    return {"full_text": full_text, "pages": pages_text, "tables": all_tables}


def split_into_clauses(full_text: str) -> list[dict]:
    """
    Splits on common RBI/IRDAI numbering patterns:
    e.g. '1.', '1.1', '1.1.1', '(a)', '(i)' etc.
    This is a first-pass heuristic — expect to refine per document type.
    """
    # Matches patterns like "1.", "1.1", "1.1.1" at line start
    pattern = re.compile(r"\n(?=\d+(\.\d+)*\.?\s+[A-Z(])")
    raw_chunks = pattern.split(full_text)

    clauses = []
    for chunk in raw_chunks:
        if not chunk or not chunk.strip():
            continue
        # Extract the leading number as a clause reference
        match = re.match(r"^(\d+(\.\d+)*)\.?\s+(.*)", chunk.strip(), re.DOTALL)
        if match:
            clauses.append(
                {"clause_ref": match.group(1), "text": match.group(3).strip()}
            )
        else:
            clauses.append({"clause_ref": None, "text": chunk.strip()})

    return clauses


if __name__ == "__main__":
    doc = extract_structured_text("raw_pdfs/sample2.pdf")
    with open("output_extractor.txt", "w", encoding="utf-8") as f:
        f.write(str(split_into_clauses(doc["full_text"])))
