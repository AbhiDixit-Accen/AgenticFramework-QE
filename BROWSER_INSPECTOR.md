# QEAF Browser Inspector

A powerful browser element inspection tool that captures web elements and generates stable, framework-specific selectors for test automation.

## Features

✅ **Phase 1: Browser Inspector (JavaScript)** - COMPLETE
- Hover overlay with element highlighting
- Click event interception (capture phase)
- Prevents page navigation during inspection
- Comprehensive element metadata extraction (tag, id, classes, ARIA, XPath, DOM path)

✅ **Phase 2: Python API Layer** - COMPLETE  
- FastAPI server endpoints
- `ElementPayload` schema with Pydantic validation
- `/api/inspect/capture` endpoint for real-time element capture
- Session management and persistence

✅ **Phase 3: Selector Engine (Core Logic)** - COMPLETE
- Priority-based selector generation:
  1. `data-testid`, `data-test`, `data-cy`
  2. ARIA role + accessible name
  3. Unique ID
  4. Stable CSS paths
  5. XPath (fallback)
- Framework-specific adapters:
  - **Playwright** - `page.get_by_test_id()`, `page.get_by_role()`, `page.locator()`
  - **Selenium** - `By.ID`, `By.CSS_SELECTOR`, `By.XPATH`
  - **Cypress** - `cy.get('[data-cy="..."]')`, `cy.contains()`

✅ **Phase 4: Selector Validation** - COMPLETE
- DOM query validation (uniqueness, visibility, count)
- Stability scoring (1-5 scale)
- Ranked selectors by priority

✅ **Phase 5: UI Overlay & Output** - COMPLETE
- In-browser inspector panel
- Framework-tabbed selector display
- One-click copy buttons
- Real-time element highlighting

## Quick Start

### 1. Start the Backend

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the web server (includes inspector API)
qeaf web
```

The API will run on `http://127.0.0.1:8080`

### 2. Open the Demo Page

```bash
# Open the demo HTML in your browser
open examples/inspector_demo.html
```

Or manually navigate to: `file:///path/to/AgenticFramework-QE/examples/inspector_demo.html`

### 3. Activate Inspector

1. Click the **"🎯 Activate Inspector"** button
2. Hover over any element to see the highlight
3. Click an element to capture it
4. View generated selectors in the side panel
5. Click **"Copy"** buttons to copy selectors

## Architecture

```
Browser (JavaScript)
  ↓
  QEAFInspector.activate()
  ↓
Element Click → extractElementMetadata()
  ↓
POST /api/inspect/capture → BrowserInspectorAgent
  ↓
SelectorEngine.generate_selectors()
  ↓
Framework Adapters (Playwright, Selenium, Cypress)
  ↓
Response → Display in Panel with Copy Buttons
```

## API Endpoints

### `POST /api/inspect/capture`
Capture element and generate selectors.

**Request:**
```json
{
  "action": "capture_element",
  "payload": {
    "tagName": "button",
    "id": "submit-btn",
    "attributes": {
      "data-testid": "submit-button",
      "aria-label": "Submit form"
    },
    "classList": ["btn", "btn-primary"],
    "innerText": "Submit",
    "xpath": "//button[@id='submit-btn']",
    "session_id": "demo_123456"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "element_id": "abc123",
    "selectors": [
      {
        "framework": "playwright",
        "selectors": [
          {
            "type": "data-testid",
            "selector": "page.get_by_test_id('submit-button')",
            "priority": 1
          }
        ]
      }
    ]
  }
}
```

### `GET /api/inspect/script`
Get the browser inspector JavaScript code.

### `GET /api/inspect/session/{session_id}`
Retrieve captured elements for a session.

## Integration with Test Generation

The browser inspector **automatically integrates** with QEAF's test generation pipeline:

### Workflow

1. **Capture Elements** - Use browser inspector to capture elements during manual exploration
2. **Elements Stored** - Captured elements are stored in a separate vector DB (isolated from requirements RAG)
3. **Test Script Generation** - When generating test scripts, the system automatically queries the vector DB
4. **Real Selectors Used** - Captured selectors from actual pages are used instead of LLM-generated ones

### How It Works

```python
# 1. User captures elements via browser inspector
# Elements are automatically stored in vector DB at:
# quality_engineering_agentic_framework/utils/rag/elements_vectordb/

# 2. User generates test scripts
# TestScriptGenerator automatically:
# - Extracts element descriptions from test cases (e.g., "login button", "email field")
# - Queries the element vector DB for matching elements
# - Uses real captured selectors instead of generating new ones
# - Includes them in the LLM prompt for accurate test generation

# Example test case:
test_cases = [
    {
        "title": "Login Test",
        "actions": [
            "Click on login button",      # -> Queries DB for "login button"
            "Enter email in email field"  # -> Queries DB for "email field"
        ]
    }
]

# Generated script will use actual selectors like:
# page.get_by_test_id('login-btn')  # From captured element
# page.locator('#email')            # From captured element
```

### Automatic Integration

**No code changes needed!** The integration is automatic:

- ✅ Element capture stores to vector DB automatically
- ✅ Test script generation queries vector DB automatically
- ✅ Real selectors are preferred over generated ones
- ✅ Works across sessions and pages

## Selector Priority Rules

1. **Test Attributes** (Priority 1)
   - `data-testid="..."`
   - `data-test="..."`
   - `data-cy="..."`

2. **ARIA** (Priority 2)
   - `role="button"` + `aria-label="..."`
   - Accessible name matching

3. **Unique ID** (Priority 3)
   - `id="unique-id"`

4. **Name Attribute** (Priority 4)
   - `name="field-name"`

5. **Stable CSS** (Priority 5)
   - Classes without auto-generated patterns
   - Excludes: `css-*`, `sc-*`, `jsx-*`, `makeStyles-*`

6. **XPath** (Priority 6)
   - Absolute or relative XPath

7. **Text Content** (Fallback)
   - Text-based locators for short text

## Framework-Specific Examples

### Playwright
```python
# Data-testid (preferred)
page.get_by_test_id('submit-button')

# Role-based
page.get_by_role('button', name='Submit')

# Text-based
page.get_by_text('Submit')

# CSS locator
page.locator('#submit-btn')
```

### Selenium
```python
# ID
driver.find_element(By.ID, 'submit-btn')

# CSS Selector
driver.find_element(By.CSS_SELECTOR, '[data-testid="submit-button"]')

# XPath
driver.find_element(By.XPATH, '//button[@id="submit-btn"]')
```

### Cypress
```javascript
// Data-cy
cy.get('[data-cy="submit-button"]')

// ID
cy.get('#submit-btn')

// Contains text
cy.contains('Submit')
```

## Vector Database Integration

Elements are stored in a **separate vector database** from the requirements RAG system:

- **Requirements RAG**: `utils/rag/vectordb_*/` - For requirement documents
- **Element Storage**: `utils/rag/elements_vectordb/` - For captured web elements

### Why Separate?

1. **Different use cases** - Requirements for test case generation, elements for test script generation
2. **No interference** - Element captures don't pollute requirement embeddings
3. **Independent scaling** - Can clear/rebuild element DB without affecting requirements
4. **Targeted queries** - Each system queries its own domain-specific data

### Element Storage Features

```python
from quality_engineering_agentic_framework.utils.rag.element_storage import get_element_storage

storage = get_element_storage()

# Store element (happens automatically during capture)
storage.store_element(
    element_data=element_metadata,
    selectors=generated_selectors,
    session_id=session_id,
    page_url=page_url
)

# Query similar elements (happens automatically during test generation)
similar_elements = storage.query_similar_elements(
    query="blue submit button",
    top_k=5
)

# Find elements for specific page
page_elements = storage.get_elements_by_page("https://example.com/login")

# Get session statistics
stats = storage.get_stats()
# Returns: {'status': 'active', 'total_elements': 42, 'db_path': '...'}
```

## Troubleshooting

**Inspector doesn't load:**
- Ensure backend is running: `qeaf web`
- Check API URL in demo page: `window.QEAF_API_URL`
- Open browser console for errors

**Selectors not generated:**
- Check browser console for API errors
- Verify `/api/inspect/capture` endpoint is accessible
- Ensure `BrowserInspectorAgent` import in `endpoints.py`

**CORS errors:**
- Backend has CORS middleware enabled
- If using custom domain, update CORS origins in `endpoints.py`

## Next Steps

- [ ] Add vector DB storage for captured elements
- [ ] Implement LLM-powered selector optimization
- [ ] Create Streamlit UI tab for inspection history
- [ ] Add selector validation via Playwright integration
- [ ] Export captured elements as Page Object files
- [ ] Screenshot capture on element selection
- [ ] Multi-page inspection sessions
- [ ] Selector change detection over time

## Files Created

- `agents/browser_inspector.py` - Main agent with selector engine + framework adapters
- `utils/rag/element_storage.py` - **Separate vector DB for elements** (isolated from requirements RAG)
- `utils/browser_inspector.js` - Browser-side JavaScript for element capture
- `web/api/inspector_endpoints.py` - API endpoints (add to `endpoints.py`)
- `web/api/models.py` - Pydantic models (BrowserInspectorRequest, etc.)
- `examples/inspector_demo.html` - Demo page with test elements
- `BROWSER_INSPECTOR.md` - This documentation

## Contributing

To extend the inspector:

1. **Add new framework adapter** - Edit `browser_inspector.py`, add adapter class
2. **Modify selector priority** - Update `SelectorEngine.priority_order`
3. **Enhance metadata extraction** - Edit `browser_inspector.js` `extractElementMetadata()`
4. **Add new API actions** - Update `BrowserInspectorAgent.process()`
