import os
import re
import time
import logging
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import (
    PLATFORM_DOMAINS, PLATFORM_WEIGHTS, PLATFORM_INDICATORS,
    PROPAGANDA_KEYWORDS, PROPAGANDA_PATTERNS,
    CAMPAIGN_INDICATORS, COMMERCIAL_KEYWORDS, DISCLOSURE_KEYWORDS,
    THRESHOLDS, SCORING_WEIGHTS,
    RATE_LIMIT_PER_MINUTE, API_KEY_HEADER,
)
from database import init_db, save_analysis, submit_for_review
from cache import cache
from workers import enqueue, start_worker, stop_worker
from auth import router as auth_router, get_current_user
from dashboard import router as dashboard_router
from human_review import router as review_router
from llm_explainer import generate_explanation, retrieve_evidence
from rag import init_rag, fact_store
from ml_classifier import ContentMLClassifier
from feature_extractor import FeatureExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("content_detector")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_rag()
    start_worker()
    yield
    stop_worker()


app = FastAPI(title="Content Flag API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(review_router)

# ============= CORS =============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= RATE LIMITING =============

_rate_store: dict = defaultdict(list)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = time.time()
        window = 60
        _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window]
        if len(_rate_store[ip]) >= RATE_LIMIT_PER_MINUTE:
            logger.warning("Rate limit exceeded for IP: %s", ip)
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
        _rate_store[ip].append(now)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# ============= LEGACY API KEY AUTH (kept for backward compat) =============

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)
_EXPECTED_API_KEY = os.environ.get("API_KEY", "")

async def verify_api_key(api_key: Optional[str] = Depends(_api_key_header)):
    if not _EXPECTED_API_KEY:
        return
    if api_key != _EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# ============= DATA MODELS =============

class ContentInput(BaseModel):
    text: str
    source_url: Optional[str] = None
    author: Optional[str] = None
    timestamp: Optional[str] = None
    engagement_count: Optional[int] = 0
    platform: Optional[str] = None

class FactCheckClaim(BaseModel):
    claim: str
    verdict: str
    confidence: float
    source: str

class FlagResponse(BaseModel):
    classification: str
    confidence: float
    risk_score: float
    reasoning: dict
    fact_checks: list[FactCheckClaim]
    flags: list[str]

# ============= PLATFORM DETECTION =============

def detect_platform(source_url: Optional[str], platform: Optional[str]) -> str:
    if platform:
        return platform.lower()
    if source_url:
        url_lower = source_url.lower()
        for p, domains in PLATFORM_DOMAINS.items():
            if any(d in url_lower for d in domains):
                return p
    return "unknown"

# ============= PROPAGANDA DETECTION =============

class PropagandaDetector:
    # Context patterns that reduce propaganda score (legitimate uses of strong words)
    _CONTEXT_REDUCERS = [
        r'\b(historical|history|war|novel|film|book|study|research|report|according to)\b',
        r'\b(scientist|researcher|professor|expert|official|spokesperson)\b',
        r'\b(said|stated|reported|published|found|concluded|noted)\b',
    ]
    # Narrative manipulation patterns that boost score
    _NARRATIVE_PATTERNS = [
        r'\b(wake up|open your eyes|they don.t want you to know|hidden truth)\b',
        r'\b(share before (it.s )?deleted|forward this|spread the word)\b',
        r'\b(mainstream media|fake news|lamestream|deep state|globalist)\b',
        r'\b(sheeple|brainwashed|sleeping|controlled|puppet)\b',
        r'(\?{2,}|!{3,})',  # Multiple ? or !!!+
    ]

    def analyze_language(self, text: str) -> dict:
        scores = {}
        text_lower = text.lower()
        words = text_lower.split()
        word_count = max(len(words), 1)

        for category, kws in PROPAGANDA_KEYWORDS.items():
            count = sum(text_lower.count(w) for w in kws)
            scores[category] = min(count / word_count, 1.0)

        pattern_matches = sum(1 for p in PROPAGANDA_PATTERNS if re.search(p, text))
        scores["suspicious_patterns"] = min(pattern_matches / len(PROPAGANDA_PATTERNS), 1.0)

        if words:
            from collections import Counter as _Counter
            top_freq = _Counter(words).most_common(1)[0][1] / len(words)
            scores["word_repetition"] = min(top_freq * 5, 1.0)
        else:
            scores["word_repetition"] = 0

        # Context-aware adjustment: reduce score when legitimate context detected
        context_hits = sum(
            1 for p in self._CONTEXT_REDUCERS if re.search(p, text, re.I)
        )
        context_reduction = min(context_hits * 0.08, 0.25)

        # Narrative manipulation boost
        narrative_hits = sum(
            1 for p in self._NARRATIVE_PATTERNS if re.search(p, text, re.I)
        )
        scores["narrative_manipulation"] = min(narrative_hits / len(self._NARRATIVE_PATTERNS), 1.0)

        # Apply context reduction to all keyword scores
        for key in list(scores.keys()):
            scores[key] = max(scores[key] - context_reduction, 0.0)

        return scores

    def check_sentiment_extremity(self, text: str) -> float:
        emotional_count = sum(
            text.lower().count(word)
            for word in PROPAGANDA_KEYWORDS.get("emotional_words", [])
        )
        base = min(emotional_count / max(len(text.split()), 1) * 10, 1.0)
        # Reduce if text has journalistic/academic context
        context_hits = sum(
            1 for p in self._CONTEXT_REDUCERS if re.search(p, text, re.I)
        )
        return max(base - context_hits * 0.1, 0.0)

# ============= PAID CAMPAIGN DETECTION =============

class PaidCampaignDetector:
    def detect_commercial_language(self, text: str) -> float:
        text_lower = text.lower()
        matches = sum(1 for kw in COMMERCIAL_KEYWORDS if kw in text_lower)
        return min(matches / max(len(COMMERCIAL_KEYWORDS), 1), 1.0)

    def detect_call_to_action(self, text: str) -> float:
        matches = sum(1 for p in CAMPAIGN_INDICATORS if re.search(p, text, re.IGNORECASE))
        return min(matches / len(CAMPAIGN_INDICATORS), 1.0)

    def check_disclosure(self, text: str) -> float:
        has_disclosure = any(kw in text.lower() for kw in DISCLOSURE_KEYWORDS)
        return 0.8 if has_disclosure else 0.2

# ============= FACT-CHECKING ENGINE =============

class FactChecker:
    def __init__(self):
        self.known_false_claims = {
            "earth is flat": ("false", 0.95),
            "vaccines cause autism": ("false", 0.98),
            "moon landing was fake": ("false", 0.99),
        }
        self.known_true_claims = {
            "water boils at 100 degrees celsius": ("true", 0.99),
            "gravity exists": ("true", 0.99),
        }

    def extract_claims(self, text: str) -> list[str]:
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20][:5]

    def fact_check_claims(self, claims: list[str]) -> list[FactCheckClaim]:
        results = []
        for claim in claims:
            claim_lower = claim.lower()
            for known, (verdict, confidence) in self.known_false_claims.items():
                if known in claim_lower:
                    results.append(FactCheckClaim(
                        claim=claim[:100], verdict=verdict,
                        confidence=confidence, source="internal_knowledge_base"
                    ))
                    break
            else:
                for known, (verdict, confidence) in self.known_true_claims.items():
                    if known in claim_lower:
                        results.append(FactCheckClaim(
                            claim=claim[:100], verdict=verdict,
                            confidence=confidence, source="internal_knowledge_base"
                        ))
                        break
        return results

# ============= MAIN CLASSIFIER =============

class ContentClassifier:
    def __init__(self):
        # Rule-based detectors (kept as fallback + flag generation)
        self.propaganda_detector = PropagandaDetector()
        self.campaign_detector = PaidCampaignDetector()
        self.fact_checker = FactChecker()
        self.feature_extractor = FeatureExtractor()

        # ML model (primary classifier when available)
        self.ml_model = ContentMLClassifier()
        self._use_ml = self.ml_model.load_model("models/current")
        if self._use_ml:
            logger.info("ML model loaded — using hybrid ML classification")
        else:
            logger.info("No ML model found — using rule-based fallback")

    def _platform_flags(self, text: str, platform: str) -> list[str]:
        indicators = PLATFORM_INDICATORS.get(platform, [])
        matches = sum(1 for p in indicators if re.search(p, text, re.IGNORECASE))
        if matches >= THRESHOLDS["platform_indicator_min_matches"]:
            return [f"Platform-specific patterns detected for {platform}"]
        return []

    def _generate_flags(self, features: dict, class_probs: dict,
                        false_claim_ratio: float, platform: str,
                        text: str) -> list[str]:
        """Generate human-readable flags from features and ML probabilities."""
        flags = []

        # From ML probabilities
        if class_probs.get("propaganda", 0) > 0.5:
            flags.append("High emotional language detected")
        if class_probs.get("paid_campaign", 0) > 0.5:
            flags.append("Promotional/commercial content detected")

        # From rule-based features (interpretability)
        if false_claim_ratio > THRESHOLDS["false_claim_flag"]:
            flags.append("Contains potentially false claims")
        if features.get("has_disclosure", 0) < 0.5 and class_probs.get("paid_campaign", 0) > 0.3:
            flags.append("Missing advertising disclosures")
        if features.get("caps_ratio", 0) > 0.3:
            flags.append("Excessive ALL CAPS usage detected")
        if features.get("suspicious_pattern_count", 0) > 2:
            flags.append("Suspicious formatting patterns detected")

        # Platform-specific flags
        flags.extend(self._platform_flags(text, platform))

        return flags or ["No major red flags detected"]

    def _classify_rules(self, content: ContentInput) -> FlagResponse:
        """Original rule-based classification (fallback path)."""
        text = content.text
        platform = detect_platform(content.source_url, content.platform)
        weights = PLATFORM_WEIGHTS.get(platform, PLATFORM_WEIGHTS["unknown"])
        sw = SCORING_WEIGHTS

        prop_analysis = self.propaganda_detector.analyze_language(text)
        sentiment_extremity = self.propaganda_detector.check_sentiment_extremity(text)
        propaganda_score = min((
            sum(prop_analysis.values()) / len(prop_analysis) * sw["propaganda"]["language"] +
            sentiment_extremity * sw["propaganda"]["sentiment"]
        ) * weights["propaganda"], 1.0)

        commercial_score = self.campaign_detector.detect_commercial_language(text)
        cta_score = self.campaign_detector.detect_call_to_action(text)
        disclosure_score = self.campaign_detector.check_disclosure(text)
        campaign_score = min((
            commercial_score * sw["campaign"]["commercial"] +
            cta_score * sw["campaign"]["cta"] +
            (1 - disclosure_score) * sw["campaign"]["no_disclosure"]
        ) * weights["campaign"], 1.0)

        claims = self.fact_checker.extract_claims(text)
        fact_checks = self.fact_checker.fact_check_claims(claims)
        false_claim_ratio = sum(1 for fc in fact_checks if fc.verdict == "false") / max(len(fact_checks), 1)

        t = THRESHOLDS
        if propaganda_score > t["propaganda_high"] and campaign_score < t["campaign_high"]:
            classification, confidence = "propaganda", propaganda_score
        elif campaign_score > t["campaign_high"] and propaganda_score < t["propaganda_high"]:
            classification, confidence = "paid_campaign", campaign_score
        elif propaganda_score > t["propaganda_mixed"] and campaign_score > t["campaign_mixed"]:
            classification = "mixed"
            confidence = (propaganda_score + campaign_score) / 2
        else:
            classification = "neutral"
            confidence = 1 - max(propaganda_score, campaign_score)

        rw = sw["risk"]
        risk_score = (
            propaganda_score * rw["propaganda"] +
            campaign_score * rw["campaign"] +
            false_claim_ratio * rw["false_claims"]
        )

        flags = []
        if propaganda_score > t["propaganda_high"]:
            flags.append("High emotional language detected")
        if campaign_score > t["campaign_high"]:
            flags.append("Promotional/commercial content detected")
        if false_claim_ratio > t["false_claim_flag"]:
            flags.append("Contains potentially false claims")
        if disclosure_score < t["disclosure_flag"]:
            flags.append("Missing advertising disclosures")
        if len([p for p in PROPAGANDA_PATTERNS if re.search(p, text)]) > 2:
            flags.append("Suspicious formatting patterns detected")
        flags.extend(self._platform_flags(text, platform))

        return FlagResponse(
            classification=classification,
            confidence=confidence,
            risk_score=risk_score,
            reasoning={
                "propaganda_score": propaganda_score,
                "campaign_score": campaign_score,
                "sentiment_extremity": sentiment_extremity,
                "false_claim_ratio": false_claim_ratio,
                "platform": platform,
            },
            fact_checks=fact_checks,
            flags=flags or ["No major red flags detected"],
        )

    def classify(self, content: ContentInput) -> FlagResponse:
        """
        Classify content using ML model (primary) with rule-based fallback.

        Returns exactly the same FlagResponse schema regardless of which
        path is taken.
        """
        # Fallback to rules if no ML model
        if not self._use_ml:
            return self._classify_rules(content)

        text = content.text
        platform = detect_platform(content.source_url, content.platform)

        # --- ML prediction (primary classification) ---
        ml_result = self.ml_model.predict(text, platform)
        classification = ml_result["classification"]
        confidence = ml_result["confidence"]
        class_probs = ml_result["class_probabilities"]

        # --- Fact-checking (always rule-based) ---
        claims = self.fact_checker.extract_claims(text)
        fact_checks = self.fact_checker.fact_check_claims(claims)
        false_claim_ratio = (
            sum(1 for fc in fact_checks if fc.verdict == "false") /
            max(len(fact_checks), 1)
        )

        # --- Risk score from ML probabilities + fact-check ---
        risk_score = (
            class_probs.get("propaganda", 0) * 40 +
            class_probs.get("paid_campaign", 0) * 30 +
            false_claim_ratio * 30
        )
        risk_score = min(risk_score, 100)

        # --- Flags from rule-based features (interpretability) ---
        features = self.feature_extractor.extract(text, platform)
        flags = self._generate_flags(
            features, class_probs, false_claim_ratio, platform, text
        )

        return FlagResponse(
            classification=classification,
            confidence=confidence,
            risk_score=risk_score,
            reasoning={
                "propaganda_score": round(class_probs.get("propaganda", 0), 4),
                "campaign_score": round(class_probs.get("paid_campaign", 0), 4),
                "sentiment_extremity": round(features.get("emotional_word_ratio", 0), 4),
                "false_claim_ratio": round(false_claim_ratio, 4),
                "platform": platform,
            },
            fact_checks=fact_checks,
            flags=flags,
        )

# ============= API ENDPOINTS =============

classifier = ContentClassifier()

@app.post("/analyze", response_model=FlagResponse, dependencies=[Depends(verify_api_key)])
async def analyze_content(content: ContentInput):
    """Analyze content and flag as propaganda / paid campaign / neutral"""
    if not content.text or not content.text.strip() or len(content.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text must be at least 10 characters")

    cache_key = f"analyze:{hash(content.text)}"
    cached = await cache.get(cache_key)
    if cached:
        return FlagResponse(**cached)

    try:
        result = classifier.classify(content)
        result_dict = result.model_dump()

        await cache.set(cache_key, result_dict, ttl=300)

        platform = result.reasoning.get("platform", "unknown")
        analysis_id = await save_analysis(
            content.text, content.source_url, platform, result_dict
        )

        # Background: async fact-check + high-risk alert
        await enqueue("fact_check_async", {"text": content.text, "analysis_id": analysis_id})
        if result.risk_score > 60:
            await enqueue("high_risk_alert", {
                "analysis_id": analysis_id,
                "risk_score": result.risk_score,
                "classification": result.classification,
            })
            await submit_for_review(analysis_id)

        logger.info("classify platform=%s classification=%s confidence=%.2f risk=%.1f",
                    platform, result.classification, result.confidence, result.risk_score)
        return result
    except Exception:
        logger.exception("Unexpected error in /analyze")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


class ExplainRequest(BaseModel):
    text: str
    classification: str
    reasoning: dict
    flags: list[str]
    fact_checks: list = []


@app.post("/explain", dependencies=[Depends(verify_api_key)])
async def explain_content(req: ExplainRequest):
    """Generate LLM explanation + RAG evidence for a classification result."""
    try:
        explanation = await generate_explanation(
            req.text, req.classification, req.reasoning, req.flags, req.fact_checks
        )
        # RAG: retrieve grounding evidence for the most suspicious claim
        claims = re.split(r'[.!?]+', req.text)
        top_claim = next((s.strip() for s in claims if len(s.strip()) > 20), req.text[:200])
        rag_evidence = fact_store.search(top_claim, top_k=3)
        llm_evidence = await retrieve_evidence(top_claim)
        return {
            "explanation": explanation,
            "rag_evidence": rag_evidence,
            "llm_evidence": llm_evidence,
        }
    except Exception:
        logger.exception("Unexpected error in /explain")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/batch", response_model=list[FlagResponse], dependencies=[Depends(verify_api_key)])
async def analyze_batch(contents: list[ContentInput]):
    """Batch analyze multiple pieces of content"""
    if not contents:
        raise HTTPException(status_code=400, detail="Batch list cannot be empty")
    try:
        results = [classifier.classify(c) for c in contents]
        for content, result in zip(contents, results):
            platform = result.reasoning.get("platform", "unknown")
            await save_analysis(content.text, content.source_url, platform, result.model_dump())
        logger.info("batch size=%d", len(results))
        return results
    except Exception:
        logger.exception("Unexpected error in /batch")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
