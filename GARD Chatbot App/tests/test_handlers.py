"""
Unit tests for GARD Chatbot handlers.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.symptom import handle_symptom_query
from handlers.orgs import handle_organization_query
from handlers.code_assistant import handle_code_query


class TestSymptomHandler:
    """Test cases for symptom query handler."""
    
    def test_handle_symptom_query_basic(self):
        """Test basic symptom query handling."""
        # Mock the required dependencies
        with patch('handlers.symptom.classify_query') as mock_classify, \
             patch('handlers.symptom.dispatch_tool') as mock_dispatch:
            
            # Setup mocks
            mock_classify.return_value = "symptom"
            mock_dispatch.return_value = {"response": "Test response"}
            
            # Test the function
            result = handle_symptom_query("What are the symptoms of Leigh syndrome?")
            
            # Assertions
            assert result is not None
            mock_classify.assert_called_once()
            mock_dispatch.assert_called_once()
    
    def test_handle_symptom_query_empty(self):
        """Test symptom query with empty input."""
        result = handle_symptom_query("")
        assert result is None or "error" in result.lower()


class TestOrganizationHandler:
    """Test cases for organization query handler."""
    
    def test_handle_organization_query_basic(self):
        """Test basic organization query handling."""
        with patch('handlers.orgs.classify_query') as mock_classify, \
             patch('handlers.orgs.dispatch_tool') as mock_dispatch:
            
            mock_classify.return_value = "organization"
            mock_dispatch.return_value = {"response": "Test response"}
            
            result = handle_organization_query("What organizations help with rare diseases?")
            
            assert result is not None
            mock_classify.assert_called_once()
            mock_dispatch.assert_called_once()


class TestCodeAssistantHandler:
    """Test cases for code assistant handler."""
    
    def test_handle_code_query_basic(self):
        """Test basic code query handling."""
        with patch('handlers.code_assistant.classify_query') as mock_classify, \
             patch('handlers.code_assistant.dispatch_tool') as mock_dispatch:
            
            mock_classify.return_value = "code"
            mock_dispatch.return_value = {"response": "Test code response"}
            
            result = handle_code_query("How do I implement a RAG system?")
            
            assert result is not None
            mock_classify.assert_called_once()
            mock_dispatch.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
