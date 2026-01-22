"""
API Endpoints for Quality Engineering Agentic Framework

This module provides FastAPI endpoints for the framework.
"""

import os
import json
import tempfile
import uuid
from typing import Dict, List, Optional, Any, Union
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
import asyncio
import subprocess
import sys

from quality_engineering_agentic_framework.web.api.models import (
    LLMConfig, AgentConfig, TestCase, 
    TestCaseGenerationRequest, TestCaseGenerationResponse,
    TestScriptGenerationRequest, TestScriptGenerationResponse,
    TestDataGenerationRequest, TestDataGenerationResponse,
    PromptTemplate, PromptTemplateListResponse,
    ChatMessage, ChatRequest, ChatResponse,
    TestCaseArtifact, TestScriptArtifact, TestDataArtifact
)
from quality_engineering_agentic_framework.llm.llm_factory import LLMFactory
from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
from quality_engineering_agentic_framework.agents.test_script_generator import TestScriptGenerator
from quality_engineering_agentic_framework.agents.test_data_generator import TestDataGenerator
from quality_engineering_agentic_framework.agents.api_test_case_creation import APITestCaseCreationAgent
from quality_engineering_agentic_framework.web.api.models import APITestCaseGenerationRequest, APITestCaseGenerationResponse
from quality_engineering_agentic_framework.utils.logger import get_logger, setup_logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Quality Engineering Agentic Framework API",
    description="API for Quality Engineering Agentic Framework",
    version="0.2.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range"],
)

# Store active agent sessions
agent_sessions = {}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Quality Engineering Agentic Framework API", "version": "0.2.0"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An error occurred: {str(exc)}"},
    )


@app.post("/api/test-case-generation")
async def generate_test_cases(request: TestCaseGenerationRequest):
    """Generate test cases from requirements."""
    print("\n\n!!! RECEIVED REQUEST AT /api/test-case-generation !!!\n\n")
    logger.info("=== Received test case generation request ===")
    logger.info(f"Requirements: {request.requirements[:100]}...")
    
    try:
        # Create LLM
        llm_config = request.llm_config.model_dump()
        logger.info(f"Creating LLM with config: {llm_config}")
        llm = LLMFactory.create_llm(llm_config)
        
        # Create agent
        agent_config = {}
        logger.info("Creating TestCaseGenerationAgent")
        agent = TestCaseGenerationAgent(llm, agent_config)
        
        # Process requirements
        logger.info("Processing requirements...")
        result = await agent.process(request.requirements)
        
        # Extract test cases and product context
        if isinstance(result, dict):
            test_cases = result.get("test_cases", [])
            product_context = result.get("product_context", "")
        else:
            test_cases = result
            product_context = ""
            
        # Ensure we have a list for test cases
        if not isinstance(test_cases, list):
            logger.warning(f"Test cases is not a list, got: {type(test_cases)}")
            test_cases = [test_cases] if test_cases else []
        
        logger.info(f"Generated {len(test_cases)} test cases")
        
        # Return the response
        response = {
            "test_cases": test_cases,
            "product_context": product_context
        }
        logger.info("Sending response...")
        return response
        
    except Exception as e:
        logger.error(f"Error in generate_test_cases: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )


@app.post("/api/test-script-generation", response_model=TestScriptGenerationResponse)
async def generate_test_scripts(request: TestScriptGenerationRequest):
    logger.info("Received test script generation request")
    try:
        # Convert Pydantic models to dictionaries for logging
        request_dict = request.model_dump()
        if 'llm_config' in request_dict and 'api_key' in request_dict['llm_config']:
            request_dict['llm_config']['api_key'] = '***'
        logger.info(f"Request data: {request_dict}")
        
        # Create LLM
        llm_config = request.llm_config.model_dump()
        llm = LLMFactory.create_llm(llm_config)
        
        # Initialize agent
        agent_config = request.agent_config.dict() if request.agent_config else {}
        agent = TestScriptGenerator(llm, agent_config)
        
        # Convert test cases to dictionaries for processing
        test_cases_dicts = [tc.model_dump() for tc in request.test_cases]
        
        # Process test cases
        test_scripts = await agent.process(test_cases_dicts)
        
        return TestScriptGenerationResponse(test_scripts=test_scripts)
    
    except Exception as e:
        logger.error(f"Error generating test scripts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-data-generation", response_model=TestDataGenerationResponse)
async def generate_test_data(request: TestDataGenerationRequest):
    """Generate test data from test cases or test scripts."""
    try:
        # Create LLM
        llm_config = request.llm_config.model_dump()
        llm = LLMFactory.create_llm(llm_config)
        
        # Create agent config
        agent_config = request.agent_config.model_dump() if request.agent_config else {}
        
        # Create agent
        agent = TestDataGenerator(llm, agent_config)
        
        # Process input data
        test_data = await agent.process(request.input_data)
        
        return TestDataGenerationResponse(test_data=test_data)
    
    except Exception as e:
        logger.error(f"Error generating test data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-data-export")
async def export_test_data(
    test_data: Dict[str, Any],
    output_format: str = Form(...),
    output_dir: str = Form(None)
):
    """Export test data to files."""
    try:
        # Create a temporary directory if output_dir is not provided
        if not output_dir:
            output_dir = tempfile.mkdtemp()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Create agent
        agent = TestDataGenerator(None, {"output_format": output_format})
        
        # Export test data
        created_files = agent.export_data(test_data, output_dir)
        
        # Return the paths to the created files
        return {"files": created_files}
    
    except Exception as e:
        logger.error(f"Error exporting test data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/api-test-case-generation", response_model=APITestCaseGenerationResponse)
async def api_test_case_generation(request: APITestCaseGenerationRequest):
    """
    Generate API test cases from API details.
    """
    logger.info("=== Received API test case generation request ===")
    logger.info(f"API Details: {request.api_details}")
    logger.info(f"LLM Config: {request.llm_config}")

    try:
        # Create LLM
        llm_config = request.llm_config.model_dump()
        logger.info(f"Creating LLM with config: {llm_config}")
        llm = LLMFactory.create_llm(llm_config)

        # Create agent
        agent = APITestCaseCreationAgent(llm, {})

        # Process API details
        logger.info("Processing API details...")
        test_cases = await agent.process(request.api_details)

        # Ensure we have a list
        if not isinstance(test_cases, list):
            logger.warning(f"Test cases is not a list, got: {type(test_cases)}")
            test_cases = [test_cases] if test_cases else []

        logger.info(f"Generated {len(test_cases)} API test cases")

        # Return the response
        response = APITestCaseGenerationResponse(test_cases=test_cases)
        logger.info("Sending response...")
        return response

    except Exception as e:
        logger.error(f"Error in api_test_case_generation: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )


@app.get("/prompt-templates", response_model=PromptTemplateListResponse)
async def get_prompt_templates():
    """Get a list of available prompt templates."""
    try:
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "templates")
        templates = []
        if os.path.exists(templates_dir):
            for filename in os.listdir(templates_dir):
                if filename.endswith(".txt"):
                    with open(os.path.join(templates_dir, filename), 'r') as f:
                        content = f.read()
                    
                    templates.append(PromptTemplate(
                        name=filename,
                        content=content
                    ))
        
        return PromptTemplateListResponse(templates=templates)
    
    except Exception as e:
        logger.error(f"Error getting prompt templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("prompt-templates")
async def save_prompt_template(template: PromptTemplate):
    """Save a prompt template."""
    try:
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "templates")
        os.makedirs(templates_dir, exist_ok=True)
        
        template_path = os.path.join(templates_dir, template.name)
        with open(template_path, 'w') as f:
            f.write(template.content)
        
        return {"message": f"Template saved: {template.name}"}
    
    except Exception as e:
        logger.error(f"Error saving prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file and return its contents."""
    try:
        contents = await file.read()
        
        # Try to parse as JSON if the file has a .json extension
        if file.filename.endswith(".json"):
            try:
                data = json.loads(contents)
                return {"filename": file.filename, "content_type": "json", "content": data}
            except json.JSONDecodeError:
                pass
        
        # Return as text
        return {"filename": file.filename, "content_type": "text", "content": contents.decode()}
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest, session_id: str = Query(None)):
    """Chat with an agent."""
    try:
        # Validate message size
        if len(request.messages) > 50:  # Arbitrary limit
            raise HTTPException(status_code=400, detail="Too many messages in conversation")
        
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create LLM
        llm_config = request.llm_config.dict()
        llm = LLMFactory.create_llm(llm_config)
        
        # Get or create agent
        agent_key = f"{session_id}_{request.agent_type}"
        
        if agent_key in agent_sessions:
            agent = agent_sessions[agent_key]
        else:
            # Select the appropriate agent based on agent_type
            if request.agent_type == "test_case":
                agent = TestCaseGenerationAgent(llm, {})
            elif request.agent_type == "test_script":
                agent = TestScriptGenerator(llm, {})
            elif request.agent_type == "test_data":
                agent = TestDataGenerator(llm, {})
            else:
                raise HTTPException(status_code=400, detail=f"Unknown agent type: {request.agent_type}")
            
            # Store the agent in the session
            agent_sessions[agent_key] = agent
        
        # Process the chat request
        response_content, artifacts = await agent.chat(request.messages)
        
        # Create the response
        chat_response = ChatResponse(
            message=ChatMessage(role="assistant", content=response_content)
        )
        
        # Add artifacts if any
        if artifacts:
            if request.agent_type == "test_case" and "test_cases" in artifacts:
                chat_response.artifacts = TestCaseArtifact(test_cases=artifacts["test_cases"])
            elif request.agent_type == "test_script" and "test_scripts" in artifacts:
                chat_response.artifacts = TestScriptArtifact(test_scripts=artifacts["test_scripts"])
            elif request.agent_type == "test_data" and "test_data" in artifacts:
                chat_response.artifacts = TestDataArtifact(test_data=artifacts["test_data"])
        
        return chat_response
    
    except ValueError as e:
        logger.error(f"Validation error in chat: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


def check_dependencies():
    """Check if all dependencies in requirements.txt are installed."""
    try:
        requirements_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "requirements.txt")
        if os.path.exists(requirements_path):
            logger.info(f"Checking dependencies from {requirements_path}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
            logger.info("Dependencies updated successfully.")
        else:
            logger.warning(f"requirements.txt not found at {requirements_path}")
    except Exception as e:
        logger.error(f"Failed to update dependencies: {str(e)}")

def start_api_server(port=8000):
    """Start the API server."""
    import uvicorn
    # Using log_config=None avoids 'Unable to configure formatter 'default'' error in PyInstaller
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)


if __name__ == "__main__":
    import sys
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_api_server(port)