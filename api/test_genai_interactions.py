import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    pytest.skip("GEMINI_API_KEY is not configured", allow_module_level=True)

client = genai.Client(api_key=api_key)
try:
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input="Find 2 jewellers in Singapore with their actual phone numbers. Reply ONLY with valid JSON."
    )
    print("Success:", interaction.output_text)
except Exception as e:
    print("Error:", type(e), e)
