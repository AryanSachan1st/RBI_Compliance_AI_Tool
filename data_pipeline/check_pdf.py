# check_pdfs.py
from pathlib import Path

pdf_dir = Path("raw_pdfs")
bad_files = []

for pdf_path in pdf_dir.glob("*.pdf"):
    with open(pdf_path, "rb") as f:
        header = f.read(5)
    size = pdf_path.stat().st_size
    if header != b"%PDF-":
        bad_files.append((pdf_path.name, size, header))

print(f"Checked {len(list(pdf_dir.glob('*.pdf')))} files")
print(f"Bad files (not real PDFs): {len(bad_files)}\n")

for name, size, header in bad_files:
    print(f"{name} | size={size} bytes | header={header}")
