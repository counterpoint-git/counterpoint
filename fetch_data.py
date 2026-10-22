import os
import time
from datetime import datetime, timezone
import feedparser
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class BenchmarkItem(BaseModel):
    metric: str
    score: int

class CreatorVerdict(BaseModel):
    product_name: str
    consensus_score: float
    verdict_summary: str = Field(description="Write like a real human tech reviewer talking to a friend, avoiding robotic jargon.")
    benchmarks: list[BenchmarkItem]
    pros: list[str]
    cons: list[str]

class TechNewsItem(BaseModel):
    category: str
    headline: str
    hot_take: str = Field(description="Keep it sounding casual, sharp, and like a human-written hot take.")

class WebsiteData(BaseModel):
    last_updated: str
    featured_review: CreatorVerdict
    live_news: list[TechNewsItem]

feeds = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.tomshardware.com/feeds/all",
    "https://feeds.arstechnica.com/arstechnica/technology-lab"
]

raw_headlines = []
for url in feeds:
    parsed = feedparser.parse(url)
    for entry in parsed.entries[:3]:
        raw_headlines.append(f"- {entry.title}")

headlines_text = "\n".join(raw_headlines)
current_time = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""
Current time: {current_time}
Live tech headlines:
{headlines_text}

Instructions for you:
1. Set 'last_updated' to '{current_time}'.
2. Pick the biggest tech headline for 'featured_review'. Write the summary like a real human tech enthusiast sharing an honest opinion over coffee—no stiff corporate language. Include 4 clean benchmark metrics (1-100), 3 pros, and 2 cons.
3. Choose 3 distinct tech news items for 'live_news'. Write the hot takes using punchy, casual, everyday human phrasing.
"""

# Automatic fallback queue covering active models to prevent downtime
fallback_models = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite"
]

response = None
for model_name in fallback_models:
    try:
        print(f"Trying engine: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WebsiteData,
            ),
        )
        if response and response.text:
            print(f"Successfully generated using {model_name}!")
            break
    except Exception as err:
        print(f"Engine {model_name} busy: {err}. Switching backup...")
        time.sleep(3)

if not response or not response.text:
    raise RuntimeError("All backup models are currently busy. Try again shortly.")

with open("data.json", "w", encoding="utf-8") as f:
    f.write(response.text)

print("data.json updated successfully!")
