GARD Chatbot App – Project README
A Streamlit-based chatbot that helps patients and caregivers query structured rare disease symptom and organization data using OpenAI Assistants and Azure services.

🔹 Main Application File
gard_chatbot_app_V2-2.py
Main Streamlit app. Routes user input through classification, filter normalization, handler functions, and optional assistant calls for advanced output.

🔹 Handler Modules (handlers/)
symptom.py
Handles structured disease symptom lookups with filters like body system and frequency.

orgs.py
Finds relevant patient organizations based on disease name or category. Logs unmatched cases.

code_assistant.py
Generates plots or data comparisons using the OpenAI Code Interpreter Assistant and symptom data.

🔹 Service Modules (services/)
classify_query.py
Runs GPT-based classification of user input to extract intent, subject, and filters. Fills a prompt template with valid values before querying.

filtering.py
Normalizes filter values (e.g. synonyms, plural forms) and extracts likely disease name from filters or subject fallback.

🔹 Config & Shared Logic (config/)
shared_data.py
Central source for environment variables, prompt templates, canonical vocab, assistant IDs, and preloaded JSON data.

filter_vocab.py
Defines valid filter values (e.g. body systems, frequencies, disease categories) used in prompt injection.

azure_filter_schema.json
Reference-only JSON schema with expanded vocab and metadata. Not actively used in code.

🔹 Data Files (data/)
disease_symptom_map.json
Main structured dataset of diseases and their symptoms, including frequency, synonyms, and system tags.

organization_disease_map.json
Patient organization data mapped to disease names and categories.

🔹 Prompts (prompts/)
classification_prompt2.txt
Template prompt for GPT query classification. Placeholders are dynamically filled with canonical vocab.

system_instruction.txt
Defines global assistant behavior, safety rules, and tone for semantic questions.

code_interpreter_instruction.txt
Instruction prompt for the Code Interpreter Assistant when visualizing symptoms or comparing conditions.

🔹 Utilities (utils/)
symptom_utils.py
Helper functions like get_structured_symptoms() and build_symptom_synonym_map() used throughout the app and shared data logic.

🔹 Scripts & Tools (scripts/ or ad hoc)
upload_files_to_assistants.py
Standalone script to register JSON files with the Azure Assistant API.

assistant_id.py
Utility for manually retrieving assistant IDs from Azure OpenAI. Not used in app runtime.

🔹 Logs
logs/unmatched_patient_org_queries.log
Populated dynamically when the org handler fails to match a user query to any known orgs or categories.

🔹 Assets
axle_logo.png
Displayed in the UI header using base64 encoding.

🔹 Miscellaneous
requirements.txt
Defines all Python dependencies. Required for deployment or setup in any new environment.

__pycache__/ & *.pyc
Ignore or delete these compiled files. Python regenerates them automatically.
