import json
import re
import streamlit as st
from config.shared_data import DEBUG_MODE, disease_synonym_map, symptom_synonyms_map, org_name_lookup
from config.filter_vocab import valid_filter_values

# Define the function schema GPT will use to structure its output
classification_function = {
    "name": "classify_query",
    "description": "Classifies user intent for a rare disease query.",
    "parameters": {
        "type": "object",
        "properties": {
            "intents": {
                "type": "array",
                "items": { "type": "string" },
                "description": "List of one or more classification intents"
            },
            "entities": {
                "type": "object",
                "properties": {
                    "disease": { "type": "array", "items": {"type": "string"} },
                    "organization": { "type": "array", "items": {"type": "string"} },
                    "symptom": { "type": "array", "items": {"type": "string"} },
                    "body_system": { "type": "array", "items": {"type": "string"} },
                    "service_type": { "type": "array", "items": {"type": "string"} }
                },
                "description": "Structured entity extraction by type"
            },
            "filters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": { "type": "string" },
                        "value": { "type": "string" }
                    },
                    "required": ["field", "value"]
                }
            }
        },
        "required": ["intents", "entities", "filters"]
    }
}

# Main function
def classify_query(client, deployment_name, user_query):
    try:
        prompt_path = "prompts/classification_prompt2.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Fill in valid filter vocab into the prompt
        prompt_filled = prompt_template \
            .replace("{{BODY_SYSTEM_VALUES}}", json.dumps(valid_filter_values["body_system"])) \
            .replace("{{SYMPTOM_FREQUENCY_VALUES}}", json.dumps(valid_filter_values["symptom_frequency"])) \
            .replace("{{DISEASE_CATEGORY_VALUES}}", json.dumps(valid_filter_values["disease_category"])) \
            .replace("{{SERVICE_TYPE_VALUES}}", json.dumps(valid_filter_values["service_type"]))

        # Send prompt + schema to GPT
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a query classifier."},
                {"role": "user", "content": prompt_filled + "\n\nQ: " + user_query}
            ],
            functions=[classification_function],
            function_call={"name": "classify_query"},
            temperature=0
        )
        
        print("🧠 RAW GPT FUNCTION CALL:\n", response.choices[0].message)

        # Extract structured arguments
        func_call = response.choices[0].message.function_call
        if not func_call or func_call.name != "classify_query":
            raise ValueError("Function call did not return valid classification.")

        raw = json.loads(func_call.arguments)
        entities = raw.get("entities", {
            "disease": [],
            "organization": [],
            "symptom": [],
            "body_system": [],
            "service_type": []
        })

        raw_entities = json.loads(func_call.arguments).get("entities", {}).copy()


        # Attempt to infer types using heuristics
        # Logic to detect comparison or support-check queries
        subject_text = " ".join(
            entities.get("disease", []) +
            entities.get("organization", []) +
            entities.get("symptom", [])
        ).lower()

        # Detect named diseases/orgs in the subject
        parts = re.split(r"\band\b|\bvs\b|,", subject_text)
        parts = [p.strip() for p in parts if p.strip()]

        # ⚠️ Only apply fallback logic if GPT missed all disease, organization, and symptom entities
        if not any(entities.get(k) for k in ["disease", "organization", "symptom"]):
            for p in parts:
                pl = p.lower()

                if pl in disease_synonym_map:
                    entities["disease"].append(disease_synonym_map[pl])
                elif pl in org_name_lookup:
                    entities["organization"].append(org_name_lookup[pl]["org_name"])
                elif pl in symptom_synonyms_map:
                    entities["symptom"].append(symptom_synonyms_map[pl]["canonical"])
                else:
                    # As a last resort, still guess — but log for auditing
                    entities["disease"].append(p.title())

        result = {
            "intents": raw.get("intents", []),
            "entities": entities,
            "filters": raw.get("filters", [])
        }

        # Detect multiple diseases or orgs
        if " and " in subject_text or " vs " in subject_text:
            parts = re.split(r"\band\b|\bvs\b", subject_text)
            clean = [p.strip() for p in parts if p.strip()]
            if len(clean) == 2:
                if any(i in result["intents"] for i in ["symptoms_list", "semantic"]):
                    result["intents"].append("symptom_comparison")
                    result["subject"] = clean
                elif "patient_org" in result["intents"]:
                    result["intents"].append("organization_comparison")
                    result["subject"] = clean

        # Detect org-support checks
        if "support" in subject_text or "cover" in subject_text:
            if "patient_org" in result["intents"] and entities.get("disease"):
                result["intents"].append("org_support_check")

        # Detect reverse symptom lookup
        if any(phrase in subject_text for phrase in [
            "what diseases have", "which diseases have", "diseases with", "what conditions have"
        ]):
            if "symptoms_list" not in result["intents"]:
                result["intents"].append("symptom_lookup_reverse")

        if DEBUG_MODE:
            st.markdown("### 🧪 Classification Output")
            st.code(json.dumps(result, indent=2))

        return result

    except Exception as e:
        st.error(f"Classification failed: {e}")
        return {"intents": ["semantic"], "entities": {}, "filters": []}
