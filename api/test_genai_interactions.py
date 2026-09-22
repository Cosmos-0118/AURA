import os
from dotenv import load_dotenv
load_dotenv("/Users/hemanth_babu/AURA/.env")
from google import genai

client = genai.Client()
try:
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input="Find 2 jewellers in Singapore with their actual phone numbers. Reply ONLY with valid JSON."
    )
    print("Success:", interaction.output_text)
except Exception as e:
    print("Error:", type(e), e)
