# Architecture & Deployment Guide

## System Architecture

### Core Components

```
┌────────────────────────────────────────────────────────┐
│                    FastAPI Server                      │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │         Content Analyzer Pipeline               │  │
│  │                                                 │  │
│  │  Input → Validate → Analyze → Score → Output  │  │
│  └─────────────────────────────────────────────────┘  │
│           ↓                    ↓                        │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Propaganda       │  │ Campaign Detector        │  │
│  │ Detector         │  │                          │  │
│  │ • Language       │  │ • Commercial keywords    │  │
│  │ • Sentiment      │  │ • CTAs                   │  │
│  │ • Patterns       │  │ • Disclosures            │  │
│  └──────────────────┘  └──────────────────────────┘  │
│           ↓                    ↓                        │
│  ┌────────────────────────────────────────────────┐  │
│  │    Fact-Checking Engine                       │  │
│  │  • Extract claims                             │  │
│  │  • Check multiple sources                     │  │
│  │  • Aggregate results                          │  │
│  └────────────────────────────────────────────────┘  │
│                        ↓                               │
│  ┌────────────────────────────────────────────────┐  │
│  │    Classification & Scoring                    │  │
│  │  • Combine all signals                         │  │
│  │  • Calculate confidence                        │  │
│  │  • Generate flags                              │  │
│  └────────────────────────────────────────────────┘  │
│                        ↓                               │
│                   JSON Response                        │
└────────────────────────────────────────────────────────┘
```

## Classification Decision Tree

```
                    Content Input
                         │
                    ┌────┴────┐
                    ▼         ▼
           ┌──────────────┐  ┌─────────────────┐
           │ Propaganda   │  │ Campaign Score  │
           │ Score > 0.6  │  │ > 0.6           │
           └──────────────┘  └─────────────────┘
              │         │         │         │
         YES │         │ NO  YES │         │ NO
            ▼         │        ▼         │
      ┌─────────┐    │   ┌──────────┐   │
      │Prop = T │    │   │Camp = T  │   │
      └─────────┘    │   └──────────┘   │
          │          │         │        │
          ├──────┬───┤         │        │
          │      │   │         │        │
          ▼      ▼   ▼         ▼        ▼
       MIXED CAMPAIGN NEUTRAL MIXED  NEUTRAL
     (if both > 0.5)  (both low)   (if both > 0.5)


Risk Score = Propaganda Score × 40% + Campaign Score × 30% + False Claims × 30%
```

## Implementation Approaches

### Approach 1: Lightweight (MVP - 2-3 days)
**Best for:** Quick prototype, limited budget, small deployment

```
Architecture:
  • Single FastAPI server
  • Basic pattern matching
  • Internal knowledge base only
  • Single database (SQLite)
  • No external API calls

Pros:
  ✓ Fast to build
  ✓ Low operational cost
  ✓ No external dependencies
  ✓ Easy to deploy locally

Cons:
  ✗ Limited fact-checking
  ✗ Only English
  ✗ Accuracy ~70-75%
  ✗ No real-time updates
```

**File to use:** `content_detector_api.py` (standalone)

### Approach 2: Standard (Recommended - 1-2 weeks)
**Best for:** Production deployment, medium scale, good accuracy needed

```
Architecture:
  • FastAPI backend
  • Redis caching
  • PostgreSQL database
  • Fact-check API integrations
  • React frontend
  • Docker containerization

Services:
  - API Server (multiple instances)
  - Cache layer
  - Database
  - Monitoring & logging
  - Background job queue for batch processing

Pros:
  ✓ Good accuracy (~80-85%)
  ✓ Scalable
  ✓ Real fact-checking
  ✓ Web dashboard
  ✓ Production-ready

Cons:
  ✗ More complex
  ✗ Higher operational cost
  ✗ Requires DevOps
```

**Files to use:** 
- `content_detector_api.py` + `advanced_fact_checking.py`
- Plus database + caching layer

### Approach 3: Enterprise (Advanced - 3-4 weeks)
**Best for:** Large-scale deployment, high reliability, custom needs

```
Architecture:
  • Microservices:
    - Propaganda detector service
    - Campaign detector service
    - Fact-checking orchestrator
    - API gateway
  • Kubernetes orchestration
  • ElasticSearch for logging
  • Prometheus monitoring
  • ML model serving (TensorFlow/PyTorch)
  • Multiple data sources
  • Real-time streaming pipeline

Infrastructure:
  - Load balancer
  - Multiple API instances
  - Cache clusters (Redis)
  - Database replicas
  - Message queue (Kafka/RabbitMQ)
  - ML model service

Pros:
  ✓ Highest accuracy (~85-90%)
  ✓ Highly scalable
  ✓ Resilient to failures
  ✓ Real-time processing
  ✓ Custom ML models
  ✓ Enterprise monitoring

Cons:
  ✗ Complex system
  ✗ Expensive infrastructure
  ✗ Requires experienced team
  ✗ Maintenance overhead
```

## Deployment Options

### Option 1: Local/Development
```bash
# Single command deployment
python content_detector_api.py

# Access at http://localhost:8000
```

### Option 2: Docker (Recommended for Development)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "content_detector_api:app", "--host", "0.0.0.0"]
```

```bash
docker build -t content-detector:latest .
docker run -p 8000:8000 content-detector:latest
```

### Option 3: Cloud Platforms

**AWS**
```yaml
# Using AWS Lambda + API Gateway
Runtime: Python 3.10
Memory: 1024 MB
Timeout: 30 seconds
Environment: requirements.txt

# Cost: ~$0.20 per 1M requests
```

**Google Cloud**
```yaml
# Using Cloud Run
Container: Docker image
Memory: 512MB
Timeout: 60 seconds

# Cost: $0.15 per 1M requests
```

**Azure**
```yaml
# Using Azure Functions
Runtime: Python 3.10
Trigger: HTTP
Plan: Consumption

# Cost: $0.20 per 1M requests
```

**Heroku** (Simplest)
```bash
# 1. Create Procfile
web: uvicorn content_detector_api:app --host=0.0.0.0 --port=$PORT

# 2. Deploy
git push heroku main

# Cost: $7-50/month
```

### Option 4: On-Premise (Enterprise)
```yaml
Infrastructure:
  - Multiple servers (3+)
  - Load balancer (Nginx/HAProxy)
  - Database server (PostgreSQL)
  - Cache layer (Redis)
  - Monitoring stack (Prometheus + Grafana)

Scaling:
  - Horizontal: Add more API servers
  - Vertical: Increase server resources
  - Database: Implement replication
```

## Scaling Considerations

### Small Scale (< 1000 requests/day)
- Single server
- SQLite database
- No caching needed
- Cost: ~$5-20/month

### Medium Scale (1K-100K requests/day)
- 2-3 API servers
- PostgreSQL database
- Redis cache
- Background worker queue
- Cost: ~$50-200/month

### Large Scale (> 100K requests/day)
- 5-10+ API servers
- Database clusters
- Advanced caching
- Message queue system
- Monitoring stack
- Cost: $500+/month

## Performance Tuning

### API Response Time Targets

**Current Performance:**
- Single request: ~200-500ms
- Batch (10 items): ~1-2s
- Fact-checking adds: ~500ms-2s per request

### Optimization Strategies

1. **Caching**
   ```python
   # Cache fact-check results
   @cache.cached(timeout=86400)  # 24 hours
   def get_fact_check(claim):
       return fact_checker.check(claim)
   ```

2. **Async Processing**
   ```python
   # Move fact-checking to background task
   from celery import shared_task
   
   @shared_task
   def fact_check_async(claim_id):
       # Fact-check in background
       pass
   ```

3. **Database Indexing**
   ```sql
   CREATE INDEX idx_claim_text ON fact_checks (claim_text);
   CREATE INDEX idx_verdict ON fact_checks (verdict);
   ```

4. **API Rate Limiting**
   ```python
   from slowapi import Limiter
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/analyze")
   @limiter.limit("100/minute")
   async def analyze(content: ContentInput):
       pass
   ```

## Monitoring & Logging

### Key Metrics to Track
- API response time (p50, p95, p99)
- Classification accuracy
- False positive rate
- False negative rate
- Cache hit ratio
- Error rate
- Request volume

### Recommended Stack
```
Metrics: Prometheus
Visualization: Grafana
Logging: ELK Stack (Elasticsearch, Logstash, Kibana)
Tracing: Jaeger
Alerting: Alertmanager
```

### Sample Prometheus Metrics
```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
response_time = Histogram('response_time_seconds', 'Response time')
classification_accuracy = Gauge('classification_accuracy', 'Accuracy')

@app.post("/analyze")
async def analyze(content: ContentInput):
    request_count.inc()
    with response_time.time():
        result = classifier.classify(content)
    return result
```

## Security Considerations

### Input Validation
```python
class ContentInput(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source_url: Optional[str] = Field(regex=r'^https?://')
```

### Rate Limiting
- 100 requests/minute per IP
- 1000 requests/hour per API key

### Data Privacy
```python
# Encrypt sensitive data at rest
from cryptography.fernet import Fernet

cipher = Fernet(key)
encrypted_text = cipher.encrypt(content.text.encode())
```

### HTTPS/TLS
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    proxy_pass http://localhost:8000;
}
```

## Testing Strategy

### Unit Tests
```python
def test_propaganda_detector():
    detector = PropagandaDetector()
    text = "WAKE UP!!! They're destroying everything!!!"
    score = detector.analyze_language(text)
    assert score['emotional_words'] > 0.5

def test_campaign_detector():
    detector = PaidCampaignDetector()
    text = "Buy now! Use code SAVE20! #ad #sponsored"
    score = detector.detect_commercial_language(text)
    assert score > 0.7
```

### Integration Tests
```python
def test_full_pipeline():
    result = classifier.classify(ContentInput(
        text="Sample propaganda text here",
        source_url="https://example.com"
    ))
    assert result.classification in ["propaganda", "paid_campaign", "neutral", "mixed"]
    assert 0 <= result.risk_score <= 100
```

### Performance Tests
```python
import time

def test_performance():
    content = ContentInput(text="x" * 1000)
    start = time.time()
    result = classifier.classify(content)
    elapsed = time.time() - start
    assert elapsed < 1.0  # Should complete in < 1 second
```

## Recommended Next Steps

1. **Week 1-2**: Build MVP with `content_detector_api.py`
2. **Week 2-3**: Add fact-checking APIs from `advanced_fact_checking.py`
3. **Week 3-4**: Build React dashboard
4. **Week 4-5**: Deploy to cloud platform
5. **Week 5+**: Iterate based on feedback, improve ML models

---

**Questions?** See README.md for more details or check the example code in example_usage.py
