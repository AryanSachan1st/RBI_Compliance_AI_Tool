from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analysis_job_routes import router as analysis_job_router
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

# Needed once the UI is served separately from the API (i.e. not going
# through the Vite dev proxy). Wide open for now - tighten allow_origins
# to the deployed frontend URL before shipping to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "The API is up and running..."}


app.include_router(document_router)
app.include_router(analysis_job_router)
