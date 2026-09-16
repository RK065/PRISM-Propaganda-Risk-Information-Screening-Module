"""
Advanced Fact-Checking Module
Integrates with real fact-checking APIs and services
"""

import os
import re
import logging
import requests
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
import json

from config import GOOGLE_FACT_CHECK_SOURCES

logger = logging.getLogger("fact_checker")


@dataclass
class FactCheckResult:
    claim: str
    verdict: str  # true, false, mixed, unverified
    verdict_source: str
    confidence: float
    review_url: str
    reviewer_organization: str
    published_date: Optional[str] = None


class MultiSourceFactChecker:
    """Fact-checking using multiple real APIs"""

    def __init__(self):
        self.google_fact_check_api = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        self.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        self.claimbuster_api_key = os.environ.get("CLAIMBUSTER_API_KEY", "")
        self.mbfc_api_key = os.environ.get("MBFC_API_KEY", "")

    # ---- single reusable helper ----

    def fact_check_google_source(self, text: str, source: dict) -> List[FactCheckResult]:
        """
        Query Google Fact Check API filtered to a specific publisher site.
        source: one entry from config.GOOGLE_FACT_CHECK_SOURCES
        """
        results = []
        try:
            params = {
                "query": text,
                "key": self.google_api_key,
                "languageCode": source["language"],
                "reviewPublisherSiteFilter": source["site"],
            }
            response = requests.get(self.google_fact_check_api, params=params, timeout=10)
            response.raise_for_status()
            verdict_map = source["verdict_map"]
            for claim in response.json().get("claims", [])[:3]:
                review = claim.get("claimReview", [{}])[0]
                verdict_text = review.get("textualRating", "unverified").lower()
                results.append(FactCheckResult(
                    claim=claim.get("text", text)[:100],
                    verdict=verdict_map.get(verdict_text, "unverified"),
                    verdict_source=source["label"],
                    confidence=source["confidence"],
                    review_url=review.get("url", ""),
                    reviewer_organization=source["org"],
                    published_date=review.get("reviewDate"),
                ))
        except requests.RequestException as e:
            logger.warning("%s fact check error: %s", source['label'], e)
        return results

    # ---- Google generic (no site filter) ----

    def fact_check_google(self, text: str, limit: int = 5) -> List[FactCheckResult]:
        """Use Google Fact Check API without a site filter"""
        results = []
        verdict_map = {
            "true": "true", "false": "false", "mixed": "mixed",
            "disputed": "mixed", "partially true": "mixed", "misleading": "false",
        }
        try:
            params = {"query": text, "key": self.google_api_key, "languageCode": "en"}
            response = requests.get(self.google_fact_check_api, params=params, timeout=10)
            response.raise_for_status()
            for claim in response.json().get("claims", [])[:limit]:
                review = claim.get("claimReview", [{}])[0]
                verdict_text = review.get("textualRating", "unverified").lower()
                results.append(FactCheckResult(
                    claim=claim.get("text", text)[:100],
                    verdict=verdict_map.get(verdict_text, "unverified"),
                    verdict_source="Google Fact Check",
                    confidence=0.85,
                    review_url=review.get("url", ""),
                    reviewer_organization=review.get("publisher", {}).get("name", "Unknown"),
                    published_date=review.get("reviewDate"),
                ))
        except requests.RequestException as e:
            logger.warning("Google Fact Check API error: %s", e)
        return results

    # ---- Non-Google sources ----

    def fact_check_snopes(self, text: str) -> List[FactCheckResult]:
        """Check against Snopes (unofficial endpoint — placeholder for integration)"""
        results = []
        try:
            response = requests.get(
                "https://www.snopes.com/api/v1/search/",
                params={"q": text},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if response.status_code == 200:
                data = response.json()
                results = [
                    FactCheckResult(
                        claim=item.get("title", text)[:100],
                        verdict=item.get("status", "unverified").lower(),
                        verdict_source="Snopes",
                        confidence=0.8,
                        review_url=item.get("url", ""),
                        reviewer_organization="Snopes.com",
                        published_date=item.get("publish_date"),
                    )
                    for item in data.get("results", [])[:3]
                ]
        except requests.RequestException as e:
            logger.warning("Snopes fact check error: %s", e)
        return results

    def fact_check_politifact(self, text: str) -> List[FactCheckResult]:
        """PolitiFact statements API"""
        results = []
        try:
            response = requests.get(
                "https://www.politifact.com/api/v2/statements/",
                params={"text__contains": text[:50]},
                timeout=10,
            )
            if response.status_code == 200:
                for statement in response.json().get("results", [])[:3]:
                    ruling = statement.get("ruling", {})
                    results.append(FactCheckResult(
                        claim=statement.get("statement", text)[:100],
                        verdict=ruling.get("slug", "unverified"),
                        verdict_source="PolitiFact",
                        confidence=0.85,
                        review_url=statement.get("url", ""),
                        reviewer_organization="PolitiFact",
                        published_date=statement.get("statement_date"),
                    ))
        except requests.RequestException as e:
            logger.warning("PolitiFact fact check error: %s", e)
        return results

    def fact_check_wikipedia(self, text: str) -> List[FactCheckResult]:
        """Basic Wikipedia reference check"""
        results = []
        try:
            import wikipedia
            for topic in self._extract_topics(text)[:3]:
                try:
                    page = wikipedia.page(topic)
                    results.append(FactCheckResult(
                        claim=f"Reference to '{topic}'",
                        verdict="true",
                        verdict_source="Wikipedia",
                        confidence=0.7,
                        review_url=page.url,
                        reviewer_organization="Wikipedia",
                        published_date=None,
                    ))
                except (wikipedia.exceptions.DisambiguationError,
                        wikipedia.exceptions.PageError):
                    pass
        except ImportError:
            logger.warning("Wikipedia API not installed. Install with: pip install wikipedia-api")
        return results

    def fact_check_claimbuster(self, text: str) -> List[FactCheckResult]:
        """ClaimBuster API — academic claim scoring"""
        results = []
        try:
            response = requests.post(
                "https://idir.uta.edu/claimbuster/api/v2/score/text/",
                headers={"x-api-key": self.claimbuster_api_key},
                json={"input_text": text[:500]},
                timeout=10,
            )
            if response.status_code == 200:
                for item in response.json().get("results", [])[:3]:
                    score = item.get("score", 0)
                    results.append(FactCheckResult(
                        claim=item.get("text", text)[:100],
                        verdict="unverified" if score < 0.5 else "mixed",
                        verdict_source="ClaimBuster",
                        confidence=score,
                        review_url="https://idir.uta.edu/claimbuster/",
                        reviewer_organization="UT Arlington IDIR Lab",
                    ))
        except requests.RequestException as e:
            logger.warning("ClaimBuster API error: %s", e)
        return results

    def fact_check_mbfc(self, text: str) -> List[FactCheckResult]:
        """Media Bias/Fact Check — source credibility ratings"""
        results = []
        try:
            response = requests.get(
                "https://api.mediabiasfactcheck.com/v1/search",
                headers={"Authorization": f"Bearer {self.mbfc_api_key}"},
                params={"q": text[:100]},
                timeout=10,
            )
            if response.status_code == 200:
                for item in response.json().get("results", [])[:3]:
                    factual = item.get("factual_reporting", "").lower()
                    verdict = "true" if "high" in factual else ("false" if "low" in factual else "mixed")
                    results.append(FactCheckResult(
                        claim=f"Source credibility: {item.get('name', text[:50])}",
                        verdict=verdict,
                        verdict_source="Media Bias/Fact Check",
                        confidence=0.75,
                        review_url=item.get("url", ""),
                        reviewer_organization="MediaBiasFactCheck.com",
                    ))
        except requests.RequestException as e:
            logger.warning("MBFC API error: %s", e)
        return results

    # ---- helpers ----

    def _extract_topics(self, text: str) -> List[str]:
        """Extract proper-noun topics for Wikipedia lookup"""
        import re
        matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        return list(set(matches))[:5]

    # ---- aggregate ----

    def check_all_sources(self, text: str) -> List[FactCheckResult]:
        """Fact-check across all sources and return deduplicated results sorted by confidence"""
        all_results: List[FactCheckResult] = []

        # Generic Google + non-Google sources
        all_results.extend(self.fact_check_google(text))
        all_results.extend(self.fact_check_snopes(text))
        all_results.extend(self.fact_check_politifact(text))
        all_results.extend(self.fact_check_wikipedia(text))
        all_results.extend(self.fact_check_claimbuster(text))
        all_results.extend(self.fact_check_mbfc(text))

        # All Google-filtered publisher sources from config
        for source in GOOGLE_FACT_CHECK_SOURCES:
            all_results.extend(self.fact_check_google_source(text, source))

        # Deduplicate by claim text, keeping highest-confidence result
        unique: dict = {}
        for result in all_results:
            key = result.claim.lower()
            if key not in unique or result.confidence > unique[key].confidence:
                unique[key] = result

        return sorted(unique.values(), key=lambda x: x.confidence, reverse=True)


# ============= CLAIM EXTRACTION =============

class AdvancedClaimExtractor:
    """
    Extract factual claims from text.
    Uses spaCy (en_core_web_sm) when available for sentence segmentation + NER;
    falls back to regex heuristics if spaCy is not installed.
    """

    def __init__(self):
        self._nlp = None
        try:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            pass  # spaCy or model not installed — regex fallback will be used

    # ---- claim-worthiness signals ----
    _CLAIM_VERBS = {"is", "are", "was", "were", "causes", "leads", "results",
                    "proves", "shows", "confirms", "reveals", "found", "says"}
    _STAT_RE = re.compile(r'\d+\s*%|\d+\s*(?:million|billion|thousand|percent)', re.I)

    def _is_claim_worthy(self, sent_text: str) -> bool:
        """Return True if a sentence looks like a factual claim worth checking."""
        lower = sent_text.lower()
        has_verb = any(f" {v} " in f" {lower} " for v in self._CLAIM_VERBS)
        has_stat = bool(self._STAT_RE.search(sent_text))
        return (has_verb or has_stat) and len(sent_text.strip()) > 15

    def extract_claims(self, text: str) -> List[str]:
        """Extract potentially false/controversial claims."""
        if self._nlp is not None:
            return self._extract_with_spacy(text)
        return self._extract_with_regex(text)

    def _extract_with_spacy(self, text: str) -> List[str]:
        """spaCy-based extraction: sentence segmentation + NER context."""
        doc = self._nlp(text)
        # Collect named entities for context
        entities = {ent.text for ent in doc.ents
                    if ent.label_ in {"PERSON", "ORG", "GPE", "NORP", "EVENT", "LAW"}}
        claims = []
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not self._is_claim_worthy(sent_text):
                continue
            # Boost priority if sentence contains a named entity
            has_entity = any(ent in sent_text for ent in entities)
            claims.append((sent_text, has_entity))
        # Sort: entity-containing claims first
        claims.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in claims][:10]

    def _extract_with_regex(self, text: str) -> List[str]:
        """Regex fallback when spaCy is unavailable."""
        pattern1 = r'(?:^|\s)([A-Z][^.!?]*(?:is|are|was|were)[^.!?]*[.!?])'
        pattern2 = r'(\d+%?\s+(?:of|percent|million|billion)[^.!?]*[.!?])'
        pattern3 = r'([^.!?]*(?:causes|leads to|results in|because)[^.!?]*[.!?])'
        claims = [
            m.strip()
            for pattern in (pattern1, pattern2, pattern3)
            for m in re.findall(pattern, text)
        ]
        return list({c for c in claims if len(c) > 15})[:10]


# ============= EXAMPLE USAGE =============

if __name__ == "__main__":
    fact_checker = MultiSourceFactChecker()
    claim_extractor = AdvancedClaimExtractor()

    example_text = """
    A recent study showed that 95% of vaccines cause severe reactions.
    The Earth is actually flat and NASA is covering it up.
    Coffee consumption was proven to add 20 years to your life.
    """

    print("=== Advanced Fact-Checking Example ===\n")
    print("Extracting claims...")
    for i, claim in enumerate(claim_extractor.extract_claims(example_text), 1):
        print(f"  {i}. {claim}")

    print("\n\nFact-checking from multiple sources...")
    for result in fact_checker.check_all_sources(example_text):
        print(f"\nClaim: {result.claim}")
        print(f"  Verdict: {result.verdict.upper()}")
        print(f"  Source: {result.verdict_source} ({result.reviewer_organization})")
        print(f"  Confidence: {result.confidence:.0%}")
        if result.review_url:
            print(f"  URL: {result.review_url}")
