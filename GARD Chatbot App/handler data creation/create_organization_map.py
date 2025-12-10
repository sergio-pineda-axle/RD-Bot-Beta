import os
import json
from collections import defaultdict

# CONFIGURATION
RAW_DISEASE_FOLDER = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\raw_json_files"
ORG_INPUT_FILE = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\GARD Chatbot App\data\organization_disease_map.json"
OUTPUT_FILE = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\GARD Chatbot App\data\organization_map_automated.json"
LOG_FOLDER = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\GARD Chatbot App\logs"
MATCH_LOG_FILE = os.path.join(LOG_FOLDER, "org_disease_match_log.txt")
UNMATCHED_ORG_LOG_FILE = os.path.join(LOG_FOLDER, "unmatched_org_names.log") 

# Load organization map
with open(ORG_INPUT_FILE, "r", encoding="utf-8") as f:
    org_data = json.load(f)

# Build lookup maps
org_name_map = {org["org_name"].strip().lower(): org for org in org_data}
org_tag_map = defaultdict(list)
for org in org_data:
    for tag in org.get("tags", []):
        org_tag_map[tag.strip().lower()].append(org)

# Track match status
org_disease_tracker = {}
match_logs = []
unmatched_orgs = set() # stores (org_name, disease, homepage)


# Initialize disease list for each org
for org in org_data:
    org["disease_name"] = []

# Process each disease file
for filename in os.listdir(RAW_DISEASE_FOLDER):
    if not filename.endswith(".json"):
        continue

    filepath = os.path.join(RAW_DISEASE_FOLDER, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    disease = data.get("GARD_Name__c") or data.get("Name")
    if not disease:
        continue

    matched = set()

    # Match by patient org name
    for org_entry in data.get("Organization_Supported_Diseases__c", []):
        org_name = org_entry.get("Account_Name__c", "").strip()
        org_name_lower = org_name.lower()
        if org_name_lower in org_name_map:
            org = org_name_map[org_name_lower]
            org["disease_name"].append(disease)
            matched.add(org["org_name"])
            match_logs.append(f"{disease}: matched by org name → {org['org_name']}")
        elif org_name:
            homepage = org_entry.get("Website__c", "").strip()
            match_logs.append(f"{disease}: ⚠️ unmatched org name → '{org_name}' (URL: {homepage or 'N/A'})")
            unmatched_orgs.add((org_name, disease, homepage))

    # Match by Disease Category tag to org.disease_category
    tag_categories = data.get("tags", {}).get("Disease Category", [])
    for tag in tag_categories:
        tag_lower = tag.strip().lower()
        for org in org_data:
            if any(cat.strip().lower() == tag_lower for cat in org.get("disease_category", [])):
                if disease not in org["disease_name"]:
                    org["disease_name"].append(disease)
                    matched.add(org["org_name"])
                    match_logs.append(f"{disease}: matched by disease category → {org['org_name']}")

    if not matched:
        match_logs.append(f"{disease}: ❌ no org match found")

# Deduplicate disease list
for org in org_data:
    org["disease_name"] = sorted(set(org["disease_name"]))

# Save final output
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(org_data, f, indent=2, ensure_ascii=False)

# Save match log
with open(MATCH_LOG_FILE, "w", encoding="utf-8") as f:
    for line in match_logs:
        f.write(line + "\n")

# Save unmatched org log
with open(UNMATCHED_ORG_LOG_FILE, "w", encoding="utf-8") as f:
    for org_name, disease, homepage in sorted(unmatched_orgs):
        f.write(f"{disease}: '{org_name}' not found in org map — homepage: {homepage or 'N/A'}\n")

print(f"✅ Created: {OUTPUT_FILE}")
print(f"📝 Match log: {MATCH_LOG_FILE}")
print(f"⚠️ Unmatched orgs: {UNMATCHED_ORG_LOG_FILE}")
