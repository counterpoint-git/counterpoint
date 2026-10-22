import os
import json
from datetime import datetime, timezone, timedelta
import urllib.request
import xml.etree.ElementTree as ET
import google.generativeai as genai

DATA_FILE = "data.json"

def fetch_rss_headlines():
    rss_urls = [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.feedburner.com/oreilly/radar/atom",
        "https://www.engadget.com/rss.xml",
        "https://gizmodo.com/feed"
    ]
    headlines = []
    for url in rss_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                for item in root.findall('.//item')[:15]:
                    title = item.find('title')
                    if title is not None and title.text:
                        headlines.append(title.text.strip())
        except Exception:
            continue
    return headlines

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    headlines = fetch_rss_headlines()
    context_str = "\n".join(headlines) if headlines else "General major consumer tech updates, silicon releases, AI models, mobile hardware, and operating systems."

    prompt = f"""
    You are the lead editor of 'Counterpoint', an independent tech publication.
    Based on the recent tech headlines and trends provided below, generate a comprehensive dataset containing EXACTLY 100 items in the 'featured_stories' array covering a diverse range of hardware, software, AI, and consumer tech topics.
    
    Return a valid JSON object only, with NO markdown backticks outside, pure JSON string matching this exact structure:
    {{
        "last_updated": "{datetime.now(timezone.utc).strftime('%b %d, %Y - %H:%M UTC')}",
        "featured_stories": [
            {{
                "id": "story-1",
                "tag": "Deep Dive Editorial",
                "title": "Compelling Technical Title 1",
                "summary": "Detailed technical analysis summary paragraph explaining the headline..."
            }}
        ],
        "video_playlist": [
            {{
                "id": "vid-1",
                "title": "Video title suggestion",
                "channel": "Channel Name",
                "search_query_hint": "YouTube search query"
            }}
        ]
    }}
    
    Ensure there are precisely 100 items in the 'featured_stories' array covering distinct consumer tech topics. Recent headlines context: {context_str}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        data = json.loads(text)
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully updated data.json with 100 articles")
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    main()
