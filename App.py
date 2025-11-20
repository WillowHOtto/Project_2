from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel
import os
import json
import urllib.request
import urllib.parse

app = Flask(__name__)

# pydantic model
class JokeResponse(BaseModel):
    dad_joke: str
    gemini_joke: str

# Configuration
api = 'https://icanhazdadjoke.com'
SEARCH_URL = f'{api}/search'
HEADERS = {
    'User-Agent': 'My Library (https://github.com/rosymaple/gemini)',
    'Accept': 'application/json'
}

GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=GOOGLE_API_KEY)

def fetch_joke(keyword):
    """Fetch a joke from the API based on keyword or get a random one."""
    try:
        if keyword and keyword.strip():
            qs = urllib.parse.urlencode({'term': keyword.strip(), 'limit': 5})
            url = f'{SEARCH_URL}?{qs}'
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                data = json.load(resp)
                results = data.get('results', [])
                if results:
                    return results[0].get('joke'), keyword
                else:
                    # Fall back to random joke
                    req = urllib.request.Request(api + '/', headers=HEADERS)
                    with urllib.request.urlopen(req) as resp:
                        data = json.load(resp)
                        return data.get('joke'), "random"
        else:
            # Get random joke
            req = urllib.request.Request(api + '/', headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                data = json.load(resp)
                return data.get('joke'), "random"
                
    except Exception as e:
        print(f"Error fetching joke: {e}")
        fallback_jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? Because he was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a sleeping bull? A bulldozer!"
        ]
        import random
        return random.choice(fallback_jokes), "fallback"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_joke', methods=['POST'])
def get_joke():
    try:
        data = request.get_json()
        keyword = data.get('keyword', '')
        personalization = data.get('personalization', 'funny')
        
        # Fetch the joke
        joke, source = fetch_joke(keyword)
        
        if not joke:
            return jsonify({'error': 'No joke found. Please try a different keyword.'}), 400
        
        # Prepare content for Gemini
        clean_joke = joke.replace('\n', ' ')
        contents = f"""Personalize a dad joke using user's personalization input.

{personalization}

Original dad joke:
{clean_joke}

"""
        
        # Get personalized joke from Gemini
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=(
                    "You are a PG-13 comedy writer chatbot. You will receive one or more dad jokes from the API and a "
                    "user personalization instruction. Choose the best, most relevant joke from the API, "
                    "and rewrite it using your own chatbot ideas "
                    "to match the personalization style requested by the user. Do not repeat the original joke."
                ),
                response_mime_type='application/json',
                response_schema=JokeResponse,
            ),
        )
        
        result = response.parsed
        
        return jsonify({
            'success': True,
            'original_joke': joke,
            'personalized_joke': result.gemini_joke,
            'source': source
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)