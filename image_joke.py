import os
import sys
import json
import urllib.request
import urllib.parse
import requests  # Used for downloading the image

# --- Gemini Imports ---
from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel

# --- Configuration ---
# Set these API Keys in your environment variables for security!
GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')

def clean_up_image(filename: str):
    """Deletes a file if it exists."""
    print(f"\n Attempting to clean up file: {filename}...")
    try:
        os.remove(filename)
        print(f"✅ Successfully deleted {filename}.")
    except FileNotFoundError:
        # This is expected on the very first run if the file wasn't created yet
        print(f"File {filename} not found, nothing to delete.")
    except Exception as e:
        # Catch permissions errors, files being used by another program, etc.
        print(f"Error deleting {filename}: {e}")

if not GOOGLE_API_KEY:
    print("FATAL ERROR: Please set GEMINI_API_KEY environment variable.")
    sys.exit(1)

# Initialize Clients
client_gemini = genai.Client(api_key=GOOGLE_API_KEY)


# --- I Can Haz Dad Joke API Setup ---
api = 'https://icanhazdadjoke.com'
SEARCH_URL = f'{api}/search'
HEADERS = {
    'User-Agent': 'My Library (https://github.com/rosymaple/gemini)',
    'Accept': 'application/json'
}

# --- Pydantic Model for Gemini Output ---
class JokeResponse(BaseModel):
    dad_joke: str
    gemini_joke: str

# --- 1. Image Generation Functions ---

def generate_image_from_text(prompt_text: str):
    """Generates an image from a given text prompt using OpenAI's DALL-E 3."""
    try:
        # Create a more descriptive prompt for DALL-E based on the joke text
        image_prompt = f"A funny, whimsical, single-panel cartoon illustrating the concept of: '{prompt_text}'"
        
        print(f"\n Generating image for prompt: {image_prompt[:80]}...")
        
        response = client_gemini.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=image_prompt,
            config=dict(
            number_of_images=1, 
            output_mime_type="image/jpeg",
            aspect_ratio="1:1",
            )
        )
        return response.generated_images[0].image.image_bytes
    except Exception as e:
        print(f"An error occurred during image generation: {e}")
        return None

def save_image_bytes_to_local_directory(image_bytes: bytes, filename: str = "personalized_joke_image.jpg"):
    """
    Saves image bytes directly to a file in the same directory.
    This is the function needed when the API returns binary data (bytes), not a URL.
    """
    if not image_bytes:
        print("Download failed: No image data provided.")
        return

    try:
        # CRITICAL: Open the file in 'wb' (write-binary) mode
        with open(filename, 'wb') as f:
            f.write(image_bytes)
        
        print(f"✅ Image successfully saved to: {filename}")

    except Exception as e:
        print(f"An unexpected error occurred during file save: {e}")


# --- 2. Main Execution Logic ---

if __name__ == "__main__":
    
    # --- A. User Input and API Search ---
    
    keyword = input('Enter search term for dad jokes (leave blank for random): ')
    personalization = input('What style of joke would you like? (silly, punny, nerdy, sarcastic, cheesy, one-liner, long story, cringe, etc): ')

    joke = None
    try:
        if keyword.strip():
            qs = urllib.parse.urlencode({'term': keyword.strip(), 'limit': 1})
            url = f'{SEARCH_URL}?{qs}'
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                data = json.load(resp)
                joke = data.get('results', [{}])[0].get('joke')
        else:
            req = urllib.request.Request(api + '/', headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                data = json.load(resp)
                joke = data.get('joke')
    except Exception as e:
        print(f"Error accessing joke API: {e}")
        sys.exit(1)

    if not joke:
        print('No joke found for that keyword.')
        sys.exit(1)

    # --- B. Gemini Personalization ---

      # Prepare content for Gemini
    clean_joke = joke.replace('\n', ' ')
    contents = f"""Personalize a dad joke using user's personalization input.

{personalization}

Original dad joke:
{clean_joke}

"""
    
    try:
        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=(
                    """You are a PG-13 comedy writer chatbot. You will receive an original dad joke and a user personalization instruction. 
                    Rewrite the joke using your own ideas to match the personalization style requested by the user. Do not repeat the original joke.
                    """
                ),
                response_mime_type='application/json',
                response_schema=JokeResponse,
            ),
        )
        result = response.parsed  # This is the Pydantic object

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)

    # --- C. Output and Image Generation ---

    # Print the text results
    print("-" * 50)
    print(f"Original Dad Joke:\n-> {result.dad_joke}")
    print(f"\nGemini AI Personalized Joke ({personalization.upper()} Style):\n-> {result.gemini_joke}")
    print("-" * 50)

    # Generate and download the image for the personalized joke
    joke_text_for_image = result.gemini_joke
    
    if joke_text_for_image:
        image_bytes = generate_image_from_text(joke_text_for_image) 
        if image_bytes:
            save_image_bytes_to_local_directory(image_bytes)