"""
Command Line Interface Module

This module provides a command-line interface for the framework.
"""

import os
import json
import asyncio
import click
from typing import Dict, Any, Optional

from quality_engineering_agentic_framework.utils.config_loader import ConfigLoader
from quality_engineering_agentic_framework.utils.logger import setup_logging, get_logger
from quality_engineering_agentic_framework.llm.llm_factory import LLMFactory
from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
from quality_engineering_agentic_framework.agents.test_script_generator import TestScriptGenerator
from quality_engineering_agentic_framework.agents.test_data_generator import TestDataGenerator
from quality_engineering_agentic_framework.web.run_web import run_web

logger = get_logger(__name__)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """Quality Engineering Agentic Framework (QEAF) CLI."""
    # Load configuration
    if config:
        config_dict = ConfigLoader.load_and_validate_config(config)
    else:
        config_dict = ConfigLoader.load_and_validate_config()
    
    # Set up logging
    log_config = config_dict.get("logging", {})
    if verbose:
        log_config["level"] = "DEBUG"
    setup_logging(log_config)
    
    # Store configuration in context
    ctx.ensure_object(dict)
    ctx.obj['config'] = config_dict


@cli.command()
@click.option('--requirements', '-r', required=True, type=click.Path(exists=True), help='Path to requirements file')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output directory')
@click.pass_context
def run(ctx, requirements, output):
    """Run the full agent workflow."""
    config = ctx.obj['config']
    
    # Create output directory if it doesn't exist
    os.makedirs(output, exist_ok=True)
    
    # Read requirements file
    with open(requirements, 'r') as f:
        requirements_text = f.read()
    
    # Run the workflow
    asyncio.run(run_workflow(config, requirements_text, output))


@cli.command()
@click.option('--agent', '-a', required=True, type=click.Choice(['test-case-generation', 'test-script-generator', 'test-data-generator']), help='Agent to run')
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Path to input file')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output directory or file')
@click.pass_context
def run_agent(ctx, agent, input, output):
    """Run a specific agent."""
    config = ctx.obj['config']
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
    
    # Read input file
    with open(input, 'r') as f:
        input_text = f.read()
    
    # Run the specified agent
    if agent == 'test-case-generation':
        asyncio.run(run_test_case_generation(config, input_text, output))
    elif agent == 'test-script-generator':
        # Input should be a JSON file with test cases
        test_cases = json.loads(input_text)
        asyncio.run(run_test_script_generator(config, test_cases, output))
    elif agent == 'test-data-generator':
        # Input could be test cases or test scripts
        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError:
            # If not JSON, treat as test scripts
            input_data = {os.path.basename(input): input_text}
        
        asyncio.run(run_test_data_generator(config, input_data, output))


@cli.command()
@click.option('--api-port', type=int, default=8000, help='Port for the API server')
@click.option('--ui-port', type=int, default=8501, help='Port for the UI server')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
def web(api_port, ui_port, no_browser):
    """Run the web interface."""
    run_web(api_port=api_port, ui_port=ui_port, open_browser=not no_browser)


async def run_workflow(config: Dict[str, Any], requirements_text: str, output_dir: str) -> None:
    """
    Run the full agent workflow.
    
    Args:
        config: Framework configuration
        requirements_text: Requirements text
        output_dir: Output directory
    """
    logger.info("Starting full workflow")
    
    # Create LLM
    llm_config = config.get("llm", {})
    llm = LLMFactory.create_llm(llm_config)
    
    # Step 1: Generate test cases from requirements
    logger.info("Step 1: Generating test cases from requirements")
    agent_config = config.get("agents", {}).get("test_case_generation", {})
    test_case_generation = TestCaseGenerationAgent(llm, agent_config)
    test_cases = await test_case_generation.process(requirements_text)
    
    # Save test cases
    test_cases_path = os.path.join(output_dir, "test_cases.json")
    with open(test_cases_path, 'w') as f:
        json.dump(test_cases, f, indent=2)
    logger.info(f"Saved test cases to {test_cases_path}")
    
    # Step 2: Generate test scripts from test cases
    logger.info("Step 2: Generating test scripts from test cases")
    agent_config = config.get("agents", {}).get("test_script_generator", {})
    test_script_generator = TestScriptGenerator(llm, agent_config)
    test_scripts = await test_script_generator.process(test_cases)
    
    # Save test scripts
    scripts_dir = os.path.join(output_dir, "test_scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    for filename, content in test_scripts.items():
        file_path = os.path.join(scripts_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
    logger.info(f"Saved test scripts to {scripts_dir}")
    
    # Step 3: Generate test data
    logger.info("Step 3: Generating test data")
    agent_config = config.get("agents", {}).get("test_data_generator", {})
    test_data_generator = TestDataGenerator(llm, agent_config)
    test_data = await test_data_generator.process(test_cases)
    
    # Save test data
    data_dir = os.path.join(output_dir, "test_data")
    os.makedirs(data_dir, exist_ok=True)
    created_files = test_data_generator.export_data(test_data, data_dir)
    logger.info(f"Saved test data to {', '.join(created_files)}")
    
    logger.info("Workflow completed successfully")


async def run_test_case_generation(config: Dict[str, Any], requirements_text: str, output_path: str) -> None:
    """
    Run the Test Case Generation agent.
    
    Args:
        config: Framework configuration
        requirements_text: Requirements text
        output_path: Output file path
    """
    # Create LLM
    llm_config = config.get("llm", {})
    llm = LLMFactory.create_llm(llm_config)
    
    # Create and run agent
    agent_config = config.get("agents", {}).get("test_case_generation", {})
    agent = TestCaseGenerationAgent(llm, agent_config)
    test_cases = await agent.process(requirements_text)
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(test_cases, f, indent=2)
    
    logger.info(f"Saved test cases to {output_path}")


async def run_test_script_generator(config: Dict[str, Any], test_cases: list, output_dir: str) -> None:
    """
    Run the Test Script Generator agent.
    
    Args:
        config: Framework configuration
        test_cases: Test cases
        output_dir: Output directory
    """
    # Create LLM
    llm_config = config.get("llm", {})
    llm = LLMFactory.create_llm(llm_config)
    
    # Create and run agent
    agent_config = config.get("agents", {}).get("test_script_generator", {})
    agent = TestScriptGenerator(llm, agent_config)
    test_scripts = await agent.process(test_cases)
    
    # Save output
    os.makedirs(output_dir, exist_ok=True)
    for filename, content in test_scripts.items():
        file_path = os.path.join(output_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
    
    logger.info(f"Saved test scripts to {output_dir}")


async def run_test_data_generator(config: Dict[str, Any], input_data: Any, output_dir: str) -> None:
    """
    Run the Test Data Generator agent.
    
    Args:
        config: Framework configuration
        input_data: Test cases or test scripts
        output_dir: Output directory
    """
    # Create LLM
    llm_config = config.get("llm", {})
    llm = LLMFactory.create_llm(llm_config)
    
    # Create and run agent
    agent_config = config.get("agents", {}).get("test_data_generator", {})
    agent = TestDataGenerator(llm, agent_config)
    test_data = await agent.process(input_data)
    
    # Save output
    os.makedirs(output_dir, exist_ok=True)
    created_files = agent.export_data(test_data, output_dir)
    
    logger.info(f"Saved test data to {', '.join(created_files)}")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()