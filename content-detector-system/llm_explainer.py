"""
LLM-assisted explanation generation.
Uses OpenAI-compatible API (set OPENAI_API_KEY + optionally OPENAI_BASE_URL).
Falls back to a rule-based template explanation when no API key is set.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("llm_explainer")

_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

_SYSTEM_PROMPT = """You are a content moderation analyst. Given a piece of text and its
classification scores, write a concise 2-3 sentence explanation for a human reviewer.
Be factual, neutral, and cite specific phrases from the text as evidence.
Do not repeat the scores verbatim — translate them into plain language."""


def _template_explanation(classification: str, reasoning: dict, flags: list[str]) -> str:
    """Rule-based fallback when no LLM is available."""
    prop = reasoning.get("propaganda_score", 0)
    camp = reasoning.get("campaign_score", 0)
    platform = reasoning.get("platform", "unknown")
    flag_summary = "; ".join(flags[:3]) if flags else "no major red flags"

    if classification == "propaganda":
        return (
            f"This content shows elevated propaganda signals (score {prop:.0%}) "
            f"on {platform}, including: {flag_summary}. "
            "It uses emotionally charged language and narrative manipulation patterns."
        )
    if classification == "paid_campaign":
        return (
            f"This content appears to be a paid promotion (score {camp:.0%}) "
            f"on {platform}. Detected: {flag_summary}."
        )
    if classification == "mixed":
        return (
            f"This content shows both propaganda ({prop:.0%}) and commercial ({camp:.0%}) "
            f"signals on {platform}. Detected: {flag_summary}."
        )
    return f"No significant manipulation signals detected on {platform}. {flag_summary}."


async def generate_explanation(
    text: str,
    classification: str,
    reasoning: dict,
    flags: list[str],
    fact_checks: Optional[list] = None,
) -> str:
    """
    Generate a human-readable explanation for a classification result.
    Returns LLM-generated text if OPENAI_API_KEY is set, else template fallback.
    """
    if not _API_KEY:
        return _template_explanation(classification, reasoning, flags)

    try:
        import httpx

        fact_summary = ""
        if fact_checks:
            false_claims = [fc for fc in fact_checks if fc.get("verdict") == "false"]
            if false_claims:
                fact_summary = f"\nFalse claims detected: {[fc['claim'] for fc in false_claims[:2]]}"

        user_msg = (
            f"Text (first 500 chars): {text[:500]}\n"
            f"Classification: {classification}\n"
            f"Scores: propaganda={reasoning.get('propaganda_score', 0):.2f}, "
            f"campaign={reasoning.get('campaign_score', 0):.2f}, "
            f"risk={reasoning.get('risk_score', 0):.1f}\n"
            f"Flags: {', '.join(flags[:5])}"
            f"{fact_summary}"
        )

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {_API_KEY}"},
                json={
                    "model": _MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.warning("LLM explanation failed: %s — using template fallback", e)
        return _template_explanation(classification, reasoning, flags)


async def retrieve_evidence(claim: str, top_k: int = 3) -> list[dict]:
    """
    Ask the LLM to retrieve supporting/contradicting evidence for a claim.
    Returns a list of {source, snippet, supports_claim} dicts.
    Falls back to empty list if no API key.
    """
    if not _API_KEY:
        return []

    try:
        import httpx

        prompt = (
            f"For the claim: \"{claim[:200]}\"\n"
            f"List {top_k} real, verifiable pieces of evidence (supporting or contradicting). "
            "Format each as JSON: {\"source\": \"...\", \"snippet\": \"...\", \"supports_claim\": true/false}"
        )

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {_API_KEY}"},
                json={
                    "model": _MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            import json, re
            raw = response.json()["choices"][0]["message"]["content"]
            # Extract JSON objects from the response
            matches = re.findall(r'\{[^{}]+\}', raw)
            results = []
            for m in matches[:top_k]:
                try:
                    results.append(json.loads(m))
                except json.JSONDecodeError:
                    pass
            return results

    except Exception as e:
        logger.warning("Evidence retrieval failed: %s", e)
        return []
