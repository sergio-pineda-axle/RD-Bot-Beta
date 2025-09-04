# utils/symptom_utils.py
# This file contains reusable functions that do the actual filtering on your JSON symptom map.

def get_structured_symptoms(disease_symptom_map, disease, body_systems=None, freq_filter=None, symptom_name_filter=None, symptom_synonyms_map=None):
    normalized_disease = disease.strip().lower()
    normalized_map = {k.strip().lower(): v for k, v in disease_symptom_map.items()}
    symptom_entries = normalized_map.get(normalized_disease, {}).get("symptoms", [])
    
    if body_systems:
        normalized_targets = set()

        for bs in body_systems:
            if isinstance(bs, dict) and "value" in bs:
                normalized_targets.add(bs["value"].strip().lower())
            elif isinstance(bs, str):
                normalized_targets.add(bs.strip().lower())

        symptom_entries = [
            s for s in symptom_entries
            if normalized_targets.intersection(
                bs.strip().lower() for bs in s.get("body_systems", [])
            )
        ]

    if freq_filter:
        if isinstance(freq_filter, list):
            symptom_entries = [s for s in symptom_entries if s.get("frequency") in freq_filter]
        else:
            symptom_entries = [s for s in symptom_entries if s.get("frequency") == freq_filter]

    if symptom_name_filter:
        symptom_name_filter = symptom_name_filter.strip().lower()
        canonical_name = symptom_synonyms_map.get(symptom_name_filter, symptom_name_filter) if symptom_synonyms_map else symptom_name_filter

        symptom_entries = [
            s for s in symptom_entries
            if s["symptom_name"].strip().lower() == canonical_name
        ]

    print(f"🧪 Found {len(symptom_entries)} symptoms for disease = '{disease}'")

    return sorted(symptom_entries, key=lambda x: x.get("frequency_rank") if isinstance(x.get("frequency_rank"), int) else 999)

def build_symptom_synonym_map(disease_symptom_map):
    synonym_map = {}

    for disease_entry in disease_symptom_map.values():
        symptoms = disease_entry.get("symptoms", [])
        for s in symptoms:
            canonical = s["symptom_name"]
            synonym_map[canonical.lower()] = canonical
            for syn in s.get("symptom_synonyms", []):
                synonym_map[syn.lower()] = canonical

    return synonym_map