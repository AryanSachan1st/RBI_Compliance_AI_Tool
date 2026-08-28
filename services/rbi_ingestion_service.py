import PyPDF2
from services.text_preprocessing import create_chunks, create_embeddings, store_embeddings
from services.document_parser import extract_pdf_text
import chromadb


def ingest_rbi_source():
    print("Ingesting RBI Source...")
    path = "storage/rbi_docs/dummy_rbi_rulebook.pdf"

    text = extract_pdf_text(path)

    chunks = create_chunks(text)
    embeddings = create_embeddings(chunks)
    store_embeddings(chunks, embeddings, "source")