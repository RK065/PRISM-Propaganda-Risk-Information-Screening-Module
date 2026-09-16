"""
Example usage patterns for the Content Detector API
"""

import requests
import json
import html
from typing import Optional

BASE_URL = "http://localhost:8000"

class ContentDetectorClient:
    def __init__(self, api_url: str = BASE_URL):
        self.api_url = api_url

    def analyze_single(
        self,
        text: str,
        source_url: Optional[str] = None,
        author: Optional[str] = None,
        platform: Optional[str] = None
    ) -> dict:
        """Analyze a single piece of content"""
        payload = {
            "text": text,
            "source_url": source_url,
            "author": author,
            "platform": platform,
        }
        response = requests.post(f"{self.api_url}/analyze", json=payload)
        response.raise_for_status()
        return response.json()

    def analyze_batch(self, contents: list[dict]) -> list[dict]:
        """Analyze multiple pieces of content at once"""
        payload = [
            {
                "text": c.get("text"),
                "source_url": c.get("source_url"),
                "author": c.get("author"),
                "platform": c.get("platform"),
            }
            for c in contents
        ]
        response = requests.post(f"{self.api_url}/batch", json=payload)
        response.raise_for_status()
        return response.json()

    def get_risk_summary(self, result: dict) -> str:
        """Human-readable risk summary"""
        risk_score = result.get("risk_score", 0)
        classification = result.get("classification", "unknown")
        
        if risk_score > 80:
            risk_level = "CRITICAL"
        elif risk_score > 60:
            risk_level = "HIGH"
        elif risk_score > 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return f"{risk_level} RISK - Classified as: {html.escape(str(classification))}"


def print_result(result: dict):
    print(f"  Platform : {html.escape(str(result['reasoning'].get('platform', 'unknown')))}")
    print(f"  Classification: {html.escape(str(result['classification']))}")
    print(f"  Risk Score: {result['risk_score']:.1f}/100")
    print(f"  Confidence: {result['confidence']:.2%}")
    print(f"  Flags:")
    for flag in result.get('flags', []):
        print(f"    • {html.escape(str(flag))}")


# ============= EXAMPLE 1: Analyze a Single Post =============
if __name__ == "__main__":
    client = ContentDetectorClient()

    propaganda_text = """
    WAKE UP PEOPLE!!! They're DESTROYING our country with their lies and conspiracies! 
    The fake news media won't tell you the TRUTH about what's really happening. 
    Everyone needs to see this - SHARE NOW before they take it down!!! 
    #FakeNews #RealTruth #WakeUpAmerica
    """

    print("\n=== Example 1: X/Twitter - Propaganda Post ===")
    try:
        result = client.analyze_single(propaganda_text, platform="twitter")
        print_result(result)
    except Exception as e:
        print(f"Error: {e}")

    instagram_text = """
    Hey loves! 🌸 This skincare routine changed my life! Use code GLOW20 for 20% off! 
    Link in bio to shop! Gifted by @brandname 💕 #ad #sponsored #gifted #skincare #collab
    """

    print("\n=== Example 2: Instagram - Paid Campaign ===")
    try:
        result = client.analyze_single(instagram_text, platform="instagram")
        print_result(result)
    except Exception as e:
        print(f"Error: {e}")

    youtube_text = """
    SMASH that like button and subscribe! Hit the notification bell so you never miss a video!
    Today's video is sponsored by NordVPN - use code TECH50 for 50% off at checkout!
    Check the link in the description below. Don't forget to comment and share!
    """

    print("\n=== Example 3: YouTube - Sponsored Content ===")
    try:
        result = client.analyze_single(youtube_text, platform="youtube")
        print_result(result)
    except Exception as e:
        print(f"Error: {e}")

    whatsapp_text = """
    URGENT!!! Forward this message to all your contacts before it gets deleted!
    The government is hiding this from you. Share this to every group you're in.
    Don't ignore - copy paste and send NOW!!!
    """

    print("\n=== Example 4: WhatsApp - Viral Misinformation ===")
    try:
        result = client.analyze_single(whatsapp_text, platform="whatsapp")
        print_result(result)
    except Exception as e:
        print(f"Error: {e}")

    reddit_text = """
    TIL that the moon landing was actually real and well-documented. 
    OP here - crossposting from r/history. Upvote if you found this interesting!
    Edit: Thanks for the awards!
    """

    print("\n=== Example 5: Reddit - Neutral Post ===")
    try:
        result = client.analyze_single(reddit_text, platform="reddit")
        print_result(result)
    except Exception as e:
        print(f"Error: {e}")

    news_text = """
    BREAKING: According to anonymous sources, officials say the new policy will take effect next week.
    Exclusive investigation obtained by our reporters reveals leaked documents.
    Developing story - updated 10 mins ago.
    """

    print("\n=== Example 6: News Site - Breaking News ===")
    try:
        result = client.analyze_single(news_text, source_url="https://ndtv.com/article")
        print_result(result)
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== Example 7: Batch - Multi-platform ===")
    contents = [
        {"text": propaganda_text, "author": "user1",        "platform": "twitter"},
        {"text": instagram_text,  "author": "influencer",   "platform": "instagram"},
        {"text": youtube_text,    "author": "youtuber",     "platform": "youtube"},
        {"text": whatsapp_text,   "author": "unknown",      "platform": "whatsapp"},
        {"text": reddit_text,     "author": "redditor",     "platform": "reddit"},
        {"text": news_text,       "source_url": "https://ndtv.com/article"},
    ]
    try:
        results = client.analyze_batch(contents)
        for i, result in enumerate(results):
            print(f"\nContent {i+1}: {client.get_risk_summary(result)} [{result['reasoning'].get('platform')}]")
    except Exception as e:
        print(f"Error: {e}")


# ============= EXAMPLE 5: Real-world Integration =============
"""
Example: Monitor a Twitter/X account for suspicious posts

def monitor_twitter_account(account_handle: str):
    import tweepy  # pip install tweepy
    
    # Setup Twitter API credentials
    client = tweepy.Client(bearer_token="YOUR_BEARER_TOKEN")
    detector = ContentDetectorClient()
    
    # Get recent tweets
    tweets = client.get_users_tweets(id="...", max_results=100)
    
    flagged_content = []
    for tweet in tweets.data:
        result = detector.analyze_single(tweet.text)
        
        if result['risk_score'] > 60:  # Flag high-risk content
            flagged_content.append({
                'tweet_id': tweet.id,
                'text': tweet.text,
                'classification': result['classification'],
                'risk_score': result['risk_score'],
                'flags': result['flags']
            })
    
    return flagged_content
"""

# ============= EXAMPLE 6: Flask Web Dashboard =============
"""
Example: Simple web dashboard to visualize flagged content

from flask import Flask, render_template, request
import json

app = Flask(__name__)
detector = ContentDetectorClient()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    result = detector.analyze_single(data.get('text'))
    return result

@app.route('/api/dashboard-stats', methods=['GET'])
def stats():
    # Could aggregate historical data here
    return {
        'total_analyzed': 1000,
        'propaganda_count': 250,
        'campaign_count': 180,
        'neutral_count': 570,
        'average_risk_score': 35.2
    }

if __name__ == '__main__':
    app.run(debug=True)
"""
