import json
import time
import re

import os
import streamlit as st


from openai import AzureOpenAI
from config.shared_data import (
    DEBUG_MODE,
    aoai_endpoint,
    aoai_subscription_key,
    assistant_id,
    assistant_api_version,
    code_interpreter_prompt,
    disease_synonym_map,
    disease_symptom_map,
    org_disease_map
)



# Utility function
def strip_code_blocks(text):
    return re.sub(r"```(?:python)?\s*.*?```", "", text, flags=re.DOTALL).strip()

# Function: Extract chart metadata with assistant
def extract_chart_metadata(response_text):
    import re
    title = re.search(r"plt\.title\(['\"](.+?)['\"]\)", response_text)
    x_label = re.search(r"plt\.xlabel\(['\"](.+?)['\"]\)", response_text)
    y_label = re.search(r"plt\.ylabel\(['\"](.+?)['\"]\)", response_text)
    
    title_text = title.group(1) if title else "a chart"
    x_text = x_label.group(1) if x_label else "X-axis"
    y_text = y_label.group(1) if y_label else "Y-axis"
    
    return (
        f"The chart titled '{title_text}' shows how {y_text.lower()} are distributed across {x_text.lower()} categories. "
    )

# Function: Filter (preprocess) data for assistant 
def preprocess_for_assistant(subjects, body_system_filters=None, freq_filters=None, plan=None):
    """
    Extracts only the GPT-planned fields from disease_symptom_map or org_disease_map.
    No filtering or enrichment is done here — just raw extraction of selected fields.
    """
    if not isinstance(subjects, list):
        subjects = [subjects]

    results = {}

    print("[preprocess_for_assistant] Plan received:", plan)

    for name in subjects:
        name_lower = name.lower().strip()
        canonical_name = disease_synonym_map.get(name_lower, name_lower)

        # Disease-based extraction
        if canonical_name in disease_symptom_map:
            symptoms = disease_symptom_map[canonical_name].get("symptoms", [])
            requested_fields = plan.get("disease", []) if plan else []

            # Build field subsets
            result = {}
            if "symptom_name" in requested_fields:
                result["symptom_names"] = [s["symptom_name"] for s in symptoms]
            if "symptom_synonyms" in requested_fields:
                result["symptom_synonyms"] = [s.get("symptom_synonyms", []) for s in symptoms]
            if "frequency" in requested_fields:
                result["frequencies"] = [s.get("frequency") for s in symptoms]
            if "frequency_rank" in requested_fields:
                result["frequency_ranks"] = [s.get("frequency_rank") for s in symptoms]
            if "body_systems" in requested_fields:
                result["body_systems"] = [s.get("body_systems", []) for s in symptoms]

            result["symptom_count"] = len(symptoms)
            results[name] = result

            print(f"[preprocess_for_assistant] Extracting for: {canonical_name}")
            print(f"[preprocess_for_assistant] Available symptoms: {len(symptoms)}")
            print(f"[preprocess_for_assistant] Requested fields: {requested_fields}")

        # Organization-based extraction
        elif canonical_name in org_disease_map:
            org_entry = org_disease_map[canonical_name]
            requested_fields = plan.get("organization", []) if plan else []

            result = {}
            for field in requested_fields:
                if field in org_entry:
                    result[field] = org_entry[field]
            results[name] = result


    return results

# Funciton: Handle Queries Using Code Interpreter Assistant
# This function takes a user query, classifies it to extract disease/body system, fetches related symptom data, and asks an OpenAI Assistant to write and run Python code to generate a chart using that data.
def call_code_interpreter_assistant(intent, filters, subject, structured_data, query=""):
    """
    Sends structured data and query to assistant to generate a chart or summary.
    Assumes structured_data has already been prepared using plan + preprocessing.
    """

    image_data = None  # Placeholder for image data if needed

    client = AzureOpenAI(
        azure_endpoint=aoai_endpoint,
        api_key=aoai_subscription_key,
        api_version=assistant_api_version
    )

    inline_data = json.dumps(structured_data, indent=2)

    filters_text = "\n".join(
        f"- {f['field']} = \"{f['value']}\"" for f in filters
    )

    user_intent = f"The user asked: \"{query.strip()}\"\n\n" if query else ""

    query_with_data = f"""
    Instructions:
    {code_interpreter_prompt}

    Here was the user's query:
    {user_intent}

    Here is structured data relevant to the query:
    ```json
    {inline_data}
    ```

    Please answer this question by applying the following structured filters before analyzing the data:
    {filters_text or "None"}
    """

    print("\n--- Prompt sent to Assistant ---\n", query_with_data)

    # Start a thread and send the message
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query_with_data
    )

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    # Wait for completion
    status_text = st.empty()
    while run.status in ["queued", "in_progress"]:
        status_text.markdown(f"⏳ Assistant status: **{run.status}**...")
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    status_text.markdown(f"✅ Assistant status: **{run.status}**")

    if run.status != "completed":
        return {
            "display": f"Assistant returned no usable output. Status: {run.status}",
            "summary": "",
            "cleaned": ""
        }

    # Process assistant response
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    content_blocks = messages.data[0].content
    results = []
    final_image_data = None

    for block in content_blocks:
        if hasattr(block, "text"):
            code_text = block.text.value
            match = re.search(r"```(?:python)?\s*(.*?)```", code_text, re.DOTALL)
            
            if match:
                python_code = match.group(1).strip()
                chart_summary = extract_chart_metadata(python_code)
                results.append(f"📊 {chart_summary}")

                # ✅ Passive safety check — even if not executing
                if any(s in python_code for s in ["os.", "open(", "/mnt/data", "subprocess", "shutil", "socket", "requests"]):
                    results.append("🚫 Assistant code contains disallowed operations (filesystem/network). Skipped.")
                    return {
                        "display": "\n".join(results),
                        "summary": chart_summary,
                        "cleaned": strip_code_blocks(python_code),
                        "image_data": None
                    }
                # Execution is disabled
                results.append("ℹ️ Assistant returned code, but image was expected — skipping local execution.")

            else:
                results.append("⚠️ No executable code block returned.")
                if "import matplotlib" not in code_text.lower():
                    results.append(code_text)

        elif hasattr(block, "image_file"):
            image_id = block.image_file.file_id
            image_response = client.files.content(image_id) # Use AzureOpenAI client to fetch the image content
            final_image_data = image_response.read()
            results.append("🖼️ Image output rendered above.")

        else:
            results.append("⚠️ Unknown content type.")

    return {
        "display": "\n\n".join(results),
        "summary": extract_chart_metadata("\n".join(results)),
        "cleaned": strip_code_blocks("\n".join(results)),
        "image_data": final_image_data
    }



                # Removed this from code as assistant code tends to just produce an image and unlikely raw python will ever be needed
                # This used to belong after the `if match:` block
                #try:
                #import matplotlib.pyplot as plt
                #import contextlib
                #import io
                    # with contextlib.redirect_stdout(io.StringIO()) as f:
                    #    local_vars = {"plt": plt}
                    #    # This is a security measure to prevent code execution that could access the filesystem or network

                    #    if any(s in python_code for s in ["os.", "open(", "/mnt/data"]):
                    #        st.error("⚠️ Unsafe assistant code blocked.")
                    #        st.code(python_code)
                    #        results.append("Blocked potentially unsafe code execution.")


                        # else:
                        #    exec(python_code, local_vars)
                        #python_code = re.sub(r"plt\.xticks\([^)]+\)", "", python_code)
                        #if "plt" in local_vars:
                        #    fig = local_vars["plt"].gcf()
                        #    if fig.get_axes():
                        #        buf = io.BytesIO()
                        #        fig.savefig(buf, format="png", bbox_inches="tight")
                        #        buf.seek(0)
                        #        final_image_data = buf.read()  # <== Save for return
                        #        st.image(buf, caption="Chart (assistant-rendered)")
                        #        results.append("🖼️ Plot rendered above.")
                        #    else:
                        #        results.append("⚠️ Plot was generated but had no visible axes.")
                        
                        #else:
                        #    results.append("⚠️ Plot was not generated.")

                #except Exception as e:
                #    st.error("❌ Exception during code execution")
                #    st.code(python_code)
                #    st.exception(e)
                #    results.append("⚠️ Chart execution failed.")
                #    results.append("Assistant code:\n" + python_code)
            