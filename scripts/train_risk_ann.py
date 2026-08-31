"""Train the small ANN from the versioned demo/evaluation data."""
import json
import sys
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from models.risk_ann_model import RISK_LABELS, RiskANN

rows = json.loads((root / "data" / "risk_ann_demo_training.json").read_text(encoding="utf-8-sig"))
features = np.array([row["features"] for row in rows], dtype=float)
labels = np.array([RISK_LABELS.index(row["label"]) for row in rows], dtype=int)
model = RiskANN.initialize()
model.fit(features, labels)
output = root / "storage" / "models" / "risk_ann_demo.npz"
model.save(output)
print(output)
