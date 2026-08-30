from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes.document_routes import router as document_router
from services.rbi_ingestion_service import ingest_rbi_source

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Started...")
    ingest_rbi_source()
    yield
    print("Application is shutting down...")

app = FastAPI(
    title="AI Compliance Analysis Tool",
    description="AI-Powered Regulatory Compliance Verification Platform for BFSI Documents.",
    lifespan=lifespan,
)

@app.get("/")
def read_root():
    return {
        "message": "The API is up and running..."
    }


app.include_router(document_router)