"""
Feedback Training Module — Continuous Learning Loop.

Allows new user-submitted text+label pairs to be:
  1. Stored persistently in the training dataset
  2. Used to retrain the model on the expanded dataset

Usage (CLI):
    # Add a single sample
    python feedback_trainer.py --add --text "Some text..." --label propaganda

    # Add and immediately retrain
    python feedback_trainer.py --add --text "Some text..." --label opinion --retrain

    # Bulk-add from a JSON file  [{"text": "...", "label": "..."}]
    python feedback_trainer.py --bulk-add feedback_entries.json

    # Retrain on the full updated dataset
    python feedback_trainer.py --retrain

    # Show dataset stats
    python feedback_trainer.py --stats

Usage (Python API):
    from feedback_trainer import FeedbackTrainer
    ft = FeedbackTrainer()
    ft.add_entry("Some new text", "propaganda")
    ft.retrain()
"""

import argparse
import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("feedback_trainer")

# Hardcoded paths — never constructed from user input
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATASET = os.path.join(_BASE_DIR, "datasets", "full_3class_dataset.json")
_FEEDBACK_LOG = os.path.join(_BASE_DIR, "datasets", "feedback_log.jsonl")
_DEFAULT_MODEL_DIR = os.path.join(_BASE_DIR, "models", "v3")

VALID_LABELS = {"propaganda", "opinion", "neutral"}


class FeedbackTrainer:
    """
    Manages user-submitted training entries and triggers model retraining.

    Each new entry is:
      1. Appended to the master dataset (full_3class_dataset.json)
      2. Logged to a separate feedback audit trail (feedback_log.jsonl)
    """

    def __init__(
        self,
        dataset_path: str = _DEFAULT_DATASET,
        model_dir: str = _DEFAULT_MODEL_DIR,
        feedback_log_path: str = _FEEDBACK_LOG,
    ):
        self.dataset_path = Path(dataset_path)
        self.model_dir = model_dir
        self.feedback_log_path = Path(feedback_log_path)
        self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Core: Add entries
    # ------------------------------------------------------------------ #

    def add_entry(
        self,
        text: str,
        label: str,
        platform: str = "user_feedback",
        source: Optional[str] = None,
    ) -> dict:
        """
        Add a single text+label pair to the dataset and the feedback log.

        Args:
            text:     The content text.
            label:    One of 'propaganda', 'opinion', 'neutral'.
            platform: Source platform tag (default: 'user_feedback').
            source:   Optional free-text source note.

        Returns:
            The stored entry dict.
        """
        label = label.strip().lower()
        if label not in VALID_LABELS:
            raise ValueError(
                f"Invalid label '{label}'. Must be one of: {', '.join(sorted(VALID_LABELS))}"
            )

        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty.")

        entry = {
            "text": text,
            "content_type": label,
            "platform": platform,
        }

        # 1. Append to master dataset
        self._append_to_dataset(entry)

        # 2. Write to feedback audit log (JSONL — one entry per line)
        log_record = {
            **entry,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "source": source or "manual",
        }
        with open(self.feedback_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_record) + "\n")

        logger.info(
            "✓ Added entry [%s] (%d chars) → dataset now has %d items",
            label,
            len(text),
            self._dataset_size(),
        )
        return log_record

    def add_entries_bulk(self, entries: list[dict]) -> int:
        """
        Add multiple entries at once.

        Each entry must have 'text' and 'label' keys.
        Returns the number of successfully added entries.
        """
        added = 0
        for entry in entries:
            try:
                self.add_entry(
                    text=entry["text"],
                    label=entry["label"],
                    platform=entry.get("platform", "user_feedback"),
                    source=entry.get("source", "bulk_import"),
                )
                added += 1
            except (ValueError, KeyError) as e:
                logger.warning("Skipped entry: %s", e)
        return added

    # ------------------------------------------------------------------ #
    #  Core: Retrain
    # ------------------------------------------------------------------ #

    def retrain(self) -> dict:
        """
        Retrain the model on the full (expanded) dataset.

        Returns the training results dict from ContentMLClassifier.train().
        """
        from ml_classifier import ContentMLClassifier

        logger.info("🚀 Retraining model on updated dataset: %s", self.dataset_path)
        clf = ContentMLClassifier()
        results = clf.train(str(self.dataset_path), self.model_dir)

        logger.info(
            "✅ Retrain complete — Best: %s | F1: %.4f | Dataset: %d items",
            results["best_model"],
            results["best_f1_macro"],
            results["dataset_size"],
        )
        return results

    # ------------------------------------------------------------------ #
    #  Stats & Utilities
    # ------------------------------------------------------------------ #

    def get_stats(self) -> dict:
        """Return dataset statistics."""
        dataset = self._load_dataset()
        class_counts = Counter(item["content_type"] for item in dataset)
        total = len(dataset)

        # Count feedback entries
        feedback_count = 0
        if self.feedback_log_path.exists():
            with open(self.feedback_log_path, "r", encoding="utf-8") as f:
                feedback_count = sum(1 for _ in f)

        return {
            "total_samples": total,
            "class_distribution": dict(class_counts.most_common()),
            "class_percentages": {
                cls: round(count / total * 100, 1) if total > 0 else 0
                for cls, count in class_counts.items()
            },
            "user_feedback_entries": feedback_count,
            "dataset_path": str(self.dataset_path),
            "model_dir": self.model_dir,
        }

    def print_stats(self) -> None:
        """Print formatted dataset statistics."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("DATASET STATISTICS")
        print("=" * 60)
        print(f"Total Samples:          {stats['total_samples']:,}")
        print(f"User Feedback Entries:  {stats['user_feedback_entries']:,}")
        print(f"\nClass Distribution:")
        for cls, count in stats["class_distribution"].items():
            pct = stats["class_percentages"][cls]
            print(f"  • {cls:<12}: {count:>6,}  ({pct:.1f}%)")
        print(f"\nDataset Path: {stats['dataset_path']}")
        print(f"Model Dir:    {stats['model_dir']}")
        print("=" * 60 + "\n")

    def get_feedback_history(self, last_n: int = 20) -> list[dict]:
        """Return the last N feedback entries from the audit log."""
        if not self.feedback_log_path.exists():
            return []
        entries = []
        with open(self.feedback_log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-last_n:]

    def predict_and_add(
        self, text: str, correct_label: str, platform: str = "user_feedback"
    ) -> dict:
        """
        Predict the label for a text, show the result, then store
        the user-provided correct label for future training.

        Returns dict with prediction, correct label, and match status.
        """
        from ml_classifier import ContentMLClassifier

        clf = ContentMLClassifier()
        clf.load_model(self.model_dir)
        prediction = clf.predict(text)

        # Store the correct label
        entry = self.add_entry(text, correct_label, platform)

        predicted = prediction["classification"]
        confidence = prediction["confidence"]
        is_correct = predicted == correct_label

        result = {
            "text_snippet": text[:80] + ("..." if len(text) > 80 else ""),
            "predicted_label": predicted,
            "predicted_confidence": confidence,
            "correct_label": correct_label,
            "was_correct": is_correct,
            "stored": True,
        }

        if is_correct:
            logger.info(
                "✓ Model predicted correctly: %s (%.1f%%) — stored for reinforcement",
                predicted,
                confidence * 100,
            )
        else:
            logger.info(
                "✗ Model predicted %s (%.1f%%) but correct is %s — stored for correction",
                predicted,
                confidence * 100,
                correct_label,
            )
        return result

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _load_dataset(self) -> list[dict]:
        if not self.dataset_path.exists():
            return []
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _append_to_dataset(self, entry: dict) -> None:
        dataset = self._load_dataset()
        dataset.append(entry)
        with open(self.dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

    def _dataset_size(self) -> int:
        if not self.dataset_path.exists():
            return 0
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return len(json.load(f))


# ================================================================== #
#  CLI
# ================================================================== #

def main():
    parser = argparse.ArgumentParser(
        description="Feedback Training — add entries to dataset and retrain"
    )
    parser.add_argument("--add", action="store_true", help="Add a single entry")
    parser.add_argument("--text", type=str, help="Text content to add")
    parser.add_argument(
        "--label",
        type=str,
        choices=sorted(VALID_LABELS),
        help="Correct label for the text",
    )
    parser.add_argument("--platform", type=str, default="user_feedback", help="Platform tag")
    parser.add_argument("--bulk-add", type=str, metavar="FILE", help="Bulk-add from JSON file")
    parser.add_argument("--retrain", action="store_true", help="Retrain model on updated dataset")
    parser.add_argument("--stats", action="store_true", help="Show dataset statistics")
    parser.add_argument("--history", action="store_true", help="Show recent feedback entries")
    parser.add_argument(
        "--predict-and-add",
        action="store_true",
        help="Predict, then store correct label",
    )
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL_DIR, help="Model directory")
    parser.add_argument(
        "--dataset",
        type=str,
        default=_DEFAULT_DATASET,
        help="Dataset path",
    )
    args = parser.parse_args()

    ft = FeedbackTrainer(dataset_path=args.dataset, model_dir=args.model)

    if args.add:
        if not args.text or not args.label:
            print("❌ --text and --label are required with --add")
            return
        result = ft.add_entry(args.text, args.label, args.platform)
        print(f"✓ Stored: [{result['content_type']}] '{result['text'][:60]}...'")

        if args.retrain:
            ft.retrain()

    elif args.bulk_add:
        with open(args.bulk_add, "r", encoding="utf-8") as f:
            entries = json.load(f)
        added = ft.add_entries_bulk(entries)
        print(f"✓ Added {added}/{len(entries)} entries to dataset")

        if args.retrain:
            ft.retrain()

    elif args.predict_and_add:
        if not args.text or not args.label:
            print("❌ --text and --label are required with --predict-and-add")
            return
        result = ft.predict_and_add(args.text, args.label)
        status = "✓ CORRECT" if result["was_correct"] else "✗ WRONG"
        print(f"\n{status}")
        print(f"  Predicted: {result['predicted_label']} ({result['predicted_confidence']:.1%})")
        print(f"  Correct:   {result['correct_label']}")
        print(f"  Stored for future training: Yes")

    elif args.retrain:
        ft.retrain()

    elif args.stats:
        ft.print_stats()

    elif args.history:
        history = ft.get_feedback_history()
        if not history:
            print("No feedback entries yet.")
            return
        print(f"\n{'='*70}")
        print(f"LAST {len(history)} FEEDBACK ENTRIES")
        print(f"{'='*70}")
        for i, entry in enumerate(history, 1):
            print(
                f"  {i}. [{entry['content_type']}] "
                f"'{entry['text'][:50]}...'  ({entry.get('added_at', 'N/A')})"
            )
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
