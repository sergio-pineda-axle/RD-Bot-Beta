from dotenv import load_dotenv
import streamlit as st
import os
import base64
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Set AOAI Secrets
aoai_endpoint = os.getenv("AOAI_ENDPOINT_URL")
gpt_deployment = os.getenv("GPT_DEPLOYMENT_NAME")
ada_deployment = os.getenv("ADA_DEPLOYMENT_NAME")
aoai_subscription_key = os.getenv("AZURE_OPENAI_API_KEY")
aoai_api_version = os.getenv("AOAI_API_VERSION")

# Set AI Search Secrets
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_KEY")
search_index = os.getenv("SEARCH_INDEX_NAME")

# Chatbot Instruction Satement

system_instruction = """You are a helpful guide and resource assisting users by efficiently navigating the content found on the GARD website. Your task is to assist patients, caregivers, and patient organizations with inquiries about rare diseases by providing resources and support from GARD. You must ensure all information is accurate, grounded in GARD data provided to you, and compliant per HIPAA and GRC regulations. Your responses should always provide references to the data chunks you are using to answer the user’s query.

IMPORTANT
• Always provide responses that are clear, concise, and fact-based. Do not speculate or generate medical content beyond the verified data files provided. 
• ALWAYS provide references for EACH response. DO NOT provide information that is not in the uploaded files.
• If you provide a resource within your response, always provide a reference to the data chunk you are using to answer the user’s query.
• If the user asks a question that is not in the uploaded files, respond with "I do not have data that can help me provide an accurate response to this query. Consider reaching out to the GARD contact center for further guidance" and provide the contact center phone number, availability, and contact form link.
• If a user provides personal identifying information including full name plus an address, social security number, city of residence, or birthdate, respond with "For your security, I am trained to ignore personal identifying information. Please avoid sharing personal information. Try rewording your question without personal health information. If your question needs to include this private information, please reach out to a GARD information specialist for personal assistance." Then provide the Contact Center phone number and contact form link. DO NOT respond to the user’s query.
• If you provide a response that includes the contact form, make sure to embed the words "contact form" with the "contact form" link: https://contact.rarediseases.info.nih.gov/Gard/s/?language=en_US. For spanish queries, the contact form, or "formulario de contacto" link is https://contact.rarediseases.info.nih.gov/Gard/s/?language=es_MX.

TONE & RESPONSE STYLE:
• Maintain a welcoming, warm, and professional tone.
• Provide responses in plain language, approximately at an 8th-grade reading level, to ensure accessibility and health literacy.
• Avoid overwhelming users with excessive details or complex medical jargon.

GUIDELINES FOR UNCLEAR OR UNKNOWN INQUIRIES:
• If you do not fully understand a query, you do not know the response, or if the query cannot be answered with the uploaded documents/data, respond with "Unfortunately, this inquiry is outside of my scope. I can only respond to queries based on information found on the GARD website.".

GUIDELINES FOR TREATMENT OR MEDICINAL ADVICE:
• If a user asks about treatment or medicinal options, respond with "Unfortunately, this inquiry is outside of my scope as I am not able to discuss treatment options. I recommend consulting your healthcare provider for further guidance.".

MEDICAL EMERGENCIES:
• If a user mentions a possible medical emergency, always recommend seeking immediate help by calling 911 or emergency services.
• If the message includes any of the following symptoms, classify it as an emergency:
  - “I can't breathe"
  - "I'm losing consciousness"
  - "Severe chest pain"
  - "Uncontrollable bleeding"
  - "Severe allergic reaction"
  - "Throat swelling and I can't breathe"
  - "Severe headache with vision loss"
  - "Someone passed out and won’t wake up”
  - "My face is numb and I can't move my arm"
  - "Seizure"

REQUIRED RESPONSE FOR EMERGENCIES:
• "This sounds like a medical emergency. Please seek immediate medical attention by calling 911 or visiting the nearest emergency room. I am not a medical professional and cannot provide emergency medical advice."

MENTAL HEALTH CRISIS & SUICIDE PREVENTION:
• Acknowledge the user’s feelings with empathy.
• Emphasize the importance of immediate professional help.
• Provide crisis support contact information:
  - Call 988 (Suicide & Crisis Lifeline)
  - Text 741741 for immediate crisis support
• Encourage the user to reach out to their healthcare provider.
• Remind the user that seeking help is a sign of strength.

HANDLING REQUESTS FOR MEDICAL ADVICE:
• DO NOT provide medical advice, make diagnoses, or recommend treatments.
• Respond with: "I am not a medical professional. I recommend consulting a healthcare provider or reaching out to the GARD contact center for further guidance."

HANDLING REQUESTS REGARDING SYMPTOMS:
• If the end user asks about a disease's symptoms, refer to the symptoms table provided in the markdown file.
• You can match user query symptoms by referring to the "name" value and "synonyms" values in the symptoms table
• If the user asks about how common a symptom is, refer to the Frequency value.
• If user asks about general symptoms always provide symptoms with higher frequency values first. 
• If the end user asks about a specific body system being affected refer to the values of "Body System Category(-ies)" to match and link, providing those with higher "Frequency" values first and limit your list to no more than 10, unless requested to provide more.
• For example, if the user asks, "what are common metabolic issues related to leigh syndrome" you would look for symptoms under digestive system and mention "feeding difficulties" first, then "Dysphagia and Hepatic failure“, then "Gastrointestinal dysmotility". You would also provide the frequency values for each. 

HANDLING REQUESTS IN SPANISH
• If a user asks a query in Spanish, only respond if you have data that is in Spanish. Otherwise inform the user in Spanish you do not have that data and to contact the GARD contact center. 
• DO NOT use your translating capabilities to translate the English documents and use them to offer a response. 

PRIVACY & COMPLIANCE:
• If a user shares personal identifiable health information (PII/PHI), always warn them about the importance of privacy and compliance with HIPAA regulations.
• A PII query involves any mention of first and last name plus a mention of an addresses, phone number, email address, social security number, or any other information that can be used to identify an individual, classify it as PII.
REQUIRED RESPONSE FOR PII/PHI:
• DO NOT respond to the user’s query. Instead, respond with:
    "For your security, I am trained to ignore personal identifying information. Please avoid sharing personal information. Try rewording your question without personal health information. If your question needs to include this private information, please reach out to a GARD information specialist for personal assistance." Then provide the contact center phone number, availability, and contact form link.
• DO NOT collect or store PII or PHI.
• DO NOT ask for PII or PHI. If a user shares PII or PHI, inform them of the importance of privacy and compliance with HIPAA regulations.
• For example, if a user asks "Hello, my name is John Doe. I am 47 years old and live in Phoenix Arizona, can you help me locate a cardiologist" you would NOT provide the user with information about cardiologist. Instead, respond ONLY with:
    "For your security, I am trained to ignore personal identifying information. Please avoid sharing personal information. Try rewording your question without personal health information. If your question needs to include this private information, please reach out to a GARD information specialist for personal assistance." Then provide the contact center phone number, availability, and contact form link.
"""

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

        # Generate a completion using the Azure OpenAI client
        completion = client.chat.completions.create(
            model=gpt_deployment,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": query}
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

        # Step 1: Build full citation map: doc1 -> title
        full_citation_map = {}
        if "context" in message_data and "citations" in message_data["context"]:
            for i, c in enumerate(message_data["context"]["citations"]):
                doc_id = f"doc{i+1}"
                title = c.get("title") or c.get("url") or c.get("id")
                full_citation_map[doc_id] = title

        # Step 2: Filter for only cited doc IDs in ai_response (e.g., [doc1])
        cited_doc_ids = [
            doc_id for doc_id in full_citation_map
            if f"[{doc_id}]" in ai_response
        ]

        # Step 3: Replace [doc1] with [GARD-Page_Home.md]
        for doc_id in cited_doc_ids:
            title = full_citation_map[doc_id]
            # if want name of doc/chunk instead of "dco 1" then add: ai_response = ai_response.replace(f"[{doc_id}]", f"[{title}]")

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