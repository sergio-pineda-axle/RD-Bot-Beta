from openai import AzureOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AOAI_ENDPOINT_URL"),
    api_version="2024-05-01-preview"
)

# Get a list of assistants you've created
assistants = client.beta.assistants.list()

# Print their names and IDs
for a in assistants.data:
    print(f"{a.name}: {a.id}")