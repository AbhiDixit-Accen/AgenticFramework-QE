# Quality Engineering Agentic Framework (QEAF)

An AI-powered framework that uses autonomous agents to automate the software testing process based on user-defined requirements.

## Overview

QEAF consists of three main agents:

1. **Test Case Generation Agent**: Converts plaintext or structured software requirements into structured test cases.
2. **Test Script Generator**: Transforms test cases into executable Selenium test scripts.
3. **Synthetic Test Data Generator**: Creates valid, edge-case, and randomized test data for the test cases.

## Features

- Configurable LLM Layer supporting OpenAI GPT-4, Google Gemini, and other LLMs
- Domain-specific requirement pattern support
- Selenium WebDriver test script generation
- Synthetic test data generation with CSV and JSON export
- Modular and extensible architecture
- Configuration via YAML or JSON
- Comprehensive logging and error handling
- Web-based UI for easy interaction with the framework

## Installation

```bash
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Run the full pipeline
qeaf run --requirements path/to/requirements.txt --output path/to/output

# Run specific agent
qeaf run-agent --agent test-case-generation --input path/to/input.txt --output path/to/output

# Run the web interface
qeaf web
```

### Web Interface

The framework includes a web-based UI that allows you to:

1. Configure LLM backends (OpenAI, Gemini)
2. Manage API keys securely
3. Edit prompt templates
4. Interact with agents through a user-friendly interface
5. View and download outputs

To start the web interface:

```bash
qeaf web
```

This will start both the API server and the Streamlit UI, and open your browser to the UI.

### Docker Deployment

You can also run the framework using Docker:

```bash
# Build and run using docker-compose
docker-compose up -d

# Or build and run manually
docker build -t qeaf .
docker run -p 8000:8000 -p 8501:8501 -v ./config:/app/config qeaf
```

### Configuration

Create a `config.yaml` file in the `config/` directory:

```yaml
llm:
  provider: openai  # or gemini
  model: gpt-4
  api_key: your_api_key_here

agents:
  test_case_generation:
    prompt_template: "templates/test_case_generation_prompt.txt"
    output_format: "gherkin"
  test_script_generator:
    browser: chrome
  test_data_generator:
    output_format: json  # or csv
```

## Web Interface Walkthrough

### 1. LLM Configuration

In the sidebar, you can:
- Select the LLM provider (OpenAI or Gemini)
- Choose the model
- Enter your API key
- Adjust temperature and max tokens

### 2. Test Case Generation

In the "Test Case Generation" tab:
- Configure the agent (output format, prompt template)
- Enter requirements text or upload a file
- Generate test cases
- View and download the results

### 3. Test Script Generation

In the "Test Script Generation" tab:
- Configure the agent (framework, browser, prompt template)
- Use test cases from the previous step or upload a file
- Generate test scripts
- View and download individual scripts or all as a ZIP

### 4. Test Data Generation

In the "Test Data Generation" tab:
- Configure the agent (output format, data variations, edge cases)
- Use input from previous steps or upload a file
- Generate test data
- View and download the results in JSON or CSV format

## License

[Your License]