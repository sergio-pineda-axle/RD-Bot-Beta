import re
from config.shared_data import disease_symptom_map, disease_synonym_map, org_disease_map

def plan_data_extraction(client, deployment, query, subject_type, available_fields):
    """
    This function uses GPT to plan which structured fields should be extracted
    for a given subject type (disease or organization) based on the user query.

    It does NOT extract or filter data — just selects which fields are relevant.
    """

    # Prepare a comma-separated list of field names for this subject type
    print("[plan_data_extraction] Available fields passed in:")
    print(available_fields)
    field_options = available_fields.get(subject_type, [])
    field_list = ", ".join(field_options)

    prompt = f"""
    You are a planning module for a rare disease assistant.

    Given a user question and a subject type ({subject_type}), choose which fields are needed to answer the question using structured data.

    Respond only with a JSON list of the most relevant fields.

    The subject type is: {subject_type}

    The available fields are:
    {field_list}

    The user question is:
    {query}
    """

    # Ask GPT to select relevant fields
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a planning module for field extraction."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=200
    )

    print("[plan_data_extraction] Prompt sent:")
    print(prompt)

    print("[plan_data_extraction] Raw GPT response:")
    print(response.choices[0].message.content.strip())

    try:
        extracted = response.choices[0].message.content.strip()

        # Remove any enclosing markdown code block
        match = re.search(r"```(?:json)?\s*(.*?)```", extracted, re.DOTALL)
        if match:
            extracted_clean = match.group(1).strip()
        else:
            extracted_clean = extracted.strip()

        selected_fields = eval(extracted_clean) if extracted_clean.startswith("[") else []
        print(f"[plan_data_extraction] Parsed selected_fields = {selected_fields}")
    except Exception as e:
        print("[plan_data_extraction] Parsing error:", e)
        selected_fields = []

    return {subject_type: selected_fields}
