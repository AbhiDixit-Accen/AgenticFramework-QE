"""
Test Script Generator Agent

Transforms structured test cases or rendered DOM into executable automation test scripts (Selenium, Playwright, etc.)
for any language, framework, and project structure.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
from lxml import etree

from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger
from quality_engineering_agentic_framework.web.api.models import ChatMessage

logger = get_logger(__name__)


class TestScriptGenerator(AgentInterface):
    """
    Generates executable web automation test scripts (Selenium, Playwright, etc.) from structured test cases or rendered DOM.
    Fully supports multiple languages, frameworks, and project structures.
    """

    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        super().__init__(llm, config)
        self.language = str(config.get("language", "Python")).lower().strip()
        self.framework = str(config.get("framework", "pytest")).lower().strip()
        self.browser = str(config.get("browser", "chrome")).lower().strip()
        self.project_structure = config.get("project_structure", {
            "pages": "src/pages/",
            "tests": "tests/",
            "utils": "utils/"
        })
        logger.info(f"Initialized TestScriptGenerator with language={self.language}, framework={self.framework}, browser={self.browser}")
        self._validate_config()
        self.prompt_template = self._load_prompt_template(config.get("prompt_template"))

    def _validate_config(self):
        valid_languages = {
            "python": ["pytest", "unittest", "robot", "playwright"],
            "java": ["junit", "testng", "cucumber", "playwright", "selenide"],
            "javascript": ["jest", "mocha", "cypress", "playwright"],
            "typescript": ["jest", "mocha", "cypress", "playwright", "webdriverio"],
            "c#": ["nunit", "xunit", "mstest", "playwright"]
        }
        if self.language not in valid_languages:
            raise ValueError(f"Unsupported language: {self.language}. Supported: {', '.join(valid_languages.keys())}")
        if self.framework not in valid_languages[self.language]:
            raise ValueError(f"Unsupported framework '{self.framework}' for {self.language}. Supported: {', '.join(valid_languages[self.language])}")
        logger.info(f"Configuration validated: language={self.language}, framework={self.framework}")

    def _load_prompt_template(self, template_path: Optional[str]) -> str:
        if template_path and os.path.exists(template_path):
            try:
                with open(template_path, 'r') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load prompt template: {e}")
        
        return """
        You are a senior test automation engineer. Generate fully working web automation scripts using {framework}.
        Requirements:
        - Language: {language}
        - Framework: {framework}
        - Browser: {browser}
        - Project Structure: Pages -> {pages}, Tests -> {tests}, Utils -> {utils}
        
        Test Cases or Locators:
        {test_cases}

        Guidelines:
        - NO placeholders (do not use TODO, pass, or comments instead of code)
        - Generate fully executable code
        - Include Page Objects and utility classes
        - Use best practices for {language} + {framework}
        - Include imports, assertions, and proper error handling
        - Handle Synchronization:
            * For Selenium/Appium: Use explicit waits for element visibility/clickability.
            * For Playwright/Cypress: Rely on native auto-waiting where appropriate.
        - Ensure scripts are maintainable and follow the provided project structure.
        - Format each file in a code block with filename and extension:
        ```{language}:filename.{extension}
        // code
        ```
        """

    async def process(
        self,
        test_cases: List[Dict[str, Any]],
        rendered_dom: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Process structured test cases or a rendered DOM to generate automation scripts.
        """
        locator_info = {}

        # Check if structured test cases provide any locators
        locators_provided = False
        for tc in test_cases:
            for action in tc.get("actions", []):
                if "locator" in action:
                    locators_provided = True
                    break
            if locators_provided:
                break

        if not locators_provided and rendered_dom:
            # Only parse DOM if no locators are provided
            soup = BeautifulSoup(rendered_dom, "html.parser")
            dom_tree = etree.HTML(str(soup))
            tags = ["input", "button", "a", "select", "textarea"]
            elements = soup.find_all(tags)
            for idx, el in enumerate(elements, 1):
                el_id = el.get("id")
                el_class = el.get("class")
                css_selector = f"#{el_id}" if el_id else ("." + ".".join(el_class) if el_class else el.name)
                try:
                    xpath = dom_tree.getpath(dom_tree.xpath(f"//*[@id='{el_id}']")[0]) if el_id else None
                except Exception:
                    xpath = None

                locator_info[idx] = {
                    "tag": el.name,
                    "text": el.get_text(strip=True),
                    "id": el_id,
                    "class": el_class,
                    "css_selector": css_selector,
                    "xpath": xpath
                }

        # Convert test cases to string for LLM prompt
        test_cases_str = ""
        for i, tc in enumerate(test_cases):
            test_cases_str += f"Test Case {i+1}: {tc.get('title', 'Untitled')}\n"
            test_cases_str += f"Description: {tc.get('description', 'N/A')}\n"
            test_cases_str += "Preconditions:\n" + "\n".join(f"- {p}" for p in tc.get("preconditions", [])) + "\n"
            test_cases_str += "Actions:\n"
            for a in tc.get("actions", []):
                if isinstance(a, dict):
                    action_desc = f"- {a.get('action', 'Unknown Action')}"
                    if 'locator' in a:
                        locators = a['locator']
                        if isinstance(locators, dict):
                            locator_parts = [f"{k}: {v}" for k, v in locators.items()]
                            action_desc += " | Locator: " + ", ".join(locator_parts)
                        else:
                            action_desc += f" | Locator: {locators}"
                    else:
                        if not locators_provided and rendered_dom:
                            action_desc += " | Locator: (to be determined from DOM)"
                    if 'value' in a:
                        action_desc += f" | Value: {a['value']}"
                else:
                    # Handle string-based actions
                    action_desc = f"- {str(a)}"
                    if not locators_provided and rendered_dom:
                        action_desc += " | Locator: (to be determined from DOM)"
                
                test_cases_str += action_desc + "\n"
            test_cases_str += "Expected Results:\n" + "\n".join(f"- {r}" for r in tc.get("expected_results", [])) + "\n\n"

        # Prepare prompt for LLM
        file_extensions = {"python": "py", "java": "java", "javascript": "js", "typescript": "ts", "c#": "cs"}
        ext = file_extensions.get(self.language, "txt")
        language_name = self.language.capitalize()

        prompt = self.prompt_template.format(
            language=language_name,
            framework=self.framework,
            browser=self.browser,
            pages=self.project_structure["pages"],
            tests=self.project_structure["tests"],
            utils=self.project_structure["utils"],
            test_cases=test_cases_str,
            extension=ext
        )

        system_message = f"""
        You are a senior test automation engineer. Generate {self.framework} test scripts with Page Objects using
        multiple locator strategies (id, name, class, CSS selector, XPath) where appropriate.
        Ensure scripts use best practices for {self.language} + {self.framework}, including proper 
        synchronization (waits), error handling, and robust assertions.
        """

        try:
            response = await self.llm.generate(prompt=prompt, system_message=system_message, temperature=0.7, max_tokens=4000)
            files = self._parse_files_from_response(response)
            if not files:
                return {"fallback.txt": response}
            return files
        except Exception as e:
            logger.error(f"Error generating scripts: {e}", exc_info=True)
            return {"error.txt": str(e)}

    def _parse_files_from_response(self, response: str) -> Dict[str, str]:
        files = {}
        if not response:
            return files
        # Detect code blocks with language and filename
        matches = re.findall(r'```(?:\w+):([^\n]+)\n([\s\S]*?)```', response)
        for filename, code in matches:
            files[filename.strip()] = code.strip()
        return files

    def _extract_test_cases(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        for msg in reversed(messages):
            if msg.role == "user":
                try:
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', msg.content)
                    if json_match:
                        return json.loads(json_match.group(1))
                    return json.loads(msg.content)
                except:
                    continue
        return []

    async def chat(self, messages: List[ChatMessage]) -> Tuple[str, Optional[Dict[str, Any]]]:
        latest_msg = next((m for m in reversed(messages) if m.role == "user"), None)
        if not latest_msg:
            return "No user messages detected.", None
        test_cases = self._extract_test_cases(messages)
        if test_cases:
            scripts = await self.process(test_cases)
            summary = "\n".join(list(scripts.keys())[:3])
            response = f"Generated {len(scripts)} test files. Examples:\n{summary}"
            return response, {"test_scripts": scripts}
        return "Please provide structured test cases in JSON format.", None

    def get_name(self) -> str:
        return "test_script_generator"

    def get_description(self) -> str:
        return "Transforms structured test cases or rendered DOM into fully executable Selenium test scripts for any language/framework."
