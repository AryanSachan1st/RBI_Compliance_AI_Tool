"""Evaluate a trained CNN on a held-out image folder and write JSON metrics."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from services.evaluation_service import classification_metrics

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("models/authenticity_model.h5"))
    parser.add_argument("--labels", type=Path, default=Path("models/authenticity_labels.json"))
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/cnn_holdout_results.json"))
    args = parser.parse_args()
    import tensorflow as tf
    labels = json.loads(args.labels.read_text(encoding="utf-8")); model = tf.keras.models.load_model(args.model)
    dataset = tf.keras.utils.image_dataset_from_directory(args.dataset, shuffle=False, image_size=(224, 224), batch_size=16)
    expected = [labels[index] for batch in dataset for index in batch[1].numpy()]
    predicted = [labels[index] for index in model.predict(dataset, verbose=0).argmax(axis=1)]
    result = classification_metrics(expected, predicted); args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__": main()
