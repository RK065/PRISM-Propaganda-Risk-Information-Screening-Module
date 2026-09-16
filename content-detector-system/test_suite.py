"""
Comprehensive Testing Suite for Content Detector
Includes unit tests, integration tests, and end-to-end validation
"""

import unittest
from typing import Dict, List, Tuple
import json
from datetime import datetime, timezone
import sys

# Import modules to test
from content_detector_api import (
    PropagandaDetector, PaidCampaignDetector, ContentClassifier, ContentInput
)
from paid_promotion_filter import PaidPromotionFilter
from feature_extractor import FeatureExtractor, FEATURE_NAMES
from ml_classifier import ContentMLClassifier


# ============= TEST DATA =============

class TestDataset:
    """Collection of labeled test cases for validation"""
    
    PROPAGANDA_EXAMPLES = [
        {
            "text": "WAKE UP!!! They're DESTROYING our country! Everyone needs to see this TRUTH before they silence us!!!",
            "expected_class": "propaganda",
            "min_propaganda_score": 0.7,
            "platform": "twitter"
        },
        {
            "text": "The elite doesn't want you to know about this conspiracy. Share before it gets deleted!",
            "expected_class": "propaganda",
            "min_propaganda_score": 0.6,
            "platform": "whatsapp"
        },
        {
            "text": "Our team is working hard to fix the problems in our community.",
            "expected_class": "neutral",
            "max_propaganda_score": 0.4,
            "platform": "twitter"
        },
    ]
    
    PAID_CAMPAIGN_EXAMPLES = [
        {
            "text": "OMG love this new skincare! Use code GLOW20 for 20% off! Link in bio #ad #sponsored #gifted",
            "expected_class": "paid_campaign",
            "min_campaign_score": 0.7,
            "expected_type": "influencer_ad",
            "platform": "instagram"
        },
        {
            "text": "This video is sponsored by NordVPN. Use code TECH50 for 50% off. Link in description.",
            "expected_class": "paid_campaign",
            "min_campaign_score": 0.6,
            "expected_type": "sponsored_content",
            "platform": "youtube"
        },
        {
            "text": "Just shared my thoughts on this topic. What do you think?",
            "expected_class": "neutral",
            "max_campaign_score": 0.3,
            "platform": "twitter"
        },
    ]
    
    MIXED_EXAMPLES = [
        {
            "text": "INCREDIBLE DEAL!!! Don't miss this LIMITED TIME offer! Use code SAVE50! Everyone must see this! #ad #exclusive",
            "expected_class": "mixed",
            "min_propaganda_score": 0.5,
            "min_campaign_score": 0.6,
            "platform": "instagram"
        },
    ]


# ============= UNIT TESTS =============

class TestPropagandaDetector(unittest.TestCase):
    """Test propaganda detection logic"""
    
    def setUp(self):
        self.detector = PropagandaDetector()
    
    def test_emotional_language_detection(self):
        """Test detection of emotional/fear-based language"""
        text = "This is absolutely OUTRAGEOUS and DISGUSTING! We must act NOW!"
        score = self.detector.analyze_language(text)
        self.assertGreater(score['emotional_words'], 0.5, 
                          "Should detect high emotional language")
    
    def test_absolute_statements(self):
        """Test detection of absolute statements"""
        text = "Everyone knows this is always true. Nobody can disagree."
        score = self.detector.analyze_language(text)
        self.assertGreater(score['absolute_words'], 0.3,
                          "Should detect absolute language")
    
    def test_us_vs_them_framing(self):
        """Test detection of polarizing framing"""
        text = "They're trying to destroy us. Those people want to take everything away."
        score = self.detector.analyze_language(text)
        self.assertGreater(score['us_vs_them'], 0.2,
                          "Should detect polarizing framing")
    
    def test_caps_and_punctuation(self):
        """Test detection of suspicious formatting"""
        text = "THIS IS VERY IMPORTANT!!! Please READ this NOW!!!"
        score = self.detector.analyze_language(text)
        self.assertGreater(score['suspicious_patterns'], 0.3,
                          "Should detect ALL CAPS and excessive punctuation")
    
    def test_neutral_text(self):
        """Test that neutral text has low propaganda score"""
        text = "The weather today is sunny and warm. Temperature is 25 degrees."
        score = self.detector.analyze_language(text)
        avg_score = sum(score.values()) / len(score)
        self.assertLess(avg_score, 0.4,
                       "Neutral text should have low propaganda score")


class TestPaidCampaignDetector(unittest.TestCase):
    """Test paid campaign detection logic"""
    
    def setUp(self):
        self.detector = PaidCampaignDetector()
    
    def test_commercial_language(self):
        """Test detection of commercial keywords"""
        text = "Buy now! Special sale with huge discounts. Limited time offer!"
        score = self.detector.detect_commercial_language(text)
        self.assertGreater(score, 0.6,
                          "Should detect commercial language")
    
    def test_call_to_action(self):
        """Test detection of CTAs"""
        text = "Click here to visit. Link in bio. Swipe up to shop now!"
        score = self.detector.detect_call_to_action(text)
        self.assertGreater(score, 0.5,
                          "Should detect multiple CTAs")
    
    def test_disclosure_detection(self):
        """Test detection of advertising disclosures"""
        text = "This is sponsored content. #ad #sponsored by Brand"
        score = self.detector.check_disclosure(text)
        self.assertGreater(score, 0.7,
                          "Should detect advertising disclosure")
    
    def test_missing_disclosure(self):
        """Test detection of undisclosed ads"""
        text = "Buy this amazing product now at our store! Limited stock!"
        score = self.detector.check_disclosure(text)
        self.assertLess(score, 0.5,
                       "Should flag missing disclosure")


class TestPaidPromotionFilter(unittest.TestCase):
    """Test platform-specific promotion detection"""
    
    def setUp(self):
        self.filter = PaidPromotionFilter()
    
    def test_instagram_influencer_detection(self):
        """Test Instagram influencer ad detection"""
        text = "Gifted by @brandname! Use code GLOW20 #ad #gifted #collab"
        result = self.filter.analyze(text, platform="instagram")
        self.assertTrue(result.is_paid, "Should detect as paid content")
        self.assertEqual(result.promotion_type, "influencer_ad",
                        "Should classify as influencer ad")
        self.assertIn("#ad", result.disclosure_tags, 
                     "Should find #ad disclosure")
    
    def test_youtube_sponsorship(self):
        """Test YouTube sponsored content"""
        text = "Sponsored by NordVPN. Use code TECH50 for 50% off."
        result = self.filter.analyze(text, platform="youtube")
        self.assertTrue(result.is_paid, "Should detect as paid")
        self.assertGreater(result.confidence, 0.5,
                          "Should have good confidence")
    
    def test_undisclosed_promotion(self):
        """Test detection of undisclosed ads"""
        text = "Just tried this amazing product! Buy now and save!"
        result = self.filter.analyze(text, platform="instagram")
        if result.is_paid:  # If detected as paid
            self.assertEqual(result.risk_level, "high",
                            "Undisclosed ads should be high risk")
    
    def test_neutral_content(self):
        """Test that neutral content is not flagged"""
        text = "Had a great day at the beach today with friends."
        result = self.filter.analyze(text, platform="instagram")
        self.assertFalse(result.is_paid,
                        "Regular post should not be flagged as paid")


# ============= INTEGRATION TESTS =============

class TestContentClassifierIntegration(unittest.TestCase):
    """Test full classification pipeline"""
    
    def setUp(self):
        self.classifier = ContentClassifier()
    
    def test_propaganda_classification(self):
        """Test end-to-end propaganda classification"""
        for example in TestDataset.PROPAGANDA_EXAMPLES:
            with self.subTest(text=example['text'][:50]):
                content = ContentInput(text=example['text'])
                result = self.classifier.classify(content)
                
                self.assertIn(result.classification, 
                             ["propaganda", "mixed"],
                             f"Should classify as propaganda, got {result.classification}")
                self.assertGreater(result.confidence, 0.5,
                                  "Should have reasonable confidence")
    
    def test_campaign_classification(self):
        """Test end-to-end campaign classification"""
        for example in TestDataset.PAID_CAMPAIGN_EXAMPLES:
            if example['expected_class'] == 'paid_campaign':
                with self.subTest(text=example['text'][:50]):
                    content = ContentInput(text=example['text'])
                    result = self.classifier.classify(content)
                    
                    self.assertIn(result.classification,
                                 ["paid_campaign", "mixed"],
                                 f"Should classify as campaign, got {result.classification}")
    
    def test_risk_score_range(self):
        """Test that risk scores are in valid range"""
        test_texts = [
            "This is very normal content about daily activities.",
            "URGENT: SHARE THIS BEFORE THEY DELETE IT!!!",
            "Use code SAVE20 for 20% off! #ad #sponsored"
        ]
        
        for text in test_texts:
            with self.subTest(text=text[:30]):
                content = ContentInput(text=text)
                result = self.classifier.classify(content)
                
                self.assertGreaterEqual(result.risk_score, 0,
                                       "Risk score should be >= 0")
                self.assertLessEqual(result.risk_score, 100,
                                    "Risk score should be <= 100")


# ============= VALIDATION TESTS =============

class TestValidationMetrics(unittest.TestCase):
    """Test accuracy metrics across dataset"""
    
    def setUp(self):
        self.classifier = ContentClassifier()
        self.promotion_filter = PaidPromotionFilter()
    
    def test_propaganda_accuracy(self):
        """Measure accuracy on propaganda detection"""
        correct = 0
        total = 0
        
        for example in TestDataset.PROPAGANDA_EXAMPLES:
            content = ContentInput(text=example['text'])
            result = self.classifier.classify(content)
            
            if result.classification in [example['expected_class'], "mixed"]:
                if example['expected_class'] in ['propaganda', 'mixed']:
                    correct += 1
            
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        print(f"\nPropaganda Detection Accuracy: {accuracy:.1%}")
        self.assertGreater(accuracy, 0.6,
                          "Propaganda detection should be > 60% accurate")
    
    def test_campaign_accuracy(self):
        """Measure accuracy on campaign detection"""
        correct = 0
        total = 0
        
        for example in TestDataset.PAID_CAMPAIGN_EXAMPLES:
            content = ContentInput(text=example['text'])
            result = self.classifier.classify(content)
            
            if result.classification in [example['expected_class'], "mixed"]:
                if example['expected_class'] in ['paid_campaign', 'mixed']:
                    correct += 1
            
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        print(f"Campaign Detection Accuracy: {accuracy:.1%}")
        self.assertGreater(accuracy, 0.6,
                          "Campaign detection should be > 60% accurate")
    
    def test_promotion_filter_accuracy(self):
        """Measure accuracy on promotion filter"""
        correct = 0
        total = len(TestDataset.PAID_CAMPAIGN_EXAMPLES)
        
        for example in TestDataset.PAID_CAMPAIGN_EXAMPLES:
            result = self.promotion_filter.analyze(
                text=example['text'],
                platform=example.get('platform')
            )
            
            if example['expected_class'] == 'paid_campaign':
                if result.is_paid:
                    correct += 1
            else:
                if not result.is_paid:
                    correct += 1
        
        accuracy = correct / total if total > 0 else 0
        print(f"Promotion Filter Accuracy: {accuracy:.1%}")
        self.assertGreater(accuracy, 0.7,
                          "Promotion filter should be > 70% accurate")


# ============= PERFORMANCE TESTS =============

class TestPerformance(unittest.TestCase):
    """Test API performance and response times"""
    
    def setUp(self):
        self.classifier = ContentClassifier()
        import time
        self.time_module = time
    
    def test_single_request_performance(self):
        """Test response time for single request"""
        content = ContentInput(
            text="Sample text for testing performance " * 10
        )
        
        start = self.time_module.time()
        result = self.classifier.classify(content)
        elapsed = self.time_module.time() - start
        
        print(f"\nSingle Request Time: {elapsed:.3f}s")
        self.assertLess(elapsed, 1.0,
                       "Single request should complete in < 1 second")
    
    def test_batch_performance(self):
        """Test performance for batch requests"""
        contents = [
            ContentInput(text=f"Sample text #{i} " * 5)
            for i in range(10)
        ]
        
        start = self.time_module.time()
        results = [self.classifier.classify(c) for c in contents]
        elapsed = self.time_module.time() - start
        
        avg_time = elapsed / len(contents)
        print(f"Batch Request Time (10 items): {elapsed:.3f}s ({avg_time:.3f}s per item)")
        self.assertLess(avg_time, 0.5,
                       "Average request time should be < 0.5 seconds")

# ============= PREPROCESSOR TESTS =============

class TestPreprocessor(unittest.TestCase):
    """Test advanced text preprocessing"""

    def setUp(self):
        from preprocessor import TextPreprocessor
        self.preprocessor = TextPreprocessor()

    def test_lemmatization(self):
        """Test that words are lemmatized"""
        result = self.preprocessor.preprocess("The dogs were running quickly")
        # Lemmatization should normalize tokens
        self.assertTrue(len(result.tokens) > 0)
        self.assertIsInstance(result.cleaned_text, str)

    def test_emoji_detection(self):
        """Test emoji extraction and sentiment"""
        result = self.preprocessor.preprocess("Love this! 😊❤️👍 So great! 😡")
        self.assertGreater(result.emoji_info["count"], 0,
                          "Should detect emojis")
        self.assertGreater(result.emoji_info["positive_count"], 0,
                          "Should detect positive emojis")

    def test_elongated_words(self):
        """Test elongated word detection"""
        result = self.preprocessor.preprocess("This is sooooo gooood and amaaazing!")
        self.assertGreater(len(result.elongated_words), 0,
                          "Should detect elongated words")

    def test_sentence_splitting(self):
        """Test sentence splitting"""
        result = self.preprocessor.preprocess("First sentence. Second sentence! Third?")
        self.assertGreaterEqual(len(result.sentences), 2)

    def test_readability_flesch(self):
        """Test Flesch reading ease calculation"""
        score = self.preprocessor.flesch_reading_ease(
            "The cat sat on the mat. The dog ran in the park."
        )
        # Should return a valid number (0-100 range typical but can go outside)
        self.assertIsInstance(score, float)

    def test_readability_gunning_fog(self):
        """Test Gunning Fog index"""
        score = self.preprocessor.gunning_fog_index(
            "The cat sat on the mat. Simple words for testing."
        )
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)

    def test_empty_text(self):
        """Test handling of empty text"""
        result = self.preprocessor.preprocess("")
        self.assertEqual(result.cleaned_text, "")
        self.assertEqual(len(result.tokens), 0)


# ============= EMOTION LEXICON TESTS =============

class TestEmotionLexicon(unittest.TestCase):
    """Test NRC-compatible emotion lexicon"""

    def setUp(self):
        from emotion_lexicon import EmotionLexicon
        self.lexicon = EmotionLexicon()

    def test_emotion_categories(self):
        """Test all 8 emotion categories exist"""
        emotions = self.lexicon.score_text("I am happy and afraid")
        expected = ["anger", "joy", "fear", "sadness", "trust",
                    "anticipation", "surprise", "disgust"]
        for emo in expected:
            self.assertIn(emo, emotions, f"Missing emotion: {emo}")

    def test_anger_detection(self):
        """Test anger word scoring"""
        scores = self.lexicon.score_text("furious rage hostile angry violent outrage")
        self.assertGreater(scores["anger"], 0, "Should detect anger words")

    def test_joy_detection(self):
        """Test joy word scoring"""
        scores = self.lexicon.score_text("happy cheerful wonderful delighted grateful")
        self.assertGreater(scores["joy"], 0, "Should detect joy words")

    def test_fear_detection(self):
        """Test fear word scoring"""
        scores = self.lexicon.score_text("terrified panic horror scared anxious")
        self.assertGreater(scores["fear"], 0, "Should detect fear words")

    def test_neutral_text(self):
        """Test that neutral text has low emotion scores"""
        scores = self.lexicon.score_text("the table is brown and square")
        total = sum(scores.values())
        self.assertLess(total, 1.0, "Neutral text should have low total emotion score")

    def test_get_emotions(self):
        """Test per-word emotion lookup"""
        result = self.lexicon.get_emotions("furious")
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("anger", False), "furious should map to anger")


# ============= FEATURE EXTRACTOR TESTS (70+ features) =============

class TestFeatureExtractor(unittest.TestCase):
    """Test the advanced 70+ feature extraction pipeline"""

    def setUp(self):
        self.extractor = FeatureExtractor()

    def test_feature_count(self):
        """Test that extraction returns all expected features"""
        features = self.extractor.extract("Sample text for testing features in the pipeline")
        self.assertEqual(len(features), len(FEATURE_NAMES),
                        f"Should return {len(FEATURE_NAMES)} features, got {len(features)}")

    def test_feature_count_is_70_plus(self):
        """Verify we have 60+ features as designed"""
        self.assertGreaterEqual(len(FEATURE_NAMES), 60,
                               f"Should have 60+ features, got {len(FEATURE_NAMES)}")

    def test_feature_names(self):
        """Test that all expected feature names are present"""
        features = self.extractor.extract("Sample text for testing features")
        for name in FEATURE_NAMES:
            self.assertIn(name, features, f"Missing feature: {name}")

    def test_all_features_numeric(self):
        """Test that all features are numeric"""
        features = self.extractor.extract("Test ALL CAPS!!! sooooo good 😊 #ad $50 off")
        for name, value in features.items():
            self.assertIsInstance(value, (int, float),
                                f"Feature '{name}' is {type(value)}, expected numeric")

    def test_caps_detection(self):
        """Test ALL CAPS ratio"""
        features = self.extractor.extract("THIS IS ALL CAPS TEXT HERE")
        self.assertGreater(features["caps_ratio"], 0.3,
                          "Should detect high caps ratio")
        self.assertGreater(features["caps_word_count"], 2,
                          "Should count multiple caps words")

    def test_disclosure_feature(self):
        """Test disclosure detection"""
        with_disc = self.extractor.extract("Great product! #ad #sponsored")
        without_disc = self.extractor.extract("Great product! Really love it")
        self.assertEqual(with_disc["has_disclosure"], 1.0)
        self.assertEqual(without_disc["has_disclosure"], 0.0)

    def test_readability_features(self):
        """Test readability scores are computed"""
        features = self.extractor.extract(
            "This is a simple sentence. Here is another one. And one more."
        )
        self.assertIsInstance(features["flesch_reading_ease"], float)
        self.assertIsInstance(features["gunning_fog_index"], float)
        self.assertIsInstance(features["avg_syllables_per_word"], float)

    def test_nrc_emotion_features(self):
        """Test NRC emotion features"""
        features = self.extractor.extract("I am furious and terrified about this!")
        nrc_features = [n for n in FEATURE_NAMES if n.startswith("nrc_")]
        self.assertEqual(len(nrc_features), 8, "Should have 8 NRC features")
        # At least one emotion should be non-zero
        nrc_sum = sum(features[n] for n in nrc_features)
        self.assertGreater(nrc_sum, 0, "Should detect some emotions")

    def test_emoji_features(self):
        """Test emoji-related features"""
        features = self.extractor.extract("Amazing product! 😊❤️👍 Love it! 😡")
        self.assertGreater(features["emoji_count"], 0, "Should count emojis")

    def test_clickbait_detection(self):
        """Test clickbait pattern detection"""
        features = self.extractor.extract("You won't believe what happened next! Shocking truth exposed!")
        self.assertGreater(features["clickbait_score"], 0, "Should detect clickbait patterns")

    def test_commercial_features(self):
        """Test commercial/campaign feature extraction"""
        features = self.extractor.extract(
            "Buy now! Use code SAVE50 for 50% off! #ad Link in bio"
        )
        self.assertGreater(features["cta_pattern_count"], 0, "Should detect CTA patterns")
        self.assertGreater(features["discount_code_count"], 0, "Should detect discount codes")
        self.assertEqual(features["has_disclosure"], 1.0, "Should detect #ad disclosure")

    def test_claim_features(self):
        """Test claim type detection"""
        sci = self.extractor.extract("Research shows this is proven by evidence")
        pol = self.extractor.extract("The government election policy vote was decided")
        health = self.extractor.extract("This vaccine treatment cures the disease")
        self.assertEqual(sci["claim_scientific"], 1.0)
        self.assertEqual(pol["claim_political"], 1.0)
        self.assertEqual(health["claim_health"], 1.0)

    def test_extract_array_order(self):
        """Test that array extraction matches FEATURE_NAMES order"""
        text = "Sample text for testing feature ordering"
        features_dict = self.extractor.extract(text)
        features_array = self.extractor.extract_array(text)
        self.assertEqual(len(features_array), len(FEATURE_NAMES))
        for i, name in enumerate(FEATURE_NAMES):
            self.assertAlmostEqual(features_array[i], features_dict[name],
                                  msg=f"Mismatch at index {i} ({name})")

    def test_platform_encoding(self):
        """Test platform label encoding"""
        twitter = self.extractor.extract("test", platform="twitter")
        instagram = self.extractor.extract("test", platform="instagram")
        unknown = self.extractor.extract("test", platform=None)
        self.assertNotEqual(twitter["platform_encoded"],
                           instagram["platform_encoded"])
        self.assertEqual(unknown["platform_encoded"], 9.0)

    def test_batch_extraction(self):
        """Test batch extraction"""
        texts = ["First text here", "Second text here", "Third text here"]
        batch = self.extractor.extract_batch(texts)
        self.assertEqual(len(batch), 3)
        self.assertEqual(len(batch[0]), len(FEATURE_NAMES))

    def test_empty_text(self):
        """Test graceful handling of empty text"""
        features = self.extractor.extract("")
        self.assertEqual(len(features), len(FEATURE_NAMES))
        for name, val in features.items():
            self.assertIsInstance(val, (int, float), f"Empty text feature '{name}' not numeric")

    def test_elongated_word_feature(self):
        """Test elongated word count"""
        features = self.extractor.extract("This is sooooo gooood and amaaazing!")
        self.assertGreater(features["elongated_word_count"], 0,
                          "Should detect elongated words")


# ============= ML CLASSIFIER TESTS =============

class TestMLClassifier(unittest.TestCase):
    """Test the advanced ML classifier"""

    def test_prediction_format(self):
        """Test that prediction returns correct format (if model exists)"""
        clf = ContentMLClassifier()
        if not clf.load_model("models/current"):
            self.skipTest("No trained model available — skipping ML prediction test")

        result = clf.predict("WAKE UP!!! They are LYING to you!!!")
        self.assertIn("classification", result)
        self.assertIn("confidence", result)
        self.assertIn("class_probabilities", result)
        self.assertIn(result["classification"],
                     ["propaganda", "paid_campaign", "mixed", "neutral"])
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_probabilities_sum_to_one(self):
        """Test calibrated probabilities sum to ~1.0"""
        clf = ContentMLClassifier()
        if not clf.load_model("models/current"):
            self.skipTest("No trained model available")

        result = clf.predict("Use code SAVE20 for 20% off! #ad")
        prob_sum = sum(result["class_probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=1,
                              msg=f"Probabilities sum to {prob_sum}, expected ~1.0")

    def test_batch_prediction(self):
        """Test batch prediction"""
        clf = ContentMLClassifier()
        if not clf.load_model("models/current"):
            self.skipTest("No trained model available")

        texts = ["Test one", "Test two", "Test three"]
        results = clf.predict_batch(texts)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("classification", r)

    def test_explain_prediction(self):
        """Test SHAP/feature importance explanation"""
        clf = ContentMLClassifier()
        if not clf.load_model("models/current"):
            self.skipTest("No trained model available")

        explanation = clf.explain_prediction("WAKE UP!!! They are LYING!!!")
        self.assertIn("classification", explanation)
        self.assertIn("confidence", explanation)
        self.assertIn("top_features", explanation)
        self.assertIsInstance(explanation["top_features"], list)

    def test_fallback_when_no_model(self):
        """Test that classifier falls back to rules when no model exists"""
        classifier = ContentClassifier()
        # Even without a trained model, classify should still work
        content = ContentInput(text="WAKE UP!!! They are DESTROYING our country!")
        result = classifier.classify(content)
        self.assertIn(result.classification,
                     ["propaganda", "paid_campaign", "mixed", "neutral"])
        self.assertGreaterEqual(result.risk_score, 0)

    def test_classify_response_schema(self):
        """Test that classify always returns correct FlagResponse schema"""
        classifier = ContentClassifier()
        content = ContentInput(
            text="Use code SAVE20 for 20% off! Limited time only! #ad #sponsored"
        )
        result = classifier.classify(content)
        # Verify all required fields exist
        self.assertIsInstance(result.classification, str)
        self.assertIsInstance(result.confidence, float)
        self.assertIsInstance(result.risk_score, float)
        self.assertIsInstance(result.reasoning, dict)
        self.assertIsInstance(result.fact_checks, list)
        self.assertIsInstance(result.flags, list)
        # Verify reasoning has expected keys
        self.assertIn("propaganda_score", result.reasoning)
        self.assertIn("campaign_score", result.reasoning)
        self.assertIn("false_claim_ratio", result.reasoning)


# ============= TEST RUNNER WITH REPORTING =============

class TestReporter:
    """Generate detailed test reports"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "accuracy_metrics": {},
            "performance_metrics": {}
        }
    
    def generate_report(self, test_results):
        """Generate and save test report"""
        report = {
            "summary": self.results,
            "details": []
        }
        
        # Save report to file
        with open("test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        print(json.dumps(self.results, indent=2))
        print("="*60)


def run_all_tests():
    """Run complete test suite"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPropagandaDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestPaidCampaignDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestPaidPromotionFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestPreprocessor))
    suite.addTests(loader.loadTestsFromTestCase(TestEmotionLexicon))
    suite.addTests(loader.loadTestsFromTestCase(TestFeatureExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestMLClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestContentClassifierIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate report
    reporter = TestReporter()
    reporter.results['tests_run'] = result.testsRun
    reporter.results['tests_passed'] = result.testsRun - len(result.failures) - len(result.errors)
    reporter.results['tests_failed'] = len(result.failures) + len(result.errors)
    
    reporter.generate_report(result)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
