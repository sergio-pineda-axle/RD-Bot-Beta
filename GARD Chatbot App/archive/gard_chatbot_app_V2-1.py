from dotenv import load_dotenv
import streamlit as st
import os
import base64
import json
import logging
import difflib
import re
from openai import AzureOpenAI
from handlers.symptom_utils import get_structured_symptoms
from filter_vocab import valid_filter_values
from filter_synonyms import filter_synonyms
from handlers.symptom_utils import build_symptom_synonym_map

# Load environment variables
load_dotenv()

# Load disease-symptom structured map
with open("disease_symptom_map.json", "r", encoding="utf-8") as f:
    raw_map = json.load(f)
    disease_symptom_map = {k.lower(): v for k, v in raw_map.items()}
    symptom_synonyms_map = build_symptom_synonym_map(disease_symptom_map)

# Load organization to disease-service mapping
with open("organization_disease_map.json", "r", encoding="utf-8") as f:
    org_disease_map = json.load(f)

# Load prompt template with placeholders
with open("prompts/classification_prompt2.txt", encoding="utf-8") as f:
    prompt_template = f.read()

# Inject canonical filter values
prompt_filled = prompt_template \
    .replace("{{BODY_SYSTEM_VALUES}}", json.dumps(valid_filter_values["body_system"])) \
    .replace("{{SYMPTOM_FREQUENCY_VALUES}}", json.dumps(valid_filter_values["symptom_frequency"])) \
    .replace("{{DISEASE_CATEGORY_VALUES}}", json.dumps(valid_filter_values["disease_category"])) \
    .replace("{{SERVICE_TYPE_VALUES}}", json.dumps(valid_filter_values["service_type"]))

# Retrieve AOAI Secrets
aoai_endpoint = os.getenv("AOAI_ENDPOINT_URL")
gpt_deployment = os.getenv("GPT_DEPLOYMENT_NAME")
ada_deployment = os.getenv("ADA_DEPLOYMENT_NAME")
aoai_subscription_key = os.getenv("AZURE_OPENAI_API_KEY")
aoai_api_version = os.getenv("AOAI_API_VERSION")

# Retrieve AI Search Secrets
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_KEY")
search_index = os.getenv("SEARCH_INDEX_NAME")

# Location information for accessing classification and system instructions prompts
def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()
    
# Function to extract title from citation
def get_title_from_citation(citation):
    fallback = citation.get("content", "").strip().split("\n")[0]
    return (
        citation.get("title")
        or citation.get("url")
        or citation.get("id")
        or citation.get("disease_name")
        or citation.get("symptom_name")
        or citation.get("specialist_type")
        or citation.get("section_title")
        or citation.get("body_system")
        or citation.get("cause_type")
        or citation.get("disease_category")
        or citation.get("inheritance_pattern")
        or fallback
        or "Untitled Document"
    )

# Load Assistant Chatbot Instruction Satement
system_instruction = load_prompt("prompts/system_instruction.txt")

# Enable Debug Mode
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

# Setup Logging
logging.basicConfig(
    filename="chatbot_debug.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Function: Normalize filters and resolve disease name
def normalize_filters(filters, subject):
    normalized_filters = []
    disease = None

    for f in filters:
        field = f["field"]
        value = f["value"].lower()

        # Handle symptom_name separately using symptom_synonyms_map
        if field == "symptom_name":
            canonical = symptom_synonyms_map.get(value)
            
            if not canonical:
                # Fuzzy partial match
                best_match = None
                highest_score = 0.0
                for synonym_key, target in symptom_synonyms_map.items():
                    score = difflib.SequenceMatcher(None, value, synonym_key).ratio()
                    if score > highest_score and score > 0.8:
                        best_match = target
                        highest_score = score

                canonical = best_match or canonical

            normalized_filters.append({"field": field, "value": canonical or value})
        else:
            syn_map = filter_synonyms.get(field, {})
            norm_value = syn_map.get(value)

            # Reverse match if value wasn't a synonym key but a known expanded value
            if not norm_value:
                for k, v in syn_map.items():
                    if isinstance(v, list) and value in [s.lower() for s in v]:
                        norm_value = v
                        break

            # Fallback to passthrough
            norm_value = norm_value or value
            if isinstance(norm_value, list):
                for val in norm_value:
                    normalized_filters.append({"field": field, "value": val})
            else:
                normalized_filters.append({"field": field, "value": norm_value})

        if field not in valid_filter_values and field != "symptom_name":
            logging.warning(f"Unknown filter field: {field}")

    # Step 2: Extract disease from filters if possible
    for f in normalized_filters:
        if f["field"].lower() in {"disease_name", "disease_category"}:
            disease = f["value"]
            break

    # Step 3: Fallback to subject if disease not found
    if not disease and subject:
        norm = filter_synonyms.get("disease_category", {}).get(subject.lower())
        disease = norm if isinstance(norm, str) else subject.strip()

    return normalized_filters, disease

# Function: Classify user query
def classify_query(client, deployment_name, user_query):
    # Step 0: Pre-check for known symptom canonical name or synonyms in the query
    def detect_all_symptom_synonyms_in_query(query, synonyms_map):
        query_lower = query.lower()
        words = query_lower.split()
        matches = []
        seen = set()

        # Try sliding windows of 3- to 7-word chunks
        for size in range(1, 8):
            for i in range(len(words) - size + 1):
                chunk = " ".join(words[i:i+size])
                clean_chunk = re.sub(r"[^\w\s]", "", chunk)

                for synonym, canonical in synonyms_map.items():
                    if canonical in seen:
                        continue
                    clean_syn = re.sub(r"[^\w\s]", "", synonym.lower())
                    score = difflib.SequenceMatcher(None, clean_chunk, clean_syn).ratio()
                    if score > 0.78:  # slightly relaxed for multi match
                        matches.append(canonical)
                        seen.add(canonical)
        
        return list(set(matches))  # remove duplicates

    try:
        # If GPT fails or skips symptom_name filter, inject it ourselves
        detected_symptoms = detect_all_symptom_synonyms_in_query(user_query, symptom_synonyms_map)

        if detected_symptoms:
            if " of " in user_query.lower():
                possible_disease = user_query.lower().split(" of ")[-1].strip(" ?.")  # crude fallback
            else:
                possible_disease = user_query

            filters = [{"field": "symptom_name", "value": sym} for sym in detected_symptoms]
            return {
                "intent": "symptoms_list",
                "subject": possible_disease,
                "filters": filters
            }

        # Otherwise fall back to GPT classification
        with open("prompts/classification_prompt2.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()

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
        if DEBUG_MODE:
            st.markdown("### 🧪 Classification raw output:")
            st.code(content)

        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed classification JSON:\n{content}\n\nError: {e}")

    except Exception as e:
        st.error(f"Classification failed: {e}")
        return {"intent": "semantic", "subject": "", "filters": []}


def detect_symptom_synonym(query, synonyms_map):
    query_lower = query.lower()
    for synonym, canonical in synonyms_map.items():
        if synonym.lower() in query_lower:
            return canonical
    return None

# Function to handle symptoms based on classification with 1st gpt call
def handle_symptoms(filters, subject=None):
    filters, disease = normalize_filters(filters, subject)
    if not disease:
        disease = subject  # fallback to classifier subject
    body_system_filters = []

    if DEBUG_MODE:
        st.markdown("### 🧪 Parsed Filters")
        st.code(json.dumps(filters, indent=2))

    freq_filters = []

    for f in filters:
        if f["field"].lower() == "symptom_frequency":
            val = f["value"]
            if isinstance(val, list):
                freq_filters.extend(val)
            else:
                freq_filters.append(val)

    for f in filters:
        if f["field"].lower() == "disease":
            disease = f["value"]
        elif f["field"].lower() == "body_system":
            val = f["value"]
            if isinstance(val, list):
                body_system_filters.extend(val)
            else:
                body_system_filters.append(val)
    
    if not disease:
        return None
    
    symptom_names = [f["value"] for f in filters if f["field"] == "symptom_name"]

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

    if DEBUG_MODE:
        st.markdown("### ✅ Symptoms Returned from Lookup")
        st.code(json.dumps(symptoms[:10], indent=2))

    if not symptoms:
        return None

    # Sort descending if "less common" was in original filter list
    # Capture all original raw values (before normalization)
    original_freq_terms = [f["value"].lower() for f in filters if f["field"].lower() == "symptom_frequency"]
    sort_least_common = any(term in {"less common", "rare", "least common"} for term in original_freq_terms)

    # Sort accordingly
    sorted_symptoms = sorted(symptoms, key=lambda s: s.get("frequency_rank", 99), reverse=not sort_least_common)

    formatted = f"## Structured Symptoms for {disease} ({', '.join(body_system_filters) if body_system_filters else 'All Systems'})\n"
    for s in sorted_symptoms[:10]:
        formatted += f"- **{s['symptom_name']}** *(Frequency: {s.get('frequency', 'unknown')})*\n"
    return formatted

# Function to handle patient organization based on classification with 1st gpt call
def handle_patient_org(filters, subject=None):
    filters, disease = normalize_filters(filters, subject)
    if DEBUG_MODE:
        logging.info(f"[ORG] Subject: {subject} | Normalized disease: {disease}")
    matching_entries = []
    service_type_filter = None

    # Match by disease_name
    for org in org_disease_map:
        if disease.lower() in [d.lower() for d in org.get("disease_name", [])]:
            services = org.get("services_offered", [])
            filtered_services = [
                s for s in services
                if s.get("type") and s.get("url")
                and (not service_type_filter or service_type_filter in s["type"].lower())
            ]
            if filtered_services:
                lines = [f"  - **{s['type'].title()}**: [Link]({s['url']})" for s in filtered_services]
                matching_entries.append(f"- **{org['org_name']}**\n" + "\n".join(lines))

    # Fallback match by disease_category
    if not matching_entries:
        for org in org_disease_map:
            if any(disease.lower() == cat.lower() for cat in org.get("disease_category", [])):
                services = org.get("services_offered", [])
                filtered_services = [
                    s for s in services
                    if s.get("type") and s.get("url")
                    and (not service_type_filter or service_type_filter in s["type"].lower())
                ]
                lines = [f"  - **{s['type'].title()}**: [Link]({s['url']})" for s in filtered_services]

                if not lines:
                    lines.append("  - No specific services listed, but this organization supports this disease category.")

                matching_entries.append(f"- **{org['org_name']}**\n" + "\n".join(lines))

    # Final fallback: match by org_name OR fuzzy match org-resembling subject
    if not matching_entries:
        for org in org_disease_map:
            org_name = org.get("org_name", "")
            org_name_lower = org_name.lower()
            disease_lower = disease.lower()

            if disease_lower in org_name_lower or org_name_lower in disease_lower:
                services = org.get("services_offered", [])
                filtered_services = [
                    s for s in services
                    if s.get("type") and s.get("url")
                    and (not service_type_filter or service_type_filter in s["type"].lower())
                ]
                lines = [f"  - **{s['type'].title()}**: [Link]({s['url']})" for s in filtered_services]

                if not lines:
                    lines.append("  - No specific services listed, but this organization may be relevant.")

                matching_entries.append(f"- **{org_name}**\n" + "\n".join(lines))

    if DEBUG_MODE and matching_entries:
        st.markdown("### ✅ Structured Org Results Used")
        st.code("\n\n".join(matching_entries))

    if not matching_entries:
        if DEBUG_MODE:
            st.warning(f"⚠️ No orgs matched for normalized subject: '{disease}'")
        try:
            with open("logs/unmatched_patient_org_queries.log", "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"Unmatched subject: {subject or '[missing subject]'} → normalized: {disease or '[missing disease]'}\n"
                )
        except Exception as e:
            if DEBUG_MODE:
                st.warning(f"Failed to write to log: {e}")
        return f"No patient organizations found for **{disease}**."

    return f"## Patient Organizations for {disease}\n\n" + "\n\n".join(matching_entries)



# MAIN FUNCTION: Chat Interaction

# Function to handle the chat interaction
def chat(messages, query):
    messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(query)
    with st.spinner('Processing...'):

        # Create AOAI Client
        client = AzureOpenAI(
            azure_endpoint=aoai_endpoint,
            api_key=aoai_subscription_key,
            api_version=aoai_api_version,
        )

        # Step 1: Classify the query

        classification = classify_query(client, gpt_deployment, query)
        structured_parts = []

        if classification["intent"] in {"symptoms_list", "mixed"}:
            filters, subject = normalize_filters(classification.get("filters", []), classification.get("subject"))
            symptom_response = handle_symptoms(filters, subject)
            if symptom_response:
                structured_parts.append(symptom_response)

        if classification["intent"] in {"patient_org", "mixed"}:
            org_response = handle_patient_org(classification["filters"], classification.get("subject"))
            if org_response:
                structured_parts.append(org_response)

        structured_symptom_block = "\n\n---\n\n".join(structured_parts)
      
        # Step 2: Generate a completion using the Azure OpenAI client
        if structured_symptom_block:
            combined_user_input = (
                f"The following structured symptom data is relevant and should be used to answer the query below.\n\n"
                f"{structured_symptom_block}\n\n"
                f"Question: {query}"
            )
        else:
            combined_user_input = query
        
        completion = client.chat.completions.create(
            model=gpt_deployment,
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": combined_user_input},
            ],
            max_tokens=500,
            temperature=0.5,
            top_p=0.85,
            frequency_penalty=0.1,
            presence_penalty=0,
            stop=None,
            stream=False,
            extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": f"{search_endpoint}",
                        "index_name": search_index,
                        "semantic_configuration": "default",
                        "query_type": "vector_simple_hybrid",
                        "fields_mapping": {},
                        "in_scope": True,
                        "filter": None,
                        "strictness": 3,
                        "top_n_documents": 5,
                        "authentication": {
                            "type": "api_key",
                            "key": f"{search_key}"
                        },
                        "embedding_dependency": {
                            "type": "deployment_name",
                            "deployment_name": ada_deployment
                        }
                    }
                }]
            }
        )

        response_data = completion.to_dict()
        message_data = response_data["choices"][0]["message"]
        ai_response = message_data["content"]

    # DISPLAY REFERENCE SOURCES ON UI
        # Step 1: Build full citation map: doc1 -> title
        full_citation_map = {}
        if "context" in message_data and "citations" in message_data["context"]:
            for i, c in enumerate(message_data["context"]["citations"]):
                doc_id = f"doc{i+1}"
                full_citation_map[doc_id] = get_title_from_citation(c)

        if DEBUG_MODE:
            st.markdown("### 🗂️ Full Citation Map")
            st.code(json.dumps(full_citation_map, indent=2))

        # Step 2: Filter for only cited doc IDs in ai_response (e.g., [doc1])
        cited_doc_ids = [
            doc_id for doc_id in full_citation_map
            if f"[{doc_id}]" in ai_response
        ]

        if DEBUG_MODE:
            st.markdown("### 🔍 Cited Doc IDs Detected in Response")
            st.code(json.dumps(cited_doc_ids, indent=2))

        # Step 3: Replace [doc1] with [GARD-Page_Home.md]
        pass

        if DEBUG_MODE:
            st.markdown("### ✏️ AI Response After Replacements")
            st.code(ai_response)
        
        # Step 4: Show response and only cited sources
        messages.append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(ai_response)

            if cited_doc_ids and "context" in message_data and "citations" in message_data["context"]:
                st.markdown("**Sources:**")
                for doc_id in cited_doc_ids:
                    index = int(doc_id.replace("doc", ""))
                    citation = message_data["context"]["citations"][index - 1] if index - 1 < len(message_data["context"]["citations"]) else None
                    if citation:
                        title = get_title_from_citation(citation)
                        content = citation.get("content", "")
                        with st.expander(f"{doc_id} - {title}"):
                            st.markdown(content)

# Clear session state
def clear_session(messages):
    st.cache_data.clear()
    messages.clear()
    return messages

# Main app entrypoint
def main():
    st.set_page_config(page_title="Rare Disease Chatbot", page_icon="🧬")

    # Load and encode image
    logo_path = os.path.join(os.path.dirname(__file__), "axle_logo.png")
    with open(logo_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode()

    # Center the image
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src="data:image/png;base64,{base64_image}" width="180">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div style="text-align: center;">
            <h1>Rare Disease Chatbot</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("Hi there. I’m here to help you learn more about rare diseases. Please note I am not a doctor and cannot give medical advice. For your safety and privacy, please avoid sharing any personal health information.")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    query = st.chat_input("Input query here...")

    avatars = {
        "assistant": "🤖",
        "user": "🧑‍💻"
    }

    # Display past messages
    for message in st.session_state.messages:
        avatar = avatars.get(message["role"], "?")
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Handle new input
    if query:
        chat(st.session_state.messages, query)

    # Button to clear chat
    clear_chat_placeholder = st.empty()
    if clear_chat_placeholder.button("Start New Session"):
        st.session_state.messages = clear_session(st.session_state.messages)
        clear_chat_placeholder.empty()
        st.success("Chat session has been reset.")

if __name__ == "__main__":
    main()