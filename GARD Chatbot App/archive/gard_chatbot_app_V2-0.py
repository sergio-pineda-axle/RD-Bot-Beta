from dotenv import load_dotenv
import streamlit as st
import os
import base64
import json
import logging
from openai import AzureOpenAI
from handlers.symptom_utils import get_structured_symptoms

# Load environment variables
load_dotenv()

# Load metadata schema for filtering
with open("azure_filter_schema.json", "r") as f:
    metadata_schema = json.load(f)

# Load disease-symptom structured map
with open("disease_symptom_map.json", "r", encoding="utf-8") as f:
    disease_symptom_map = json.load(f)

# Load organization to disease-service mapping
with open("organization_disease_map.json", "r", encoding="utf-8") as f:
    org_disease_map = json.load(f)

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

# Sub-Function (Definition): Query Classification Helper
def classify_query(client, deployment_name, user_query):

    # 1. Load Classification Helper Prompt
    classification_prompt = load_prompt("prompts/classification_prompt.txt")

    # 2. Request to Azure OpenAI model to interpret query and identify type, target, and filter values
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": classification_prompt},
                {"role": "user", "content": f"User query: {user_query}"}
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()
        if not content or not content.strip():
            raise ValueError("Empty response from classification GPT.")

        # Debug output for visibility
        st.code(content, language="json")  # or: print("Classification output:", content)
        return json.loads(content.strip())
    
    # 3. Ensure bot won't crash if GPT retruns malformed JSON
    except Exception as e:
        st.error(f"Failed to parse classification JSON: {e}")
        return {"type": "semantic", "filters": []}

# MAIN FUNCTION: Chat Interaction
def chat(messages, query):

    # Add user query to message history and display in chat window
    messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(query)
    with st.spinner('Processing...'):

    # 1. Initialize client to call Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=aoai_endpoint,
            api_key=aoai_subscription_key,
            api_version=aoai_api_version,
        )

    # 2. Run classify query function and retreive query classifcation from first GPT call (semantic, structured, mixed)
        classification = classify_query(client, gpt_deployment, query)

    # 3. Define Handlers for each intent 

        # Handling queries about patient organizations
        def handle_patient_org(filters):
            disease = None
            for f in filters:
                if f["field"].lower() == "disease":
                    disease = f["value"]
                    break

            if not disease:
                return None

            matching_entries = []
            for org in org_disease_map:
                if disease.lower() in [d.lower() for d in org.get("disease_name", [])]:
                    services = org.get("services_offered", [])
                    lines = []
                    for s in services:
                        if s.get("type") and s.get("url"):
                            lines.append(f"  - **{s['type']}**: [Link]({s['url']})")
                    if lines:
                        matching_entries.append(f"- **{org['org_name']}**\n" + "\n".join(lines))

            if not matching_entries:
                return None

            return f"Here are patient organizations that support **{disease}**:\n\n" + "\n\n".join(matching_entries)

        # Handling queries about specialists
        def handle_specialist(filters):
            # For now, let GPT handle via RAG
            return None

        # Handling queries involving medical emergencies
        def handle_emergency(query):
            danger_signs = [
                "I can't breathe",
                "I'm losing consciousness",
                "Severe chest pain",
                "Uncontrollable bleeding",
                "Severe allergic reaction",
                "Throat swelling and I can't breathe",
                "Severe headache with vision loss",
                "Passed out/fainted and won’t wake up",
                "Face is numb and I can't move my arm",
                "Seizure"
            ]
            for sign in danger_signs:
                if any(isinstance(q, str) and sign in q.lower() for q in query):

                    return (
                        "This sounds like a medical emergency. Please seek immediate medical attention by calling 911 or visiting the nearest emergency room. I am not a medical professional and cannot provide emergency medical advice."
                    )
            return None
        
        # Handling queries about symptoms
        def handle_symptoms(filters):
            disease = None
            body_system = None
            for f in filters:
                if f["field"].lower() == "disease":
                    disease = f["value"]
                elif f["field"].lower() == "body_system":
                    body_system = f["value"].strip().lower()

            if not disease:
                return None  # Not enough info

            symptoms = get_structured_symptoms(disease_symptom_map, disease, body_system)
            if not symptoms:
                return None

            # Format structured symptoms
            formatted = f"Based on available data for **{disease}** affecting the **{body_system or 'all systems'}**, common symptoms include:\n\n"
            for s in symptoms[:10]:
                name = s["symptom_name"]
                freq = s.get("frequency", "Unknown frequency")
                formatted += f"- **{name}** *(Frequency: {freq})*\n"
            
            return formatted

    # 4. Define a registry of intent handlers to Target values
        INTENT_REGISTRY = {
            "symptoms": handle_symptoms,
            "specialist": handle_specialist,
            "patient_org": handle_patient_org,
            "emergency": handle_emergency
        }
        
    # 5. Execute Handlers if Target Matches
        structured_response_parts = []
        structured_context = {}
        filters = classification.get("filters", [])
        targets = classification.get("target", [])

    # 6. Normalize targets to always be a list
        if isinstance(targets, str):
            targets = [targets]

    # 7. Check for "Medical Emergency" override first
        emergency_response = handle_emergency(query)
        if emergency_response:
            messages.append({"role": "assistant", "content": emergency_response})
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(emergency_response)
            return  # Skip rest

    # 8. If not a med emergency, collect all structured responses first
        handled_targets = []
        for target in targets:
            handler = INTENT_REGISTRY.get(target)
            if handler:
                response_part = handler(filters)
                if response_part:
                    structured_response_parts.append(response_part)
                    handled_targets.append(target)

    # 8b Yields any remaining content needed to be addressed by GPT   
        remaining_targets = [t for t in targets if t not in handled_targets]

    # Now that structured_response_parts is populated, build context
        structured_context = {
            "summary": "\n\n".join(structured_response_parts)
        } if structured_response_parts else {}

    # 9. For structured response(s), respond directly
        if classification["type"] == "structured":
            if structured_response_parts:
                full_response = "\n\n".join(structured_response_parts)
                messages.append({"role": "assistant", "content": full_response})
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(full_response)
            return  # Only return early for structured queries

    # 10. For hybrid (mixed) RAG queries, build filter string only from RAG-relevant fields
        filter_str = None
        if classification["type"] == "mixed" and classification.get("filters"):
            try:
                valid_metadata_fields = metadata_schema.keys()
                
                # Define only those fields that are meaningful for RAG filtering
                rag_filter_fields = {"inheritance", "category", "hpo_id"}

                filter_parts = [
                    f"{metadata_schema[f['field']]['index_field']} eq '{f['value']}'"
                    for f in classification["filters"]
                    if f["field"] in valid_metadata_fields and f["field"] in rag_filter_fields
                ]

                if filter_parts:
                    filter_str = " and ".join(filter_parts)

            except Exception as e:
                st.warning(f"Filter parsing failed: {e}")

    # 11. Log the classification result
        messages.append({
            "role": "system",
            "content": f"🧠 **Interpreter Output:**\n```json\n{json.dumps(classification, indent=2)}\n```"
        })
        
        # Temporary debug output
        if DEBUG_MODE:
            st.markdown(f"**Search filters used:** `{filter_str or 'None'}`")

        if classification["type"] in {"semantic", "mixed"}:
            if DEBUG_MODE:
                st.warning(f"Skipping filters due to `{classification['type']}` query to avoid over-filtering: `{filter_str}`")
            filter_str = None

    # 12. Construct message history to pass to GPT
        messages_for_gpt = [{"role": "system", "content": system_instruction}]

        # Inject structured response as prior assistant reply
        if classification["type"] == "mixed" and structured_response_parts:
            messages_for_gpt.append({
                "role": "assistant",
                "content": "\n\n".join(structured_response_parts)
            })

        # Build GPT follow-up prompt based on remaining targets
        if remaining_targets:
            remaining_query = (
                f"Please continue by addressing the remaining part of the query related to: "
                f"{', '.join(remaining_targets)}."
            )
        else:
            remaining_query = (
                "The structured data has been provided above. Please expand on any related information "
                "or assist further as needed."
            )

        messages_for_gpt.append({
            "role": "user",
            "content": remaining_query
        })  

        #temporary debug output showing full GPT sequence
        if DEBUG_MODE:
            st.markdown("### 💬 Final Messages Sent to GPT")
            for msg in messages_for_gpt:
                role = msg.get("role", "unknown").upper()
                st.markdown(f"**{role}**:\n```\n{msg['content']}\n```")

        # Placeholder system fallback if no structured data at all (safe)
        if not structured_response_parts:
            messages_for_gpt.append({
                "role": "system",
                "content": (
                    "Note: The structured system did not provide any data. Please ensure your response is helpful and reference only available information."
                )
            })

        if DEBUG_MODE:
            st.markdown("### 📨 GPT Input Message Stack")
            for m in messages_for_gpt:
                st.markdown(f"**{m['role']}**:\n```\n{m['content']}\n```")

    # 13. Generate a complete response by calling Azure OpenAI client (2nd APT GPT Call)
        completion = client.chat.completions.create(
            model=gpt_deployment,
            messages=messages_for_gpt,
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
                        "filter": filter_str,
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

    # 14. Process the response from Azure OpenAI and provide to user
        response_data = completion.to_dict()
        message_data = response_data["choices"][0]["message"]
        ai_response = message_data["content"]

        if DEBUG_MODE:
            st.markdown("### 🧠 GPT Raw Response")
            st.code(ai_response)

        if DEBUG_MODE:
            st.markdown("### 📦 Full GPT Message Object")
            st.code(json.dumps(message_data, indent=2))

        # Check for empty RAG retrieval
        no_rag_hits = (
            "context" in message_data
            and "citations" in message_data["context"]
            and len(message_data["context"]["citations"]) == 0
        )

        if DEBUG_MODE:
            st.markdown("### 🧾 RAG Citations Debug")
            st.code(json.dumps(message_data.get("context", {}), indent=2))


        # Give GPT a signal if there's no semantic content retrieved and no structured fallback
        if no_rag_hits and not structured_response_parts:
            messages_for_gpt.append({
                "role": "system",
                "content": (
                    "Note: The search system was unable to retrieve any relevant documents from the knowledge base for this query. You should let the user know that this topic might not be covered by current data."
                )
            })

        # Temporary DEBUG: Show RAG Top-K Chunks Retrieved
        if DEBUG_MODE and "context" in message_data and "citations" in message_data["context"]:
            st.markdown("### 🔎 Top-K RAG Chunks Retrieved by Azure Search")
            for i, citation in enumerate(message_data["context"]["citations"], start=1):
                title = citation.get("title", "Untitled")
                content = citation.get("content", "")
                st.markdown(f"**doc{i} — {title}**")
                st.code(content[:1000])  # truncate if needed

    # 14b Combine structured + GPT for mixed queries
        if classification["type"] == "mixed" and structured_response_parts:
            ai_response = "\n\n".join(structured_response_parts) + "\n\n---\n\n" + ai_response


        #temporary debug output
        if DEBUG_MODE:
            st.markdown("### 🧱 Structured Response Used")
            st.code("\n\n".join(structured_response_parts))

    # 15. Provide citation information in response

        # a: Build full citation map: doc1 -> title
        full_citation_map = {}
        if "context" in message_data and "citations" in message_data["context"]:
            for i, c in enumerate(message_data["context"]["citations"]):
                doc_id = f"doc{i+1}"
                title = c.get("title") or c.get("url") or c.get("id")
                full_citation_map[doc_id] = title

        # b: Filter for only cited doc IDs in ai_response (e.g., [doc1])
        cited_doc_ids = [
            doc_id for doc_id in full_citation_map
            if f"[{doc_id}]" in ai_response
        ]

        # c: Replace [doc1] with [GARD-Page_Home.md]
        for doc_id in cited_doc_ids:
            title = full_citation_map[doc_id]
            # if want name of doc/chunk instead of "dco 1" then add: ai_response = ai_response.replace(f"[{doc_id}]", f"[{title}]")

        # d: Show response and only cited sources
        messages.append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(ai_response)

            if cited_doc_ids and "context" in message_data and "citations" in message_data["context"]:
                st.markdown("**Sources:**")
                for doc_id in cited_doc_ids:
                    index = int(doc_id.replace("doc", ""))
                    citation = message_data["context"]["citations"][index - 1] if index - 1 < len(message_data["context"]["citations"]) else None
                    if citation:
                        title = citation.get("title", "Unknown Source")
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
        "user": "🧑‍💻",
        "system": "💻"
    }

    # Display past messages
    for message in st.session_state.messages:
        avatar = avatars.get(message["role"], "?")
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Handle new input
    if query:
        chat(st.session_state.messages, query)
        try:
            st.experimental_rerun()
        except AttributeError:
            st.warning("Streamlit version does not support rerun; please update to 1.30+ for best behavior.")

    # Button to clear chat
    clear_chat_placeholder = st.empty()
    if clear_chat_placeholder.button("Start New Session"):
        st.session_state.messages = clear_session(st.session_state.messages)
        clear_chat_placeholder.empty()
        st.success("Chat session has been reset.")

if __name__ == "__main__":
    main()

