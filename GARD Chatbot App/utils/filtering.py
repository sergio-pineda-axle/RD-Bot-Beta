## Function: Normalize Filters
# This function takes user-provided filters (like symptom names, body systems, or frequency) and tries to clean them up by:
# 1. Replacing synonyms with standard values
# 2. Resolving ambiguous or fuzzy matches
# 3. Extracting the most likely disease name either from filters or the question's subject

import difflib
import logging
from config.shared_data import valid_filter_values, symptom_synonyms_map, disease_symptom_map, disease_synonym_map

filter_synonyms = {
    "body_system": {
        "heart": "Cardiovascular System",
        "cardiac": "Cardiovascular System",
        "cardiology": "Cardiovascular System",
        "blood": "Blood and Blood-Forming Tissue",
        "muscle": "Musculoskeletal System",
        "muscles": "Musculoskeletal System",
        "brain": "Nervous System",
        "neurology": "Nervous System",
        "skin": "Skin System",
        "integumentary system": "Skin System",
        "gut": "Digestive System",
        "digestive": "Digestive System",
        "stomach": "Digestive System",
        "immune": "Immune System",
        "respiratory": "Respiratory System",
        "lungs": "Respiratory System",
        "vision": "Eye",
        "eye": "Eye",
        "hearing": "Ear",
        "ear": "Ear",
        "endocrine": "Endocrine System",
        "urinary": "Urinary System",
        "renal": "Urinary System"
    },
    "disease_category": {
        "rare disease": "Rare",
        "rare diseases": "Rare",
        "general rare diseases": "Rare",
        "general rare disease community": "Rare",
        "muscle diseases": "Muscular Dystrophies",
        "muscle conditions": "Muscular Dystrophies",
        "mitochondrial disorders": "Mitochondrial",
        "mitochondrial diseases": "Mitochondrial",
        "neurodevelopmental disorders": "Neurodevelopmental",
        "inborn errors of metabolism": "Metabolic",
        "neuromuscular conditions": "Neuromuscular"
    },
    "symptom_frequency": {
        "less common": ["Uncommon (<1-4%)", "Occasional (5-29%)"],
        "rare": ["Uncommon (<1-4%)"],
        "common": ["Very frequent (80-99%)", "Frequent (30-79%)"],
        "frequent": ["Very frequent (80-99%)", "Frequent (30-79%)"],
        "typical": ["Very frequent (80-99%)", "Frequent (30-79%)"],
        "very common": ["Very frequent (80-99%)"]
    }
}

def normalize_filters(filters, subject, entities=None):
    normalized_filters = [] #Store the cleaned-up version of each filter
    disease = None #Placeholder for detected disease name
    if isinstance(subject, list):
        subject = subject[0] if subject else ""
    if isinstance(subject, list):
        subject = subject[0] if subject else ""
    if isinstance(subject, str) and subject:
        subject = disease_synonym_map.get(subject.strip().lower(), subject)

    # Promote entities into filters if not already present
    if entities:
        if not filters:
            filters = []

        # Map entities to filter fields
        entity_to_field = {
            "symptom": "symptom_name",
            "body_system": "body_system",
            "service_type": "service_type"
        }

        for key, field in entity_to_field.items():
            for val in entities.get(key, []):
                filters.append({"field": field, "value": val})

    # Go through each filter to normalize its value and detect synonyms
    for f in filters:
        field = f["field"]
        value = f["value"].lower()

        # Special case/handle: symptom names are checked against a symptom synonym map to ensure we use the official/canonical name
        if field == "symptom_name":
            canonical = symptom_synonyms_map.get(value)
            
            # If we don't find a direct match, try fuzzy matching (looking for similar-sounding words) 
            if not canonical: 
                best_match = None
                highest_score = 0.0
                for synonym_key, target in symptom_synonyms_map.items():
                    score = difflib.SequenceMatcher(None, value, synonym_key).ratio()
                    if score > highest_score and score > 0.8:
                        best_match = target
                        highest_score = score

                canonical = best_match or canonical

            normalized_filters.append({"field": field, "value": canonical or value})
        
        # For non-symptom filters (like body system or disease category), check if they match known synonyms and standardize them
        else:
            syn_map = filter_synonyms.get(field, {})
            norm_value = syn_map.get(value)

            # Reverse match if value wasn't a synonym key but a known expanded value (Sometimes the value might actually be the expanded form (like "Very frequent") —this checks for that too)
            if not norm_value:
                for k, v in syn_map.items():
                    if isinstance(v, list) and value in [s.lower() for s in v]:
                        norm_value = v
                        break

            # If no match was found in synonyms, just use the original value
            norm_value = norm_value or value
            if isinstance(norm_value, list):
                for val in norm_value:
                    normalized_filters.append({"field": field, "value": val})
            else:
                normalized_filters.append({"field": field, "value": norm_value})

        # Warn the developer if the filter field isn't recognized
        if field not in valid_filter_values and field != "symptom_name":
            logging.warning(f"Unknown filter field: {field}")

    # Try to find the disease name from the normalized filters list
    for f in normalized_filters:
        if f["field"].lower() in {"disease_name", "disease_category"}:
            disease = f["value"]
            break

    # If no disease was found in filters, try using the subject string (which includes dis category) as a fallback
    if not disease and subject:
        norm = filter_synonyms.get("disease_category", {}).get(subject.lower())
        disease = norm if isinstance(norm, str) else subject.strip()

    # Final normalization of disease using disease_synonym_map
    if disease and isinstance(disease, str):
        disease = disease_synonym_map.get(disease.lower(), disease)

    print(f"[normalize_filters] Final normalized subject: {subject}")

    return normalized_filters, disease

def apply_filters(symptom_list, body_system_filters=None, freq_filters=None):
    if not symptom_list:
        return []

    result = [] 
    for sym in symptom_list:
        body_match = (
            not body_system_filters
            or any(system in body_system_filters for system in sym.get("body_systems", []))
        )
        freq_match = (
            not freq_filters
            or sym.get("frequency") in freq_filters
        )

        if body_match and freq_match:
            result.append(sym)

    return result