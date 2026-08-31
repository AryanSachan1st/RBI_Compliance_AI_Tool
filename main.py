from contextlib import asynccontextmanager

from fastapi import FastAPI

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


app.include_router(document_router)
app.include_router(evaluation_router)
