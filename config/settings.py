import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR/".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")