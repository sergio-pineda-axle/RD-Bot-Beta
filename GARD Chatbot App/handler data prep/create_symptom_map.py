import os
import json

# CONFIGURATION
input_folder = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\raw_json_files"
output_file = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\GARD Chatbot App\data\disease_symptom_map_automated.json"

# FREQUENCY RANK MAPPING
freq_rank_map = {
    "Always (100%)": 0,
    "Very frequent (80-99%)": 1,
    "Frequent (30-79%)": 2,
    "Occasional (5-29%)": 3,
    "Uncommon (<1-4%)": 4
}

# HELPER FUNCTION TO CLEAN SPLIT FIELDS
def clean_split(val):
    if not val:
        return []
    return [item.strip() for item in val.split(";") if item.strip()]

# NEW DATA STRUCTURE
disease_symptom_map = {}

# PROCESS ALL RAW JSON FILES
for filename in os.listdir(input_folder):
    if not filename.endswith(".json"):
        continue

    filepath = os.path.join(input_folder, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    disease_name = data.get("GARD_Name__c") or data.get("Name")
    if not disease_name:
        continue

    disease_synonyms = clean_split(data.get("GARD_Synonym__c", ""))

    feature_list = data.get("GARD_Disease_Feature__c", [])
    symptom_records = []

    for feature in feature_list:
        feat = feature.get("Feature__r", {})
        if feat.get("HPO_Feature_Type__c") != "Symptom":
            continue

        name = feat.get("HPO_Name__c")
        if not name:
            continue

        symptom_synonyms = clean_split(feat.get("HPO_Synonym__c", ""))
        systems = clean_split(feat.get("Feature_System__c", ""))
        frequency = feature.get("HPO_Frequency__c", "")
        rank = freq_rank_map.get(frequency, None)

        symptom_records.append({
            "symptom_name": name,
            "symptom_synonyms": symptom_synonyms,
            "body_systems": systems,
            "frequency": frequency,
            "frequency_rank": rank
        })

    if symptom_records:
        disease_symptom_map[disease_name] = {
            "disease_synonyms": disease_synonyms,
            "symptoms": symptom_records
        }

# WRITE TO OUTPUT FILE
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(disease_symptom_map, f, indent=2, ensure_ascii=False)

print(f"✅ Rebuilt disease symptom map saved to: {output_file}")
