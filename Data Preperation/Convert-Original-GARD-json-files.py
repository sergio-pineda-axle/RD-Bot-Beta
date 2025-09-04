import os
import json

def process_and_convert_symptoms(input_json, output_json, output_md):
    """
    Processes the input JSON to apply reformatting logic to the output JSON
    and filters symptoms with "symptom type = symptom" for the Markdown file.

    Args:
        input_json (str): Path to the input JSON file.
        output_json (str): Path to the output reformatted JSON file.
        output_md (str): Path to the output Markdown file with filtered symptoms.
    """

    # Ensure output directories exist
    for path in [output_json, output_md]:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        # Load the input JSON data
        with open(input_json, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{input_json}' was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: The file '{input_json}' is not a valid JSON file.")
        return

    # Reformat the JSON data
    reformatted_data = {
        "Overview": {
            "Name": data.get("Name", "Not specified"),
            "Full Name": data.get("Disease_Name_Full__c", "Not specified"),
            "Synonyms": data.get("Synonyms_List__c", "Not specified"),
            "Description": data.get("Curated_Disease_Description__c", "Not specified"),
            "Type": data.get("Disease_Type__c", "Not specified"),
            "Estimates": {
                "USA": data.get("Curated_USA_Estimate__c", "Not specified"),
                "World": data.get("World_Estimate__c", "Not specified")
            }
        },
        "Causes": {
            "Description": data.get("Cause_Description__c", "Not specified"),
            "Inheritance Patterns": data.get("Inheritance__c", [])
        },
        "Symptoms": {
            "Symptom": [
                {
                    "Name": feature.get("Feature__r", {}).get("HPO_Name__c", "Not specified"),
                    "Synonyms": feature.get("Feature__r", {}).get("HPO_Synonym__c", "Not specified"),
                    "Description": feature.get("Feature__r", {}).get("HPO_Description__c", "Not specified"),
                    "Body System Category(-ies)": feature.get("Feature__r", {}).get("HPO_Category__c", "Not specified"),
                    "Frequency": feature.get("HPO_Frequency__c", "Not specified"),
                    "Symptom Type": feature.get("Feature__r", {}).get("HPO_Feature_Type__c", "Not specified")
                } for feature in data.get("GARD_Disease_Feature__c", [])
                if feature.get("Feature__r", {}).get("HPO_Feature_Type__c") == "Symptom"
            ],
            "Lab": [
                {
                    "Name": feature.get("Feature__r", {}).get("HPO_Name__c", "Not specified"),
                    "Synonyms": feature.get("Feature__r", {}).get("HPO_Synonym__c", "Not specified"),
                    "Description": feature.get("Feature__r", {}).get("HPO_Description__c", "Not specified"),
                    "Body System Category(-ies)": feature.get("Feature__r", {}).get("HPO_Category__c", "Not specified"),
                    "Frequency": feature.get("HPO_Frequency__c", "Not specified"),
                    "Symptom Type": feature.get("Feature__r", {}).get("HPO_Feature_Type__c", "Not specified")
                } for feature in data.get("GARD_Disease_Feature__c", [])
                if feature.get("Feature__r", {}).get("HPO_Feature_Type__c") == "Lab"
            ]
        },
        "Diagnosis and Testing": [
            {
                "Type": diag.get("Type__c", "Not specified"),
                "Details": diag.get("Curie__c", "Not specified")
            } for diag in data.get("Diagnosis__c", [])
        ],
        "Support Organizations": [
            {
                "Name": org.get("Account_Name__c", "Not specified"),
                "Website": org.get("Website__c", "Not specified")
            } for org in data.get("Organization_Supported_Diseases__c", [])
        ],
        "External Resources": [
            {
                "Source": ext.get("Source__c", "Not specified"),
                "URL": ext.get("URL__c", "Not specified")
            } for ext in data.get("External_Identifier_Disease__c", [])
        ],
        "_comments": {
            "Deprecated Fields": "Fields not displayed on the website have been preserved for reference.",
            "Source Fields": "All source fields were extracted from the original JSON."
        }
    }

    # Save the reformatted JSON data to output_json
    try:
        with open(output_json, 'w') as json_file:
            json.dump(reformatted_data, json_file, indent=4)
        print(f"Reformatted JSON file successfully created at: {output_json}")
    except PermissionError:
        print(f"Error: Permission denied when writing to '{output_json}'.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while writing JSON: {e}")
        return

    # Filter symptoms where "HPO_Feature_Type__c" = "Symptom"
    filtered_symptoms = [
        {
            "Name": feature.get("Feature__r", {}).get("HPO_Name__c", "Not specified"),
            "Synonyms": feature.get("Feature__r", {}).get("HPO_Synonym__c", "Not specified"),
            "Description": feature.get("Feature__r", {}).get("HPO_Description__c", "Not specified"),
            "Body System Category(-ies)": feature.get("Feature__r", {}).get("HPO_Category__c", "Not specified"),
            "Frequency": feature.get("HPO_Frequency__c", "Not specified")
        }
        for feature in data.get("GARD_Disease_Feature__c", [])
        if feature.get("Feature__r", {}).get("HPO_Feature_Type__c") == "Symptom"
    ]

    # Generate Markdown content for filtered symptoms
    markdown_content = "# Symptoms\n\n"
    markdown_content += (
        "The types of symptoms experienced, and their intensity, may vary among "
        "people with this disease. Your experience may be different from others. "
        "Consult your healthcare team for more information.\n\n"
        "The following describes the symptom(s) associated with this disease "
        "along with the corresponding body system(s), description, synonyms, and frequency:\n\n"
    )

    for symptom in filtered_symptoms:
        markdown_content += f"#### {symptom['Name']}\n"
        markdown_content += f"* Synonyms: {symptom.get('Synonyms', 'Not specified')}\n"
        markdown_content += f"* Description: {symptom.get('Description', 'Not specified')}\n"
        markdown_content += f"* Body System Category(-ies): {symptom.get('Body System Category(-ies)', 'Not specified')}\n"
        markdown_content += f"* Frequency: {symptom.get('Frequency', 'Not specified')}\n\n"

    try:
        with open(output_md, 'w') as md_file:
            md_file.write(markdown_content)
        print(f"Markdown file successfully created at: {output_md}")
    except PermissionError:
        print(f"Error: Permission denied when writing to '{output_md}'.")
    except Exception as e:
        print(f"An unexpected error occurred while writing Markdown: {e}")

# Example usage
input_json = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Input_json_files\6877_Leigh-syndrome.json"
output_json = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Converted_files\6877_Leigh-syndrome_reformatted.json"
output_md = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Chatbot_Input-Files\6877_Leigh-syndrome_symptoms.md"

process_and_convert_symptoms(input_json, output_json, output_md)