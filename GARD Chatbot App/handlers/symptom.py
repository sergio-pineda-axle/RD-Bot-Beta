## Function: Handle Symptom Queries
# Main tool that gets called when the user query is about symptoms (intent: "symptoms_list").

import re
import json
import difflib
import streamlit as st
from utils.symptom_utils import get_structured_symptoms
from utils.filtering import normalize_filters
from config.shared_data import disease_symptom_map, disease_synonym_map, DEBUG_MODE

def handle_symptoms(filters, subject=None):
    
    # Step 1: Normalize the filter inputs and try to extract the disease name
    filters, disease = normalize_filters(filters, subject)
    disease = disease_synonym_map.get(disease.lower(), disease)

    
    print(f"[handle_symptoms] Disease after normalization: {disease}")

    body_system_filters = [] # Initialize before extracting from filters
    freq_filters = [] # Hold any frequency terms like "common" or "rare"
    
    # If disease name wasn't extracted during normalization, fallback to using the subject text
    if not disease:
        disease = subject  # fallback to classifier subject

    # Step 2: Pull out any frequency filters from the list
    for f in filters:
        if f["field"].lower() == "symptom_frequency":
            val = f["value"]
            if isinstance(val, list):
                freq_filters.extend(val)
            else:
                freq_filters.append(val)

    # Step 3: Extract body system filters if they exist
        elif f["field"].lower() == "body_system":
            val = f["value"]
            if isinstance(val, list):
                body_system_filters.extend(val)
            else:
                body_system_filters.append(val)
    
    # If we still don't have a disease, no data is provided to gpt
    if not disease:
        return None
    
    # Step 4: Check if the user asked about specific symptoms
    symptom_names = [f["value"] for f in filters if f["field"] == "symptom_name"]

    if symptom_names:
        # Look up only the specific symptoms provided, based on the disease
        symptoms = []
        for name in symptom_names:
            matched = get_structured_symptoms(
                disease_symptom_map,
                disease.lower(),
                body_system_filters,
                freq_filters,
                symptom_name_filter=name
            )
            symptoms.extend(matched)
    else:
        # If no specific symptom was named, return all matching symptoms for the disease
        symptoms = get_structured_symptoms(
            disease_symptom_map,
            disease.lower(),
            body_system_filters,
            freq_filters
        )

    # If no symptoms were found, stop here
    if not symptoms:
        return None

    # Step 5: Check if the user’s original query included words like "common" or "rare"
    original_freq_terms = [f["value"].lower() for f in filters if f["field"].lower() == "symptom_frequency"]
    sort_least_common = any(term in {"less common", "rare", "least common"} for term in original_freq_terms)
    sort_most_common = any(term in {"very common", "most common", "common"} for term in original_freq_terms)

    # Helper function: gives each frequency a ranking from most to least common
    def rank_frequency(f):
        order = [
            "Always (100%)",
            "Very frequent (80-99%)",
            "Frequent (30-79%)",
            "Occasional (5-29%)",
            "Uncommon (<1-4%)"
        ]
        try:
            return order.index(f)
        except ValueError:
            return 99  # Unknown or missing frequencies go to the bottom

    # Step 6: Sort the symptoms depending on what user asked for
    if sort_least_common:
        sorted_symptoms = sorted(symptoms, key=lambda s: rank_frequency(s["frequency"]))
    elif sort_most_common:
        sorted_symptoms = sorted(symptoms, key=lambda s: rank_frequency(s["frequency"]))
    else:
        # Default sorting uses the pre-ranked "frequency_rank" value
        sorted_symptoms = sorted(symptoms, key=lambda s: s.get("frequency_rank") if isinstance(s.get("frequency_rank"), int) else 99)


    # Step 7: Format the top 100 results into readable Markdown for the chatbot reply
    unique_body_systems = list(dict.fromkeys([bs.lower() for bs in body_system_filters]))
    body_system_label = ', '.join(unique_body_systems) if unique_body_systems else 'All Systems'
    count = len(sorted_symptoms)
    intro_line = f"There are {count} {body_system_label} symptoms for {disease}.\n\n"

    formatted = f"## Structured Symptoms for {disease} ({body_system_label})\n"
    for s in sorted_symptoms[:100]:
        formatted += f"- **{s['symptom_name']}** *(Frequency: {s.get('frequency', 'unknown')})*\n"

    return intro_line + formatted

def handle_symptom_comparison(filters, subject, disease_symptom_map):
    from utils.symptom_utils import get_structured_symptoms
    from config.shared_data import disease_synonym_map

    # Flatten subject from entity extraction (may be dicts or objects)
    if isinstance(subject, list):
        subject = [s["value"] if isinstance(s, dict) and "value" in s else str(s) for s in subject]
    elif isinstance(subject, str) and (" and " in subject or " vs " in subject):
        parts = re.split(r"\band\b|\bvs\b", subject)
        subject = [p.strip() for p in parts if p.strip()]
    else:
        return "❌ I need two disease names to compare."

    if not isinstance(subject, list) or len(subject) != 2:
        return "❌ I need exactly two diseases to compare."

    # Normalize names
    disease_a = disease_synonym_map.get(subject[0].lower(), subject[0])
    disease_b = disease_synonym_map.get(subject[1].lower(), subject[1])

    # Filter parsing
    body_system_filters = [f["value"] for f in filters if f["field"] == "body_system"]
    freq_filters = [f["value"] for f in filters if f["field"] == "symptom_frequency"]

    # Get structured symptom sets
    symptoms_a = get_structured_symptoms(disease_symptom_map, disease_a.lower(), body_system_filters, freq_filters)
    symptoms_b = get_structured_symptoms(disease_symptom_map, disease_b.lower(), body_system_filters, freq_filters)

    # Canonical symptom names only for comparison
    names_a = {s["symptom_name"].strip().lower() for s in symptoms_a}
    names_b = {s["symptom_name"].strip().lower() for s in symptoms_b}

    shared = names_a & names_b
    only_a = names_a - names_b
    only_b = names_b - names_a

    formatted = f"## Symptom Comparison: {disease_a} vs {disease_b}\n"

    if shared:
        formatted += f"\n**Shared Symptoms ({len(shared)}):**\n" + "\n".join(f"- {s}" for s in sorted(shared))
    if only_a:
        formatted += f"\n\n**Unique to {disease_a} ({len(only_a)}):**\n" + "\n".join(f"- {s}" for s in sorted(only_a))
    if only_b:
        formatted += f"\n\n**Unique to {disease_b} ({len(only_b)}):**\n" + "\n".join(f"- {s}" for s in sorted(only_b))

    return formatted


# Function: Handle reverse lookup Queries
def handle_symptom_lookup_reverse(filters, subject_list, disease_symptom_map):
    if not subject_list or not isinstance(subject_list, list):
        return "❌ Please provide at least one symptom to look up."

    query_symptoms = [s.lower().strip() for s in subject_list if isinstance(s, str)]
    body_system_filters = [f["value"] for f in filters if f["field"] == "body_system"]

    matches = []

    for disease, record in disease_symptom_map.items():
        disease_symptom_names = []
        for s in record.get("symptoms", []):
            name = s.get("symptom_name", "").lower()
            synonyms = [syn.lower() for syn in s.get("symptom_synonyms", [])]
            disease_symptom_names.extend([name] + synonyms)

        # Match only if all input symptoms are found in the disease symptom set
        if all(any(qs in dsn for dsn in disease_symptom_names) for qs in query_symptoms):
            matches.append(disease)

    if not matches:
        return f"❌ No diseases found with symptom '{disease_symptom_names}'."

    formatted = "## Diseases with All of These Symptoms:\n"
    formatted += f"**Query symptoms:** {', '.join(subject_list)}\n\n"
    formatted += "\n".join(f"- {d}" for d in sorted(matches))
    return formatted