import json
import os

# Function to convert JSON to Markdown
def convert_json_to_markdown(input_file, output_file):
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    # Load the JSON data
    try:
        with open(input_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: The file '{input_file}' is not a valid JSON file.")
        return

    # Start creating the Markdown content
    markdown_content = "# Symptoms\n\n"
    markdown_content += (
        "The types of symptoms experienced, and their intensity, may vary among "
        "people with this disease. Your experience may be different from others. "
        "Consult your healthcare team for more information.\n\n"
        "The following describes the symptom(s) associated with this disease "
        "along with the corresponding body system(s), description, synonyms, and frequency:\n\n"
    )

    for symptom in data.get("Symptoms", []):
        markdown_content += f"#### {symptom['Name']}\n"
        markdown_content += f"* Synonyms: {symptom.get('Synonyms', 'Not specified')}\n"
        markdown_content += f"* Description: {symptom.get('Description', 'Not specified')}\n"
        markdown_content += f"* Body System Category(-ies): {symptom.get('Body System Category(-ies)', 'Not specified')}\n"
        markdown_content += f"* Frequency: {symptom.get('Frequency', 'Not specified')}\n\n"

    # Write the Markdown content to the output file
    try:
        with open(output_file, 'w') as output:
            output.write(markdown_content)
        print(f"Markdown file successfully created at: {output_file}")
    except PermissionError:
        print(f"Error: Permission denied when writing to '{output_file}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# File paths
input_json = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Input_json_files\Symptoms_6877_Leigh-syndrome.json"
output_md = r"C:\Users\SergioPineda\OneDrive - Axle\Documents\GARD Chatbot Research\Data Preperation\Output_json_files\Symptoms_6877_Leigh-syndrome.md"

# Convert JSON to Markdown
convert_json_to_markdown(input_json, output_md)