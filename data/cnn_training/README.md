# CNN image dataset

Place only self-created, public, or otherwise permitted images here. Use a held-out folder for evaluation; do not evaluate on training images.

```
data/cnn_training/
  Loan_Agreement/*.png
  Insurance_Policy/*.png
  KYC_Form/*.png
  Other/*.png

data/cnn_evaluation/       # same class folders, never used for training
```

Train a MobileNetV2 transfer-learning classifier:

```powershell
python scripts/train_document_classifier.py --dataset data/cnn_training --epochs 8
python scripts/evaluate_document_classifier.py --dataset data/cnn_evaluation
```

Training produces `models/authenticity_model.h5` and `models/authenticity_labels.json`. The model is intentionally excluded from Git: it is a generated artifact and must be versioned through an approved model registry/release process. Do not report its metrics until the held-out evaluation has been run.
