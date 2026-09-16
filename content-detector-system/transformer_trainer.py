"""
Transformer Fine-Tuning Module for Content Detection.

Supports fine-tuning transformer architectures:
  - distilbert-base-uncased (default, fast baseline)
  - microsoft/deberta-v3-base (deep contextual model)

Classes: propaganda, opinion, neutral
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Check device: Apple MPS, CUDA, or CPU
def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class ContentDataset(Dataset):
    """PyTorch Dataset for text tokenization."""

    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 256):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = str(self.texts[idx])
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        if self.labels:
            item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item


class TransformerDetector:
    """Trainer and Evaluator for Transformer models."""

    def __init__(self, model_name: str = "distilbert-base-uncased", num_labels: int = 3):
        self.model_name = model_name
        self.num_labels = num_labels
        self.device = get_device()
        self.label_mapping = {"propaganda": 0, "opinion": 1, "neutral": 2}
        self.inv_label_mapping = {0: "propaganda", 1: "opinion", 2: "neutral"}
        
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            logger.info("Loading tokenizer & model: %s on device: %s", model_name, self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name, num_labels=num_labels
            )
            self.model.to(self.device)
        except Exception as e:
            logger.error("Failed to load HuggingFace model %s: %s", model_name, e)
            raise e

    def train(
        self,
        dataset_path: str,
        output_dir: str = "models/transformer",
        epochs: int = 3,
        batch_size: int = 16,
        lr: float = 2e-5,
    ) -> Dict[str, float]:
        """Full training loop."""
        from transformers import AdamW, get_linear_schedule_with_warmup

        path = Path(dataset_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        valid_items = [
            item for item in data
            if item.get("text") and item.get("content_type") in self.label_mapping
        ]
        logger.info("Loaded %d valid items for Transformer training", len(valid_items))

        texts = [item["text"] for item in valid_items]
        labels = [self.label_mapping[item["content_type"]] for item in valid_items]

        train_texts, val_texts, train_labels, val_labels = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )

        train_dataset = ContentDataset(train_texts, train_labels, self.tokenizer)
        val_dataset = ContentDataset(val_texts, val_labels, self.tokenizer)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        optimizer = AdamW(self.model.parameters(), lr=lr, weight_decay=0.01)
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=int(total_steps * 0.1), num_training_steps=total_steps
        )

        logger.info("Starting Transformer Training (%d epochs)...", epochs)
        best_f1 = 0.0

        for epoch in range(epochs):
            t0 = time.time()
            self.model.train()
            total_loss = 0.0

            for step, batch in enumerate(train_loader):
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                batch_labels = batch["labels"].to(self.device)

                self.model.zero_grad()
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=batch_labels,
                )
                loss = outputs.loss
                total_loss += loss.item()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()

            avg_loss = total_loss / len(train_loader)
            val_acc, val_f1, report = self.evaluate(val_loader)
            elapsed = time.time() - t0

            logger.info(
                "Epoch %d/%d [%.1fs] - Loss: %.4f - Val Acc: %.4f - Val F1: %.4f",
                epoch + 1, epochs, elapsed, avg_loss, val_acc, val_f1
            )

            if val_f1 > best_f1:
                best_f1 = val_f1
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                self.model.save_pretrained(out)
                self.tokenizer.save_pretrained(out)
                logger.info("Saved best Transformer model to %s", out)

        return {"val_accuracy": val_acc, "val_f1": best_f1}

    def evaluate(self, dataloader: DataLoader) -> Tuple[float, float, str]:
        """Evaluate model on a dataset loader."""
        self.model.eval()
        predictions = []
        true_labels = []

        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                preds = torch.argmax(outputs.logits, dim=1)
                predictions.extend(preds.cpu().numpy())
                true_labels.extend(labels.cpu().numpy())

        acc = accuracy_score(true_labels, predictions)
        f1 = f1_score(true_labels, predictions, average="macro", zero_division=0)
        report = classification_report(
            true_labels, predictions,
            target_names=["propaganda", "opinion", "neutral"],
            digits=4,
        )
        return acc, f1, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transformer Fine-Tuning for Content Detection")
    parser.add_argument("--dataset", type=str, default="datasets/full_3class_dataset.json", help="Path to dataset")
    parser.add_argument("--model_name", type=str, default="distilbert-base-uncased", help="HuggingFace model name")
    parser.add_argument("--output", type=str, default="models/transformer", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    args = parser.parse_args()

    detector = TransformerDetector(model_name=args.model_name)
    detector.train(
        dataset_path=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
