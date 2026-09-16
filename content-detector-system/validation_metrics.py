"""
Accuracy Validation & Metrics Suite
Evaluate system performance against labeled datasets
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from content_detector_api import ContentClassifier, ContentInput
from paid_promotion_filter import PaidPromotionFilter
from data_collection import AnnotatedContent, DatasetBuilder


# ============= METRICS DEFINITIONS =============

@dataclass
class ConfusionMatrix:
    """Confusion matrix for classification metrics"""
    true_positive: int = 0
    true_negative: int = 0
    false_positive: int = 0
    false_negative: int = 0
    
    def accuracy(self) -> float:
        """Overall accuracy"""
        total = self.true_positive + self.true_negative + self.false_positive + self.false_negative
        if total == 0:
            return 0.0
        return (self.true_positive + self.true_negative) / total
    
    def precision(self) -> float:
        """Precision (of positive predictions)"""
        total = self.true_positive + self.false_positive
        if total == 0:
            return 0.0
        return self.true_positive / total
    
    def recall(self) -> float:
        """Recall (sensitivity)"""
        total = self.true_positive + self.false_negative
        if total == 0:
            return 0.0
        return self.true_positive / total
    
    def f1_score(self) -> float:
        """F1 score (harmonic mean of precision and recall)"""
        p = self.precision()
        r = self.recall()
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
    
    def specificity(self) -> float:
        """Specificity (true negative rate)"""
        total = self.true_negative + self.false_positive
        if total == 0:
            return 0.0
        return self.true_negative / total


@dataclass
class ClassMetrics:
    """Metrics for a single class"""
    class_name: str
    confusion_matrix: ConfusionMatrix = field(default_factory=ConfusionMatrix)
    
    def __str__(self) -> str:
        cm = self.confusion_matrix
        return f"""
{self.class_name}:
  Accuracy:   {cm.accuracy():.1%}
  Precision:  {cm.precision():.1%}
  Recall:     {cm.recall():.1%}
  F1 Score:   {cm.f1_score():.1%}
  Specificity: {cm.specificity():.1%}
        """


@dataclass
class ValidationReport:
    """Complete validation report"""
    dataset_name: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_samples: int = 0
    total_correct: int = 0
    overall_accuracy: float = 0.0
    class_metrics: Dict[str, ClassMetrics] = field(default_factory=dict)
    per_platform_accuracy: Dict[str, float] = field(default_factory=dict)
    error_analysis: Dict[str, List[str]] = field(default_factory=dict)
    
    def save(self, path: str = "validation_reports") -> None:
        """Save report to file"""
        base = Path(path).resolve()
        base.mkdir(exist_ok=True)
        
        filename = f"validation_{self.dataset_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        filepath = (base / filename).resolve()
        if not str(filepath).startswith(str(base)):
            raise ValueError("Path traversal detected")
        
        report_data = {
            "dataset_name": self.dataset_name,
            "timestamp": self.timestamp,
            "total_samples": self.total_samples,
            "total_correct": self.total_correct,
            "overall_accuracy": self.overall_accuracy,
            "class_metrics": {
                name: {
                    "accuracy": metrics.confusion_matrix.accuracy(),
                    "precision": metrics.confusion_matrix.precision(),
                    "recall": metrics.confusion_matrix.recall(),
                    "f1_score": metrics.confusion_matrix.f1_score(),
                }
                for name, metrics in self.class_metrics.items()
            },
            "per_platform_accuracy": self.per_platform_accuracy,
            "error_analysis": self.error_analysis
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        # Export to reports/ directory as evaluation_v1.json and evaluation_v1.md
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        with open(reports_dir / "evaluation_v1.json", "w") as f:
            json.dump(report_data, f, indent=2)
            
        md_lines = [
            f"# Evaluation Report: {self.dataset_name}",
            f"**Timestamp**: {self.timestamp}  ",
            f"**Total Samples**: {self.total_samples}  ",
            f"**Overall Accuracy**: {self.overall_accuracy:.2%}  \n",
            "## Class Metrics",
            "| Class | Accuracy | Precision | Recall | F1-Score |",
            "|---|---|---|---|---|",
        ]
        for name, metrics in self.class_metrics.items():
            cm = metrics.confusion_matrix
            md_lines.append(f"| {name} | {cm.accuracy():.1%} | {cm.precision():.1%} | {cm.recall():.1%} | {cm.f1_score():.1%} |")

        md_lines.append("\n## Platform Breakdown")
        for plat, acc in self.per_platform_accuracy.items():
            md_lines.append(f"- **{plat}**: {acc:.1%}")

        with open(reports_dir / "evaluation_v1.md", "w") as f:
            f.write("\n".join(md_lines) + "\n")

        print(f"Validation report saved to: {filepath}")
        print(f"Exported reports/evaluation_v1.json and reports/evaluation_v1.md")


class AccuracyValidator:
    """Validate system accuracy against labeled dataset"""

    def _update_confusion_matrix(self, class_metrics, true_class, predicted_class):
        """Update confusion matrix for all classes based on prediction."""
        cm = class_metrics[true_class].confusion_matrix
        if predicted_class == true_class:
            cm.true_positive += 1
        else:
            cm.false_negative += 1
        for other_class in class_metrics:
            if other_class != true_class:
                cm_other = class_metrics[other_class].confusion_matrix
                if predicted_class == other_class:
                    cm_other.false_positive += 1
                else:
                    cm_other.true_negative += 1

    def __init__(self):
        self.classifier = ContentClassifier()
        self.promotion_filter = PaidPromotionFilter()
        self.report = None
    
    def validate_dataset(self, items: List[AnnotatedContent], 
                        dataset_name: str = "validation") -> ValidationReport:
        """Validate system against labeled items"""
        
        report = ValidationReport(dataset_name=dataset_name, total_samples=len(items))
        class_metrics = {}
        platform_accuracy = {}
        error_analysis = {}
        
        # Initialize metrics for each class
        for class_name in ["propaganda", "paid_campaign", "neutral", "mixed"]:
            class_metrics[class_name] = ClassMetrics(class_name)
        
        correct_predictions = 0
        platform_results = {}
        
        print(f"\nValidating {len(items)} items...")
        print("=" * 60)
        
        for i, item in enumerate(items):
            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{len(items)}")
            
            # Get prediction from system
            content = ContentInput(text=item.text)
            prediction = self.classifier.classify(content)
            predicted_class = prediction.classification
            
            # Compare with label
            is_correct = predicted_class == item.content_type or \
                        (predicted_class == "mixed" and item.content_type in ["propaganda", "paid_campaign"]) or \
                        (item.content_type == "mixed" and predicted_class in ["propaganda", "paid_campaign"])
            
            if is_correct:
                correct_predictions += 1
            
            # Update confusion matrix
            self._update_confusion_matrix(class_metrics, item.content_type, predicted_class)
            
            # Track platform accuracy
            platform = item.platform
            if platform not in platform_results:
                platform_results[platform] = {"correct": 0, "total": 0}
            platform_results[platform]["total"] += 1
            if is_correct:
                platform_results[platform]["correct"] += 1
            
            # Track errors
            if not is_correct:
                error_key = f"{item.content_type}→{predicted_class}"
                if error_key not in error_analysis:
                    error_analysis[error_key] = []
                error_analysis[error_key].append({
                    "text": item.text[:100],
                    "confidence": prediction.confidence,
                    "risk_score": prediction.risk_score
                })
        
        # Calculate per-platform accuracy
        for platform, results in platform_results.items():
            accuracy = results["correct"] / results["total"] if results["total"] > 0 else 0
            platform_accuracy[platform] = accuracy
        
        # Finalize report
        report.total_correct = correct_predictions
        report.overall_accuracy = correct_predictions / len(items) if items else 0
        report.class_metrics = class_metrics
        report.per_platform_accuracy = platform_accuracy
        report.error_analysis = error_analysis
        
        self.report = report
        return report
    
    def print_report(self) -> None:
        """Print formatted validation report"""
        if not self.report:
            print("No validation report generated yet")
            return
        
        report = self.report
        
        print("\n" + "=" * 70)
        print("VALIDATION REPORT")
        print("=" * 70)
        print(f"Dataset: {report.dataset_name}")
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Samples: {report.total_samples}")
        print(f"Correct Predictions: {report.total_correct}/{report.total_samples}")
        print(f"Overall Accuracy: {report.overall_accuracy:.1%}")
        print("=" * 70)
        
        print("\nPER-CLASS METRICS:")
        print("-" * 70)
        for class_name in ["propaganda", "paid_campaign", "neutral", "mixed"]:
            if class_name in report.class_metrics:
                print(report.class_metrics[class_name])
        
        print("\nPER-PLATFORM ACCURACY:")
        print("-" * 70)
        for platform, accuracy in sorted(report.per_platform_accuracy.items()):
            print(f"  {platform:15} {accuracy:.1%}")
        
        if report.error_analysis:
            print("\nTOP MISCLASSIFICATIONS:")
            print("-" * 70)
            for error_type, errors in list(report.error_analysis.items())[:5]:
                print(f"\n  {error_type} ({len(errors)} errors)")
                for error in errors[:2]:
                    print(f"    - Text: {error['text']}")
                    print(f"      Confidence: {error['confidence']:.1%}")
        
        print("\n" + "=" * 70)


class ComparisonValidator:
    """Compare system predictions with human judgments"""
    
    def __init__(self):
        self.classifier = ContentClassifier()
        self.promotion_filter = PaidPromotionFilter()
    
    def inter_annotator_agreement(self, annotations: List[Dict]) -> float:
        """
        Calculate agreement between multiple annotators (Cohen's Kappa)
        
        annotations format:
        [
            {"text": "...", "labels": ["label1", "label2", "label3"]},
            ...
        ]
        """
        from collections import Counter
        
        total_agreement = 0
        
        for annotation in annotations:
            labels = annotation.get("labels", [])
            if len(labels) < 2:
                continue
            
            # Count agreements
            label_counts = Counter(labels)
            most_common = label_counts.most_common(1)[0][0]
            agreements = label_counts[most_common]
            
            # Calculate agreement for this item
            item_agreement = (agreements - 1) / (len(labels) - 1)
            total_agreement += item_agreement
        
        avg_agreement = total_agreement / len(annotations) if annotations else 0
        return avg_agreement
    
    def system_vs_human_comparison(self, 
                                   system_predictions: List[Dict],
                                   human_labels: List[str]) -> Dict:
        """
        Compare system predictions against human consensus labels
        
        Returns agreement metrics and confusion analysis
        """
        
        if len(system_predictions) != len(human_labels):
            raise ValueError("Number of predictions must match number of labels")
        
        agreement = 0
        disagreements = []
        
        for pred, human_label in zip(system_predictions, human_labels):
            pred_class = pred["classification"]
            
            if pred_class == human_label:
                agreement += 1
            else:
                disagreements.append({
                    "system_prediction": pred_class,
                    "human_label": human_label,
                    "confidence": pred.get("confidence", 0),
                    "risk_score": pred.get("risk_score", 0)
                })
        
        agreement_rate = agreement / len(human_labels)
        
        return {
            "agreement_rate": agreement_rate,
            "agreement_count": agreement,
            "total_samples": len(human_labels),
            "disagreements": disagreements,
            "disagreement_rate": 1 - agreement_rate
        }


# ============= VALIDATION BENCHMARKS =============

class ValidationBenchmarks:
    """Standard benchmarks for success"""
    
    @staticmethod
    def get_benchmarks() -> Dict:
        return {
            "acceptable": {
                "overall_accuracy": 0.70,
                "propaganda_precision": 0.70,
                "propaganda_recall": 0.65,
                "campaign_precision": 0.70,
                "campaign_recall": 0.65,
                "neutral_accuracy": 0.80,
            },
            "good": {
                "overall_accuracy": 0.80,
                "propaganda_precision": 0.80,
                "propaganda_recall": 0.75,
                "campaign_precision": 0.80,
                "campaign_recall": 0.75,
                "neutral_accuracy": 0.90,
            },
            "excellent": {
                "overall_accuracy": 0.90,
                "propaganda_precision": 0.90,
                "propaganda_recall": 0.85,
                "campaign_precision": 0.90,
                "campaign_recall": 0.85,
                "neutral_accuracy": 0.95,
            }
        }
    
    @staticmethod
    def evaluate_against_benchmarks(report: ValidationReport) -> Dict:
        """Evaluate report against benchmarks"""
        benchmarks = ValidationBenchmarks.get_benchmarks()
        
        performance_level = None
        met_benchmarks = []
        failed_benchmarks = []
        
        # Extract key metrics
        metrics = {
            "overall_accuracy": report.overall_accuracy,
        }
        
        if "propaganda" in report.class_metrics:
            prop_cm = report.class_metrics["propaganda"].confusion_matrix
            metrics["propaganda_precision"] = prop_cm.precision()
            metrics["propaganda_recall"] = prop_cm.recall()
        
        if "paid_campaign" in report.class_metrics:
            camp_cm = report.class_metrics["paid_campaign"].confusion_matrix
            metrics["campaign_precision"] = camp_cm.precision()
            metrics["campaign_recall"] = camp_cm.recall()
        
        if "neutral" in report.class_metrics:
            neutral_cm = report.class_metrics["neutral"].confusion_matrix
            metrics["neutral_accuracy"] = neutral_cm.accuracy()
        
        # Check against benchmarks
        for level, threshold_dict in benchmarks.items():
            level_met = True
            for metric, threshold in threshold_dict.items():
                if metrics.get(metric, 0) < threshold:
                    level_met = False
                    failed_benchmarks.append((metric, metrics.get(metric, 0), threshold))
                else:
                    met_benchmarks.append((metric, metrics.get(metric, 0)))
            
            if level_met:
                performance_level = level
        
        return {
            "performance_level": performance_level or "below_acceptable",
            "met_benchmarks": met_benchmarks,
            "failed_benchmarks": failed_benchmarks,
            "current_metrics": metrics
        }


# ============= EXAMPLE USAGE =============

if __name__ == "__main__":
    from data_collection import SampleDataCollection
    
    print("=" * 70)
    print("ACCURACY VALIDATION")
    print("=" * 70)
    
    # Create sample validation dataset
    sample_data = []
    samples = SampleDataCollection()
    sample_data.extend(samples.get_propaganda_samples())
    sample_data.extend(samples.get_campaign_samples())
    sample_data.extend(samples.get_neutral_samples())
    sample_data.extend(samples.get_mixed_samples())
    
    # Validate system
    validator = AccuracyValidator()
    report = validator.validate_dataset(sample_data, dataset_name="sample_validation")
    
    # Print report
    validator.print_report()
    
    # Save report
    report.save()
    
    # Evaluate against benchmarks
    print("\nBENCHMARK EVALUATION:")
    print("-" * 70)
    benchmark_results = ValidationBenchmarks.evaluate_against_benchmarks(report)
    
    print(f"Performance Level: {benchmark_results['performance_level'].upper()}")
    print(f"\nMet Benchmarks ({len(benchmark_results['met_benchmarks'])}):")
    for metric, value in benchmark_results['met_benchmarks']:
        print(f"  ✓ {metric}: {value:.1%}")

    if benchmark_results['failed_benchmarks']:
        print(f"\nFailed Benchmarks ({len(benchmark_results['failed_benchmarks'])}):")
        for metric, value, threshold in benchmark_results['failed_benchmarks']:
            print(f"  ✗ {metric}: {value:.1%} (target: {threshold:.1%})")
