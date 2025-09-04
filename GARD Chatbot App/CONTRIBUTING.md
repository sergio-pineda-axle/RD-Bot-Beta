# Contributing to GARD Chatbot

Thank you for your interest in contributing to the GARD Chatbot project! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project follows a code of conduct that we expect all contributors to adhere to. By participating, you are expected to uphold this code.

### Our Pledge

- Be respectful and inclusive
- Focus on what is best for the community
- Show empathy towards other community members
- Accept constructive criticism gracefully
- Use welcoming and inclusive language

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** for your changes
4. **Make your changes** following our guidelines
5. **Test your changes** thoroughly
6. **Submit a pull request**

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Docker (optional, for containerized development)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/sergio-pineda-axle/RD-Bot-Beta.git
   cd RD-Bot-Beta/GARD\ Chatbot\ App
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   make install-dev
   # or
   pip install -r requirements.txt
   pip install pytest pytest-cov black flake8 mypy pre-commit
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   make run
   # or
   streamlit run gard_chatbot_app_V2-2.py
   ```

## Contributing Guidelines

### Types of Contributions

- **Bug fixes**: Fix issues in existing functionality
- **New features**: Add new capabilities to the chatbot
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Performance**: Optimize existing code
- **Security**: Address security concerns

### Before You Start

1. **Check existing issues** to see if your contribution is already being worked on
2. **Create an issue** for significant changes to discuss the approach
3. **Ensure you have the necessary permissions** for the changes you want to make

## Pull Request Process

### Creating a Pull Request

1. **Create a feature branch** from the latest main branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test your changes**
   ```bash
   make test
   make lint
   ```

4. **Commit your changes** with a clear commit message
   ```bash
   git commit -m "feat: add new symptom classification feature"
   ```

5. **Push your branch** and create a pull request

### Pull Request Guidelines

- **Use descriptive titles** that clearly explain what the PR does
- **Provide detailed descriptions** of changes and motivation
- **Reference related issues** using keywords like "Fixes #123"
- **Include screenshots** for UI changes
- **Ensure all tests pass** and code coverage is maintained
- **Request reviews** from appropriate team members

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(handlers): add new symptom classification logic
fix(services): resolve Azure Search connection timeout
docs(readme): update installation instructions
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Maximum line length: 88 characters
- Use type hints where appropriate

### Code Quality

- Write clean, readable, and maintainable code
- Use meaningful variable and function names
- Add docstrings for all public functions and classes
- Keep functions small and focused on a single responsibility
- Avoid code duplication

### Example Code Style

```python
def classify_symptom_query(query: str) -> Optional[str]:
    """
    Classify a symptom-related query.
    
    Args:
        query: The user's query string
        
    Returns:
        Classification result or None if unable to classify
        
    Raises:
        ValueError: If query is empty or invalid
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Implementation here
    return classification_result
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage
pytest --cov=. --cov-report=html
```

### Writing Tests

- Write tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Use fixtures for common test data

### Test Structure

```python
class TestSymptomHandler:
    """Test cases for symptom query handler."""
    
    def test_handle_symptom_query_success(self):
        """Test successful symptom query handling."""
        # Arrange
        query = "What are the symptoms of Leigh syndrome?"
        expected_result = "symptom"
        
        # Act
        result = handle_symptom_query(query)
        
        # Assert
        assert result == expected_result
```

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use clear, concise language
- Include parameter descriptions and return values
- Add examples for complex functions

### README Updates

- Update README.md for significant changes
- Include setup instructions for new features
- Update version numbers and dependencies
- Add troubleshooting sections when needed

## Medical Compliance

⚠️ **Important**: This is a medical application. All contributions must:

- Maintain medical accuracy and safety
- Include appropriate disclaimers
- Follow healthcare data privacy guidelines
- Not provide specific medical advice
- Direct users to consult healthcare professionals

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion
- **Email**: Contact the development team directly

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to GARD Chatbot! 🚀
