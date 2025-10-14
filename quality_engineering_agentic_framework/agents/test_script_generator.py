"""
Test Script Generator Agent

Transforms structured test cases or rendered DOM into executable Selenium test scripts
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
    Generates executable Selenium test scripts from structured test cases or rendered DOM.
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
            "python": ["pytest", "unittest", "robot"],
            "java": ["junit", "testng", "cucumber"],
            "javascript": ["jest", "mocha", "cypress"],
            "c#": ["nunit", "xunit", "mstest"]
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
        
        # Updated default template with page load & element waits
        return """
        You are a senior test automation engineer. Generate fully working Selenium automation scripts.
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
        - Include imports, waits, error handling, and assertions
        - Ensure **page load is complete** before interacting with elements
        - Use **explicit waits** for web elements (presence, visibility, clickable) before actions
        - Apply waits in a language/framework-specific way that works seamlessly
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
        Process structured test cases or a rendered DOM to generate Selenium scripts.
        
        Args:
            test_cases: List of structured test cases
            rendered_dom: Optional HTML string of the rendered page for locator extraction
        
        Returns:
            Dictionary of filename -> script content
        """
        locator_info = {}

        if rendered_dom:
            # Parse rendered DOM
            soup = BeautifulSoup(rendered_dom, "html.parser")
            dom_tree = etree.HTML(str(soup))

            tags = ["input", "button", "a", "select", "textarea"]
            elements = soup.find_all(tags)

            for idx, el in enumerate(elements, 1):
                el_id = el.get("id")
                el_name = el.get("name")
                el_class = el.get("class")

                # Build CSS selector
                if el_id:
                    css_selector = f"#{el_id}"
                elif el_class:
                    css_selector = "." + ".".join(el_class)
                else:
                    css_selector = el.name

                # Build XPath
                try:
                    xpath = dom_tree.getpath(dom_tree.xpath(f"//*[@id='{el_id}']")[0]) if el_id else None
                except Exception:
                    xpath = None

                locator_info[idx] = {
                    "tag": el.name,
                    "text": el.get_text(strip=True),
                    "id": el_id,
                    "name": el_name,
                    "class": el_class,
                    "css_selector": css_selector,
                    "xpath": xpath
                }

            test_cases_str = json.dumps(locator_info, indent=2)
        else:
            # Convert structured test cases to string
            test_cases_str = ""
            for i, tc in enumerate(test_cases):
                test_cases_str += f"Test Case {i+1}: {tc.get('title', 'Untitled')}\n"
                test_cases_str += f"Description: {tc.get('description', 'N/A')}\n"
                test_cases_str += "Preconditions:\n" + "\n".join(f"- {p}" for p in tc.get("preconditions", [])) + "\n"
                test_cases_str += "Actions:\n" + "\n".join(f"- {a}" for a in tc.get("actions", [])) + "\n"
                test_cases_str += "Expected Results:\n" + "\n".join(f"- {r}" for r in tc.get("expected_results", [])) + "\n\n"

        # Prepare prompt for LLM
        file_extensions = {"python": "py", "java": "java", "javascript": "js", "c#": "cs"}
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
        You are a senior test automation engineer. Generate Selenium test scripts with Page Objects using
        multiple locator strategies (id, name, class, CSS selector, XPath) for all elements.
        Include proper waits for page load and web elements, error handling, and assertions.
        Use the structured locator JSON as reference for element selectors.
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
