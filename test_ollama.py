import os
from dotenv import load_dotenv
from ollama import Client

load_dotenv()

api_key = os.getenv("OLLAMA_API_KEY")

if not api_key:
    print("ERROR: Ollama API key was not found.")
    exit()

client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": f"Bearer {api_key}"
    }
)

print("Connecting to Ollama Cloud...")

response = client.chat(
    model="gpt-oss:120b",
    messages=[
        {
            "role": "user",
            "content": "Say hello to my new skincare AI project in one short sentence."
        }
    ]
)

print("\nOllama response:")
print(response.message.content)