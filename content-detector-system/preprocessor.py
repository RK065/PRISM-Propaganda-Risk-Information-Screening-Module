"""
Advanced text preprocessing module for feature extraction.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logging.warning("NLTK not found. Falling back to basic preprocessing.")

@dataclass
class PreprocessedText:
    raw_text: str
    cleaned_text: str
    tokens: List[str]
    sentences: List[str]
    emoji_info: Dict
    elongated_words: List[str]

class TextPreprocessor:
    def __init__(self):
        self.lemmatizer = None
        if NLTK_AVAILABLE:
            try:
                self.lemmatizer = WordNetLemmatizer()
            except Exception as e:
                logging.warning(f"Error initializing NLTK lemmatizer: {e}")
                
        self.positive_emojis = set("😊❤️👍🎉😍🥰💪✨🔥💯🙌👏😄😃😁💕🌟⭐🎊🥳💖")
        self.negative_emojis = set("😡😤😭💀👎😠🤬😱😰😨😢🤮😷💔😩😫😵🥺😖😣")
        
    def _lemmatize(self, words: List[str]) -> List[str]:
        if self.lemmatizer:
            try:
                return [self.lemmatizer.lemmatize(w.lower()) for w in words]
            except Exception:
                return [w.lower() for w in words]
        return [w.lower() for w in words]
        
    def _split_sentences(self, text: str) -> List[str]:
        if not text.strip():
            return []
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(text)
                if sentences:
                    return sentences
            except Exception:
                pass
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def extract_emoji_info(self, text: str) -> Dict:
        emojis = [c for c in text if c in self.positive_emojis or c in self.negative_emojis]
        pos_count = sum(1 for e in emojis if e in self.positive_emojis)
        neg_count = sum(1 for e in emojis if e in self.negative_emojis)
        return {
            "count": len(emojis),
            "positive_count": pos_count,
            "negative_count": neg_count,
            "emojis": emojis
        }

    def preprocess(self, text: str) -> PreprocessedText:
        if not text:
            return PreprocessedText(
                raw_text="", cleaned_text="", tokens=[], sentences=[],
                emoji_info={"count": 0, "positive_count": 0, "negative_count": 0, "emojis": []},
                elongated_words=[]
            )
            
        sentences = self._split_sentences(text)
        cleaned_text = text.lower()
        
        if NLTK_AVAILABLE:
            try:
                words = word_tokenize(cleaned_text)
            except Exception:
                words = re.findall(r'\b\w+\b', cleaned_text)
        else:
            words = re.findall(r'\b\w+\b', cleaned_text)
            
        tokens = self._lemmatize(words)
        emoji_info = self.extract_emoji_info(text)
        elongated_words = list(set([w for w in words if re.search(r'(.)\1{2,}', w)]))
        
        return PreprocessedText(
            raw_text=text,
            cleaned_text=cleaned_text,
            tokens=tokens,
            sentences=sentences,
            emoji_info=emoji_info,
            elongated_words=elongated_words
        )

    def count_syllables(self, word: str) -> int:
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word.endswith("e"):
            count -= 1
        if count == 0:
            count += 1
        return count

    def avg_syllables_per_word(self, tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        return sum(self.count_syllables(t) for t in tokens) / len(tokens)

    def flesch_reading_ease(self, text: str) -> float:
        if not text.strip():
            return 0.0
        sentences = self._split_sentences(text)
        words = re.findall(r'\b\w+\b', text)
        if not words or not sentences:
            return 0.0
            
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = self.avg_syllables_per_word(words)
        
        score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
        return float(score)

    def gunning_fog_index(self, text: str) -> float:
        if not text.strip():
            return 0.0
        sentences = self._split_sentences(text)
        words = re.findall(r'\b\w+\b', text)
        if not words or not sentences:
            return 0.0
            
        complex_words = sum(1 for w in words if self.count_syllables(w) >= 3)
        avg_sentence_length = len(words) / len(sentences)
        complex_word_ratio = complex_words / len(words)
        
        score = 0.4 * (avg_sentence_length + 100 * complex_word_ratio)
        return float(score)
