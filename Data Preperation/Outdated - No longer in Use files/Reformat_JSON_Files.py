import os
import json

def reformat_json(input_folder, output_folder):
    """
    Reformats JSON files in the input folder to make them LLM-friendly and saves them to the output folder.
    """

    # Iterate through all JSON files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.json'):
            input_path = os.path.join(input_folder, filename)
            output_filename = f"{os.path.splitext(filename)[0]}_reformatted.json"
            output_path = os.path.join(output_folder, output_filename)

            # Load the JSON data
            with open(input_path, 'r') as file:
                data = json.load(file)

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

            # Save the reformatted JSON data
            with open(output_path, 'w') as outfile:
                json.dump(reformatted_data, outfile, indent=4)

# Paths to input and output folders *WILL NEED TO BE CHANGED TO NEW LOCATION*
input_folder = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Input_json_files"
output_folder = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Output_json_files"


# Execute the reformatting function
try:
    reformat_json(input_folder, output_folder)
except FileNotFoundError as e:
    print(e)