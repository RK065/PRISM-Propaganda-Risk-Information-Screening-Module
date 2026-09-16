"""
Emotion lexicon for content detection.
Compatible with NRC Emotion Lexicon categories.
"""
import logging

class EmotionLexicon:
    def __init__(self):
        self.emotions = {
            "anger": {
                "furious", "rage", "hostile", "hatred", "angry", "violent", "aggression", 
                "outrage", "resent", "livid", "mad", "wrath", "fury", "annoyed", "irritated",
                "bitter", "enraged", "infuriated", "scorn", "spite", "vindictive", "fuming",
                "boiling", "cross", "displeased", "frustrated", "grumpy", "hostility",
                "indignant", "irate", "outraged", "provoked", "resentful", "sullen", "tantrum",
                "temper", "agitated", "belligerent", "combative", "fierce", "glare", "growl"
            },
            "joy": {
                "happy", "delight", "cheerful", "celebrate", "wonderful", "blessed", "thrilled",
                "excited", "love", "grateful", "joyful", "ecstatic", "glad", "pleased", "elated",
                "jubilant", "merry", "radiant", "smiling", "sunny", "triumphant", "upbeat",
                "bliss", "charm", "cheer", "delighted", "enjoy", "entertain", "excellent",
                "fabulous", "fantastic", "fun", "glorious", "good", "great", "grin", "hilarious",
                "humor", "joke", "laugh", "lively", "lucky", "magic", "marvelous", "outstanding",
                "perfect", "pleasant", "rejoice", "smile", "splendid", "superb", "sweet"
            },
            "fear": {
                "afraid", "terrified", "dread", "panic", "horror", "scared", "anxious", "alarming",
                "threat", "frightened", "terror", "fearful", "nervous", "spooked", "apprehensive",
                "coward", "creepy", "daunting", "despair", "dismay", "doom", "eerie", "fright",
                "ghastly", "ghost", "horrible", "horrific", "intimidate", "monster", "nightmare",
                "ominous", "paranoia", "petrified", "phobia", "quiver", "scary", "shiver", "shock",
                "sinister", "spooky", "startle", "suspicious", "tense", "terrible", "threaten",
                "tremble", "worry", "alarm", "danger", "fret", "panicked"
            },
            "sadness": {
                "grief", "sorrow", "miserable", "depressed", "heartbreak", "mourn", "tragic", 
                "painful", "lonely", "cry", "sad", "unhappy", "gloomy", "melancholy", "weep",
                "tear", "anguish", "bleak", "depressing", "desolate", "despair", "devastated",
                "disappoint", "dismal", "distress", "dolorous", "down", "dreary", "forlorn",
                "gloom", "grieving", "heartbroken", "helpless", "hopeless", "hurt", "lament",
                "loss", "moan", "mournful", "pathetic", "pity", "regret", "remorse", "sob",
                "somber", "sorrowful", "suffer", "tears", "tragedy", "weeping", "woe", "woeful"
            },
            "trust": {
                "honest", "reliable", "faithful", "loyal", "confident", "believe", "genuine",
                "authentic", "sincere", "dependable", "trust", "trustworthy", "safe", "secure",
                "truth", "valid", "assure", "certain", "commit", "confide", "convince",
                "credibility", "defend", "entrust", "faith", "guarantee", "honor", "integrity",
                "pledge", "promise", "protect", "rely", "respect", "solid", "steadfast", "support",
                "swear", "true", "truthful", "unfailing", "validate", "verify", "vow", "accept",
                "accord", "agree", "ally", "friend", "partner", "reassure", "steady"
            },
            "anticipation": {
                "expect", "predict", "hope", "await", "prepare", "eager", "upcoming", "plan",
                "ready", "anticipate", "foresee", "future", "imminent", "longing", "outlook",
                "prospect", "wait", "yearn", "advance", "approach", "aspire", "assume",
                "calculate", "destiny", "divine", "envision", "expectant", "expectation",
                "forecast", "foresight", "guess", "hopeful", "impending", "intend", "intent",
                "look", "pending", "plan", "plot", "promise", "prophecy", "schedule", "soon",
                "suppose", "suspense", "tomorrow", "watch", "wish", "anxious", "curious"
            },
            "surprise": {
                "shocked", "astonished", "unexpected", "unbelievable", "stunning", "startling",
                "amazing", "sudden", "remarkable", "jaw-dropping", "surprise", "amaze",
                "astonish", "astound", "awe", "baffled", "bewildered", "breathtaking", "confound",
                "daze", "dumbfounded", "flabbergasted", "gasp", "incredible", "marvel", "miracle",
                "mystify", "overwhelm", "perplex", "shock", "speechless", "stagger", "startle",
                "stun", "stunned", "surprised", "unanticipated", "unforeseen", "unpredictable",
                "wonder", "wow", "abrupt", "ambush", "bomb", "burst", "catch", "jolt", "magic"
            },
            "disgust": {
                "revolting", "repulsive", "sickening", "nauseating", "vile", "gross", "loathsome",
                "abhorrent", "detestable", "foul", "disgust", "nausea", "appalling", "awful",
                "crap", "creepy", "dirty", "disagreeable", "disgusting", "distasteful", "evil",
                "filth", "filthy", "ghastly", "hideous", "horrid", "icky", "lousy", "macabre",
                "nasty", "nauseous", "obscene", "odious", "offensive", "putrid", "repel",
                "repugnant", "rotten", "shit", "sick", "sicken", "smut", "snob", "stink",
                "terrible", "trash", "ugly", "unpleasant", "vomit", "vulgar", "wicked"
            }
        }
        
    def get_emotions(self, word: str) -> dict[str, bool]:
        """
        Returns which emotions a word belongs to.
        """
        word = word.lower()
        result = {}
        for emotion, words in self.emotions.items():
            result[emotion] = word in words
        return result
        
    def score_text(self, text: str) -> dict[str, float]:
        """
        Returns emotion ratios (emotion_word_count / total_words) for all 8 emotions.
        """
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        total_words = len(words)
        
        scores = {emotion: 0.0 for emotion in self.emotions.keys()}
        if total_words == 0:
            return scores
            
        for word in words:
            emotions = self.get_emotions(word)
            for emotion, is_present in emotions.items():
                if is_present:
                    scores[emotion] += 1
                    
        for emotion in scores:
            scores[emotion] /= total_words
            
        return scores
