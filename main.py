import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.document_routes import router as document_router
from routes.evaluation_routes import router as evaluation_router
from services.rbi_ingestion_service import ingest_regulatory_corpus


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Started...")
    print(ingest_regulatory_corpus())
    yield
    print("Application is shutting down...")


app = FastAPI(
    title="AI Compliance Analysis Tool",
    description="AI-Powered Regulatory Compliance Verification Platform for BFSI Documents.",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {"message": "The API is up and running..."}


allowed_origins = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(document_router)
app.include_router(evaluation_router)
