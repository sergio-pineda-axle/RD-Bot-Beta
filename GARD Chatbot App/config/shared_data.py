import os
import json
from dotenv import load_dotenv
from config.filter_vocab import valid_filter_values
from utils.symptom_utils import build_symptom_synonym_map

# Load environment variables
load_dotenv()

# ------------------------
# DEBUG Environment Config
# ------------------------

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# AOAI config
aoai_endpoint = os.getenv("AOAI_ENDPOINT_URL")
aoai_subscription_key = os.getenv("AZURE_OPENAI_API_KEY")
aoai_api_version = os.getenv("AOAI_API_VERSION")
gpt_deployment = os.getenv("GPT_DEPLOYMENT_NAME")
ada_deployment = os.getenv("ADA_DEPLOYMENT_NAME")

# Search config
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_KEY")
search_index = os.getenv("SEARCH_INDEX_NAME")

# Assistant config
assistant_id = os.getenv("CODE_ASSISTANT_ID")
assistant_api_version = os.getenv("ASSISTANT_API_VERSION", "2024-05-01-preview")

# ------------------------
# Data Paths and Loaders
# ------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

def load_json_file(filename):
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)

# Load structured data files
disease_symptom_map = load_json_file("disease_symptom_map_automated.json")
org_disease_map = load_json_file("organization_map_automated.json")
# Preprocess acronyms into a lookup dict
org_name_to_record = {}

for org in org_disease_map:
    if not isinstance(org, dict):
        continue
    name = org.get("org_name", "")
    if name:
        org_name_to_record[name.lower()] = org
        # Add common acronym if present
        acronym = "".join(word[0] for word in name.split() if word[0].isupper())
        if len(acronym) >= 3:
            org_name_to_record[acronym.lower()] = org

# Export this for use in handlers
org_name_lookup = org_name_to_record

# Build canonical symptom synonym map
symptom_synonyms_map = build_symptom_synonym_map(disease_symptom_map)

# ------------------------
# Prompt Templates
# ------------------------

def load_prompt(filename):
    return open(os.path.join(BASE_DIR, "..", "prompts", filename), "r", encoding="utf-8").read()

system_instruction = load_prompt("system_instruction.txt")
prompt_template = load_prompt("classification_prompt2.txt")
code_interpreter_prompt = load_prompt("code_interpreter_instruction.txt")

# ------------------------
# Disease Synonym Map
# ------------------------
disease_synonym_map = {}

for disease_name, entry in disease_symptom_map.items():
    disease_synonym_map[disease_name.lower()] = disease_name
    for syn in entry.get("disease_synonyms", []):
        disease_synonym_map[syn.lower()] = disease_name