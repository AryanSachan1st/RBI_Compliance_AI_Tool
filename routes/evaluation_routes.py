"""Read-only endpoints for independently evaluating pipeline components."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from services.evaluation_service import classification_metrics, entity_metrics, retrieval_metrics
router = APIRouter(prefix="/evaluation", tags=["component evaluation"])
DATASET_DIRECTORY = Path("data/evaluation")
CLASSIFICATION_COMPONENTS = {"ann", "cnn", "llm_rag", "end_to_end"}
@router.get("/{component}")
def evaluate_component(component: str) -> dict:
    dataset_path = DATASET_DIRECTORY / f"{component}.json"
    if component not in CLASSIFICATION_COMPONENTS | {"rag", "entity_extraction"}: raise HTTPException(status_code=404, detail="Unknown evaluation component.")
    if not dataset_path.exists(): raise HTTPException(status_code=404, detail="Evaluation dataset not found.")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    try:
        if component == "rag": metrics = retrieval_metrics(dataset)
        elif component == "entity_extraction": metrics = entity_metrics(dataset["expected"], dataset["predicted"])
        else: metrics = classification_metrics(dataset["expected"], dataset["predicted"])
    except (KeyError, TypeError, ValueError) as exc: raise HTTPException(status_code=422, detail=f"Invalid evaluation dataset: {exc}") from exc
    return {"component": component, "metrics": metrics, "dataset": str(dataset_path)}
