import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VECTOR_DB_PATH = BASE_DIR / "data_pipeline" / "chroma_db"
COLLECTION_NAME = "rbi_irdai_clauses"
NUM_OF_K_ARGS = 5
