# Browser Inspector + Test Generation Integration

## Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: ELEMENT CAPTURE                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │  Open demo page      │
                     │  Click "Activate"    │
                     │  Click elements      │
                     └──────────────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │  browser_inspector.js│
                     │  - Hover overlay     │
                     │  - Extract metadata  │
                     │  - Send to backend   │
                     └──────────────────────┘
                                 │
                                 ▼
                     POST /api/inspect/capture
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │ BrowserInspectorAgent│
                     │ - Generate selectors │
                     │ - All frameworks     │
                     └──────────────────────┘
                                 │
                                 ▼
            ┌────────────────────┴────────────────────┐
            │                                          │
            ▼                                          ▼
  ┌─────────────────┐                    ┌─────────────────────┐
  │ Session Storage │                    │ Vector DB Storage   │
  │ (In-memory)     │                    │ elements_vectordb/  │
  │ For UI panel    │                    │ SEPARATE FROM RAG   │
  └─────────────────┘                    └─────────────────────┘
                                                    │
                                                    │
┌───────────────────────────────────────────────────┘
│
│
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 2: TEST SCRIPT GENERATION                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │  User creates test   │
                     │  cases with actions: │
                     │  "Click login button"│
                     └──────────────────────┘
                                 │
                                 ▼
                 POST /api/test-script-generation
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │ TestScriptGenerator  │
                     │ use_captured=TRUE    │
                     └──────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────┐
              │ 1. Extract element descriptions  │
              │    from test case actions        │
              │    Example: "login button"       │
              └──────────────────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────┐
              │ 2. Query element_storage.py      │
              │    find_element_by_description() │
              │    Uses SEPARATE vector DB       │
              └──────────────────────────────────┘
                                 │
                                 ▼
                     ┌────────────────────┐
                     │   Vector DB Query  │
                     │   Semantic search  │
                     │   Top-k results    │
                     └────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────┐
              │ 3. Match elements with selectors │
              │    "login button" →              │
              │    page.get_by_testid('login')   │
              └──────────────────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────┐
              │ 4. Inject into LLM prompt        │
              │    "Use these actual selectors:" │
              │    {captured_elements_info}      │
              └──────────────────────────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │   LLM generates      │
                     │   test scripts using │
                     │   REAL selectors     │
                     └──────────────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │   Generated scripts  │
                     │   with validated     │
                     │   selectors from     │
                     │   actual page!       │
                     └──────────────────────┘
```

## Key Points

### Separation of Concerns

**Requirements RAG** (`vectordb_*/`)
- Stores requirement documents (.txt, .pdf, .docx)
- Used by TestCaseGenerationAgent
- Synthesizes product context for test cases
- Vector DB location: `utils/rag/vectordb_*/`

**Element Storage** (`elements_vectordb/`)
- Stores captured web elements
- Used by TestScriptGenerator
- Provides real selectors for test scripts
- Vector DB location: `utils/rag/elements_vectordb/`
- **Completely isolated** - no cross-contamination

### Automatic Integration

No manual intervention required:

1. **Capture elements** → Automatically stored in vector DB
2. **Generate test scripts** → Automatically queries vector DB
3. **Real selectors used** → No hallucinated locators

### Example Flow

```
User Action:
1. Opens examples/inspector_demo.html
2. Activates inspector
3. Clicks on "Submit Form" button
   → Element captured with data-testid="submit-button"
   → Stored in elements_vectordb/

Later...

4. Creates test case:
   {
     "title": "Submit Form Test",
     "actions": ["Click on submit button"]
   }

5. Generates test script
   → TestScriptGenerator extracts "submit button"
   → Queries elements_vectordb/ 
   → Finds captured element with data-testid="submit-button"
   → LLM receives: "Use selector: page.get_by_test_id('submit-button')"
   → Generated script uses REAL selector!
```

## Benefits

✅ **No hallucinated selectors** - Uses actual page elements
✅ **Framework-specific** - Selectors match target framework (Playwright/Selenium/Cypress)
✅ **Validated** - Elements captured from real browser
✅ **Persistent** - Survives across sessions
✅ **Intelligent** - Semantic search finds best matches
✅ **Isolated** - Doesn't interfere with requirements RAG
