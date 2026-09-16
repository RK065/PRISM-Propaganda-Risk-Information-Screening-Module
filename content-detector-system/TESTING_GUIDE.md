# Complete Testing & Validation Guide

## Overview

This guide covers the complete testing and validation strategy for the Content Detector system. It includes:

1. **Unit Tests** - Test individual components in isolation
2. **Integration Tests** - Test full pipeline with real data
3. **Accuracy Validation** - Measure performance against labeled dataset
4. **Benchmark Testing** - Verify against success criteria
5. **Performance Testing** - Ensure API meets speed requirements

## Quick Start (5 minutes)

```bash
# Run complete validation pipeline
python validation_orchestrator.py

# View quick start guide
python validation_orchestrator.py --guide

# Or run specific validations
python test_suite.py              # Run unit/integration tests
python data_collection.py         # Create sample dataset
python validation_metrics.py      # Evaluate accuracy
```

## Testing Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Validation Orchestrator                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Phase 1: Unit Tests                                   │
│  ├─ PropagandaDetector tests                           │
│  ├─ PaidCampaignDetector tests                         │
│  ├─ PaidPromotionFilter tests                          │
│  └─ Performance tests                                  │
│                                                         │
│  Phase 2: Data Preparation                            │
│  ├─ Load/validate dataset                             │
│  ├─ Split into train/val/test                         │
│  └─ Check class distribution                          │
│                                                         │
│  Phase 3: Accuracy Validation                         │
│  ├─ Run predictions on all items                      │
│  ├─ Calculate confusion matrices                      │
│  ├─ Compute metrics (precision, recall, F1)           │
│  └─ Generate error analysis                           │
│                                                         │
│  Phase 4: Benchmark Evaluation                        │
│  ├─ Compare against "acceptable" thresholds           │
│  ├─ Compare against "good" thresholds                 │
│  ├─ Compare against "excellent" thresholds            │
│  └─ Identify improvement areas                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Test Suite Details

### Unit Tests (`test_suite.py`)

Tests individual component functionality:

#### PropagandaDetector Tests
- ✓ Emotional language detection
- ✓ Absolute statements detection
- ✓ Polarizing framing (us vs. them)
- ✓ Suspicious formatting (ALL CAPS, punctuation)
- ✓ Neutral text should score low

#### PaidCampaignDetector Tests
- ✓ Commercial keywords detection
- ✓ Call-to-action detection
- ✓ Advertising disclosure detection
- ✓ Missing disclosure flagging
- ✓ Neutral content non-flagging

#### PaidPromotionFilter Tests
- ✓ Instagram influencer ads
- ✓ YouTube sponsorships
- ✓ Undisclosed promotions
- ✓ Neutral content

#### Performance Tests
- ✓ Single request < 1 second
- ✓ Batch requests < 0.5s per item

### Integration Tests

Full pipeline testing:

```python
# Test: Propaganda Classification
text = "WAKE UP!!! They're destroying us!"
result = classifier.classify(ContentInput(text=text))
assert result.classification in ["propaganda", "mixed"]
assert result.confidence > 0.5
assert result.risk_score > 60
```

### Accuracy Validation (`validation_metrics.py`)

Measure performance against labeled data:

**Metrics Calculated:**
- **Accuracy**: Overall correctness
- **Precision**: Of flagged items, how many were actually problematic
- **Recall**: Of all problematic items, how many were caught
- **F1 Score**: Harmonic mean of precision & recall
- **Specificity**: True negative rate

**Sample Output:**
```
Propaganda:
  Accuracy:   87.5%
  Precision:  85.2%  ← Low false positives
  Recall:     88.9%  ← Low false negatives
  F1 Score:   87.0%

Paid Campaigns:
  Accuracy:   82.1%
  Precision:  80.5%
  Recall:     84.2%
  F1 Score:   82.3%

Neutral:
  Accuracy:   92.5%
  Precision:  91.8%
  Recall:     93.2%
  F1 Score:   92.5%
```

## Data Collection & Labeling

### Step 1: Understand Label Definitions

**Propaganda**
- Emotionally manipulative content
- Fear/outrage appeals
- Polarizing framing ("us vs. them")
- Exaggerated or false claims
- Designed for organic spread
- Example: "WAKE UP!!! They're destroying our country!!!"

**Paid Campaigns**
- Commercial/promotional intent
- Calls to action (click, buy, use code)
- Influencer ads, sponsored content, affiliate links
- Usually has disclosures (but not always)
- Example: "Use code SAVE20 for 20% off! #ad #sponsored"

**Neutral**
- Factual, informational content
- Personal/casual posts
- No promotional or manipulative intent
- Example: "Had a great day at the beach"

**Mixed**
- Combines propaganda + paid campaign tactics
- Example: "INCREDIBLE EXCLUSIVE DEAL!!! Limited time only! #ad"

### Step 2: Collect Content

**Sources:**
- Twitter/X: Use API or manual collection
- Instagram: Public influencer accounts
- YouTube: Comments, video descriptions
- Reddit: Subreddit posts
- WhatsApp: Forward chains
- News sites: Articles and comments

**Target Collection:**
- Minimum: 50 examples per class
- Good: 200+ examples per class
- Excellent: 500+ examples per class

### Step 3: Annotate (Label)

Create JSON file with structure:
```json
[
  {
    "text": "WAKE UP!!! They're destroying...",
    "platform": "twitter",
    "content_type": "propaganda",
    "risk_level": "high",
    "has_disclosure": false,
    "has_cta": false,
    "annotator_confidence": 0.95,
    "notes": "Clear propaganda signals",
    "tags": ["emotional_language", "all_caps", "fear_mongering"]
  },
  ...
]
```

**Required Fields:**
- `text`: The content to classify
- `platform`: Source (twitter, instagram, youtube, reddit, whatsapp, news, unknown)
- `content_type`: propaganda, paid_campaign, neutral, or mixed
- `risk_level`: low, medium, or high

**Recommended Fields:**
- `has_disclosure`: Advertising labels present?
- `has_cta`: Call-to-action detected?
- `annotator_confidence`: Your confidence (0-1)
- `tags`: Keywords describing signals

### Step 4: Quality Control

**Single Annotator:**
- Fastest (1-2 hours per 100 items)
- Sufficient for initial validation
- Risk: Personal bias

**Multi-Annotator (Recommended):**
- Have 2-3 people label same content
- Calculate agreement score (target >0.8)
- Resolve disagreements through discussion
- More robust and defensible

**Agreement Calculation:**
```python
from validation_metrics import ComparisonValidator

validator = ComparisonValidator()
agreement = validator.inter_annotator_agreement([
    {"text": "...", "labels": ["propaganda", "propaganda", "mixed"]},
    {"text": "...", "labels": ["neutral", "neutral", "neutral"]},
])
print(f"Agreement: {agreement:.1%}")  # Expected: >80%
```

## Running Validation

### Option 1: Complete Pipeline (Recommended)

```bash
python validation_orchestrator.py
```

This runs:
1. All unit tests
2. Creates sample dataset
3. Runs accuracy validation
4. Evaluates against benchmarks
5. Generates report

**Output:**
```
VALIDATION SUMMARY
=======================================================
Phases Completed: 3/3
Phases Passed: 3/3
Overall Status: SUCCESS

  unit_tests: PASSED ✓
  data_preparation: PASSED ✓
  accuracy_validation: PASSED ✓ (85.2% accuracy)
  benchmark_evaluation: GOOD
=======================================================
```

### Option 2: Run Individual Tests

```bash
# Just unit tests
python test_suite.py

# Just create dataset
python data_collection.py

# Just validate accuracy
python validation_metrics.py

# With custom dataset
python validation_metrics.py --dataset my_data.json
```

## Understanding the Results

### Accuracy Metrics

**Overall Accuracy**: (TP + TN) / (TP + TN + FP + FN)
- How often the system is correct overall
- Target: >75%

**Precision**: TP / (TP + FP)
- Of items flagged as problematic, how many actually are
- High precision = fewer false positives
- Target: >75%

**Recall**: TP / (TP + FN)
- Of all problematic items, how many does system catch
- High recall = fewer false negatives
- Target: >70%

**F1 Score**: 2 × (Precision × Recall) / (Precision + Recall)
- Balanced metric combining precision and recall
- Target: >72%

### Example Interpretation

```
System detects propaganda with:
  Precision: 85%  → 85 out of 100 flagged items are actually propaganda
  Recall: 75%     → System catches 75% of actual propaganda
  F1: 80%         → Good balance between precision and recall
```

**What this means:**
- ✓ Good at identifying propaganda (low false positives)
- ✓ Catches most propaganda (low false negatives)
- ⚠ Might miss ~25% of propaganda
- ✓ Suitable for production use

## Benchmark Thresholds

The system has 3 performance levels:

### Acceptable (Minimum for Production)
```
Overall Accuracy: 70%
Propaganda Precision: 70% | Recall: 65%
Campaign Precision: 70% | Recall: 65%
Neutral Accuracy: 80%
```

Use if: Limited labeled data, quick MVP needed

### Good (Recommended)
```
Overall Accuracy: 80%
Propaganda Precision: 80% | Recall: 75%
Campaign Precision: 80% | Recall: 75%
Neutral Accuracy: 90%
```

Use if: Production deployment with moderate traffic

### Excellent (Enterprise)
```
Overall Accuracy: 90%
Propaganda Precision: 90% | Recall: 85%
Campaign Precision: 90% | Recall: 85%
Neutral Accuracy: 95%
```

Use if: High-stakes deployment, safety-critical

## Improving Accuracy

If validation shows low accuracy:

### 1. Collect More Data
```bash
# Minimum dataset
50 examples per class = ~200 items total

# Good dataset
200 examples per class = ~800 items total

# Excellent dataset
500+ examples per class = 2000+ items total
```

### 2. Improve Labeling Consistency
- Use multi-annotator approach
- Create detailed annotation guidelines
- Review disagreements as team
- Calculate inter-annotator agreement

### 3. Adjust Thresholds
```python
# Current
if propaganda_score > 0.6:
    classification = "propaganda"

# Adjusted (more sensitive)
if propaganda_score > 0.5:  # Lower threshold
    classification = "propaganda"

# Adjusted (more conservative)
if propaganda_score > 0.7:  # Higher threshold
    classification = "propaganda"
```

### 4. Add Platform-Specific Rules
```python
# YouTube videos have different norms than Twitter
if platform == "youtube" and cta_count > 3:
    cta_score *= 0.5  # Less suspicious on YouTube
```

### 5. Fine-tune Detection Patterns
Edit `content_detector_api.py`:
```python
self.propaganda_keywords = {
    "fear_words": ["destroy", "enemy", "threat", ...],  # Add domain-specific words
    "emotional_words": [...],
    # Add new categories
    "misinformation_patterns": ["study says", "leaked", ...],
}
```

## Performance Optimization

### Target Benchmarks
- Single request: <500ms
- Batch (10 items): <5s total
- API throughput: >100 requests/sec per server

### Test Performance
```bash
python -m pytest test_suite.py::TestPerformance -v
```

### If Slow

1. **Add Caching**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def analyze_language(text):
    # Cached results
    return {...}
```

2. **Optimize Patterns**
```python
# Compile regex once
pattern = re.compile(r'CAPS_WORDS')  # Instead of re.findall inside loop
```

3. **Use Async**
```python
async def analyze_batch(items):
    tasks = [asyncio.create_task(analyze_one(item)) for item in items]
    return await asyncio.gather(*tasks)
```

## Validation Checklist

Before deploying to production:

- [ ] Run `validation_orchestrator.py` and review results
- [ ] Overall accuracy >70% (target: >80%)
- [ ] Propaganda precision/recall both >65% (target: >75%)
- [ ] Campaign precision/recall both >65% (target: >75%)
- [ ] Neutral accuracy >80% (target: >90%)
- [ ] No unit tests failing
- [ ] Performance <500ms per request
- [ ] Reviewed false positives and false negatives
- [ ] Documented any known limitations
- [ ] Tested with real-world examples from your domain

## Continuous Validation

### Monitor Production Metrics

```python
# Log predictions and outcomes
{
    "timestamp": "2024-01-15T10:30:00Z",
    "text": "...",
    "predicted_class": "propaganda",
    "confidence": 0.87,
    "actual_class": "propaganda",  # Later verified
    "is_correct": true
}
```

### Periodically Re-validate

1. Collect new data
2. Run validation_orchestrator.py
3. Compare metrics to previous runs
4. Adjust thresholds if drift detected

### Implement User Feedback Loop

Allow users to report misclassifications:
```python
@app.post("/feedback")
async def report_error(prediction_id: str, correct_label: str):
    # Store feedback
    # Use for retraining
    pass
```

## Troubleshooting

### Problem: Low Propaganda Accuracy
**Cause:** Hard to distinguish from strong opinions
**Solution:**
- Add more propaganda examples
- Adjust keywords to be more specific
- Increase propaganda_score threshold

### Problem: Campaign Accuracy Poor
**Cause:** Varies by platform
**Solution:**
- Collect platform-specific examples
- Use platform detection
- Adjust rules per platform

### Problem: Many False Positives
**Cause:** Thresholds too low
**Solution:**
- Increase classification thresholds
- Review flagged examples
- Add whitelist of acceptable phrases

### Problem: Slow API
**Cause:** Complex fact-checking
**Solution:**
- Cache fact-check results
- Use async processing
- Run fact-checking in background

## Files Reference

| File | Purpose |
|------|---------|
| `test_suite.py` | Unit & integration tests |
| `data_collection.py` | Dataset creation & management |
| `validation_metrics.py` | Accuracy evaluation |
| `validation_orchestrator.py` | Master orchestrator |
| `TESTING_GUIDE.md` | This file |

## Next Steps

1. **Run Initial Validation**
   ```bash
   python validation_orchestrator.py
   ```

2. **Review Sample Dataset**
   ```bash
   cat datasets/validation_sample/validation_sample.json
   ```

3. **Collect Your Own Data**
   - Identify 5-10 sources (Twitter, Instagram, Reddit, etc.)
   - Manually collect 50+ examples from each
   - Annotate using guidelines above

4. **Create Labeled Dataset**
   ```python
   from data_collection import DatasetBuilder, AnnotatedContent
   
   builder = DatasetBuilder("my_data")
   for item_dict in my_items:
       item = AnnotatedContent(**item_dict)
       builder.add_item(item)
   builder.save_dataset()
   ```

5. **Validate Your Data**
   ```bash
   python validation_orchestrator.py --dataset datasets/my_data/my_data.json
   ```

6. **Iterate & Improve**
   - Review misclassifications
   - Adjust thresholds
   - Add more labeled examples
   - Re-run validation

7. **Deploy When Ready**
   - Accuracy >75%
   - All benchmarks met
   - Performance acceptable
   - Documentation complete

---

**Questions or issues?** Review the relevant test output and adjust accordingly. Good luck! 🚀
