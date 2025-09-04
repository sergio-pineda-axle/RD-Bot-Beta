import json
import os

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def build_html_from_json(data):
    html_content = f"""
    <html>
    <head>
        <title>{data.get('Name', 'Disease Page')}</title>
    </head>
    <body>
        <h1>{data.get('Name', 'Unknown Disease')}</h1>
        <h2>Banner: Nomenclature</h2>
        <p>Disease Name: {data.get('Name', 'Unknown Disease')}</p>
    """
    
    # Synonyms
    if "Synonyms_List__c" in data:
        html_content += "<h2>Other Names</h2><ul>"
        for synonym in data["Synonyms_List__c"]:
            html_content += f"<li>{synonym}</li>"
        html_content += "</ul>"
    
    # Summary
    if "Curated_Disease_Description__c" in data:
        html_content += f"<h2>Summary</h2><p>{data['Curated_Disease_Description__c']}</p>"
    
    # Hardcoded text from Markdown (static snippets)
    population_estimate = data.get("Curated_USA_Estimate__c", "50,000")
    html_content += f"""
        <h2>About Leigh Syndrome</h2>
        <p>Many rare diseases have limited information. Currently, GARD aims to provide the following information for this disease:</p>
        <ul>
            <li>Population Estimate: Fewer than {population_estimate} people in the U.S. have this disease.</li>
            <li>Symptoms: May start to appear at any time in life.</li>
            <li>Cause: This disease has more than one possible cause.</li>
            <li>Organizations: Patient organizations are available to help find a specialist, or advocacy and support for this specific disease.</li>
        </ul>
    """
    
    # Additional Sections from Markdown
    html_content += """
        <h2>Multidisciplinary Care Centers</h2>
        <p>Patients with rare diseases often benefit from care at multidisciplinary clinics that specialize in their condition. These centers bring together experts from multiple specialties to provide comprehensive care.</p>

        <h2>Rare Disease Experts</h2>
        <p>Consulting a medical expert with experience in treating this rare disease can provide valuable insights and treatment options.</p>

        <h2>Find Your Community</h2>
    """
    if "Organization_Supported_Diseases__c" in data:
        html_content += "<ul>"
        for org in data["Organization_Supported_Diseases__c"]:
            html_content += f"<li>{org['Organization_Name__c']}: {org.get('Organization_Description__c', 'No description available.')}</li>"
        html_content += "</ul>"
    
    html_content += """
        <h2>Participate in Research</h2>
        <p>Research studies and clinical trials are essential for advancing knowledge about rare diseases and developing new treatments.</p>

        <h2>Contact GARD</h2>
        <p>The Genetic and Rare Diseases (GARD) Information Center provides resources and information about rare diseases. Contact GARD for more details.</p>

        <h2>Sources & References</h2>
        <p>For additional details, refer to peer-reviewed medical literature and trusted sources such as the National Institutes of Health (NIH).</p>
    """
    
    html_content += "</body></html>"
    return html_content

def save_html(content, output_folder, filename):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    output_path = os.path.join(output_folder, filename)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)

def main():
    input_json_path = r"C:\\Users\\SergioPineda\\OneDrive - Axle\\Documents\\GARD Chatbot Research\\Data Preperation\\Input_json_files\\6877_Leigh-syndrome_Pretty.json"
    output_folder = r"C:\\Users\\SergioPineda\\OneDrive - Axle\\Documents\\GARD Chatbot Research\\Data Preperation\\Converted_files"
    
    data = load_json(input_json_path)
    html_content = build_html_from_json(data)
    save_html(html_content, output_folder, "6877_Leigh-syndrome.html")

main()