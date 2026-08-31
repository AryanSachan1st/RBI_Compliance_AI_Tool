"""Train the CNN document classifier from a locally curated labelled image set."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True, help="One subdirectory per document class.")
    parser.add_argument("--output", type=Path, default=Path("models/authenticity_model.h5"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=224)
    args = parser.parse_args()
    if not args.dataset.is_dir() or not any(args.dataset.iterdir()): raise SystemExit("Dataset directory must contain one non-empty folder per class.")
    import tensorflow as tf
    train = tf.keras.utils.image_dataset_from_directory(args.dataset, validation_split=0.2, subset="training", seed=42, image_size=(args.image_size, args.image_size), batch_size=16)
    validation = tf.keras.utils.image_dataset_from_directory(args.dataset, validation_split=0.2, subset="validation", seed=42, image_size=(args.image_size, args.image_size), batch_size=16)
    classes = train.class_names
    augmentation = tf.keras.Sequential([tf.keras.layers.RandomFlip("horizontal"), tf.keras.layers.RandomRotation(0.03), tf.keras.layers.RandomContrast(0.08)])
    backbone = tf.keras.applications.MobileNetV2(include_top=False, weights="imagenet", input_shape=(args.image_size, args.image_size, 3))
    backbone.trainable = False
    model = tf.keras.Sequential([augmentation, tf.keras.applications.mobilenet_v2.preprocess_input, backbone, tf.keras.layers.GlobalAveragePooling2D(), tf.keras.layers.Dropout(0.2), tf.keras.layers.Dense(len(classes), activation="softmax")])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    history = model.fit(train.prefetch(tf.data.AUTOTUNE), validation_data=validation.prefetch(tf.data.AUTOTUNE), epochs=args.epochs)
    args.output.parent.mkdir(parents=True, exist_ok=True); model.save(args.output)
    labels_path = args.output.with_name("authenticity_labels.json")
    labels_path.write_text(json.dumps(classes, indent=2), encoding="utf-8")
    print(json.dumps({"model": str(args.output), "labels": str(labels_path), "classes": classes, "final_validation_accuracy": history.history["val_accuracy"][-1]}))

if __name__ == "__main__": main()
