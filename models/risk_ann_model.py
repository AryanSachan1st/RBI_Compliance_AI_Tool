"""Small NumPy ANN used for document-level compliance risk classification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np

RISK_LABELS = ("LOW", "MEDIUM", "HIGH")


@dataclass
class RiskANN:
    """Interpretable 4→6→3 feed-forward network with softmax outputs."""
    weights_input_hidden: np.ndarray
    bias_hidden: np.ndarray
    weights_hidden_output: np.ndarray
    bias_output: np.ndarray

    @classmethod
    def initialize(cls, seed: int = 42) -> "RiskANN":
        random = np.random.default_rng(seed)
        return cls(
            random.normal(0, 0.25, (4, 6)),
            np.zeros(6),
            random.normal(0, 0.25, (6, 3)),
            np.zeros(3),
        )

    def probabilities(self, features: np.ndarray) -> np.ndarray:
        hidden = np.maximum(0, features @ self.weights_input_hidden + self.bias_hidden)
        logits = hidden @ self.weights_hidden_output + self.bias_output
        logits -= logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        return exp / exp.sum(axis=1, keepdims=True)

    def fit(self, features: np.ndarray, labels: np.ndarray, epochs: int = 1800, learning_rate: float = 0.08) -> None:
        targets = np.eye(3)[labels]
        for _ in range(epochs):
            hidden_linear = features @ self.weights_input_hidden + self.bias_hidden
            hidden = np.maximum(0, hidden_linear)
            logits = hidden @ self.weights_hidden_output + self.bias_output
            logits -= logits.max(axis=1, keepdims=True)
            probabilities = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
            output_error = (probabilities - targets) / len(features)
            hidden_error = (output_error @ self.weights_hidden_output.T) * (hidden_linear > 0)
            self.weights_hidden_output -= learning_rate * hidden.T @ output_error
            self.bias_output -= learning_rate * output_error.sum(axis=0)
            self.weights_input_hidden -= learning_rate * features.T @ hidden_error
            self.bias_hidden -= learning_rate * hidden_error.sum(axis=0)

    def save(self, path: str | Path) -> None:
        np.savez(path, w1=self.weights_input_hidden, b1=self.bias_hidden, w2=self.weights_hidden_output, b2=self.bias_output)

    @classmethod
    def load(cls, path: str | Path) -> "RiskANN":
        data = np.load(path)
        return cls(data["w1"], data["b1"], data["w2"], data["b2"])
