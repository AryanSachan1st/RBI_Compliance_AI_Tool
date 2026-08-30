# chunking, embedding, vector store
# Chunking
# Store the embeddings in chromadb vector store locally
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Embeddings
from openai import OpenAI
from pydantic import Field


def create_chunks(text: str, chunk_size: int = 1000, overlap: int = 100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap
    )
    chunks = splitter.split_text(text)
    return chunks


def create_embeddings(chunks: list[str]):
    client = OpenAI()

    response = client.embeddings.create(model="text-embedding-3-small", input=chunks)

    embeddings = [item.embedding for item in response.data]

    return embeddings


def store_embeddings(
    chunks: list[str],
    embeddings: list[list[float]],
    name: str = Field(description="type of data (source/user)"),
):
    chroma_client = chromadb.PersistentClient(path="storage/vector_db")

    ids = [f"chunk_{i + 1}" for i in range(len(chunks))]

    if name == "source":
        collection = chroma_client.get_or_create_collection(name="rbi_source_documents")

        collection.add(ids=ids, documents=chunks, embeddings=embeddings)
    elif name == "user":
        collection = chroma_client.get_or_create_collection(name="user_documents")

        collection.add(ids=ids, documents=chunks, embeddings=embeddings)
    print("Embeddings saved in vector db successfully!")


def get_relevant_chunks(query_embeddings: list[list[float]]):
    chroma_client = chromadb.PersistentClient(path="../../storage/vector_db")

    source_collection = chroma_client.get_collection(name="legal_documents")

    top_chunks = source_collection.query(query_embeddings=query_embeddings, n_results=3)

    return top_chunks["documents"]
