import os
from google import genai
client = genai.Client()
print("Client initialized")
try:
    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input="Find 2 jewellers in Singapore"
    )
    print("Success:", interaction.output_text)
except Exception as e:
    print("Error:", type(e), e)
