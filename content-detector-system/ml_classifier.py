"""
Advanced ML Classifier for content detection.

Features:
  - Dual TF-IDF vectorization (word n-grams + character n-grams)
  - 6 candidate models: NB, LR, SVM, RF, XGBoost, LightGBM
  - Ensemble voting (TF-IDF path + feature path)
  - Confidence calibration (Platt / Isotonic)
  - SHAP explainability
  - Error analysis with saved misclassifications

Usage:
    python ml_classifier.py --train --dataset datasets/your_data.json --output models/current
    python ml_classifier.py --evaluate --dataset datasets/your_data.json --model models/current
"""

import argparse
import json
import csv
import logging
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.sparse import hstack, csr_matrix, issparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import (
    RandomForestClassifier, VotingClassifier,
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, accuracy_score, f1_score,
    precision_score, recall_score, confusion_matrix,
)
from sklearn.preprocessing import LabelEncoder, MaxAbsScaler
from sklearn.pipeline import Pipeline
import joblib

from feature_extractor import FeatureExtractor, FEATURE_NAMES, ALL_FEATURE_NAMES, EMBEDDING_DIM

logger = logging.getLogger("ml_classifier")

# ============= OPTIONAL DEPS =============

try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False
    logger.info("xgboost not available — skipping XGBoost model")

try:
    from lightgbm import LGBMClassifier
    _HAS_LGB = True
except Exception:
    _HAS_LGB = False
    logger.info("lightgbm not available — skipping LightGBM model")

try:
    import shap
    _HAS_SHAP = True
except ImportError:
    _HAS_SHAP = False

# ============= CONSTANTS =============

LABELS = ["propaganda", "paid_campaign", "mixed", "neutral", "opinion"]  # Superset of supported class labels


class SparseNonNegativeScaler:
    """Ensures feature matrix is non-negative for MultinomialNB while preserving sparse format."""
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        if issparse(X):
            X_out = X.copy()
            X_out.data = np.maximum(0, X_out.data)
            return X_out
        return np.maximum(0, X)
    def fit_transform(self, X, y=None):
        return self.transform(X)


def _build_candidate_models() -> dict:
    """Build dict of candidate model factories, skipping unavailable ones."""
    models = {
        "naive_bayes": lambda: Pipeline([
            ("scaler", MaxAbsScaler()),
            ("non_neg", SparseNonNegativeScaler()),
            ("clf", MultinomialNB(alpha=0.1)),
        ]),
        "logistic_regression": lambda: LogisticRegression(
            max_iter=3000, class_weight="balanced", C=1.0,
            solver="lbfgs",
        ),
        "linear_svc": lambda: CalibratedClassifierCV(
            LinearSVC(max_iter=2000, class_weight="balanced", C=1.0),
            cv=3, method="sigmoid",
        ),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=200, class_weight="balanced",
            max_depth=None, random_state=42, n_jobs=1,
        ),
    }
    # NOTE: XGBoost/LightGBM disabled due to macOS multiprocessing deadlocks
    # with Python 3.13 + sparse matrices. Re-enable on Linux or when fixed.
    # if _HAS_XGB:
    #     models["xgboost"] = lambda: XGBClassifier(
    #         n_estimators=200, max_depth=6, learning_rate=0.1,
    #         eval_metric="mlogloss", random_state=42, n_jobs=1,
    #     )
    # if _HAS_LGB:
    #     models["lightgbm"] = lambda: LGBMClassifier(
    #         n_estimators=200, max_depth=6, learning_rate=0.1,
    #         class_weight="balanced", random_state=42,
    #         n_jobs=1, verbose=-1,
    #     )
    return models


# ============= DATA LOADING =============

def load_dataset(path: str) -> list[dict]:
    """
    Load labeled dataset from JSON or CSV.

    Expected fields:
        - text (str): Content text.
        - content_type (str): propaganda / paid_campaign / mixed / neutral.
        - platform (str, optional): Platform name.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if path.suffix == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            items = list(csv.DictReader(f))
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("items", [])

    valid = []
    for item in items:
        text = item.get("text", "").strip()
        label = item.get("content_type", "").strip().lower()
        if text and label in LABELS:
            valid.append({
                "text": text,
                "content_type": label,
                "platform": item.get("platform", "unknown"),
            })
        else:
            logger.warning("Skipping: text=%r label=%r", text[:40] if text else "", label)

    logger.info("Loaded %d valid items from %s (skipped %d)",
                len(valid), path, len(items) - len(valid))
    return valid


# ============= MODEL COMPARISON TABLE =============

def _print_comparison_table(results: dict):
    """Print a formatted model comparison table."""
    header = f"{'Model':<24} {'Accuracy':>10} {'F1-macro':>10} {'Precision':>10} {'Recall':>10} {'Time(s)':>10}"
    sep = "=" * len(header)
    print(f"\n{sep}")
    print("MODEL COMPARISON")
    print(sep)
    print(header)
    print("-" * len(header))

    # Sort by F1
    sorted_models = sorted(
        results.items(),
        key=lambda x: x[1].get("f1_macro", 0),
        reverse=True,
    )
    for name, metrics in sorted_models:
        if "error" in metrics:
            print(f"{name:<24} {'FAILED':>10}   {metrics['error'][:40]}")
        else:
            print(f"{name:<24} {metrics['accuracy']:>10.4f} {metrics['f1_macro']:>10.4f} "
                  f"{metrics['precision_macro']:>10.4f} {metrics['recall_macro']:>10.4f} "
                  f"{metrics.get('train_time', 0):>10.2f}")
    print(sep)


# ============= ERROR ANALYSIS =============

class ErrorAnalyzer:
    """Analyze and save misclassifications for systematic improvement."""

    def __init__(self, output_dir: str = "error_analysis"):
        self.output_dir = Path(output_dir)

    def analyze(self, y_true: list, y_pred: list,
                texts: list, platforms: list,
                label_names: list) -> dict:
        """
        Analyze errors, save false positives and false negatives per class.

        Returns summary dict.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        errors = {"total": len(y_true), "correct": 0, "wrong": 0, "per_class": {}}
        fp_dir = self.output_dir / "false_positives"
        fn_dir = self.output_dir / "false_negatives"
        fp_dir.mkdir(exist_ok=True)
        fn_dir.mkdir(exist_ok=True)

        # Collect errors per class
        class_fps = {c: [] for c in label_names}
        class_fns = {c: [] for c in label_names}

        for i, (true, pred) in enumerate(zip(y_true, y_pred)):
            if true == pred:
                errors["correct"] += 1
            else:
                errors["wrong"] += 1
                # False positive for predicted class
                class_fps[pred].append({
                    "text": texts[i][:500],
                    "true_label": true,
                    "predicted": pred,
                    "platform": platforms[i] if i < len(platforms) else "unknown",
                })
                # False negative for true class
                class_fns[true].append({
                    "text": texts[i][:500],
                    "true_label": true,
                    "predicted": pred,
                    "platform": platforms[i] if i < len(platforms) else "unknown",
                })

        # Save per-class error files
        for cls in label_names:
            if class_fps[cls]:
                with open(fp_dir / f"{cls}.json", "w") as f:
                    json.dump(class_fps[cls], f, indent=2)
            if class_fns[cls]:
                with open(fn_dir / f"{cls}.json", "w") as f:
                    json.dump(class_fns[cls], f, indent=2)

            errors["per_class"][cls] = {
                "false_positives": len(class_fps[cls]),
                "false_negatives": len(class_fns[cls]),
            }

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred, labels=label_names)
        errors["confusion_matrix"] = cm.tolist()

        # Save summary
        with open(self.output_dir / "error_summary.json", "w") as f:
            json.dump(errors, f, indent=2)

        print(f"\n📁 Error analysis saved to {self.output_dir}/")
        print(f"   Correct: {errors['correct']}/{errors['total']} "
              f"({errors['correct']/max(errors['total'],1):.1%})")
        print(f"   Errors:  {errors['wrong']}")

        return errors


# ============= SHAP EXPLAINER =============

class ModelExplainer:
    """Generate SHAP-based feature importance explanations."""

    def __init__(self, model, word_vectorizer, char_vectorizer,
                 feature_names: list, label_names: list):
        self.model = model
        self.word_vec = word_vectorizer
        self.char_vec = char_vectorizer
        self.feature_names = feature_names
        self.label_names = label_names
        self._explainer = None

    def _get_all_feature_names(self) -> list[str]:
        """Build full feature name list: word_tfidf + char_tfidf + engineered."""
        names = []
        if self.word_vec:
            names.extend([f"w:{w}" for w in self.word_vec.get_feature_names_out()])
        if self.char_vec:
            names.extend([f"c:{c}" for c in self.char_vec.get_feature_names_out()])
        names.extend(self.feature_names)
        return names

    def explain(self, text: str, X_features, prediction: dict,
                top_k: int = 10) -> dict:
        """
        Generate SHAP explanation for a single prediction.

        Returns dict with top contributing features.
        """
        if not _HAS_SHAP:
            return self._fallback_explain(X_features, prediction, top_k)

        try:
            # Choose appropriate SHAP explainer
            model = self.model
            # Unwrap CalibratedClassifierCV or Pipeline
            if hasattr(model, "estimator"):
                model = model.estimator
            if hasattr(model, "named_steps"):
                model = model.named_steps.get("clf", model)

            if hasattr(model, "feature_importances_"):
                # Tree-based: RF, XGBoost, LightGBM
                explainer = shap.TreeExplainer(model)
            elif hasattr(model, "coef_"):
                # Linear: LR, SVM
                if issparse(X_features):
                    X_dense = X_features.toarray()
                else:
                    X_dense = np.array(X_features)
                explainer = shap.LinearExplainer(model, X_dense)
            else:
                return self._fallback_explain(X_features, prediction, top_k)

            if issparse(X_features):
                shap_input = X_features.toarray()
            else:
                shap_input = np.array(X_features).reshape(1, -1)

            shap_values = explainer.shap_values(shap_input)

            # Get SHAP values for predicted class
            pred_idx = self.label_names.index(prediction["classification"])
            if isinstance(shap_values, list):
                sv = shap_values[pred_idx][0]
            else:
                sv = shap_values[0]

            all_names = self._get_all_feature_names()
            # Get top features by absolute SHAP value
            top_indices = np.argsort(np.abs(sv))[-top_k:][::-1]

            top_features = []
            for idx in top_indices:
                name = all_names[idx] if idx < len(all_names) else f"feature_{idx}"
                top_features.append({
                    "feature": name,
                    "impact": round(float(sv[idx]), 4),
                })

            return {
                "classification": prediction["classification"],
                "confidence": prediction["confidence"],
                "top_features": top_features,
                "method": "shap",
            }

        except Exception as e:
            logger.warning("SHAP explanation failed: %s", e)
            return self._fallback_explain(X_features, prediction, top_k)

    def _fallback_explain(self, X_features, prediction: dict,
                          top_k: int = 10) -> dict:
        """Fallback: use feature importances or coefficients if available."""
        model = self.model
        if hasattr(model, "estimator"):
            model = model.estimator

        all_names = self._get_all_feature_names()

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            pred_idx = self.label_names.index(prediction["classification"])
            importances = np.abs(model.coef_[pred_idx]) if model.coef_.ndim > 1 else np.abs(model.coef_[0])
        else:
            return {
                "classification": prediction["classification"],
                "confidence": prediction["confidence"],
                "top_features": [],
                "method": "none",
            }

        top_indices = np.argsort(importances)[-top_k:][::-1]
        top_features = []
        for idx in top_indices:
            name = all_names[idx] if idx < len(all_names) else f"feature_{idx}"
            top_features.append({
                "feature": name,
                "impact": round(float(importances[idx]), 4),
            })

        return {
            "classification": prediction["classification"],
            "confidence": prediction["confidence"],
            "top_features": top_features,
            "method": "feature_importance",
        }


# ============= ML CLASSIFIER =============

class ContentMLClassifier:
    """
    Advanced hybrid ML classifier:
      - Dual TF-IDF (word + char n-grams)
      - 70+ engineered features
      - 6 candidate models (NB, LR, SVM, RF, XGBoost, LightGBM)
      - Ensemble voting
      - Confidence calibration
      - SHAP explainability
      - Error analysis
    """

    def __init__(self):
        self.word_vectorizer: Optional[TfidfVectorizer] = None
        self.char_vectorizer: Optional[TfidfVectorizer] = None
        self.model = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.feature_extractor = FeatureExtractor()
        self.explainer: Optional[ModelExplainer] = None
        self._is_loaded = False

    # ---------- Feature building ----------

    def _build_features(self, texts: list[str],
                        platforms: list[str],
                        fit: bool = False) -> csr_matrix:
        """
        Build combined feature matrix:
          Word TF-IDF + Char TF-IDF + Engineered features.

        Total dimensions: ~5000 + ~3000 + ~70 = ~8070
        """
        # --- Word-level TF-IDF (semantic content) ---
        if fit:
            self.word_vectorizer = TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=5000,
                min_df=2,
                max_df=0.95,
                sublinear_tf=True,
                strip_accents="unicode",
            )
            word_matrix = self.word_vectorizer.fit_transform(texts)
        else:
            word_matrix = self.word_vectorizer.transform(texts)

        # --- Character-level TF-IDF (formatting patterns) ---
        if fit:
            self.char_vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                max_features=3000,
                min_df=2,
                max_df=0.95,
                sublinear_tf=True,
            )
            char_matrix = self.char_vectorizer.fit_transform(texts)
        else:
            char_matrix = self.char_vectorizer.transform(texts)

        # --- Engineered features (75 handcrafted + 384 embedding dims) ---
        rule_features = self.feature_extractor.extract_batch_with_embeddings(texts, platforms)
        rule_matrix = csr_matrix(np.array(rule_features, dtype=np.float32))

        # Combine all three
        return hstack([word_matrix, char_matrix, rule_matrix])

    # ---------- Training ----------

    def train(self, dataset_path: str, output_dir: str = "models/current") -> dict:
        """
        Full training pipeline:
          1. Load data, build features
          2. Train 6 candidate models
          3. Print comparison table
          4. Build ensemble from top 2
          5. Calibrate probabilities
          6. Run error analysis
          7. Save everything
        """
        items = load_dataset(dataset_path)
        if len(items) < 10:
            raise ValueError(f"Need at least 10 labeled items, got {len(items)}")

        texts = [item["text"] for item in items]
        platforms = [item.get("platform", "unknown") for item in items]
        labels = [item["content_type"] for item in items]

        # Label encoding — fit on actual classes in the dataset
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(labels)
        y = self.label_encoder.transform(labels)
        label_names = list(self.label_encoder.classes_)
        print(f"   Classes found: {label_names}")

        # Build features
        print("⚙️  Building features (word TF-IDF + char TF-IDF + 70+ engineered)...")
        X = self._build_features(texts, platforms, fit=True)
        print(f"   Feature matrix: {X.shape[0]} samples × {X.shape[1]} features")
        eng_count = len(FEATURE_NAMES) + EMBEDDING_DIM
        print(f"   ({self.word_vectorizer.max_features} word TF-IDF + "
              f"{self.char_vectorizer.max_features} char TF-IDF + "
              f"{len(FEATURE_NAMES)} engineered + {EMBEDDING_DIM} embedding)\n")

        # Split
        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            X, y, np.arange(len(texts)),
            test_size=0.2, stratify=y, random_state=42,
        )

        # ---- Train all candidate models ----
        candidates = _build_candidate_models()
        model_results = {}
        trained_models = {}

        for name, factory in candidates.items():
            print(f"  Training {name}...", end="", flush=True)
            try:
                t0 = time.time()
                model = factory()
                X_tr, X_te = X_train, X_test

                model.fit(X_tr, y_train)
                y_pred = model.predict(X_te)
                elapsed = time.time() - t0

                metrics = {
                    "accuracy": round(accuracy_score(y_test, y_pred), 4),
                    "f1_macro": round(f1_score(y_test, y_pred, average="macro", zero_division=0), 4),
                    "precision_macro": round(precision_score(y_test, y_pred, average="macro", zero_division=0), 4),
                    "recall_macro": round(recall_score(y_test, y_pred, average="macro", zero_division=0), 4),
                    "train_time": round(elapsed, 2),
                }
                model_results[name] = metrics
                trained_models[name] = model
                print(f"  ✓  F1={metrics['f1_macro']:.4f}  Acc={metrics['accuracy']:.4f}  ({elapsed:.1f}s)")

            except Exception as e:
                model_results[name] = {"error": str(e)}
                print(f"  ✗  {e}")

        if not trained_models:
            raise RuntimeError("All candidate models failed.")

        # Print comparison table
        _print_comparison_table(model_results)

        # ---- Select best model and build ensemble ----
        sorted_models = sorted(
            trained_models.items(),
            key=lambda x: model_results[x[0]].get("f1_macro", 0),
            reverse=True,
        )
        best_name, best_model = sorted_models[0]
        best_f1 = model_results[best_name]["f1_macro"]

        # Try ensemble if we have 2+ successful models
        if len(sorted_models) >= 2:
            print("\n🔗 Building ensemble from top models...")
            try:
                top_models = sorted_models[:min(3, len(sorted_models))]
                # Ensure all ensemble members support predict_proba
                ensemble_estimators = []
                for mname, mmodel in top_models:
                    if mname == "naive_bayes":
                        continue  # NB needs dense input, skip for ensemble
                    if hasattr(mmodel, "predict_proba"):
                        ensemble_estimators.append((mname, mmodel))
                    elif hasattr(mmodel, "decision_function"):
                        # Wrap with calibration for proba support
                        cal_model = CalibratedClassifierCV(mmodel, cv=3, method="sigmoid")
                        cal_model.fit(X_train, y_train)
                        ensemble_estimators.append((mname, cal_model))

                if len(ensemble_estimators) >= 2:
                    ensemble = VotingClassifier(
                        estimators=ensemble_estimators,
                        voting="soft",
                    )
                    # VotingClassifier with prefit estimators
                    ensemble.estimators_ = [m for _, m in ensemble_estimators]
                    ensemble.le_ = LabelEncoder().fit(y_train)
                    ensemble.classes_ = ensemble.le_.classes_

                    y_ens = ensemble.predict(X_test)
                    ens_f1 = f1_score(y_test, y_ens, average="macro", zero_division=0)
                    ens_acc = accuracy_score(y_test, y_ens)

                    print(f"   Ensemble F1={ens_f1:.4f}  Acc={ens_acc:.4f}")
                    model_results["ensemble"] = {
                        "accuracy": round(ens_acc, 4),
                        "f1_macro": round(ens_f1, 4),
                        "precision_macro": round(precision_score(y_test, y_ens, average="macro", zero_division=0), 4),
                        "recall_macro": round(recall_score(y_test, y_ens, average="macro", zero_division=0), 4),
                    }

                    if ens_f1 > best_f1:
                        best_model = ensemble
                        best_name = "ensemble"
                        best_f1 = ens_f1
                        print(f"   ✓ Ensemble beats individual models!")
                    else:
                        print(f"   → Keeping {best_name} (F1={best_f1:.4f} > ensemble {ens_f1:.4f})")
                else:
                    print("   → Not enough models with proba support for ensemble")

            except Exception as e:
                logger.warning("Ensemble failed: %s", e)
                print(f"   → Ensemble failed: {e}")

        # ---- Confidence calibration ----
        if not isinstance(best_model, (CalibratedClassifierCV, VotingClassifier)):
            if hasattr(best_model, "predict_proba"):
                print("\n🎯 Calibrating probabilities (isotonic regression)...")
                try:
                    calibrated = CalibratedClassifierCV(
                        best_model, cv=3, method="isotonic",
                    )
                    calibrated.fit(X_train, y_train)
                    best_model = calibrated
                    print("   ✓ Calibration complete")
                except Exception as e:
                    logger.warning("Calibration failed: %s", e)

        self.model = best_model
        self._is_loaded = True

        # ---- Final evaluation ----
        y_pred = self.model.predict(X_test)
        # Use only classes actually present in the data
        actual_labels = list(self.label_encoder.classes_)
        report_str = classification_report(
            y_test, y_pred, target_names=actual_labels, zero_division=0,
        )
        report_dict = classification_report(
            y_test, y_pred, target_names=actual_labels,
            output_dict=True, zero_division=0,
        )

        print(f"\n{'=' * 60}")
        print(f"BEST MODEL: {best_name}  (F1-macro: {best_f1:.4f})")
        print("=" * 60)
        print(report_str)
        print("=" * 60)

        # ---- Error analysis ----
        print("\n🔍 Running error analysis...")
        test_texts = [texts[i] for i in idx_test]
        test_platforms = [platforms[i] for i in idx_test]
        pred_labels = [actual_labels[p] for p in y_pred]
        true_labels = [actual_labels[t] for t in y_test]

        analyzer = ErrorAnalyzer(output_dir=str(Path(output_dir) / "error_analysis"))
        error_results = analyzer.analyze(
            true_labels, pred_labels, test_texts, test_platforms, actual_labels,
        )

        # ---- Initialize explainer ----
        self.explainer = ModelExplainer(
            self.model, self.word_vectorizer, self.char_vectorizer,
            FEATURE_NAMES, actual_labels,
        )

        # Save
        self.save_model(output_dir)

        return {
            "best_model": best_name,
            "best_f1_macro": round(best_f1, 4),
            "candidate_results": model_results,
            "test_report": report_dict,
            "dataset_size": len(items),
            "train_size": X_train.shape[0],
            "test_size": X_test.shape[0],
            "feature_count": X_train.shape[1],
            "word_tfidf_features": self.word_vectorizer.max_features,
            "char_tfidf_features": self.char_vectorizer.max_features,
            "engineered_features": len(FEATURE_NAMES),
            "error_analysis": error_results,
        }

    # ---------- Prediction ----------

    def predict(self, text: str, platform: Optional[str] = None) -> dict:
        """
        Predict classification for a single text.

        Returns:
            {
                "classification": str,
                "confidence": float,  # Calibrated probability
                "class_probabilities": {class_name: prob, ...}
            }
        """
        if not self._is_loaded:
            raise RuntimeError("No model loaded. Call load_model() or train() first.")

        X = self._build_features([text], [platform or "unknown"])

        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X)[0]
        else:
            pred = self.model.predict(X)[0]
            probs = np.zeros(len(self.label_encoder.classes_))
            probs[pred] = 1.0

        label_names = self.label_encoder.classes_
        class_probs = {name: round(float(p), 4) for name, p in zip(label_names, probs)}

        pred_idx = int(np.argmax(probs))
        return {
            "classification": label_names[pred_idx],
            "confidence": round(float(probs[pred_idx]), 4),
            "class_probabilities": class_probs,
        }

    def predict_batch(self, texts: list[str],
                      platforms: Optional[list[str]] = None) -> list[dict]:
        """Batch prediction for efficiency."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")

        if platforms is None:
            platforms = ["unknown"] * len(texts)

        X = self._build_features(texts, platforms)

        if hasattr(self.model, "predict_proba"):
            all_probs = self.model.predict_proba(X)
        else:
            preds = self.model.predict(X)
            all_probs = np.zeros((len(texts), len(self.label_encoder.classes_)))
            for i, p in enumerate(preds):
                all_probs[i, p] = 1.0

        label_names = self.label_encoder.classes_
        results = []
        for probs in all_probs:
            class_probs = {n: round(float(p), 4) for n, p in zip(label_names, probs)}
            pred_idx = int(np.argmax(probs))
            results.append({
                "classification": label_names[pred_idx],
                "confidence": round(float(probs[pred_idx]), 4),
                "class_probabilities": class_probs,
            })
        return results

    def explain_prediction(self, text: str, platform: Optional[str] = None,
                           top_k: int = 10) -> dict:
        """Get SHAP explanation for a prediction."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")

        X = self._build_features([text], [platform or "unknown"])
        prediction = self.predict(text, platform)

        if self.explainer is None:
            label_names = list(self.label_encoder.classes_)
            self.explainer = ModelExplainer(
                self.model, self.word_vectorizer, self.char_vectorizer,
                FEATURE_NAMES, label_names,
            )

        return self.explainer.explain(text, X, prediction, top_k=top_k)

    # ---------- Model I/O ----------

    def save_model(self, output_dir: str = "models/current"):
        """Save all model artifacts."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, out / "model.joblib")
        joblib.dump(self.word_vectorizer, out / "word_vectorizer.joblib")
        joblib.dump(self.char_vectorizer, out / "char_vectorizer.joblib")
        joblib.dump(self.label_encoder, out / "label_encoder.joblib")

        meta = {
            "feature_names": FEATURE_NAMES,
            "labels": list(self.label_encoder.classes_),
            "word_tfidf_features": self.word_vectorizer.max_features,
            "char_tfidf_features": self.char_vectorizer.max_features,
            "engineered_features": len(FEATURE_NAMES),
            "model_type": type(self.model).__name__,
        }
        with open(out / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        logger.info("Model saved to %s", out)
        print(f"\n✓ Model saved to {out}/")

    def load_model(self, model_dir: str = "models/current") -> bool:
        """Load a previously trained model."""
        p = Path(model_dir)
        # Support both old (single vectorizer) and new (dual vectorizer) formats
        if (p / "word_vectorizer.joblib").exists():
            required = ["model.joblib", "word_vectorizer.joblib",
                         "char_vectorizer.joblib", "label_encoder.joblib"]
        elif (p / "vectorizer.joblib").exists():
            required = ["model.joblib", "vectorizer.joblib", "label_encoder.joblib"]
        else:
            self._is_loaded = False
            return False

        if not all((p / f).exists() for f in required):
            self._is_loaded = False
            return False

        self.model = joblib.load(p / "model.joblib")
        self.label_encoder = joblib.load(p / "label_encoder.joblib")

        if (p / "word_vectorizer.joblib").exists():
            self.word_vectorizer = joblib.load(p / "word_vectorizer.joblib")
            self.char_vectorizer = joblib.load(p / "char_vectorizer.joblib")
        else:
            # Legacy: single vectorizer format
            self.word_vectorizer = joblib.load(p / "vectorizer.joblib")
            self.char_vectorizer = None

        self._is_loaded = True
        logger.info("Model loaded from %s (type: %s)", p, type(self.model).__name__)
        return True

    def _build_features_compat(self, texts, platforms, fit=False):
        """Build features compatible with both old and new model formats."""
        if self.char_vectorizer is not None:
            return self._build_features(texts, platforms, fit)
        else:
            # Legacy: single vectorizer
            word_matrix = self.word_vectorizer.transform(texts)
            rule_features = self.feature_extractor.extract_batch(texts, platforms)
            rule_matrix = csr_matrix(np.array(rule_features, dtype=np.float64))
            return hstack([word_matrix, rule_matrix])

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded


# ============= CLI =============

def main():
    parser = argparse.ArgumentParser(
        description="Train or evaluate the content detection ML model.",
    )
    parser.add_argument("--train", action="store_true", help="Train a new model")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate existing model")
    parser.add_argument("--explain", type=str, default=None,
                        help="Explain a prediction for given text")
    parser.add_argument("--dataset", type=str, help="Path to labeled dataset (JSON/CSV)")
    parser.add_argument("--output", type=str, default="models/current",
                        help="Output directory for model")
    parser.add_argument("--model", type=str, default="models/current",
                        help="Model directory for eval/explain")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    clf = ContentMLClassifier()

    if args.train:
        if not args.dataset:
            print("❌ --dataset is required for training")
            return
        print(f"\n🚀 Training advanced ML pipeline on: {args.dataset}")
        print(f"   Output: {args.output}\n")
        results = clf.train(args.dataset, args.output)
        print(f"\n✅ Training complete!")
        print(f"   Best model:   {results['best_model']}")
        print(f"   F1 (macro):   {results['best_f1_macro']}")
        print(f"   Dataset:      {results['dataset_size']} items")
        print(f"   Features:     {results['feature_count']} total")
        print(f"     Word TF-IDF:  {results['word_tfidf_features']}")
        print(f"     Char TF-IDF:  {results['char_tfidf_features']}")
        print(f"     Engineered:   {results['engineered_features']}")

    elif args.evaluate:
        if not args.dataset:
            print("❌ --dataset is required for evaluation")
            return
        if not clf.load_model(args.model):
            print(f"❌ No model found at {args.model}")
            return

        items = load_dataset(args.dataset)
        texts = [item["text"] for item in items]
        platforms = [item.get("platform", "unknown") for item in items]
        true_labels = [item["content_type"] for item in items]
        predictions = clf.predict_batch(texts, platforms)
        pred_labels = [p["classification"] for p in predictions]

        print("\n" + "=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        print(classification_report(true_labels, pred_labels, zero_division=0))
        print(f"Accuracy: {accuracy_score(true_labels, pred_labels):.4f}")
        print("=" * 60)

    elif args.explain:
        if not clf.load_model(args.model):
            print(f"❌ No model found at {args.model}")
            return

        explanation = clf.explain_prediction(args.explain)
        print(f"\n📊 Prediction: {explanation['classification']} "
              f"({explanation['confidence']:.1%} confidence)")
        print(f"\nTop contributing features:")
        for feat in explanation.get("top_features", []):
            sign = "+" if feat["impact"] > 0 else ""
            print(f"   {feat['feature']:<30} {sign}{feat['impact']:.4f}")


if __name__ == "__main__":
    main()
