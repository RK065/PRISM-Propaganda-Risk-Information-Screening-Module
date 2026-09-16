"""
Feature extraction module for content detection.
"""
import re
import logging
from typing import List, Dict, Any, Optional

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not found. Linguistic features will degrade gracefully.")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logging.warning("TextBlob not found. Sentiment features will be 0.")

from preprocessor import TextPreprocessor
from emotion_lexicon import EmotionLexicon
import config

# Optional: sentence embeddings
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SBERT = True
except ImportError:
    _HAS_SBERT = False
    logging.warning("sentence-transformers not found. Embedding features disabled.")

FEATURE_NAMES = [
    # Category 1: Writing Style
    "text_length", "word_count", "sentence_count", "avg_word_length", "avg_sentence_length",
    "punctuation_ratio", "quotation_count", "repeated_punctuation_count", 
    "caps_ratio", "caps_word_count", "unique_word_ratio", "repetition_score",
    
    # Category 2: Readability
    "flesch_reading_ease", "gunning_fog_index", "avg_syllables_per_word",
    
    # Category 3: NRC Emotions
    "nrc_anger", "nrc_joy", "nrc_fear", "nrc_sadness", 
    "nrc_trust", "nrc_anticipation", "nrc_surprise", "nrc_disgust",
    
    # Category 4: Sentiment
    "textblob_polarity", "textblob_subjectivity",
    
    # Category 5: Emoji & Formatting
    "emoji_count", "positive_emoji_count", "negative_emoji_count",
    "elongated_word_count", "exclamation_count", "question_mark_count",
    
    # Category 6: Clickbait & Propaganda
    "clickbait_score", "fear_word_ratio", "emotional_word_ratio", "absolute_word_ratio", 
    "us_vs_them_ratio", "narrative_manipulation_count", "suspicious_pattern_count", 
    "false_authority_count",
    
    # Category 7: Linguistic POS/NER
    "verb_ratio", "adjective_ratio", "adverb_ratio", "pronoun_ratio", "noun_ratio",
    "ner_person_count", "ner_org_count", "ner_gpe_count",
    
    # Category 8: Claims & Social Signals
    "cta_pattern_count", "url_count", "hashtag_count", "mention_count",
    "claim_statistical", "claim_scientific", "claim_political", "claim_health",
    
    # Category 9: Fact-Check / Subtle Propaganda (NEW)
    "hedge_word_ratio", "certainty_word_ratio", "attribution_ratio",
    "vagueness_score", "specificity_score", "number_density",
    "superlative_count", "comparative_count", "causal_claim_count",
    "conditional_count", "generalization_count", "fallacy_pattern_count",
    "exaggeration_score", "contrast_word_count", "loaded_language_score",
    
    # Platform
    "platform_encoded"
]

# Sentence embedding feature names (384 dims from all-MiniLM-L6-v2)
EMBEDDING_DIM = 384
EMBEDDING_FEATURE_NAMES = [f"emb_{i}" for i in range(EMBEDDING_DIM)]
ALL_FEATURE_NAMES = FEATURE_NAMES + EMBEDDING_FEATURE_NAMES

class FeatureExtractor:
    # Word sets for fact-check features
    HEDGE_WORDS = frozenset([
        "might", "could", "may", "perhaps", "possibly", "probably", "likely",
        "seemingly", "apparently", "arguably", "suggests", "somewhat", "roughly",
        "approximately", "about", "around", "maybe", "sometimes", "often",
    ])
    CERTAINTY_WORDS = frozenset([
        "always", "never", "definitely", "certainly", "absolutely", "clearly",
        "obviously", "undoubtedly", "without doubt", "proven", "fact", "guaranteed",
        "every", "none", "all", "nobody", "everyone", "nothing", "everything",
    ])
    ATTRIBUTION_WORDS = frozenset([
        "said", "says", "according", "stated", "reported", "claimed", "noted",
        "announced", "confirmed", "testified", "declared", "argued", "contended",
    ])
    VAGUE_WORDS = frozenset([
        "things", "stuff", "something", "someone", "people", "they", "them",
        "those", "some", "many", "various", "several", "lots", "much",
    ])
    CAUSAL_PATTERNS = [
        r'\b(because|caused|leads? to|results? in|therefore|consequently|due to|owing to)\b',
    ]
    GENERALIZATION_PATTERNS = [
        r'\b(all|every|always|never|nobody|everyone|no one|nothing|everything)\b',
        r'\b(the \w+ always|\w+ never \w+)\b',
    ]
    FALLACY_PATTERNS = [
        r'\b(if .+ then .+ must)\b',  # false cause
        r'\b(either .+ or)\b',  # false dichotomy
        r'\b(everyone knows|common sense|obviously)\b',  # appeal to common sense
        r'\b(just like|same as|no different)\b',  # false equivalence
        r'\b(slippery slope|what.s next)\b',  # slippery slope
    ]
    LOADED_WORDS = frozenset([
        "destroy", "destroying", "radical", "extremist", "corrupt", "corruption",
        "dangerous", "threat", "threatening", "disaster", "disastrous", "catastrophe",
        "outrageous", "shameful", "disgusting", "horrific", "devastating", "alarming",
        "reckless", "incompetent", "failed", "failure", "betrayed", "betrayal",
        "scheme", "plot", "rigged", "stolen", "crooked", "hoax", "scam", "fraud",
        "tyranny", "oppression", "slavery", "brainwash", "propaganda", "regime",
        "socialist", "communist", "fascist", "nazi", "dictator", "elite", "elites",
    ])

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.lexicon = EmotionLexicon()
        
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm", disable=["parser"])
            except Exception as e:
                logging.warning(f"Error loading spaCy model: {e}")
                self.nlp = None

        self.sbert_model = None
        if _HAS_SBERT:
            try:
                self.sbert_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
                logging.info("SentenceTransformer loaded on CPU for embedding features.")
            except Exception as e:
                logging.warning(f"Error loading SentenceTransformer: {e}")
                self.sbert_model = None
                
    def extract(self, text: str, platform: str = None, doc = None) -> Dict[str, float]:
        features = {name: 0.0 for name in FEATURE_NAMES}
        
        if not text or not text.strip():
            return features
            
        prep = self.preprocessor.preprocess(text)
        words = prep.tokens
        raw_words = text.split()
        total_words = len(words)
        total_chars = len(text)
        
        # Category 1: Writing Style
        features["text_length"] = float(total_chars)
        features["word_count"] = float(total_words)
        features["sentence_count"] = float(len(prep.sentences))
        features["avg_word_length"] = float(sum(len(w) for w in words) / total_words) if total_words > 0 else 0.0
        if features["sentence_count"] > 0:
            features["avg_sentence_length"] = total_words / features["sentence_count"]
            
        features["punctuation_ratio"] = float(len(re.findall(r'[^\w\s]', text)) / total_chars) if total_chars > 0 else 0.0
        features["quotation_count"] = float(len(re.findall(r'["\']', text)))
        features["repeated_punctuation_count"] = float(len(re.findall(r'[!?\.]{2,}', text)))
        
        caps_letters = sum(1 for c in text if c.isupper())
        features["caps_ratio"] = float(caps_letters / total_chars) if total_chars > 0 else 0.0
        
        caps_words = sum(1 for w in raw_words if w.isupper() and len(w) > 1)
        features["caps_word_count"] = float(caps_words)
        
        # Unique word ratio and repetition
        if total_words > 0:
            features["unique_word_ratio"] = len(set(words)) / total_words
            from collections import Counter
            counts = Counter(words)
            features["repetition_score"] = float(counts.most_common(1)[0][1] / total_words) if counts else 0.0
        
        # Category 2: Readability
        features["flesch_reading_ease"] = self.preprocessor.flesch_reading_ease(text)
        features["gunning_fog_index"] = self.preprocessor.gunning_fog_index(text)
        features["avg_syllables_per_word"] = self.preprocessor.avg_syllables_per_word(words)
        
        # Category 3: NRC Emotions
        emotions = self.lexicon.score_text(text)
        for emo, score in emotions.items():
            features[f"nrc_{emo}"] = float(score)
            
        # Category 4: Sentiment
        if TEXTBLOB_AVAILABLE:
            try:
                blob = TextBlob(text)
                features["textblob_polarity"] = float(blob.sentiment.polarity)
                features["textblob_subjectivity"] = float(blob.sentiment.subjectivity)
            except Exception:
                pass
                
        # Category 5: Emoji & Formatting
        features["emoji_count"] = float(prep.emoji_info["count"])
        features["positive_emoji_count"] = float(prep.emoji_info["positive_count"])
        features["negative_emoji_count"] = float(prep.emoji_info["negative_count"])
        features["elongated_word_count"] = float(len(prep.elongated_words))
        features["exclamation_count"] = float(text.count('!'))
        features["question_mark_count"] = float(text.count('?'))
        
        # Category 6: Clickbait & Propaganda
        clickbait_patterns = [
            r"you won't believe", r"top \d+", r"shocking", r"must read", r"doctors hate",
            r"what happened next", r"this one trick", r"the truth about", r"exposed"
        ]
        features["clickbait_score"] = float(sum(1 for p in clickbait_patterns if re.search(p, prep.cleaned_text)))
        
        # Handle config propaganda keywords safely
        fear_words = getattr(config, "PROPAGANDA_KEYWORDS", {}).get("fear_words", [])
        emo_words = getattr(config, "PROPAGANDA_KEYWORDS", {}).get("emotional_words", [])
        abs_words = getattr(config, "PROPAGANDA_KEYWORDS", {}).get("absolute_words", [])
        us_vs_them = getattr(config, "PROPAGANDA_KEYWORDS", {}).get("us_vs_them", [])
        
        if total_words > 0:
            features["fear_word_ratio"] = float(sum(1 for w in words if w in fear_words) / total_words)
            features["emotional_word_ratio"] = float(sum(1 for w in words if w in emo_words) / total_words)
            features["absolute_word_ratio"] = float(sum(1 for w in words if w in abs_words) / total_words)
            features["us_vs_them_ratio"] = float(sum(1 for w in words if w in us_vs_them) / total_words)
            
        features["narrative_manipulation_count"] = float(sum(1 for p in ["wake up", "share before deleted", "mainstream media"] if p in prep.cleaned_text))
        
        suspicious_patterns = getattr(config, "PROPAGANDA_PATTERNS", [])
        features["suspicious_pattern_count"] = float(sum(1 for p in suspicious_patterns if re.search(p, prep.cleaned_text)))
        
        features["false_authority_count"] = float(sum(1 for p in ["experts say", "studies show", "scientists confirm"] if p in prep.cleaned_text))
        
        # Category 7: Linguistic POS/NER
        if doc is None and self.nlp:
            try:
                doc = self.nlp(text)
            except Exception:
                doc = None

        if doc is not None:
            try:
                pos_counts = {"VERB": 0, "ADJ": 0, "ADV": 0, "PRON": 0, "NOUN": 0}
                for token in doc:
                    if token.pos_ in pos_counts:
                        pos_counts[token.pos_] += 1
                        
                total_tokens = len(doc)
                if total_tokens > 0:
                    features["verb_ratio"] = float(pos_counts["VERB"] / total_tokens)
                    features["adjective_ratio"] = float(pos_counts["ADJ"] / total_tokens)
                    features["adverb_ratio"] = float(pos_counts["ADV"] / total_tokens)
                    features["pronoun_ratio"] = float(pos_counts["PRON"] / total_tokens)
                    features["noun_ratio"] = float(pos_counts["NOUN"] / total_tokens)
                    
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        features["ner_person_count"] += 1.0
                    elif ent.label_ == "ORG":
                        features["ner_org_count"] += 1.0
                    elif ent.label_ == "GPE":
                        features["ner_gpe_count"] += 1.0
            except Exception:
                pass
                
        # Category 8: Claims & Social Signals
        cta_patterns = getattr(config, "CAMPAIGN_INDICATORS", [])
        features["cta_pattern_count"] = float(sum(1 for p in cta_patterns if re.search(p, text, re.IGNORECASE)))
        
        features["url_count"] = float(len(re.findall(r'https?://\S+|www\.\S+', text)))
        features["hashtag_count"] = float(len(re.findall(r'#\w+', text)))
        features["mention_count"] = float(len(re.findall(r'@\w+', text)))
        
        features["claim_statistical"] = 1.0 if re.search(r'\d+.*(percent|%|million|billion|study|survey)', prep.cleaned_text) else 0.0
        features["claim_scientific"] = 1.0 if re.search(r'(research|study|scientists|proven|evidence)', prep.cleaned_text) else 0.0
        features["claim_political"] = 1.0 if re.search(r'(government|policy|election|vote|president|congress)', prep.cleaned_text) else 0.0
        features["claim_health"] = 1.0 if re.search(r'(vaccine|health|cure|disease|treatment|medical)', prep.cleaned_text) else 0.0
        
        # Category 9: Fact-Check / Subtle Propaganda
        lower_words = [w.lower() for w in raw_words]
        lower_set = set(lower_words)
        
        # Hedge words — propaganda uses fewer hedges (more certainty)
        hedge_count = sum(1 for w in lower_words if w in self.HEDGE_WORDS)
        features["hedge_word_ratio"] = float(hedge_count / total_words) if total_words > 0 else 0.0
        
        # Certainty words — propaganda uses more absolute certainty
        certainty_count = sum(1 for w in lower_words if w in self.CERTAINTY_WORDS)
        features["certainty_word_ratio"] = float(certainty_count / total_words) if total_words > 0 else 0.0
        
        # Attribution — neutral text cites sources more
        attr_count = sum(1 for w in lower_words if w in self.ATTRIBUTION_WORDS)
        features["attribution_ratio"] = float(attr_count / total_words) if total_words > 0 else 0.0
        
        # Vagueness — propaganda is often vague
        vague_count = sum(1 for w in lower_words if w in self.VAGUE_WORDS)
        features["vagueness_score"] = float(vague_count / total_words) if total_words > 0 else 0.0
        
        # Specificity — specific numbers, dates, names indicate factual content
        specific_count = len(re.findall(r'\b\d+\b', text))  # numbers
        specific_count += len(re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b', text, re.IGNORECASE))
        features["specificity_score"] = float(specific_count / max(total_words, 1))
        
        # Number density — ratio of numbers in text
        features["number_density"] = float(len(re.findall(r'\b\d[\d,.]*\b', text)) / max(total_words, 1))
        
        # Superlatives — "biggest", "worst", "most" — propaganda signal
        features["superlative_count"] = float(len(re.findall(r'\b\w*(est|most|least|worst|best|biggest|largest|smallest|highest|lowest)\b', prep.cleaned_text)))
        
        # Comparatives — "more", "better", "worse" — framing device
        features["comparative_count"] = float(len(re.findall(r'\b(more|less|better|worse|greater|fewer|higher|lower|bigger|smaller)\b', prep.cleaned_text)))
        
        # Causal claims — "because", "leads to", "results in"
        features["causal_claim_count"] = float(sum(len(re.findall(p, prep.cleaned_text, re.IGNORECASE)) for p in self.CAUSAL_PATTERNS))
        
        # Conditional statements — "if..then" framing
        features["conditional_count"] = float(len(re.findall(r'\bif\b', prep.cleaned_text)))
        
        # Generalizations — "everyone knows", "all X are Y"
        features["generalization_count"] = float(sum(len(re.findall(p, prep.cleaned_text, re.IGNORECASE)) for p in self.GENERALIZATION_PATTERNS))
        
        # Logical fallacy patterns
        features["fallacy_pattern_count"] = float(sum(len(re.findall(p, prep.cleaned_text, re.IGNORECASE)) for p in self.FALLACY_PATTERNS))
        
        # Exaggeration score — combination of superlatives + certainty + loaded language
        loaded_count = sum(1 for w in lower_words if w in self.LOADED_WORDS)
        features["exaggeration_score"] = float(
            (features["superlative_count"] + certainty_count + loaded_count) / max(total_words, 1)
        )
        
        # Contrast words — "but", "however", "although" — used differently in propaganda vs neutral
        features["contrast_word_count"] = float(len(re.findall(r'\b(but|however|although|despite|nevertheless|yet|whereas|while)\b', prep.cleaned_text)))
        
        # Loaded language score — emotionally charged words ratio
        features["loaded_language_score"] = float(loaded_count / max(total_words, 1))
        
        # Platform
        platform_mapping = {
            "twitter": 0.0, "instagram": 1.0, "youtube": 2.0, "facebook": 3.0,
            "reddit": 4.0, "telegram": 5.0, "whatsapp": 6.0, "linkedin": 7.0,
            "news": 8.0, "unknown": 9.0,
        }
        platform_key = (platform or "unknown").lower()
        features["platform_encoded"] = platform_mapping.get(platform_key, 9.0)
        
        return features

    def extract_array(self, text: str, platform: str = None, doc = None) -> List[float]:
        features_dict = self.extract(text, platform, doc)
        return [features_dict[name] for name in FEATURE_NAMES]

    def extract_with_embeddings(self, text: str, platform: str = None) -> List[float]:
        """Extract all features including sentence embeddings."""
        base_features = self.extract_array(text, platform)
        if self.sbert_model is not None:
            try:
                embedding = self.sbert_model.encode(text, show_progress_bar=False, device="cpu")
                return base_features + embedding.tolist()
            except Exception:
                return base_features + [0.0] * EMBEDDING_DIM
        else:
            return base_features + [0.0] * EMBEDDING_DIM

    def extract_batch(self, texts: List[str], platforms: List[str] = None) -> List[List[float]]:
        if not platforms:
            platforms = [None] * len(texts)
        if self.nlp:
            docs = list(self.nlp.pipe(texts, disable=["parser"], batch_size=500))
        else:
            docs = [None] * len(texts)
        return [self.extract_array(t, p, d) for t, p, d in zip(texts, platforms, docs)]

    def extract_batch_with_embeddings(self, texts: List[str], platforms: List[str] = None) -> List[List[float]]:
        """Batch extract all features including sentence embeddings."""
        if not platforms:
            platforms = [None] * len(texts)
        base_features = self.extract_batch(texts, platforms)
        if self.sbert_model is not None:
            try:
                embeddings = self.sbert_model.encode(texts, show_progress_bar=True, batch_size=128, device="cpu")
                return [bf + emb.tolist() for bf, emb in zip(base_features, embeddings)]
            except Exception as e:
                logging.warning(f"Embedding extraction failed: {e}")
                return [bf + [0.0] * EMBEDDING_DIM for bf in base_features]
        else:
            return [bf + [0.0] * EMBEDDING_DIM for bf in base_features]
