from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel
import os
import sys
import json
import urllib.request
import urllib.parse

# search icanhazdadjoke API for a keyword to retrieve relevant joke
# if no keyword, return random joke from api
# user agent suggested by API docs: https://icanhazdadjoke.com/api for tracking API usage


api = 'https://icanhazdadjoke.com'
SEARCH_URL = f'{api}/search'
HEADERS = {
	'User-Agent': 'My Library (https://github.com/rosymaple/gemini)',
	'Accept': 'application/json'
}


# pydantic model
class JokeResponse(BaseModel):
	dad_joke: str
	gemini_joke: str



GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=GOOGLE_API_KEY)



keyword = input('Enter search term for dad jokes: ')
personalization = input('What style of joke would you like? (silly, punny, nerdy, sarcastic, cheesy, one-liner, long story, cringe, etc): ')


if keyword.strip():
    qs = urllib.parse.urlencode({'term': keyword.strip(), 'limit': 5})
    url = f'{SEARCH_URL}?{qs}'
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
        results = data.get('results', [])
        if results:
            joke = results[0].get('joke')
            print(f"Found a joke about '{keyword}'!")
        else:
            print(f"No jokes found for '{keyword}'. Let's try a different word.")
            new_keyword = input('Enter a different search term for dad jokes: ')
            
            # Try the new keyword
            if new_keyword.strip():
                qs = urllib.parse.urlencode({'term': new_keyword.strip(), 'limit': 5})
                url = f'{SEARCH_URL}?{qs}'
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req) as resp:
                    data = json.load(resp)
                    results = data.get('results', [])
                    if results:
                        joke = results[0].get('joke')
                        print(f"Found a joke about '{new_keyword}'!")
                    else:
                        print(f"Still no jokes found for '{new_keyword}'. Getting a random joke.")
                        req = urllib.request.Request(api + '/', headers=HEADERS)
                        with urllib.request.urlopen(req) as resp:
                            data = json.load(resp)
                            joke = data.get('joke')
            else:
                # If no new keyword, get random joke
                req = urllib.request.Request(api + '/', headers=HEADERS)
                with urllib.request.urlopen(req) as resp:
                    data = json.load(resp)
                    joke = data.get('joke')


else:
    req = urllib.request.Request(api + '/', headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
        joke = data.get('joke')
    print("Getting a random joke!")

# FINAL FALLBACK IF ALL ELSE FAILS :-(
if not joke:
    fallback_jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What do you call a fake noodle? An impasta!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a sleeping bull? A bulldozer!"
    ]
    import random
    joke = random.choice(fallback_jokes)
    print("Using a fallback joke!")

contents = """Personalize a dad joke using user's personalization input.

{}

Original dad joke:
{}

""".format(personalization, joke.replace('\n', ' '))


response = client.models.generate_content(
    model='models/gemini-2.5-flash',
    contents=contents,
    config=GenerateContentConfig(
        system_instruction=(
            """You are a PG-13 comedy writer chatbot. You will recieve one or more dad jokes from the API and a
            user personalization instruction. Choose the best, most relevant joke from the API, 
            and rewrite it using your own chatbot ideas
            to match the personalization style requested by the user. Do not repeat the original joke.
            """
        ),
        response_mime_type='application/json',
        response_schema=JokeResponse,
    ),
)


result = response.parsed  # pydantic object


print(f"""
I CAN HAZ DAD JOKE?
{result.dad_joke}

Gemini AI personalized dad joke:
{result.gemini_joke}
""".strip())