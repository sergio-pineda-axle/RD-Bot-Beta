import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AOAI_ENDPOINT_URL"),
    api_version=os.getenv("AOAI_API_VERSION")
)

# Upload function
def upload_file(file_path):
    with open(file_path, "rb") as f:
        response = client.files.create(
            file=f,
            purpose="assistants"
        )
    return response.id

if __name__ == "__main__":
    symptom_file_id = upload_file("disease_symptom_map.json")
    org_file_id = upload_file("organization_disease_map.json")

    print("✅ Upload complete")
    print("SYMPTOM FILE ID:", symptom_file_id)
    print("ORG FILE ID:", org_file_id)