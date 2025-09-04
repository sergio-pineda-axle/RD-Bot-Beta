# GARD Chatbot Research

This repository contains all script files related to the rare disease bot developed as an internal R&D project to test a hybrid RAG (Retrieval-Augmented Generation) bot on 5 disease pages from GARD (Genetic and Rare Diseases Information Center).

## Project Overview

The GARD Chatbot is an AI-powered medical information assistant designed to provide accurate and reliable information about rare diseases. This project focuses on testing and developing a hybrid RAG approach using data from GARD's disease pages.

### Key Features

- **Hybrid RAG Implementation**: Combines retrieval and generation techniques for accurate medical information
- **Multi-Disease Support**: Currently supports 5 disease pages from GARD
- **Streamlit Interface**: User-friendly web application for interaction
- **Data Processing Pipeline**: Automated conversion and enrichment of GARD data
- **Vector Search**: Semantic search capabilities for relevant information retrieval

## Repository Structure

```
├── Data Preparation/
│   ├── Chatbot_Input_Files/          # Processed GARD data in various formats
│   │   ├── V1.3/                     # Initial data versions
│   │   ├── V1.4/                     # Enhanced data with symptoms
│   │   ├── V1.5/                     # Multi-language support
│   │   ├── V2.0/                     # Enriched data with embeddings
│   │   └── V2.2/                     # Latest data version
│   ├── Convert-Original-GARD-json-files.py
│   ├── json_to_html.py
│   └── new_json_to_html.py
│
├── GARD Chatbot App/
│   ├── gard_chatbot_app_V2-2.py      # Main Streamlit application
│   ├── handlers/                      # Request handlers
│   │   ├── code_assistant.py
│   │   ├── orgs.py
│   │   └── symptom.py
│   ├── services/                      # Core services
│   │   ├── classify_query.py
│   │   └── plan_data_extraction.py
│   ├── utils/                         # Utility functions
│   ├── config/                        # Configuration files
│   ├── prompts/                       # AI prompts and instructions
│   └── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sergio-pineda-axle/RD-Bot-Beta.git
   cd RD-Bot-Beta
   ```

2. **Install dependencies**
   ```bash
   cd "GARD Chatbot App"
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Create a `.env` file in the `GARD Chatbot App` directory
   - Add your API keys and configuration settings

### Running the Application

1. **Navigate to the app directory**
   ```bash
   cd "GARD Chatbot App"
   ```

2. **Run the Streamlit app**
   ```bash
   streamlit run gard_chatbot_app_V2-2.py
   ```

3. **Access the application**
   - Open your browser and go to `http://localhost:8501`

## Data Processing

The project includes comprehensive data processing scripts to convert and enrich GARD data:

- **JSON Conversion**: Convert original GARD JSON files to structured formats
- **Data Enrichment**: Add embeddings and metadata to improve search capabilities
- **Version Management**: Multiple data versions for testing and comparison

### Key Data Files

- **Disease Data**: Processed information for 5 GARD diseases
- **Symptom Definitions**: Comprehensive symptom definitions and mappings
- **Body System Definitions**: Medical body system classifications
- **Specialist Definitions**: Healthcare specialist type definitions

## Configuration

The application uses environment variables for configuration. Key settings include:

- API keys for AI services
- Database connections
- File paths for data sources
- Model parameters

## Development

### Project Structure

- **Handlers**: Process different types of user queries
- **Services**: Core business logic and AI integration
- **Utils**: Helper functions and utilities
- **Config**: Shared configuration and data

### Adding New Diseases

1. Add disease data to the appropriate version folder in `Data Preparation/Chatbot_Input_Files/`
2. Update the data processing scripts if needed
3. Re-run the vectorization process
4. Update the application configuration

## Important Notes

⚠️ **Medical Disclaimer**: This chatbot is designed for research and development purposes only. It should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals for medical concerns.

## Contributing

This is an internal R&D project. For questions or contributions, please contact the development team.

## License

This project is proprietary and confidential. All rights reserved.

## Contact

For questions about this project, please contact the development team at Axle Information Systems.

---

**Note**: This repository contains only the core project files. Background materials, meeting notes, and documentation are maintained separately.
