"""
Paid Promotion & Campaign Filter
Detects and categorizes paid promotions, sponsored content, and ad campaigns
across multiple media platforms.
"""

import re
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class PromotionResult:
    is_paid: bool
    promotion_type: str        # influencer_ad, brand_campaign, affiliate, sponsored_content, undisclosed_ad
    platform: str
    confidence: float          # 0-1
    disclosure_present: bool
    disclosure_tags: list[str]
    brand_mentions: list[str]
    cta_detected: list[str]
    risk_level: str            # low, medium, high
    flags: list[str]


# ============= PLATFORM-SPECIFIC PROMOTION PATTERNS =============

PLATFORM_PROMOTION_PATTERNS = {
    "instagram": {
        "disclosure":    [r"#ad\b", r"#sponsored", r"#gifted", r"#collab", r"#ambassador",
                          r"#partner", r"#affiliate", r"paid partnership", r"#promo"],
        "cta":           [r"link in bio", r"swipe up", r"use code \w+", r"dm (?:me )?for",
                          r"shop now", r"tap.*link", r"click.*link"],
        "influencer":    [r"gifted by", r"pr package", r"sent to me", r"in collaboration with",
                          r"working with", r"thank.*(?:brand|sponsor)", r"@\w+\s+(?:sent|gifted)"],
    },
    "youtube": {
        "disclosure":    [r"this video is sponsored", r"sponsored by", r"in partnership with",
                          r"paid promotion", r"#ad\b", r"#sponsored"],
        "cta":           [r"use code \w+", r"link.*description", r"check.*description",
                          r"discount.*below", r"promo code", r"affiliate link"],
        "influencer":    [r"today(?:'s)? (?:video )?(?:is )?(?:sponsored|brought to you)",
                          r"thanks? to \w+ for sponsoring", r"working with \w+",
                          r"partner(?:ed)? with"],
    },
    "twitter": {
        "disclosure":    [r"#ad\b", r"#sponsored", r"#partner", r"#affiliate", r"#promo"],
        "cta":           [r"click.*link", r"use code \w+", r"shop.*now", r"sign up",
                          r"limited.*offer", r"exclusive.*deal"],
        "influencer":    [r"in partnership", r"working with", r"collab(?:oration)? with",
                          r"gifted by", r"ambassador for"],
    },
    "youtube_shorts": {
        "disclosure":    [r"#ad\b", r"#sponsored", r"paid promotion"],
        "cta":           [r"link.*bio", r"use code \w+", r"swipe up", r"check.*link"],
        "influencer":    [r"gifted", r"sponsored", r"collab"],
    },
    "reddit": {
        "disclosure":    [r"\[sponsored\]", r"\[ad\]", r"promoted post", r"#sponsored"],
        "cta":           [r"use code \w+", r"sign up.*link", r"check.*link", r"affiliate"],
        "influencer":    [r"full disclosure", r"i was (?:paid|compensated)", r"brand deal"],
    },
    "whatsapp": {
        "disclosure":    [r"#ad\b", r"#sponsored", r"advertisement"],
        "cta":           [r"click.*link", r"use code \w+", r"order now", r"buy now",
                          r"limited.*offer", r"call.*order"],
        "influencer":    [r"brand ambassador", r"official.*partner", r"exclusive.*deal"],
    },
    "news": {
        "disclosure":    [r"advertis(?:ing|ement)", r"sponsored content", r"paid content",
                          r"brand(?:ed)? content", r"native advertising", r"partner content"],
        "cta":           [r"learn more", r"visit.*website", r"click here", r"find out more"],
        "influencer":    [r"in association with", r"brought to you by", r"presented by"],
    },
    "unknown": {
        "disclosure":    [r"#ad\b", r"#sponsored", r"#partner", r"advertisement"],
        "cta":           [r"click here", r"buy now", r"use code \w+", r"limited.*offer"],
        "influencer":    [r"gifted", r"sponsored", r"in partnership"],
    },
}

# Generic commercial keywords across all platforms
COMMERCIAL_KEYWORDS = [
    "buy", "sale", "discount", "offer", "promo", "deal", "free", "exclusive",
    "limited time", "order now", "shop", "checkout", "cart", "price", "save",
    "% off", "coupon", "voucher", "cashback", "referral", "earn",
]

# Brand signal patterns (@ mentions + capitalized brand-like words)
BRAND_PATTERNS = [
    r"@[A-Za-z0-9_]+",                          # @mentions
    r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b",         # CamelCase brand names
    r"\b[A-Z]{2,10}\b",                          # ALL CAPS brand abbreviations
]

# Promotion type classification rules
PROMOTION_TYPES = {
    "influencer_ad":      ["gifted", "collab", "ambassador", "pr package", "sent to me", "working with"],
    "affiliate":          ["affiliate", "referral", "use code", "promo code", "commission", "earn"],
    "sponsored_content":  ["sponsored by", "in partnership", "brought to you", "paid promotion", "brand deal"],
    "brand_campaign":     ["official", "launch", "new product", "introducing", "announcing", "campaign"],
    "undisclosed_ad":     [],  # fallback when paid signals exist but no disclosure
}


class PaidPromotionFilter:

    def __init__(self):
        self.commercial_keywords = COMMERCIAL_KEYWORDS

    def _detect_platform(self, platform: Optional[str], source_url: Optional[str]) -> str:
        if platform:
            return platform.lower()
        if source_url:
            url = source_url.lower()
            domain_map = {
                "instagram": ["instagram.com", "instagr.am"],
                "youtube":   ["youtube.com", "youtu.be"],
                "twitter":   ["twitter.com", "x.com", "t.co"],
                "reddit":    ["reddit.com", "redd.it"],
                "whatsapp":  ["whatsapp.com", "wa.me"],
                "news":      ["ndtv.com", "bbc.com", "reuters.com", "thehindu.com",
                              "hindustantimes.com", "timesofindia.com", "firstpost.com"],
            }
            for p, domains in domain_map.items():
                if any(d in url for d in domains):
                    return p
        return "unknown"

    def _find_matches(self, text: str, patterns: list[str]) -> list[str]:
        found = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found.extend(matches)
        return list(set(found))

    def _detect_brands(self, text: str) -> list[str]:
        brands = []
        for pattern in BRAND_PATTERNS:
            brands.extend(re.findall(pattern, text))
        # Filter out common non-brand words
        stopwords = {"I", "A", "The", "This", "That", "We", "You", "He", "She", "It",
                     "OK", "US", "UK", "TV", "AM", "PM", "RT", "DM", "OP"}
        return list(set(b for b in brands if b not in stopwords))[:10]

    def _classify_promotion_type(self, text: str, disclosure_tags: list[str]) -> str:
        text_lower = text.lower()
        for promo_type, keywords in PROMOTION_TYPES.items():
            if promo_type == "undisclosed_ad":
                continue
            if any(kw in text_lower for kw in keywords):
                return promo_type
        if disclosure_tags:
            return "sponsored_content"
        return "undisclosed_ad"

    def _compute_confidence(self, disclosure_tags: list[str], cta: list[str],
                            brands: list[str], commercial_hits: int) -> float:
        score = 0.0
        if disclosure_tags:
            score += 0.4
        if cta:
            score += min(len(cta) * 0.1, 0.3)
        if brands:
            score += min(len(brands) * 0.05, 0.2)
        score += min(commercial_hits * 0.05, 0.1)
        return min(round(score, 2), 1.0)

    def _risk_level(self, confidence: float, disclosure_present: bool) -> str:
        if not disclosure_present and confidence > 0.5:
            return "high"
        if confidence > 0.6:
            return "medium"
        if confidence > 0.3:
            return "low"
        return "low"

    def analyze(self, text: str, platform: Optional[str] = None,
                source_url: Optional[str] = None) -> PromotionResult:

        platform = self._detect_platform(platform, source_url)
        patterns = PLATFORM_PROMOTION_PATTERNS.get(platform, PLATFORM_PROMOTION_PATTERNS["unknown"])

        disclosure_tags = self._find_matches(text, patterns["disclosure"])
        cta_detected    = self._find_matches(text, patterns["cta"])
        influencer_hits = self._find_matches(text, patterns["influencer"])
        brand_mentions  = self._detect_brands(text)

        text_lower = text.lower()
        commercial_hits = sum(1 for kw in self.commercial_keywords if kw in text_lower)

        disclosure_present = len(disclosure_tags) > 0
        confidence = self._compute_confidence(disclosure_tags, cta_detected, brand_mentions, commercial_hits)
        is_paid = confidence >= 0.3 or bool(disclosure_tags) or bool(influencer_hits)
        promotion_type = self._classify_promotion_type(text, disclosure_tags) if is_paid else "none"
        risk = self._risk_level(confidence, disclosure_present)

        flags = []
        if not disclosure_present and is_paid:
            flags.append("Paid content detected without proper disclosure")
        if influencer_hits:
            flags.append(f"Influencer promotion signals: {', '.join(influencer_hits[:3])}")
        if cta_detected:
            flags.append(f"Call-to-action detected: {', '.join(cta_detected[:3])}")
        if commercial_hits > 3:
            flags.append(f"High commercial keyword density ({commercial_hits} hits)")
        if brand_mentions:
            flags.append(f"Brand mentions: {', '.join(brand_mentions[:5])}")

        return PromotionResult(
            is_paid=is_paid,
            promotion_type=promotion_type,
            platform=platform,
            confidence=confidence,
            disclosure_present=disclosure_present,
            disclosure_tags=disclosure_tags,
            brand_mentions=brand_mentions,
            cta_detected=cta_detected,
            risk_level=risk,
            flags=flags or ["No paid promotion signals detected"],
        )

    def analyze_batch(self, items: list[dict]) -> list[PromotionResult]:
        return [
            self.analyze(
                text=item.get("text", ""),
                platform=item.get("platform"),
                source_url=item.get("source_url"),
            )
            for item in items
        ]


# ============= EXAMPLE USAGE =============

if __name__ == "__main__":
    filter = PaidPromotionFilter()

    examples = [
        {
            "label": "Instagram Influencer Ad",
            "platform": "instagram",
            "text": "Obsessed with my new skincare routine! 🌸 Gifted by @GlowBrand - use code GLOW20 for 20% off! Link in bio to shop! #ad #gifted #skincare #collab",
        },
        {
            "label": "YouTube Sponsorship",
            "platform": "youtube",
            "text": "Today's video is sponsored by NordVPN! Use code TECH50 at checkout for 50% off. Link in the description below. Thanks to NordVPN for sponsoring this video!",
        },
        {
            "label": "WhatsApp Undisclosed Promo",
            "platform": "whatsapp",
            "text": "Amazing deal on AmazingBrand products! Buy 2 get 1 free! Limited time offer! Order now and save big! Call 9999999999 to order!",
        },
        {
            "label": "Reddit Affiliate",
            "platform": "reddit",
            "text": "Full disclosure: I was compensated to review this product. Use my referral code REF123 to sign up and we both earn rewards.",
        },
        {
            "label": "News Sponsored Content",
            "source_url": "https://ndtv.com/article",
            "text": "Presented by BrandCo. In association with XYZ Corp, we bring you this sponsored content. Learn more at their website.",
        },
        {
            "label": "X/Twitter Undisclosed Ad",
            "platform": "twitter",
            "text": "Just tried the new ProductX and it's amazing! Shop now at their website for an exclusive deal. Limited time only!",
        },
    ]

    for ex in examples:
        result = filter.analyze(
            text=ex["text"],
            platform=ex.get("platform"),
            source_url=ex.get("source_url"),
        )
        print(f"\n=== {ex['label']} ===")
        print(f"  Is Paid       : {result.is_paid}")
        print(f"  Type          : {result.promotion_type}")
        print(f"  Platform      : {result.platform}")
        print(f"  Confidence    : {result.confidence:.0%}")
        print(f"  Disclosure    : {'✅ Present' if result.disclosure_present else '❌ Missing'}")
        print(f"  Risk Level    : {result.risk_level.upper()}")
        print(f"  Flags:")
        for flag in result.flags:
            print(f"    • {flag}")
