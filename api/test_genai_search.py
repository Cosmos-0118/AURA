import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    pytest.skip("GEMINI_API_KEY is not configured", allow_module_level=True)

client = genai.Client(api_key=api_key)
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
