import os
import pytest
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    pytest.skip("GEMINI_API_KEY is not configured", allow_module_level=True)

client = genai.Client(api_key=api_key)
print("Client initialized")
try:
    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input="Find 2 jewellers in Singapore"
    )
    print("Success:", interaction.output_text)
except Exception as e:
    print("Error:", type(e), e)
