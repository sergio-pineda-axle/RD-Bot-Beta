## Function: Query Classification - identifies the user’s intent and what disease or filters they're asking about

import re
import json
import difflib
import streamlit as st
from config.shared_data import DEBUG_MODE, symptom_synonyms_map, prompt_template, valid_filter_values

def classify_query(client, deployment_name, user_query):
    
    # Step 0: Try to detect symptom names directly from the query before using the AI model
    def detect_all_symptom_synonyms_in_query(query, synonyms_map):
        query_lower = query.lower()
        words = query_lower.split()
        matches = []
        seen = set()

        # Check every possible 1- to 7-word phrase in the user’s query to see if it matches a known symptom synonym
        for size in range(1, 8):
            for i in range(len(words) - size + 1):
                chunk = " ".join(words[i:i+size])
                clean_chunk = re.sub(r"[^\w\s]", "", chunk)

                for synonym, canonical in synonyms_map.items():
                    if canonical in seen:
                        continue
                    clean_syn = re.sub(r"[^\w\s]", "", synonym.lower())
                    score = difflib.SequenceMatcher(None, clean_chunk, clean_syn).ratio()
                    if score > 0.78:  # Accept match if it looks at least 78% similar to a known synonym (number is adjustable and currently slightly relaxed)
                        matches.append(canonical)
                        seen.add(canonical)
        
        return list(set(matches))  # Return unique list of matched symptoms

    try:
        # If symptoms are found in the query, skip GPT classification and directly construct a symptom-based intent
        detected_symptoms = detect_all_symptom_synonyms_in_query(user_query, symptom_synonyms_map)

        if detected_symptoms:

            # Try to heuristically extract a disease name (e.g. "symptoms of leigh syndrome")
            if " of " in user_query.lower():
                possible_disease = user_query.lower().split(" of ")[-1].strip(" ?.") # Basic guess for disease name by assuming it comes after 'of' in the query
            else:
                possible_disease = user_query

            filters = [{"field": "symptom_name", "value": sym} for sym in detected_symptoms]
            return {
                "intent": "symptoms_list",
                "subject": possible_disease,
                "filters": filters
            }

        # If no clear symptoms were found, ask GPT to classify the query using a detailed prompt
        prompt_filled = prompt_template \
            .replace("{{BODY_SYSTEM_VALUES}}", json.dumps(valid_filter_values["body_system"])) \
            .replace("{{SYMPTOM_FREQUENCY_VALUES}}", json.dumps(valid_filter_values["symptom_frequency"])) \
            .replace("{{DISEASE_CATEGORY_VALUES}}", json.dumps(valid_filter_values["disease_category"])) \
            .replace("{{SERVICE_TYPE_VALUES}}", json.dumps(valid_filter_values["service_type"]))

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a query classifier."},
                {"role": "user", "content": prompt_filled + "\n\nQ: " + user_query}
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        # DEBUG (Optional): Show what GPT returns (only if debug mode is enabled)
        if DEBUG_MODE:
            st.markdown("### 🧪 Classification raw output:")
            st.code(content)

        # Remove code block markers if GPT wrapped the result in ```json
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        # Convert GPT’s response into a Python dictionary so the chatbot can use it
        try:
            return json.loads(content.strip()) 
        
        # If GPT's output isn’t valid JSON, raise an error
        except json.JSONDecodeError as e: 
            raise ValueError(f"Malformed classification JSON:\n{content}\n\nError: {e}")

    except Exception as e:
        st.error(f"Classification failed: {e}")
        return {"intent": "semantic", "subject": "", "filters": []}