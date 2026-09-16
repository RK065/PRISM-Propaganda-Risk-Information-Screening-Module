# Content Propaganda & Campaign Detector

A comprehensive API for detecting and differentiating propaganda from paid campaigns in social media content, with integrated fact-checking.

## 🎯 Overview

This system analyzes social media posts and flags them as:
- **Propaganda**: Emotionally manipulative, polarizing, fear-based content
- **Paid Campaigns**: Commercial/promotional content designed to drive engagement or sales
- **Mixed**: Content combining both characteristics
- **Neutral**: Factual, balanced content

Each classification includes:
- Risk score (0-100)
- Confidence level
- Specific flags explaining the classification
- Fact-check results for disputed claims

## 📊 How It Works

```
Input Text
    ↓
┌─────────────────────────────────┐
│  Language Analysis               │
│  • Emotional language            │
│  • Repetition patterns           │
│  • Absolute statements           │
│  • US vs THEM framing            │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Content Type Detection          │
│  • Commercial keywords           │
│  • Call-to-action language       │
│  • Advertising disclosures       │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Fact-Checking                  │
│  • Extract claims               │
│  • Verify against sources       │
│  • Check for false claims       │
└─────────────────────────────────┘
    ↓
Classification + Risk Score
```

## 🚀 Quick Start

### Installation

```bash
# Clone or download the files
cd content-detector

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the API

```bash
python content_detector_api.py
```

The API will be available at `http://localhost:8000`

View interactive API docs at: `http://localhost:8000/docs`

### Test It

```bash
# In another terminal
python example_usage.py
```

## 📝 API Endpoints

### POST `/analyze`
Analyze a single piece of content.

**Request:**
```json
{
  "text": "Your content here",
  "source_url": "https://twitter.com/...",
  "author": "username",
  "timestamp": "2024-01-01T00:00:00"
}
```

**Response:**
```json
{
  "classification": "propaganda",
  "confidence": 0.87,
  "risk_score": 75.3,
  "reasoning": {
    "propaganda_score": 0.85,
    "campaign_score": 0.23,
    "sentiment_extremity": 0.72,
    "false_claim_ratio": 0.33
  },
  "fact_checks": [
    {
      "claim": "95% of people support this claim",
      "verdict": "false",
      "confidence": 0.92,
      "source": "internal_knowledge_base"
    }
  ],
  "flags": [
    "High emotional language detected",
    "Suspicious formatting patterns detected",
    "Contains potentially false claims"
  ]
}
```

### POST `/batch`
Analyze multiple pieces of content at once.

**Request:**
```json
[
  {"text": "First post"},
  {"text": "Second post"},
  {"text": "Third post"}
]
```

**Response:** Array of analysis results

### GET `/health`
Check if API is running.

## 🔬 Detection Mechanisms

### Propaganda Detection

**Indicators:**
- Emotional language (destroy, enemy, threat, outrageous)
- Absolute statements (always, never, all, none)
- Us vs. them framing ("they're trying to...", "those people")
- ALL CAPS text and excessive punctuation
- Appeals to "truth" or "real news"
- Word repetition
- Extreme sentiment

**Example:**
```
"WAKE UP!!! They're DESTROYING our country! 
Everyone needs to see this TRUTH before they take it down!"
→ Classification: PROPAGANDA (Risk: 85/100)
```

### Paid Campaign Detection

**Indicators:**
- Commercial keywords (buy, sale, free, discount, special offer)
- Calls-to-action (click here, swipe up, link in bio, use code)
- URLs and shortened links
- Promotional hashtags (#ad, #sponsored, #affiliate)
- Limited-time language
- Discount codes

**Example:**
```
"Use code SAVE20 for 20% off! Limited time only! 
Click link in bio to shop now! #ad #sponsored"
→ Classification: PAID_CAMPAIGN (Risk: 65/100)
```

## 🔍 Fact-Checking Integration

The system includes:

1. **Internal Knowledge Base**: Common false claims (vaccines, moon landing, etc.)
2. **Advanced API Integration** (`advanced_fact_checking.py`):
   - Google Fact Check API
   - Snopes API
   - PolitiFact API
   - Wikipedia verification
   - Claim extraction via NLP

### Using Advanced Fact-Checking

```python
from advanced_fact_checking import MultiSourceFactChecker

checker = MultiSourceFactChecker()
results = checker.check_all_sources("Your controversial claim here")

for result in results:
    print(f"{result.claim}: {result.verdict}")
    print(f"  Source: {result.reviewer_organization}")
```

## 🛠️ Customization

### Add Custom Detection Patterns

Edit `content_detector_api.py`:

```python
class PropagandaDetector:
    def __init__(self):
        self.propaganda_keywords = {
            "your_category": ["word1", "word2", "word3"],
        }
```

### Adjust Risk Scoring

Modify the classification thresholds:

```python
if propaganda_score > 0.6:  # Change this threshold
    classification = "propaganda"
```

### Integrate Your Own Fact-Checking

```python
def fact_check_claims(self, claims):
    # Add your custom fact-checking logic
    for claim in claims:
        # Your API call or lookup
        results.append(FactCheckClaim(...))
    return results
```

## 📱 Integration Examples

### Twitter/X Monitoring
```python
import tweepy
from client import ContentDetectorClient

detector = ContentDetectorClient()
client = tweepy.Client(bearer_token="YOUR_TOKEN")

tweets = client.get_users_tweets(id="USER_ID")
for tweet in tweets.data:
    result = detector.analyze_single(tweet.text)
    if result['risk_score'] > 70:
        print(f"Flagged: {tweet.text}")
```

### Web Dashboard
See `example_usage.py` for Flask dashboard template

### Browser Extension
```javascript
// Content script for browser extension
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: request.text})
  })
  .then(r => r.json())
  .then(data => sendResponse(data));
});
```

## 🎓 Understanding the Score

**Risk Score (0-100)**
- 0-30: Low risk (likely neutral)
- 31-60: Medium risk (mixed signals)
- 61-100: High risk (propaganda or false claims)

**Confidence (0-1)**
- Indicates how certain the classification is
- High confidence = strong signal
- Low confidence = mixed or ambiguous content

**Fact-Check Results**
- `true`: Claim verified as accurate
- `false`: Claim contradicted by sources
- `mixed`: Partially true or misleading
- `unverified`: Insufficient data

## 🚨 Known Limitations

1. **Language**: Optimized for English; other languages need translation
2. **Context**: Doesn't understand full context/sarcasm
3. **Evolving Tactics**: New propaganda techniques emerge constantly
4. **False Positives**: Satire or strong opinions may be flagged
5. **Fact-Checking API Limits**: May hit rate limits on free tiers

## 🔄 Future Improvements

- [ ] Multilingual support
- [ ] ML model training on labeled datasets
- [ ] Network analysis (bot detection, coordinated campaigns)
- [ ] Image/video analysis
- [ ] Real-time social media monitoring
- [ ] Dashboard with historical tracking
- [ ] User feedback loop for model improvement
- [ ] Integration with Hugging Face models for better NLP

## 📊 Datasets for Training

To improve detection, train on:
- **Propaganda**: NewsGuard dataset, PROPAGANDA dataset
- **Paid Campaigns**: Transparency reports from Meta, Twitter
- **Fact-Checks**: ClaimBuster, FEVER dataset, LIAR dataset

## 🔐 Deployment

### Docker
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "content_detector_api.py"]
```

Run:
```bash
docker build -t content-detector .
docker run -p 8000:8000 content-detector
```

### Production Checklist
- [ ] Add authentication (API keys)
- [ ] Implement rate limiting
- [ ] Add logging and monitoring
- [ ] Use HTTPS
- [ ] Cache fact-check results
- [ ] Set up proper error handling
- [ ] Load balance across multiple instances
- [ ] Add database for historical data

## 📚 Resources & References

**Propaganda Detection:**
- Wei, L., et al. "Detecting All Abuse! Toward Universal Abusive Language Detection Models" (2021)
- PROPAGANDA: https://propaganda.math.unipd.it/

**Fact-Checking:**
- Google Fact Check API: https://developers.google.com/fact-check/tools/api
- Snopes API: https://www.snopes.com/
- PolitiFact: https://www.politifact.com/

**Datasets:**
- FEVER: Fact Extraction and VERification: https://fever.ai/
- LIAR: A Benchmark Dataset for Fake News Detection: https://datasets.mendeley.com/datasets/7fvnjvj8vx/1

## 📄 License

Open source for research and non-commercial use.

## 🤝 Contributing

Contributions welcome! Areas needing work:
- Multilingual support
- Better fact-checking integration
- ML model improvements
- Frontend dashboard

## ⚠️ Ethical Considerations

This tool should be used responsibly:
- Not for mass surveillance
- Respect privacy regulations (GDPR, CCPA)
- Be transparent about AI-based flagging
- Allow for human review and appeals
- Don't use to suppress legitimate speech
- Consider false positives carefully

## 📧 Support

For questions or issues, please provide:
1. Example content that was misclassified
2. Expected vs. actual result
3. Relevant context

---

**Built with ❤️ for cleaner information ecosystems**
