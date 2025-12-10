from dotenv import load_dotenv
import os
import openai
import json
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration

openai.api_type = "azure"
openai.api_base = os.getenv("AOAI_ENDPOINT_URL")
openai.api_version = os.getenv("AOAI_API_VERSION")
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
embedding_model = os.getenv("ADA_DEPLOYMENT_NAME")

# Load local JSONL file
input_folder = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Chatbot_Input_Files\V2.0\non-enriched"
output_folder = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Chatbot_Input_Files\V2.2\enriched"
os.makedirs(output_folder, exist_ok=True)

input_files = [f for f in os.listdir(input_folder) if f.endswith('.jsonl')]

# Embed content and enrich records
def embed_text(text):
    client = openai.AzureOpenAI(
        api_key=openai.api_key,
        api_version=openai.api_version,
        azure_endpoint=openai.api_base,
    )
    response = client.embeddings.create(
        model=embedding_model,
        input=[text]
    )
    return response.data[0].embedding

# ========================================
# Embed content and enrich records
# ========================================
errors = []  # store any failed records

for file in tqdm(input_files, desc="Processing files"):
    input_path = os.path.join(input_folder, file)
    with open(input_path, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]

    for i, record in enumerate(records):
        base_content = record.get("content", "").strip()

        # === Per-file prepending logic ===
        if record.get("disease_name"):
            disease_name = record["disease_name"].strip()
            base_content = f"Disease: {disease_name}\n{base_content}"

            synonyms = record.get("synonyms", [])
            if isinstance(synonyms, list) and synonyms:
                synonyms_clean = [s.strip() for s in synonyms if s.strip()]
                if synonyms_clean:
                    synonym_line = f"Also known as: {', '.join(synonyms_clean)}"
                    base_content = f"{base_content}\n{synonym_line}"

        elif "category" in file.lower():
            label = record.get("disease_category", "").strip()
            if label:
                base_content = f"Disease Category: {label}\n{base_content}"

        elif "diagnostic_journey" in file.lower():
            section_title = record.get("section_title", "").strip()
            if section_title:
                base_content = f"Section: {section_title}\n{base_content}"

        elif "gard" in file.lower():
            section_title = record.get("section_title", "").strip()
            if section_title:
                base_content = f"Section: {section_title}\n{base_content}"

        elif "inheritance" in file.lower():
            pattern_label = record.get("inheritance_pattern", "").strip()
            if pattern_label:
                base_content = f"Inheritance Pattern: {pattern_label}\n{base_content}"

        elif "specialist" in file.lower():
            spec_type = record.get("specialist_type", "").strip()
            if spec_type:
                base_content = f"Specialist Type: {spec_type}\n{base_content}"

        elif "cause" in file.lower():
            cause_type = record.get("cause_type", "").strip()
            if cause_type:
                base_content = f"Cause Type: {cause_type}\n{base_content}"

        # Skip embedding if content is empty
        if not base_content:
            print(f"⚠️ Skipping empty content at record {i} in {file}")
            record.pop("content_vector", None)
            record["has_definition"] = False
            continue

        # Embed content
        try:
            record["content_vector"] = embed_text(base_content)
        except Exception as e:
            print(f"❌ Error in {file} at record {i}: {str(e)}")
            record["content_vector"] = []
            errors.append((file, i, str(e)))

        # Update content and structured fields
        record["content"] = base_content
        record["fields"] = {
            "title": record.get("disease_name") or record.get("symptom_name") or record.get("specialist_type") or record.get("section_title") or record.get("body_system") or record.get("cause_type") or record.get("disease_category") or record.get("inheritance_pattern") or "",
            "category": record.get("category", ""),
            "body_system": record.get("body_systems", []),
            "inheritance": record.get("inheritance", ""),
            "symptom_name": record.get("symptom_name", ""),
            "specialist_type": record.get("specialist_type", ""),
            "organization_name": record.get("organization_name", "")
        }

        print(f"[{file}] Record {i} embedded with title: {record['fields']['title']}")

    # Save enriched version
    output_path = os.path.join(output_folder, file.replace(".jsonl", "_enriched.jsonl"))
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    print(f"✅ Saved: {output_path}")
    
