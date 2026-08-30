from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes.document_routes import router as document_router
from services.rbi_ingestion_service import ingest_rbi_source

# --- Added for Rule Engine integration (does not change anything above) ---
from fastapi.staticfiles import StaticFiles
from routes.compliance_routes import router as compliance_router
# --- end addition ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Started...")
    ingest_rbi_source()
    print("RBI Source embeddings ingested in the API.")
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

# --- Added for Rule Engine integration ---
# New router only; routes/document_routes.py and its pipeline are untouched.
app.include_router(compliance_router)

# Basic manual-testing UI for the rule engine.
# Visit http://127.0.0.1:8000/ui/ once the server is running — this now
# shows the LIVE PIPELINE DEMO by default (upload a doc, watch the LLM's
# extracted numbers flow automatically into the rule engine, no manual
# entry required). The old hand-entry UI (type numbers, click validate
# per rule) has been moved to http://127.0.0.1:8000/ui/manual_test.html
# for isolated single-rule testing, and is no longer the default landing
# page. Only static/index.html vs static/manual_test.html changed here —
# routes/document_routes.py, rule_engine/, and mcp_server/ are untouched.
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
# --- end addition ---