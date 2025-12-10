import os
import json

RAW_DIR = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\raw_json_files"
OUTPUT_PATH = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Chatbot_Input_Files\V2.0\non-enriched\symptom_definitions_automated.jsonl"

seen = set()
output_lines = []

for filename in os.listdir(RAW_DIR):
    if not filename.endswith(".json"):
        continue

    path = os.path.join(RAW_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Skipping invalid JSON file: {filename}")
            continue

    for entry in data.get("GARD_Disease_Feature__c", []):
        feature = entry.get("Feature__r", {})
        
        symptom_name = feature.get("HPO_Name__c", "").strip()
        if not symptom_name or symptom_name.lower() in seen:
            continue
        seen.add(symptom_name.lower())

        hpo_url = feature.get("HPO_Feature_URL__c", "").strip()
        hpo_id = hpo_url.split("/")[-1] if "hpo.jax.org" in hpo_url else None
        if not hpo_id:
            continue

        synonyms_raw = feature.get("HPO_Synonym__c", "")
        synonyms = [s.strip() for s in synonyms_raw.split(";") if s.strip()]
        synonyms_text = f"also known as {', '.join(synonyms)}," if synonyms else ""

        systems_raw = feature.get("Feature_System__c", "")
        body_systems = [bs.strip() for bs in systems_raw.split(";") if bs.strip()]
        system_text = f"This symptom affects the {', '.join(body_systems)}" if body_systems else ""

        definition = feature.get("HPO_Description__c", "").strip()
        has_definition = bool(definition)

        if has_definition:
            content = f"{symptom_name}, {synonyms_text} is {definition}. {system_text}".strip(" ,.")
        else:
            if not synonyms and not body_systems:
                content = f"{symptom_name}. No additional information is available."
            else:
                content = f"{symptom_name}, {synonyms_text}. {system_text}".strip(" ,.")

        record = {
            "id": f"symptom_{hpo_id.lower().replace(':', '')}",
            "symptom_name": symptom_name,
            "hpo_id": hpo_id,
            "category": "symptom_definition",
            "feature_type": feature.get("HPO_Feature_Type__c", "").strip(),
            "url": hpo_url,
            "definition": definition if has_definition else "",
            "content": content,
            "synonyms": synonyms,
            "body_systems": body_systems,
            "has_definition": has_definition
        }

        output_lines.append(json.dumps(record, ensure_ascii=False))

with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
    for line in output_lines:
        out.write(line + "\n")

print(f"✅ Wrote {len(output_lines)} symptom records to {os.path.basename(OUTPUT_PATH)}")
