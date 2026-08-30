import PyPDF2
from services.text_preprocessing import create_chunks, create_embeddings, store_embeddings
from services.document_parser import extract_pdf_text
import chromadb
import os

INGESTION_CHECK_FILE_PATH = "storage/rbi_source_ingested.txt"

def ingest_rbi_source():
    print("Ingesting RBI Source...")

    if os.path.exists(INGESTION_CHECK_FILE_PATH):
        print("RBI Source already ingested...")
        return

    path = "storage/rbi_source/dummy_rbi_rulebook.pdf"

    text = extract_pdf_text(path)

    chunks = create_chunks(text)
    embeddings = create_embeddings(chunks)
    store_embeddings(chunks, embeddings, "source")

    with open(INGESTION_CHECK_FILE_PATH, "w") as file:
        file.write("RBI Source ingested...")

    print("RBI Source ingested successfully!")