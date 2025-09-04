# Changelog

All notable changes to the GARD Chatbot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-01-27

### Added
- Initial release of GARD Chatbot v2.2
- Hybrid RAG implementation for medical information retrieval
- Support for 5 GARD disease pages
- Streamlit web interface
- Multi-version data processing pipeline (V1.3 → V2.2)
- Comprehensive data enrichment with embeddings
- Modular architecture with handlers, services, and utilities
- Azure OpenAI and Azure Search integration
- Medical compliance and safety disclaimers
- Docker containerization support
- CI/CD pipeline with GitHub Actions
- Comprehensive testing framework
- Code quality tools (Black, Flake8, MyPy)
- Documentation and setup guides

### Features
- **Symptom Query Handler**: Process symptom-related medical queries
- **Organization Query Handler**: Handle organization and resource queries
- **Code Assistant Handler**: Provide code-related assistance
- **Data Processing Pipeline**: Convert and enrich GARD JSON data
- **Vector Search**: Semantic search capabilities for medical information
- **Multi-language Support**: English and Spanish language support
- **Version Management**: Multiple data versions for testing and comparison

### Technical Details
- Python 3.8+ support
- Streamlit 1.45.0
- LangChain integration
- Azure OpenAI GPT and Ada models
- Azure Cognitive Search
- Comprehensive logging and error handling
- Environment-based configuration
- Docker and Docker Compose support

### Security
- Medical disclaimer and compliance measures
- Environment variable configuration
- Input validation and sanitization
- Rate limiting capabilities
- Secure API key management

## [Unreleased]

### Planned
- Additional disease support
- Enhanced UI/UX improvements
- Performance optimizations
- Extended testing coverage
- API documentation
- Monitoring and analytics
