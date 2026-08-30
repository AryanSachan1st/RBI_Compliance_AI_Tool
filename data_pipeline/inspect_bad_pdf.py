# inspect_bad_pdf.py
from pathlib import Path

# pick any one of the bad files
path = Path("raw_pdfs/0215bfe2c1bb.pdf")
content = path.read_text(encoding="utf-8", errors="replace")
print(content[:2000])
