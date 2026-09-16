"""
Central configuration for all keywords, thresholds, patterns, and source definitions.
Import from here instead of hard-coding values in individual modules.
"""

# ============= FACT-CHECKING SOURCES =============

# Each entry: (site_filter, source_label, organization, confidence, language, verdict_map)
GOOGLE_FACT_CHECK_SOURCES = [
    {
        "site": "fullfact.org",
        "label": "Full Fact",
        "org": "Full Fact",
        "confidence": 0.85,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unproven": "unverified",
        },
    },
    {
        "site": "factcheck.afp.com",
        "label": "AFP Fact Check",
        "org": "Agence France-Presse",
        "confidence": 0.88,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "satire": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "timesnownews.com",
        "label": "Times Now",
        "org": "Times Now",
        "confidence": 0.80,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "aninews.in",
        "label": "ANI Fact Check",
        "org": "Asian News International",
        "confidence": 0.82,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "thewire.in",
        "label": "The Wire",
        "org": "The Wire (Left-leaning)",
        "confidence": 0.78,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "ndtv.com",
        "label": "NDTV",
        "org": "NDTV (Center-left)",
        "confidence": 0.80,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "opindia.com",
        "label": "OpIndia",
        "org": "OpIndia (Right-leaning)",
        "confidence": 0.72,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "republicworld.com",
        "label": "Republic World",
        "org": "Republic World (Right-leaning)",
        "confidence": 0.72,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "factcheck.org",
        "label": "FactCheck.org",
        "org": "Annenberg Public Policy Center (Nonpartisan)",
        "confidence": 0.88,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "dailywire.com",
        "label": "Daily Wire",
        "org": "Daily Wire (Right-leaning)",
        "confidence": 0.70,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
    {
        "site": "vishvasnews.com",
        "label": "Vishvas News",
        "org": "Vishvas News (Dainik Bhaskar Group)",
        "confidence": 0.82,
        "language": "hi",
        "verdict_map": {
            "सच": "true", "फर्जी": "false", "भ्रामक": "false",
            "misleading": "false", "fake": "false", "true": "true",
        },
    },
    {
        "site": "firstpost.com",
        "label": "Firstpost",
        "org": "Firstpost",
        "confidence": 0.80,
        "language": "en",
        "verdict_map": {
            "true": "true", "false": "false", "misleading": "false",
            "mixed": "mixed", "unverified": "unverified",
        },
    },
]

# ============= PROPAGANDA DETECTION =============

PROPAGANDA_KEYWORDS = {
    "fear_words": ["destroy", "enemy", "threat", "danger", "crisis", "attack"],
    "absolute_words": ["always", "never", "all", "none", "everyone", "nobody"],
    "emotional_words": ["outrageous", "disgusting", "shameful", "incredible", "unbelievable"],
    "us_vs_them": ["they", "those people", "they want", "they're trying"],
}

PROPAGANDA_PATTERNS = [
    r"\b(fake news|lamestream|mainstream media)\b",
    r"\b(real [A-Za-z]+|true [A-Za-z]+)\b",
    r"[A-Z]{2,}",
    r"!{2,}|\.{3,}",
]

# ============= PAID CAMPAIGN DETECTION =============

CAMPAIGN_INDICATORS = [
    r"(click here|visit|check out|swipe up|link in bio)",
    r"(use code|discount|limited time|special offer)",
    r"(subscribe|follow|share|tag a friend)",
    r"(#ad|#sponsored|#partner|#affiliate)",
    r"(http|https)://[^\s]+",
]

COMMERCIAL_KEYWORDS = [
    "buy", "sale", "free", "offer", "price", "product", "order",
    "checkout", "cart", "save", "deal", "exclusive",
]

DISCLOSURE_KEYWORDS = [
    "#ad", "#sponsored", "#partner", "#affiliate", "advertisement", "paid",
]

# ============= CLASSIFICATION THRESHOLDS =============

THRESHOLDS = {
    "propaganda_high": 0.6,
    "campaign_high": 0.6,
    "propaganda_mixed": 0.5,
    "campaign_mixed": 0.5,
    "false_claim_flag": 0.3,
    "disclosure_flag": 0.5,
    "platform_indicator_min_matches": 2,
}

# Scoring weights
SCORING_WEIGHTS = {
    "propaganda": {"language": 0.7, "sentiment": 0.3},
    "campaign": {"commercial": 0.4, "cta": 0.4, "no_disclosure": 0.2},
    "risk": {"propaganda": 40, "campaign": 30, "false_claims": 30},
}

# ============= PLATFORM CONFIG =============

PLATFORM_DOMAINS = {
    "twitter": ["twitter.com", "x.com", "t.co"],
    "instagram": ["instagram.com", "instagr.am"],
    "youtube": ["youtube.com", "youtu.be"],
    "facebook": ["facebook.com", "fb.com", "fb.watch"],
    "reddit": ["reddit.com", "redd.it"],
    "telegram": ["t.me", "telegram.me"],
    "whatsapp": ["whatsapp.com", "wa.me"],
    "linkedin": ["linkedin.com"],
    "news": [
        "ndtv.com", "thehindu.com", "hindustantimes.com", "timesofindia.com",
        "indianexpress.com", "firstpost.com", "thewire.in", "opindia.com",
        "republicworld.com", "aninews.in", "timesnownews.com",
        "bbc.com", "reuters.com", "apnews.com", "theguardian.com",
        "nytimes.com", "washingtonpost.com", "cnn.com", "foxnews.com",
    ],
}

PLATFORM_WEIGHTS = {
    "twitter":   {"propaganda": 1.2, "campaign": 1.0, "caps_penalty": 1.3},
    "instagram": {"propaganda": 0.8, "campaign": 1.5, "caps_penalty": 0.8},
    "youtube":   {"propaganda": 1.1, "campaign": 1.3, "caps_penalty": 1.2},
    "facebook":  {"propaganda": 1.3, "campaign": 1.1, "caps_penalty": 1.2},
    "reddit":    {"propaganda": 1.0, "campaign": 0.7, "caps_penalty": 1.0},
    "telegram":  {"propaganda": 1.4, "campaign": 0.9, "caps_penalty": 1.1},
    "whatsapp":  {"propaganda": 1.5, "campaign": 0.8, "caps_penalty": 1.2},
    "linkedin":  {"propaganda": 0.7, "campaign": 1.4, "caps_penalty": 0.7},
    "news":      {"propaganda": 0.6, "campaign": 0.6, "caps_penalty": 0.5},
    "unknown":   {"propaganda": 1.0, "campaign": 1.0, "caps_penalty": 1.0},
}

PLATFORM_INDICATORS = {
    "instagram": [
        r"link in bio", r"swipe up", r"collab", r"gifted", r"pr package",
        r"use code", r"discount code", r"#ad\b", r"#sponsored", r"#gifted",
        r"#collab", r"#ambassador", r"dm for.*promo", r"paid partnership",
        r"reel", r"story", r"highlights", r"close friends",
    ],
    "youtube": [
        r"subscribe", r"smash.*like", r"hit.*bell", r"notification", r"merch",
        r"patreon", r"channel member", r"super chat", r"pinned comment",
        r"description below", r"link.*description", r"sponsored by",
        r"this video is sponsored", r"use code.*checkout", r"timestamps",
        r"like.*comment.*share", r"\d+k.*subscriber",
    ],
    "twitter": [
        r"RT @", r"retweet", r"quote tweet", r"QT", r"#[A-Za-z]+",
        r"trending", r"ratio", r"thread\b", r"\bX\.com", r"community note",
        r"spaces", r"bookmarks", r"\bpoll\b", r"\d+ likes", r"\d+ RTs",
        r"breaking:", r"JUST IN", r"developing story",
    ],
    "whatsapp": [
        r"forward.*message", r"share.*group", r"forwarded many times",
        r"send.*contacts", r"broadcast", r"status", r"voice note",
        r"this message.*deleted", r"end.to.end encrypted",
        r"copy.*paste.*share", r"don.t ignore", r"must share",
        r"share.*before.*deleted", r"government.*hiding",
    ],
    "reddit": [
        r"\bOP\b", r"\bTIL\b", r"\bIMO\b", r"\bELI5\b", r"\bAMA\b",
        r"upvote", r"downvote", r"crosspost", r"subreddit", r"r/[A-Za-z]+",
        r"mod\b", r"karma", r"gilded", r"award", r"edit:",
        r"\[deleted\]", r"\[removed\]", r"throwaway account",
    ],
    "news": [
        r"breaking", r"exclusive", r"sources say", r"according to",
        r"confirmed", r"developing", r"updated:", r"correction:",
        r"anonymous source", r"officials say", r"report says",
        r"investigation", r"leaked", r"obtained by", r"first reported",
    ],
}

# ============= API SECURITY =============

# Rate limiting: requests per minute per IP
RATE_LIMIT_PER_MINUTE = 30

# Set via environment variable API_KEY; if unset, auth is disabled (dev mode)
API_KEY_HEADER = "X-API-Key"

# ============= ML MODEL CONFIGURATION =============

# Path to the active trained model directory
ML_MODEL_DIR = "models/current"

# Fall back to rule-based classification if no trained model is found
ML_FALLBACK_TO_RULES = True

# TF-IDF vectorizer settings (used during training)
ML_TFIDF_MAX_FEATURES = 5000
ML_TFIDF_NGRAM_RANGE = (1, 2)

# Candidate model types to try during training
ML_CANDIDATE_MODELS = ["logistic_regression", "linear_svc", "random_forest"]

