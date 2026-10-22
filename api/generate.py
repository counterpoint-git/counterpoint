import os
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data.json')

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        search_query = query_params.get('q', [''])[0].strip()

        if not search_query:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing query parameter 'q'"}).encode('utf-8'))
            return

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "API key not configured"}).encode('utf-8'))
            return

        # Load existing database
        data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

        if "articles" not in data:
            data["articles"] = []

        # Check if article already exists in memory
        existing = next((a for a in data["articles"] if a["query"].lower() == search_query.lower()), None)
        if existing:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(existing).encode('utf-8'))
            return

        # Generate new article on-demand via Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        You are the lead editor of 'Counterpoint', an independent tech publication.
        Generate a deep-dive technical article responding to the reader search query: '{search_query}'.
        Return valid JSON only matching this exact schema:
        {{
            "query": "{search_query}",
            "tag": "On-Demand Deep Dive",
            "title": "Accurate, professional title about {search_query}",
            "summary": "Detailed technical analysis paragraph...",
            "youtuber_quote": "Direct expert perspective quote.",
            "consensus_score": 9.0,
            "benchmarks": [
                {{"metric": "Performance", "score": 92}},
                {{"metric": "Value", "score": 85}}
            ],
            "pros": ["Pro one", "Pro two"],
            "cons": ["Con one", "Con two"]
        }}
        """

        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()

            new_article = json.loads(text)
            data["articles"].append(new_article)

            # Save back to file
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(new_article).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
