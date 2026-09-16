"""
Master Validation Orchestrator
Unified testing and validation pipeline
"""

import sys
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

# Import all testing components
from test_suite import (
    TestPropagandaDetector, TestPaidCampaignDetector,
    TestPaidPromotionFilter, TestContentClassifierIntegration,
    TestValidationMetrics, TestPerformance, run_all_tests
)
from data_collection import DatasetBuilder, SampleDataCollection, DataCollectionGuide
from validation_metrics import AccuracyValidator, ValidationBenchmarks


BASE_REPORT_DIR = Path("validation_results").resolve()

def _safe_report_path(filename: str) -> Path:
    """Ensure report path stays within base report directory."""
    resolved = (BASE_REPORT_DIR / filename).resolve()
    if not str(resolved).startswith(str(BASE_REPORT_DIR) + "/"):
        raise ValueError(f"Path traversal detected: {filename}")
    return resolved


class ValidationOrchestrator:
    """Master orchestrator for complete validation pipeline"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "unit_tests": None,
            "integration_tests": None,
            "validation_report": None,
            "benchmark_evaluation": None,
            "summary": None
        }
    
    def run_unit_tests(self) -> bool:
        """Run all unit tests"""
        print("\n" + "=" * 70)
        print("PHASE 1: UNIT TESTS")
        print("=" * 70)
        
        try:
            success = run_all_tests()
            self.results["unit_tests"] = {"passed": success}
            
            if success:
                print("✓ Unit tests PASSED")
            else:
                print("✗ Unit tests FAILED")
            
            return success
        
        except Exception as e:
            print(f"✗ Unit tests ERROR: {e}")
            self.results["unit_tests"] = {"passed": False, "error": str(e)}
            return False
    
    def generate_sample_dataset(self) -> Path:
        """Generate sample dataset for validation"""
        print("\n" + "=" * 70)
        print("PHASE 2: DATA PREPARATION")
        print("=" * 70)
        
        # Create dataset builder
        builder = DatasetBuilder("validation_sample")
        
        # Add sample data
        samples = SampleDataCollection()
        for item in samples.get_propaganda_samples():
            builder.add_item(item)
        for item in samples.get_campaign_samples():
            builder.add_item(item)
        for item in samples.get_neutral_samples():
            builder.add_item(item)
        for item in samples.get_mixed_samples():
            builder.add_item(item)
        
        # Save dataset
        builder.save_dataset(format="json")
        builder.print_statistics()
        
        dataset_path = Path("datasets") / "validation_sample" / "validation_sample.json"
        print(f"✓ Sample dataset created: {dataset_path}")
        
        return dataset_path
    
    def run_accuracy_validation(self, dataset_path: Optional[Path] = None) -> bool:
        """Run accuracy validation against dataset"""
        print("\n" + "=" * 70)
        print("PHASE 3: ACCURACY VALIDATION")
        print("=" * 70)
        
        try:
            if dataset_path is None:
                # Use sample dataset
                dataset_path = Path("datasets/validation_sample/validation_sample.json")
            
            if not dataset_path.exists():
                print(f"✗ Dataset not found: {dataset_path}")
                print("  Generating sample dataset...")
                dataset_path = self.generate_sample_dataset()
            
            # Load dataset from fixed known path inside datasets/
            _ds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
            _ds_file = os.path.join(_ds_dir, "validation_sample", "dataset.json")
            with open(_ds_file, 'r') as f:
                items_data = json.load(f)
            
            from data_collection import AnnotatedContent
            items = [AnnotatedContent(**item) for item in items_data]
            
            # Run validation
            validator = AccuracyValidator()
            report = validator.validate_dataset(items, dataset_name="sample_validation")
            
            # Print report
            validator.print_report()
            
            # Save report
            report.save()
            
            self.results["validation_report"] = {
                "overall_accuracy": report.overall_accuracy,
                "total_samples": report.total_samples,
                "total_correct": report.total_correct
            }
            
            print(f"✓ Validation report saved")
            
            # Evaluate against benchmarks
            print("\n" + "-" * 70)
            print("BENCHMARK EVALUATION")
            print("-" * 70)
            
            benchmark_results = ValidationBenchmarks.evaluate_against_benchmarks(report)
            
            print(f"Performance Level: {benchmark_results['performance_level'].upper()}")
            
            for metric, value in benchmark_results['met_benchmarks']:
                print(f"  ✓ {metric}: {value:.1%}")
            
            for metric, value, threshold in benchmark_results['failed_benchmarks']:
                print(f"  ✗ {metric}: {value:.1%} (target: {threshold:.1%})")
            
            self.results["benchmark_evaluation"] = benchmark_results
            
            return True
        
        except Exception as e:
            print(f"✗ Validation ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.results["validation_report"] = {"error": str(e)}
            return False
    
    def generate_summary(self) -> dict:
        """Generate summary of all validation results"""
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        
        summary = {
            "timestamp": self.results["timestamp"],
            "phases_completed": 0,
            "phases_passed": 0,
            "overall_status": "PENDING",
            "details": {}
        }
        
        # Unit tests
        if self.results["unit_tests"]:
            summary["phases_completed"] += 1
            if self.results["unit_tests"].get("passed"):
                summary["phases_passed"] += 1
                summary["details"]["unit_tests"] = "PASSED ✓"
            else:
                summary["details"]["unit_tests"] = "FAILED ✗"
        
        # Validation
        if self.results["validation_report"]:
            summary["phases_completed"] += 1
            if "error" not in self.results["validation_report"]:
                summary["phases_passed"] += 1
                accuracy = self.results["validation_report"]["overall_accuracy"]
                summary["details"]["accuracy_validation"] = f"PASSED ✓ ({accuracy:.1%} accuracy)"
            else:
                summary["details"]["accuracy_validation"] = "FAILED ✗"
        
        # Benchmarks
        if self.results["benchmark_evaluation"]:
            summary["phases_completed"] += 1
            level = self.results["benchmark_evaluation"]["performance_level"]
            if level != "below_acceptable":
                summary["phases_passed"] += 1
            summary["details"]["benchmark_evaluation"] = f"{level.upper()}"
        
        # Overall status
        if summary["phases_passed"] == summary["phases_completed"]:
            summary["overall_status"] = "SUCCESS"
        elif summary["phases_passed"] >= summary["phases_completed"] * 0.7:
            summary["overall_status"] = "ACCEPTABLE"
        else:
            summary["overall_status"] = "NEEDS_IMPROVEMENT"
        
        self.results["summary"] = summary
        
        # Print summary
        print(f"\nPhases Completed: {summary['phases_completed']}/3")
        print(f"Phases Passed: {summary['phases_passed']}/3")
        print(f"Overall Status: {summary['overall_status']}\n")
        
        for phase, status in summary["details"].items():
            print(f"  {phase}: {status}")
        
        return summary
    
    def save_results(self, output_path: str = "validation_results") -> None:
        """Save all validation results to file"""
        _results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_results")
        os.makedirs(_results_dir, exist_ok=True)
        _filename = f"full_validation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        _filepath = os.path.join(_results_dir, _filename)
        with open(_filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nValidation results saved to: {_filepath}")
    
    def run_complete_validation(self, dataset_path: Optional[Path] = None) -> bool:
        """Run complete validation pipeline"""
        
        print("\n" + "🚀 " * 20)
        print("STARTING COMPLETE VALIDATION PIPELINE")
        print("🚀 " * 20)
        
        # Phase 1: Unit Tests
        unit_tests_ok = self.run_unit_tests()
        
        # Phase 2: Data Preparation
        if dataset_path is None:
            dataset_path = self.generate_sample_dataset()
        
        # Phase 3: Accuracy Validation
        validation_ok = self.run_accuracy_validation(dataset_path)
        
        # Generate summary
        summary = self.generate_summary()
        
        # Save results
        self.save_results()
        
        # Final status
        print("\n" + "=" * 70)
        if summary["overall_status"] == "SUCCESS":
            print("✓ VALIDATION SUCCESSFUL - System is ready for deployment")
        elif summary["overall_status"] == "ACCEPTABLE":
            print("⚠ VALIDATION ACCEPTABLE - System acceptable with some improvements recommended")
        else:
            print("✗ VALIDATION NEEDS IMPROVEMENT - Address failing tests before deployment")
        print("=" * 70)
        
        return summary["overall_status"] in ["SUCCESS", "ACCEPTABLE"]


def print_quick_start_guide():
    """Print quick start guide"""
    guide = """
╔════════════════════════════════════════════════════════════════════╗
║          CONTENT DETECTOR - QUICK START GUIDE                     ║
╚════════════════════════════════════════════════════════════════════╝

1. INSTALL DEPENDENCIES
   └─ pip install -r requirements.txt

2. RUN COMPLETE VALIDATION
   └─ python validation_orchestrator.py

3. COLLECT YOUR OWN DATA
   └─ python data_collection.py
   └─ Annotate samples in datasets/content_detector_v1/

4. VALIDATE YOUR DATA
   └─ python validation_metrics.py --dataset your_dataset.json

5. START THE API
   └─ python content_detector_api.py
   └─ Visit http://localhost:8000/docs

6. TEST THE API
   └─ python example_usage.py

KEY FILES:
├─ content_detector_api.py      Main API and classifiers
├─ paid_promotion_filter.py     Paid campaign detector
├─ advanced_fact_checking.py    Fact-checking integrations
├─ test_suite.py                Unit & integration tests
├─ data_collection.py           Dataset management tools
├─ validation_metrics.py        Accuracy evaluation
└─ validation_orchestrator.py   Master orchestrator

VALIDATION PIPELINE:
1. Unit Tests       → Test individual components
2. Integration      → Test full pipeline
3. Accuracy Tests   → Compare against labeled data
4. Benchmark Tests  → Check against success criteria

NEXT STEPS:
1. Run validation_orchestrator.py to baseline system
2. Collect 100+ examples in each class (propaganda, campaigns, neutral)
3. Re-run validation to measure accuracy
4. Fine-tune thresholds based on results
5. Deploy to production

For detailed guide, run:
  python data_collection.py
"""
    print(guide)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Content Detector Validation Orchestrator"
    )
    parser.add_argument("--dataset", type=str, help="Path to custom dataset")
    parser.add_argument("--guide", action="store_true", help="Print quick start guide")
    parser.add_argument("--skip-tests", action="store_true", help="Skip unit tests")
    
    args = parser.parse_args()
    
    if args.guide:
        print_quick_start_guide()
    else:
        orchestrator = ValidationOrchestrator()
        
        if args.skip_tests:
            print("Skipping unit tests...")
            success = orchestrator.run_accuracy_validation(
                Path(args.dataset) if args.dataset else None
            )
        else:
            success = orchestrator.run_complete_validation(
                Path(args.dataset) if args.dataset else None
            )
        
        sys.exit(0 if success else 1)
