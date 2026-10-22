import os
import time
from datetime import datetime, timezone
import feedparser
from google import genai
from google.genai import types
from pydantic import BaseModel

# 1. Structured data schema matching index.html
class BenchmarkItem(BaseModel):
    metric: str
    score: int

class CreatorVerdict(BaseModel):
    product_name: str
    consensus_score: float
    verdict_summary: str
    benchmarks: list[BenchmarkItem]
    pros: list[str]
    cons: list[str]

class TechNewsItem(BaseModel):
    category: str
    headline: str
    hot_take: str

class WebsiteData(BaseModel):
    last_updated: str
    featured_review: CreatorVerdict
    live_news: list[TechNewsItem]

# 2. Collect headlines from tech feeds
feeds = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.tomshardware.com/feeds/all",
    "https://feeds.arstechnica.com/arstechnica/technology-lab"
]

raw_headlines = []
for url in feeds:
    parsed = feedparser.parse(url)
    for entry in parsed.entries[:4]:
        raw_headlines.append(f"- {entry.title}")

headlines_text = "\n".join(raw_headlines)
current_time = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

# 3. Connect to Gemini API with automatic retry
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""
Current time: {current_time}
Live tech headlines:
{headlines_text}

Tasks:
1. Set 'last_updated' to '{current_time}'.
2. Pick the biggest hardware or gadget topic from these headlines for 'featured_review'. Provide a realistic consensus_score out of 10, a punchy 2-sentence verdict_summary, 4 benchmark metrics (scored 1-100), 3 pros, and 2 cons.
3. Pick 3 distinct tech stories for 'live_news'. Provide a short category, a punchy headline, and a witty, honest 1-sentence 'hot_take' on why it matters to everyday consumers.
"""

response = None
for attempt in range(4):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WebsiteData,
            ),
        )
        if response and response.text:
            break
    except Exception as e:
        print(f"Attempt {attempt + 1} hit temporary server delay: {e}. Retrying in 5 seconds...")
        time.sleep(5)

if not response or not response.text:
    raise RuntimeError("Failed to get response from Gemini after 4 attempts.")

# 4. Write data to data.json
with open("data.json", "w", encoding="utf-8") as f:
    f.write(response.text)

print("data.json successfully updated by Gemini!")
