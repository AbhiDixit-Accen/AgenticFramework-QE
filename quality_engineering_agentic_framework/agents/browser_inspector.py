"""
Browser Inspector Agent

Captures web elements from live browsers and generates stable, framework-specific selectors.
Stores elements in SEPARATE vector DB for intelligent test script generation.
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from quality_engineering_agentic_framework.agents.agent_interface import AgentInterface
from quality_engineering_agentic_framework.llm.llm_interface import LLMInterface
from quality_engineering_agentic_framework.utils.logger import get_logger
from quality_engineering_agentic_framework.web.api.models import ChatMessage
from quality_engineering_agentic_framework.utils.rag.element_storage import get_element_storage

logger = get_logger(__name__)


class BrowserInspectorAgent(AgentInterface):
    """
    Agent that manages browser inspection sessions and element storage.
    """
    
    def __init__(self, llm: LLMInterface, config: Dict[str, Any]):
        """
        Initialize the Browser Inspector agent.
        
        Args:
            llm: LLM instance to use for intelligent selector generation
            config: Dictionary containing agent-specific configuration
                - persist_to_db: bool - Whether to store elements in vector DB (default: True)
                - api_key: str - OpenAI API key for embeddings
        """
        super().__init__(llm, config)
        self.sessions = {}  # Active inspection sessions
        self.selector_engine = SelectorEngine()
        
        # Initialize element storage (separate from RAG)
        self.persist_to_db = config.get("persist_to_db", True)
        if self.persist_to_db:
            api_key = config.get("api_key") or getattr(llm, 'api_key', None)
            self.element_storage = get_element_storage(api_key)
            logger.info("Initialized Browser Inspector agent with vector DB storage")
        else:
            self.element_storage = None
            logger.info("Initialized Browser Inspector agent (session-only, no persistence)")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process browser inspection requests.
        
        Args:
            input_data: Dictionary containing action and payload
                - action: "capture_element", "validate_selector", "get_session"
                - payload: Action-specific data
            
        Returns:
            Result of the inspection action
        """
        action = input_data.get("action")
        payload = input_data.get("payload", {})
        
        if action == "capture_element":
            return await self._capture_element(payload)
        elif action == "validate_selector":
            return await self._validate_selector(payload)
        elif action == "get_session":
            return await self._get_session(payload)
        elif action == "generate_selectors":
            return await self._generate_selectors(payload)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _capture_element(self, element_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture an element and generate selectors.
        
        Args:
            element_data: Element metadata from browser
            
        Returns:
            Dict containing selectors for all frameworks
        """
        # Generate selectors for all frameworks
        selectors = await self._generate_selectors(element_data)
        
        # Store in session (memory)
        session_id = element_data.get("session_id", "default")
        page_url = element_data.get("url", "")
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "elements": {},
                "url": page_url
            }
        
        self.sessions[session_id]["elements"][element_id] = {
            "element_data": element_data,
            "selectors": selectors,
            "captured_at": datetime.now().isoformat()
        }
        
        # Store in vector DB (separate from RAG) if enabled
        if self.persist_to_db and self.element_storage:
            try:
                self.element_storage.store_element(
                    element_data=element_data,
                    selectors=selectors,
                    session_id=session_id,
                    page_url=page_url
                )
                logger.info(f"Element {element_id} persisted to vector DB")
            except Exception as e:
                logger.error(f"Failed to persist element to DB: {str(e)}")
        
        # Store in session
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "elements": {},
                "url": element_data.get("url", "")
            }
        
        self.sessions[session_id]["elements"][element_id] = {
            "element_data": element_data,
            "selectors": selectors,
            "captured_at": datetime.now().isoformat()
        }
        
        return {
            "element_id": element_id,
            "selectors": selectors,
            "session_id": session_id
        }
    
    async def _validate_selector(self, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a selector against the DOM.
        
        Args:
            validation_data: Selector and validation results from browser
            
        Returns:
            Updated selector with stability score
        """
        selector = validation_data.get("selector")
        results = validation_data.get("results", {})
        
        # Calculate stability score
        score = self._calculate_stability_score(results)
        
        return {
            "selector": selector,
            "is_valid": results.get("count", 0) == 1,
            "is_unique": results.get("count", 0) == 1,
            "is_visible": results.get("visible", False),
            "stability_score": score,
            "element_count": results.get("count", 0)
        }
    
    async def _get_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve an inspection session.
        
        Args:
            session_data: Contains session_id
            
        Returns:
            Session data
        """
        session_id = session_data.get("session_id")
        return self.sessions.get(session_id, {})
    
    async def _generate_selectors(self, element_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate all framework-specific selectors for an element.
        
        Args:
            element_data: Element metadata
            
        Returns:
            List of selectors for different frameworks
        """
        return self.selector_engine.generate_all_framework_selectors(element_data)
    
    def _generate_element_id(self, element_data: Dict[str, Any]) -> str:
        """Generate unique ID for an element based on its attributes."""
        identifier = f"{element_data.get('tagName', '')}_{element_data.get('id', '')}_{element_data.get('xpath', '')}"
        return hashlib.md5(identifier.encode()).hexdigest()[:12]
    
    def _calculate_stability_score(self, validation_results: Dict[str, Any]) -> int:
        """
        Calculate stability score (1-5) based on validation results.
        
        Args:
            validation_results: Results from DOM validation
            
        Returns:
            Stability score from 1 (unstable) to 5 (highly stable)
        """
        score = 1
        
        # Unique selector
        if validation_results.get("count") == 1:
            score += 2
        
        # Element is visible
        if validation_results.get("visible"):
            score += 1
        
        # Has stable attributes (data-testid, id, etc.)
        if validation_results.get("has_stable_attributes"):
            score += 1
        
        return min(score, 5)


class SelectorEngine:
    """
    Generates stable, UNIQUE selectors with priority-based ranking.
    Uses parent-child relationships to ensure uniqueness.
    """
    
    def __init__(self):
        self.priority_order = [
            "data-testid",
            "data-test",
            "data-cy",
            "id",
            "aria-label",
            "name",
            "css",
            "xpath"
        ]
        
        # Patterns that indicate auto-generated/unstable classes
        self.unstable_patterns = ["css-", "sc-", "jsx-", "makeStyles-", "styled-", "emotion-", "MuiBox", "\\d{5,}"]
    
    def generate_selectors(self, element_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate UNIQUE selectors for an element with priority ranking.
        Uses parent-child relationships for uniqueness.
        
        Args:
            element_data: Element metadata from browser
            
        Returns:
            Dictionary of selectors by type
        """
        selectors = {}
        
        # Extract attributes
        attrs = element_data.get("attributes", {})
        tag_name = element_data.get("tagName", "").lower()
        dom_path = element_data.get("domPath", "")
        
        # Priority 1: Test attributes (already unique by convention)
        for test_attr in ["data-testid", "data-test", "data-cy"]:
            if test_attr in attrs:
                selectors[test_attr] = f"[{test_attr}='{attrs[test_attr]}']"
        
        # Priority 2: ARIA role + accessible name
        aria_info = element_data.get("ariaInfo", {})
        role = aria_info.get("role") or attrs.get("role")
        aria_label = aria_info.get("label") or attrs.get("aria-label")
        
        if role and aria_label:
            selectors["aria"] = f"[role='{role}'][aria-label='{aria_label}']"
        elif aria_label:
            selectors["aria-label"] = f"[aria-label='{aria_label}']"
        
        # Priority 3: Unique ID
        if "id" in attrs and attrs["id"] and not self._is_unstable_id(attrs["id"]):
            selectors["id"] = f"#{attrs['id']}"
        
        # Priority 4: Name attribute
        if "name" in attrs and attrs["name"]:
            selectors["name"] = f"[name='{attrs['name']}']"
        
        # Priority 5: Build unique CSS with parent context
        unique_css = self._build_unique_css_selector(element_data)
        if unique_css:
            selectors["css"] = unique_css
            selectors["css_unique"] = unique_css  # Mark as unique
        
        # Priority 6: Parent-scoped selector for non-unique elements
        parent_scoped = self._build_parent_scoped_selector(element_data)
        if parent_scoped:
            selectors["parent_scoped"] = parent_scoped
        
        # Priority 7: nth-child based selector for repeated elements
        nth_selector = self._build_nth_child_selector(element_data)
        if nth_selector:
            selectors["nth_child"] = nth_selector
        
        # Priority 8: XPath (optimized for uniqueness)
        xpath = self._build_unique_xpath(element_data)
        if xpath:
            selectors["xpath"] = xpath
        
        # Priority 9: Combined attribute selector
        combined = self._build_combined_attribute_selector(element_data)
        if combined:
            selectors["combined"] = combined
        
        # Fallback: Text-based selector with parent scope
        inner_text = element_data.get("innerText", "").strip()
        if inner_text and len(inner_text) < 50:
            text_selector = self._build_text_with_parent_selector(element_data, inner_text)
            selectors["text"] = text_selector
        
        return selectors
    
    def _is_unstable_id(self, element_id: str) -> bool:
        """Check if ID looks auto-generated/unstable."""
        import re
        # IDs with long numbers or hex strings are usually auto-generated
        if re.search(r'\d{4,}', element_id):
            return True
        if re.search(r'[a-f0-9]{8,}', element_id.lower()):
            return True
        return False
    
    def _build_unique_css_selector(self, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Build a unique CSS selector using class combinations and parent context.
        """
        attrs = element_data.get("attributes", {})
        tag_name = element_data.get("tagName", "").lower()
        class_list = element_data.get("classList", [])
        dom_path = element_data.get("domPath", "")
        
        # Filter out unstable classes
        stable_classes = self._get_stable_classes(class_list)
        
        if not stable_classes:
            return None
        
        # Build base selector with tag and stable classes
        base_selector = f"{tag_name}.{'.'.join(stable_classes[:3])}"
        
        # If we have a meaningful parent in dom_path, use it
        if dom_path:
            parent_selector = self._extract_unique_parent_from_dom_path(dom_path)
            if parent_selector:
                return f"{parent_selector} > {base_selector}"
        
        # Add distinguishing attributes if available
        distinguishing_attrs = self._get_distinguishing_attributes(attrs)
        if distinguishing_attrs:
            attr_selector = ''.join([f"[{k}='{v}']" for k, v in distinguishing_attrs.items()])
            return f"{tag_name}{attr_selector}"
        
        return base_selector
    
    def _build_parent_scoped_selector(self, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Build selector using parent element for scoping.
        Format: parent_selector child_selector
        """
        dom_path = element_data.get("domPath", "")
        tag_name = element_data.get("tagName", "").lower()
        attrs = element_data.get("attributes", {})
        
        if not dom_path:
            return None
        
        # Parse dom_path: "div.class > span#id > button.class"
        path_parts = [p.strip() for p in dom_path.split(">")]
        
        if len(path_parts) < 2:
            return None
        
        # Find a unique parent (one with ID or data-testid)
        unique_parent = None
        for i, part in enumerate(path_parts[:-1]):
            if "#" in part or "data-testid" in str(attrs):
                unique_parent = part
                break
            # Check for form, nav, header, main, section (semantic elements)
            semantic_tags = ["form", "nav", "header", "main", "section", "article", "aside", "footer"]
            for sem_tag in semantic_tags:
                if part.startswith(sem_tag):
                    unique_parent = part
                    break
        
        if not unique_parent:
            # Use the immediate parent with index if needed
            unique_parent = path_parts[-2] if len(path_parts) >= 2 else None
        
        if unique_parent:
            # Build child selector
            child_selector = self._build_child_selector(element_data)
            return f"{unique_parent} {child_selector}"
        
        return None
    
    def _build_child_selector(self, element_data: Dict[str, Any]) -> str:
        """Build the most specific child selector possible."""
        tag_name = element_data.get("tagName", "").lower()
        attrs = element_data.get("attributes", {})
        class_list = element_data.get("classList", [])
        
        # Priority: type attribute for inputs, then name, then classes
        if tag_name == "input" and "type" in attrs:
            return f"input[type='{attrs['type']}']"
        
        if "name" in attrs:
            return f"{tag_name}[name='{attrs['name']}']"
        
        stable_classes = self._get_stable_classes(class_list)
        if stable_classes:
            return f"{tag_name}.{'.'.join(stable_classes[:2])}"
        
        return tag_name
    
    def _build_nth_child_selector(self, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Build nth-child selector for repeated elements.
        Uses the XPath to determine position.
        """
        xpath = element_data.get("xpath", "")
        dom_path = element_data.get("domPath", "")
        tag_name = element_data.get("tagName", "").lower()
        
        if not xpath:
            return None
        
        # Extract index from xpath like "/html/body/div[2]/ul/li[3]"
        import re
        matches = re.findall(r'\[(\d+)\]', xpath)
        
        if matches:
            last_index = matches[-1]
            
            # Find parent from dom_path
            path_parts = [p.strip() for p in dom_path.split(">")]
            if len(path_parts) >= 2:
                parent = path_parts[-2]
                return f"{parent} > {tag_name}:nth-child({last_index})"
        
        return None
    
    def _build_unique_xpath(self, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Build an optimized, shorter XPath that's still unique.
        Uses ancestor with ID or data-testid to shorten path.
        """
        xpath = element_data.get("xpath", "")
        dom_path = element_data.get("domPath", "")
        attrs = element_data.get("attributes", {})
        tag_name = element_data.get("tagName", "").lower()
        
        # If element has ID, use short form
        if "id" in attrs and attrs["id"] and not self._is_unstable_id(attrs["id"]):
            return f"//*[@id='{attrs['id']}']"
        
        # If we have data-testid, use it
        for test_attr in ["data-testid", "data-test", "data-cy"]:
            if test_attr in attrs:
                return f"//*[@{test_attr}='{attrs[test_attr]}']"
        
        # Try to find ancestor with ID in dom_path
        if dom_path and "#" in dom_path:
            path_parts = [p.strip() for p in dom_path.split(">")]
            for i, part in enumerate(path_parts):
                if "#" in part:
                    # Found ancestor with ID
                    ancestor_id = part.split("#")[1].split(".")[0].split("[")[0]
                    remaining_path = path_parts[i+1:]
                    if remaining_path:
                        relative_xpath = "/".join([self._css_to_xpath_part(p) for p in remaining_path])
                        return f"//*[@id='{ancestor_id}']//{relative_xpath}"
        
        # Fallback to original xpath but try to shorten
        if xpath and "//" not in xpath:
            # Find a good starting point
            parts = xpath.split("/")
            # Remove empty parts and html/body
            parts = [p for p in parts if p and p not in ["html", "body"]]
            if len(parts) > 3:
                # Use last 3 parts with //
                return "//" + "/".join(parts[-3:])
        
        return xpath
    
    def _css_to_xpath_part(self, css_part: str) -> str:
        """Convert a single CSS selector part to XPath."""
        import re
        # Handle "tag#id.class" format
        match = re.match(r'(\w+)?(?:#([\w-]+))?(?:\.([\w.-]+))?', css_part)
        if match:
            tag = match.group(1) or "*"
            id_val = match.group(2)
            classes = match.group(3)
            
            if id_val:
                return f"{tag}[@id='{id_val}']"
            elif classes:
                first_class = classes.split(".")[0]
                return f"{tag}[contains(@class,'{first_class}')]"
            return tag
        return "*"
    
    def _build_combined_attribute_selector(self, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Build a selector combining multiple attributes for uniqueness.
        """
        attrs = element_data.get("attributes", {})
        tag_name = element_data.get("tagName", "").lower()
        
        # Prioritized attributes to combine
        priority_attrs = ["type", "name", "placeholder", "title", "value", "href", "src", "alt"]
        
        combined_attrs = {}
        for attr in priority_attrs:
            if attr in attrs and attrs[attr]:
                val = attrs[attr]
                # Truncate long values
                if len(str(val)) <= 50:
                    combined_attrs[attr] = val
                if len(combined_attrs) >= 2:
                    break
        
        if len(combined_attrs) >= 2:
            attr_selector = ''.join([f"[{k}='{v}']" for k, v in combined_attrs.items()])
            return f"{tag_name}{attr_selector}"
        
        return None
    
    def _build_text_with_parent_selector(self, element_data: Dict[str, Any], text: str) -> str:
        """Build text selector with parent scope for uniqueness."""
        tag_name = element_data.get("tagName", "").lower()
        dom_path = element_data.get("domPath", "")
        
        # Truncate text
        short_text = text[:30].strip()
        
        # If we have a unique parent, scope it
        if dom_path:
            path_parts = [p.strip() for p in dom_path.split(">")]
            for part in path_parts[:-1]:
                if "#" in part:
                    return f"{part} {tag_name}:has-text('{short_text}')"
        
        return f"{tag_name}:has-text('{short_text}')"
    
    def _get_stable_classes(self, class_list: List[str]) -> List[str]:
        """Filter out unstable/auto-generated CSS classes."""
        import re
        stable = []
        for cls in class_list:
            is_unstable = False
            for pattern in self.unstable_patterns:
                if re.search(pattern, cls, re.IGNORECASE):
                    is_unstable = True
                    break
            if not is_unstable and len(cls) > 2:  # Skip very short classes
                stable.append(cls)
        return stable[:5]  # Limit to 5 classes
    
    def _get_distinguishing_attributes(self, attrs: Dict[str, str]) -> Dict[str, str]:
        """Get attributes that help distinguish the element."""
        distinguishing = {}
        useful_attrs = ["type", "placeholder", "title", "alt", "role", "aria-label"]
        
        for attr in useful_attrs:
            if attr in attrs and attrs[attr]:
                distinguishing[attr] = attrs[attr]
                if len(distinguishing) >= 2:
                    break
        
        return distinguishing
    
    def _extract_unique_parent_from_dom_path(self, dom_path: str) -> Optional[str]:
        """Extract a unique parent selector from DOM path."""
        path_parts = [p.strip() for p in dom_path.split(">")]
        
        # Look for semantic elements or elements with ID
        semantic_tags = ["form", "nav", "header", "main", "section", "article", "aside", "footer", "dialog", "modal"]
        
        for part in path_parts[:-1]:
            # Check for ID
            if "#" in part:
                return part
            # Check for semantic tags
            for sem_tag in semantic_tags:
                if part.startswith(sem_tag):
                    return part
        
        return None
    
    def generate_all_framework_selectors(self, element_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate selectors for all supported frameworks.
        
        Args:
            element_data: Element metadata from browser
            
        Returns:
            List of framework-specific selector dictionaries
        """
        # Generate base selectors
        base_selectors = self.generate_selectors(element_data)
        
        # Convert for each framework
        adapters = {
            "playwright": PlaywrightAdapter(),
            "selenium": SeleniumAdapter(),
            "cypress": CypressAdapter()
        }
        
        results = []
        for framework, adapter in adapters.items():
            framework_selectors = adapter.convert_selectors(base_selectors, element_data)
            results.append({
                "framework": framework,
                "selectors": framework_selectors
            })
        
        return results


class PlaywrightAdapter:
    """Converts selectors to Playwright format with unique parent-child selectors."""
    
    def convert_selectors(self, base_selectors: Dict[str, Any], element_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Convert to Playwright-specific selectors with uniqueness."""
        results = []
        attrs = element_data.get("attributes", {})
        
        # Priority 1: Test ID (Playwright's preferred method)
        if "data-testid" in base_selectors:
            results.append({
                "type": "data-testid",
                "selector": f"page.get_by_test_id('{attrs.get('data-testid')}')",
                "priority": 1,
                "unique": True
            })
        
        # Priority 2: Role-based with accessible name
        aria_info = element_data.get("ariaInfo", {})
        role = aria_info.get("role") or attrs.get("role") if aria_info else attrs.get("role")
        aria_label = aria_info.get("label") or attrs.get("aria-label") if aria_info else attrs.get("aria-label")
        if role and aria_label:
            results.append({
                "type": "role",
                "selector": f"page.get_by_role('{role}', name='{aria_label}')",
                "priority": 2,
                "unique": True
            })
        elif aria_label:
            results.append({
                "type": "aria-label",
                "selector": f"page.get_by_label('{aria_label}')",
                "priority": 2,
                "unique": True
            })
        
        # Priority 3: Parent-scoped locator (UNIQUE)
        if "parent_scoped" in base_selectors:
            results.append({
                "type": "parent_scoped",
                "selector": f"page.locator('{base_selectors['parent_scoped']}')",
                "priority": 3,
                "unique": True
            })
        
        # Priority 4: Unique CSS with parent context
        if "css_unique" in base_selectors:
            results.append({
                "type": "css_unique",
                "selector": f"page.locator('{base_selectors['css_unique']}')",
                "priority": 4,
                "unique": True
            })
        
        # Priority 5: nth-child for repeated elements
        if "nth_child" in base_selectors:
            results.append({
                "type": "nth_child",
                "selector": f"page.locator('{base_selectors['nth_child']}')",
                "priority": 5,
                "unique": True
            })
        
        # Priority 6: Combined attributes
        if "combined" in base_selectors:
            results.append({
                "type": "combined_attrs",
                "selector": f"page.locator('{base_selectors['combined']}')",
                "priority": 6,
                "unique": True
            })
        
        # Priority 7: Text-based
        inner_text = element_data.get("innerText", "").strip()
        if inner_text:
            results.append({
                "type": "text",
                "selector": f"page.get_by_text('{inner_text[:30]}')",
                "priority": 7,
                "unique": False
            })
        
        # Priority 8: Basic CSS (may not be unique)
        if "css" in base_selectors and "css_unique" not in base_selectors:
            results.append({
                "type": "css",
                "selector": f"page.locator('{base_selectors['css']}')",
                "priority": 8,
                "unique": False
            })
        
        # Priority 9: XPath (optimized)
        if "xpath" in base_selectors:
            results.append({
                "type": "xpath",
                "selector": f"page.locator('xpath={base_selectors['xpath']}')",
                "priority": 9,
                "unique": True
            })
        
        return sorted(results, key=lambda x: x["priority"])


class SeleniumAdapter:
    """Converts selectors to Selenium format with unique parent-child selectors."""
    
    def convert_selectors(self, base_selectors: Dict[str, Any], element_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Convert to Selenium-specific selectors with uniqueness."""
        results = []
        attrs = element_data.get("attributes", {})
        
        # Priority 1: ID (if stable)
        if "id" in base_selectors:
            results.append({
                "type": "id",
                "selector": f"driver.find_element(By.ID, '{attrs.get('id')}')",
                "priority": 1,
                "unique": True
            })
        
        # Priority 2: Name
        if "name" in base_selectors:
            results.append({
                "type": "name",
                "selector": f"driver.find_element(By.NAME, '{attrs.get('name')}')",
                "priority": 2,
                "unique": True
            })
        
        # Priority 3: Parent-scoped CSS (UNIQUE)
        if "parent_scoped" in base_selectors:
            results.append({
                "type": "parent_scoped",
                "selector": f"driver.find_element(By.CSS_SELECTOR, '{base_selectors['parent_scoped']}')",
                "priority": 3,
                "unique": True
            })
        
        # Priority 4: Unique CSS with parent context
        if "css_unique" in base_selectors:
            results.append({
                "type": "css_unique",
                "selector": f"driver.find_element(By.CSS_SELECTOR, '{base_selectors['css_unique']}')",
                "priority": 4,
                "unique": True
            })
        
        # Priority 5: nth-child selector
        if "nth_child" in base_selectors:
            results.append({
                "type": "nth_child",
                "selector": f"driver.find_element(By.CSS_SELECTOR, '{base_selectors['nth_child']}')",
                "priority": 5,
                "unique": True
            })
        
        # Priority 6: Combined attributes
        if "combined" in base_selectors:
            results.append({
                "type": "combined_attrs",
                "selector": f"driver.find_element(By.CSS_SELECTOR, '{base_selectors['combined']}')",
                "priority": 6,
                "unique": True
            })
        
        # Priority 7: Basic CSS (may not be unique)
        if "css" in base_selectors and "css_unique" not in base_selectors:
            results.append({
                "type": "css",
                "selector": f"driver.find_element(By.CSS_SELECTOR, '{base_selectors['css']}')",
                "priority": 7,
                "unique": False
            })
        
        # Priority 8: XPath (optimized)
        if "xpath" in base_selectors:
            results.append({
                "type": "xpath",
                "selector": f"driver.find_element(By.XPATH, '{base_selectors['xpath']}')",
                "priority": 8,
                "unique": True
            })
        
        # Link text for anchor elements
        inner_text = element_data.get("innerText", "").strip()
        if element_data.get("tagName", "").lower() == "a" and inner_text:
            results.append({
                "type": "link_text",
                "selector": f"driver.find_element(By.LINK_TEXT, '{inner_text}')",
                "priority": 3,
                "unique": True
            })
        
        return sorted(results, key=lambda x: x["priority"])


class CypressAdapter:
    """Converts selectors to Cypress format with unique parent-child selectors."""
    
    def convert_selectors(self, base_selectors: Dict[str, Any], element_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Convert to Cypress-specific selectors with uniqueness."""
        results = []
        attrs = element_data.get("attributes", {})
        
        # Priority 1: Data-cy (Cypress convention)
        if "data-cy" in base_selectors:
            results.append({
                "type": "data-cy",
                "selector": f"cy.get('[data-cy=\"{attrs.get('data-cy')}\"]')",
                "priority": 1,
                "unique": True
            })
        
        # Priority 2: Data-testid
        if "data-testid" in base_selectors:
            results.append({
                "type": "data-testid",
                "selector": f"cy.get('[data-testid=\"{attrs.get('data-testid')}\"]')",
                "priority": 1,
                "unique": True
            })
        
        # Priority 3: ID
        if "id" in base_selectors:
            results.append({
                "type": "id",
                "selector": f"cy.get('#{attrs.get('id')}')",
                "priority": 2,
                "unique": True
            })
        
        # Priority 4: Parent-scoped selector (UNIQUE)
        if "parent_scoped" in base_selectors:
            results.append({
                "type": "parent_scoped",
                "selector": f"cy.get('{base_selectors['parent_scoped']}')",
                "priority": 3,
                "unique": True
            })
        
        # Priority 5: Unique CSS with parent context
        if "css_unique" in base_selectors:
            results.append({
                "type": "css_unique",
                "selector": f"cy.get('{base_selectors['css_unique']}')",
                "priority": 4,
                "unique": True
            })
        
        # Priority 6: nth-child for lists
        if "nth_child" in base_selectors:
            nth_selector = base_selectors['nth_child']
            results.append({
                "type": "nth_child",
                "selector": f"cy.get('{nth_selector}')",
                "priority": 5,
                "unique": True
            })
        
        # Priority 7: Combined attributes
        if "combined" in base_selectors:
            results.append({
                "type": "combined_attrs",
                "selector": f"cy.get('{base_selectors['combined']}')",
                "priority": 6,
                "unique": True
            })
        
        # Priority 8: Contains text with parent scope
        inner_text = element_data.get("innerText", "").strip()
        if inner_text:
            # Use within() for scoped text search if parent available
            if "parent_scoped" in base_selectors:
                parent = base_selectors['parent_scoped'].split()[0]
                results.append({
                    "type": "scoped_contains",
                    "selector": f"cy.get('{parent}').contains('{inner_text[:30]}')",
                    "priority": 7,
                    "unique": True
                })
            else:
                results.append({
                    "type": "contains",
                    "selector": f"cy.contains('{inner_text[:30]}')",
                    "priority": 8,
                    "unique": False
                })
        
        # Priority 9: Basic CSS (fallback)
        if "css" in base_selectors and "css_unique" not in base_selectors:
            results.append({
                "type": "css",
                "selector": f"cy.get('{base_selectors['css']}')",
                "priority": 9,
                "unique": False
            })
        
        return sorted(results, key=lambda x: x["priority"])
