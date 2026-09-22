import os
from dotenv import load_dotenv
load_dotenv("/Users/hemanth_babu/AURA/.env")
from google import genai
from google.genai import types

client = genai.Client()
try:
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        contents="Find 2 jewellers in Singapore with their actual phone numbers",
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0,
        )
    )
    print("Success:", response.text)
except Exception as e:
    print("Error:", type(e), e)
