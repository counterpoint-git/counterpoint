import os
import json
import time
from datetime import datetime, timezone, timedelta
import feedparser
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 12-Hour Cache Guard: Skip regeneration if data.json is less than 12 hours old
DATA_FILE = "data.json"
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        # Check file modification time as a secondary guard
        mtime = datetime.fromtimestamp(os.path.getmtime(DATA_FILE), tz=timezone.utc)
        if datetime.now(timezone.utc) - mtime < timedelta(hours=12):
            print("Data is less than 12 hours old. Skipping regeneration.")
            exit(0)
    except Exception:
        pass

class BenchmarkItem(BaseModel):
    metric: str
    score: int

class CreatorVerdict(BaseModel):
    product_name: str
    consensus_score: float
    verdict_summary: str = Field(description="Write like a real human tech enthusiast talking casually to a friend over coffee, avoiding corporate jargon.")
    youtuber_quote: str = Field(description="An iconic, realistic quote mimicking a famous tech reviewer like MKBHD or Linus Tech Tips about this product.")
    benchmarks: list[BenchmarkItem]
    pros: list[str]
    cons: list[str]

class TechNewsItem(BaseModel):
    category: str
    headline: str
    hot_take: str = Field(description="Keep it sounding casual, sharp, and like a human-written hot take.")

class VideoSuggestion(BaseModel):
    title: str
    channel: str
    search_query_hint: str

class WebsiteData(BaseModel):
    last_updated: str
    featured_review: CreatorVerdict
    live_news: list[TechNewsItem]
    video_suggestions: list[VideoSuggestion]

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

Instructions:
1. Set 'last_updated' to '{current_time}'.
2. Pick the biggest tech headline for 'featured_review'. Write a casual human review summary, provide a realistic 'youtuber_quote', 4 benchmarks (1-100), 3 pros, and 2 cons.
3. Choose 3 distinct tech news items for 'live_news' with witty everyday hot takes.
4. Provide 2 relevant 'video_suggestions' related to current tech trends with title, channel name, and search hint.
"""

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
    raise RuntimeError("All backup models are currently busy.")

with open(DATA_FILE, "w", encoding="utf-8") as f:
    f.write(response.text)

print("data.json updated successfully!")
