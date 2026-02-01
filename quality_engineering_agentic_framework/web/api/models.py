"""
API Models for Quality Engineering Agentic Framework

This module defines the data models for API requests and responses.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class LLMConfig(BaseModel):
    """LLM configuration model."""
    provider: str = Field(..., description="LLM provider (openai or gemini)")
    model: str = Field(..., description="Model name")
    api_key: str = Field(..., description="API key")
    temperature: float = Field(0.2, description="Temperature parameter")
    max_tokens: int = Field(2000, description="Maximum tokens")


class AgentConfig(BaseModel):
    """Agent configuration model."""
    prompt_template: Optional[str] = Field(None, description="Prompt template content")
    output_format: Optional[str] = Field(None, description="Output format")
    language: Optional[str] = Field("python", description="Programming language (e.g., python, java, javascript, c#)")
    framework: Optional[str] = Field("pytest", description="Test framework (e.g., pytest, junit, testng, cucumber)")
    browser: Optional[str] = Field("chrome", description="Browser for UI tests (e.g., chrome, firefox, edge)")
    data_variations: Optional[int] = Field(None, description="Number of data variations (for test data generator)")
    include_edge_cases: Optional[bool] = Field(None, description="Include edge cases (for test data generator)")


class TestCase(BaseModel):
    """Test case model."""
    title: str
    description: Optional[str] = None
    preconditions: List[str]
    actions: List[str]
    expected_results: List[str]
    test_data: Optional[Dict[str, Any]] = None


class TestCaseGenerationRequest(BaseModel):
    """Request model for test case generation."""
    requirements: str = Field(..., description="Requirements text")
    llm_config: LLMConfig
    agent_config: Optional[AgentConfig] = None
    selected_documents: Optional[List[str]] = Field(None, description="List of specific filenames to use for RAG")


class TestCaseGenerationResponse(BaseModel):
    """Response model for test case generation."""
    test_cases: List[TestCase]
    product_context: Optional[str] = Field(None, description="Synthesized product context from RAG")


class APITestCaseGenerationRequest(BaseModel):
    """
    Request model for API test case generation.
    """
    api_details: Dict[str, Any] = Field(..., description="API details for test case generation (base_url, endpoint, method, headers, params, body, auth, etc.)")
    llm_config: LLMConfig


class APITestCaseGenerationResponse(BaseModel):
    """
    Response model for API test case generation.
    """
    test_cases: List[Dict[str, Any]]


class TestScriptGenerationRequest(BaseModel):
    """Request model for test script generation."""
    test_cases: List[TestCase] = Field(..., description="Test cases")
    llm_config: LLMConfig
    agent_config: Optional[AgentConfig] = None


class TestScriptGenerationResponse(BaseModel):
    """Response model for test script generation."""
    test_scripts: Dict[str, str] = Field(..., description="Dictionary mapping file names to file contents")


class TestDataGenerationRequest(BaseModel):
    """Request model for test data generation."""
    input_data: Union[List[TestCase], Dict[str, str]] = Field(..., description="Test cases or test scripts")
    llm_config: LLMConfig
    agent_config: Optional[AgentConfig] = None


class TestDataGenerationResponse(BaseModel):
    """Response model for test data generation."""
    test_data: Dict[str, Any] = Field(..., description="Generated test data")


class PromptTemplate(BaseModel):
    """Prompt template model."""
    name: str = Field(..., description="Template name")
    content: str = Field(..., description="Template content")


class PromptTemplateListResponse(BaseModel):
    """Response model for prompt template list."""
    templates: List[PromptTemplate]


# Chat models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role (user, assistant, or system)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ["user", "assistant", "system"]:
            raise ValueError('role must be "user", "assistant", or "system"')
        return v


class ChatRequest(BaseModel):
    """Request model for chat."""
    messages: List[ChatMessage] = Field(..., description="Chat history")
    llm_config: LLMConfig
    agent_type: str = Field(..., description="Type of agent to chat with (test_case, test_script, test_data)")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    selected_documents: Optional[List[str]] = Field(None, description="List of specific filenames to use for RAG")


class ChatArtifact(BaseModel):
    """Base model for chat artifacts."""
    type: str = Field(..., description="Type of artifact")


class TestCaseArtifact(ChatArtifact):
    """Test case artifact model."""
    type: str = "test_cases"
    test_cases: List[TestCase]
    product_context: Optional[str] = Field(None, description="Synthesized product context from RAG")


class TestScriptArtifact(ChatArtifact):
    """Test script artifact model."""
    type: str = "test_scripts"
    test_scripts: Dict[str, str]


class TestDataArtifact(ChatArtifact):
    """Test data artifact model."""
    type: str = "test_data"
    test_data: Dict[str, Any]


class ChatResponse(BaseModel):
    """Response model for chat."""
    message: ChatMessage
    artifacts: Optional[Union[TestCaseArtifact, TestScriptArtifact, TestDataArtifact]] = Field(None, description="Generated artifacts if any")