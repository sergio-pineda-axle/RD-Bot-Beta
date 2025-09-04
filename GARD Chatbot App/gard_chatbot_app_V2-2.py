import streamlit as st
import os
import io
os.makedirs("logs", exist_ok=True)
import base64
import json
import logging
from openai import AzureOpenAI
from services.classify_query import classify_query
from utils.filtering import normalize_filters
from config.shared_orchestration import dispatch_tool
from config.shared_data import (
    DEBUG_MODE,
    aoai_endpoint,
    aoai_subscription_key,
    aoai_api_version,
    gpt_deployment,
    ada_deployment,
    search_endpoint,
    search_key,
    search_index,
    system_instruction,
    disease_symptom_map,
    org_disease_map
)

# Setup Logging
logging.basicConfig(
    filename="chatbot_debug.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Function to extract title from citation
# Returns the most descriptive available title from a citation dictionary
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

## MAIN Function: Chat Interaction - Handles the main chat logic
def chat(messages, query):
    # Step 0: Append user message to chat history and display
    messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(query)

    with st.spinner('Processing...'):
        # Step 1: Initialize Azure OpenAI client
        client = AzureOpenAI(
            azure_endpoint=aoai_endpoint,
            api_key=aoai_subscription_key,
            api_version=aoai_api_version,
        )

        # Step 2: Run classification on the user query to extract subject, intent, and filters
        classification = classify_query(client, gpt_deployment, query)
        intents = classification.get("intents", [])
        entities = classification.get("entities", {})
        filters, _ = normalize_filters(classification.get("filters", []), "", entities)

        # DEBUG: Print classification results
        print("RAW CLASSIFIER OUTPUT:", json.dumps(classification, indent=2))

        # Step 4: Loop through each intent and delegate to the appropriate handler
        structured_outputs = []
        for intent in intents:
            result = dispatch_tool(
                intent,
                entities,
                filters,
                query,
                maps=(disease_symptom_map, org_disease_map)
            )
            if result:
                structured_outputs.append(result)

        # Step 4.5: Optionally render structured output before GPT runs
        for output in structured_outputs:
            label = output["intent"].replace("_", " ").title()
            if output["source"] == "assistant":
                if DEBUG_MODE:
                    st.markdown(f"### 📊 {label}")
            elif output["source"] == "symptom_handler":
                if DEBUG_MODE:
                    st.markdown(f"### 🧠 Structured Symptoms")
            elif output["source"] == "org_handler":
                if DEBUG_MODE:
                    st.markdown(f"### 🏥 Patient Organizations")
            
            # ⬇️ Render chart image if present
            if output.get("image_data"):
                st.image(io.BytesIO(output["image_data"]), caption="Chart (assistant-rendered)")


            # ⬇️ Render the display text
            if DEBUG_MODE:
                st.markdown(output["display"])

        # Step 5: Construct GPT input prompt using tool-generated outputs
        if structured_outputs:
            tool_block = "\n\n---\n\n".join(output["display"] for output in structured_outputs if output.get("display"))
            tool_summaries = "\n".join(f"- {output['summary']}" for output in structured_outputs if output.get("summary"))

            combined_input = (
                "The following structured outputs are the authoritative results for this query, produced by trusted tools.\n"
                + (f"Summary of tool outputs:\n{tool_summaries}\n\n" if tool_summaries else "")
                + "Do not contradict or reinterpret these results. Do not say the information is missing or that the assistant already provided a response. Supplement, summarize or provide helpful context as needed — but do not re-answer.\n\n"
                + f"{tool_block}\n\n---\n\nUser query:\n{query}"
            )
        else:
            combined_input = query  # Fallback: nothing structured available

        # Step 6: Final GPT completion based on structured results and user query
        # Keep the last 3 back-and-forths (10 messages total)
        history_slice = st.session_state.messages[-6:]

        # Make a copy so we don't mutate the original session state
        history_for_model = [m.copy() for m in history_slice]

        # Ensure the most recent user turn has the combined_input
        if history_for_model and history_for_model[-1].get("role") == "user":
            history_for_model[-1] = {"role": "user", "content": combined_input}

        # Prepend the system instruction
        messages_payload = [{"role": "user", "content": system_instruction}] + history_for_model
        completion = client.chat.completions.create(
            model=gpt_deployment,
            messages=messages_payload,
            max_tokens=1000,
            temperature=0.5,
            top_p=0.85,
            frequency_penalty=0.1,
            presence_penalty=0,
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
            },
            
        )

        # ✅ Assign first before referencing
        final_response = completion.choices[0].message.content

        # ✅ Then safe to check
        if not final_response.strip() and structured_outputs:
            final_response = "Please see the results above for your requested analysis."

        # Step 7: Show final GPT result
        messages.append({"role": "assistant", "content": final_response})
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(final_response)

        # Step 8: Handle citations robustly
        response_data = completion.to_dict()
        message_data = response_data["choices"][0]["message"]
        ai_response = message_data["content"]

        # Try to get citations from both levels
        citations_raw = []
        if "context" in response_data and "citations" in response_data["context"]:
            citations_raw = response_data["context"]["citations"]
        elif "context" in message_data and "citations" in message_data["context"]:
            citations_raw = message_data["context"]["citations"]

        # Build citation map
        full_citation_map = {}
        for i, c in enumerate(citations_raw):
            doc_id = f"doc{i+1}"
            if isinstance(c, dict):
                title = (
                    c.get("title")
                    or (c.get("content", {}).get("title") if isinstance(c.get("content", {}), dict) else None)
                    or c.get("chunk_id")
                    or "Untitled"
                )
            else:
                title = str(c)
            full_citation_map[doc_id] = title

        # Detect cited doc IDs
        cited_doc_ids = [doc_id for doc_id in full_citation_map if f"[{doc_id}]" in ai_response]

        # Show citation map
        if cited_doc_ids:

            st.markdown("**Sources:**")
            for doc_id in cited_doc_ids:
                index = int(doc_id.replace("doc", ""))
                citation = citations_raw[index - 1] if index - 1 < len(citations_raw) else None

                if isinstance(citation, dict):
                    title = get_title_from_citation(citation)
                    text = citation.get("content", {}).get("text") if isinstance(citation.get("content", {}), dict) else citation.get("content", "")
                else:
                    title = str(citation)
                    text = str(citation)

                with st.expander(f"{doc_id} - {title}"):
                    st.markdown(text)

        

## UI Specs
# Clear session state
def clear_session(messages):
    st.cache_data.clear()
    messages.clear()
    return messages

# Main app entrypoint
def main():
    st.set_page_config(page_title="Rare Disease Chatbot", page_icon="🧬")

    # Load, encode, and center Axle logo image
    logo_path = os.path.join(os.path.dirname(__file__), "axle_logo.png")
    with open(logo_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode()
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src="data:image/png;base64,{base64_image}" width="180">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Display the title and introduction
    st.markdown(
        """
        <div style="text-align: center;">
            <h1>Rare Disease Chatbot</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("Hi there. I’m here to help you learn more about rare diseases. Please note I am not a doctor and cannot give medical advice. For your safety and privacy, please avoid sharing any personal health information.")


    # Initialize session state for messages if not already present
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Create a chat input box for user queries
    query = st.chat_input("Input query here...")

    # Define different roles and their avatars
    avatars = {
        "assistant": "🤖",
        "user": "🧑‍💻"
    }

    # Display past messages from the current session (useful after reload)
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