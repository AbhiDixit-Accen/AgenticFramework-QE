# Browser Inspector UI Guide

## Overview

The Browser Element Inspector is now integrated into the Test Script Generation tab with a popup modal interface. This allows you to capture web elements directly from your application and use them automatically in test script generation.

## How to Use

### Step 1: Open the Inspector

1. Navigate to the **Test Script Generation** tab
2. Click the **🔍 Inspector** button in the top right corner
3. A popup modal will appear with the inspector interface

### Step 2: Capture Elements

**Option A: Use Demo Page**
```bash
# Open the demo page in your browser
open examples/inspector_demo.html
```

**Option B: Use Your Own Application**
1. Open your web application in a browser
2. Open browser DevTools (F12 or Right-click → Inspect)
3. Go to the **Console** tab

### Step 3: Activate Inspector

1. In the popup modal, copy the JavaScript code shown
2. Paste it into your browser's console
3. Press Enter to execute
4. Click the "Activate Inspector" button that appears on the page
5. Hover over elements to see them highlighted
6. Click on elements to capture them

### Step 4: View Captured Elements

1. In the popup modal, click **"🔍 Load Captured Elements"**
2. See a table showing all captured elements with:
   - Tag name
   - ID attribute
   - Text content
   - Best selector
   - Timestamp

### Step 5: Close Inspector

1. When done capturing, click **"✅ Close Inspector"**
2. The popup will close
3. Captured elements are now stored and ready for use

## Features

### Inspector Popup Modal

- **Large Dialog**: Provides ample space for instructions and element viewing
- **Session Management**: Each session has a unique ID for tracking
- **Element Counter**: Shows how many elements have been captured
- **Refresh Button**: Update element count in real-time
- **Collapsible Sections**: Instructions and demo info are expandable

### Captured Element Display

The table shows:
- **Tag**: HTML element type (button, input, etc.)
- **ID**: Element's ID attribute if present
- **Text**: First 50 characters of element's text
- **Selector**: Primary Playwright selector (truncated to 60 chars)
- **Timestamp**: When the element was captured

### Automatic Integration

When you generate test scripts:
1. TestScriptGenerator automatically queries the element vector DB
2. Extracts element descriptions from test case actions
3. Matches captured elements using semantic search
4. Injects real selectors into the LLM prompt
5. Generated scripts use actual page selectors (no hallucinations!)

## Inspector Code Injection

The popup automatically:
- Fetches the latest browser inspector JavaScript
- Injects the current session ID
- Configures the API base URL
- Provides code ready to paste into browser console

## Example Workflow

```
1. User clicks "🔍 Inspector" button
   ↓
2. Popup modal opens with instructions
   ↓
3. User copies JavaScript code
   ↓
4. User pastes in browser console on their app
   ↓
5. Inspector activates with overlay UI
   ↓
6. User clicks elements (button, input, link, etc.)
   ↓
7. Elements captured and sent to backend
   ↓
8. User clicks "Load Captured Elements" to verify
   ↓
9. User clicks "Close Inspector"
   ↓
10. Elements now available for test generation!
```

## Session State Variables

The inspector uses these Streamlit session variables:

```python
st.session_state.show_inspector_popup      # Boolean: Show/hide popup
st.session_state.inspector_session_id      # String: Unique session UUID
st.session_state.captured_elements_count   # Integer: Number of elements
```

## API Endpoints Used

- `GET /api/inspect/script` - Fetch inspector JavaScript
- `GET /api/inspect/session/{session_id}` - Get captured elements
- `POST /api/inspect/capture` - Store captured element (called by browser JS)

## Tips

### Best Practices

1. **Capture key elements first**: Login buttons, main navigation, critical inputs
2. **Use meaningful text**: Elements with clear text are easier to match
3. **Prefer data-testid**: If your app has test attributes, they'll be prioritized
4. **Session persistence**: Elements persist across page refreshes until you close the popup

### Troubleshooting

**"No elements captured yet"**
- Make sure you pasted the JavaScript in the console
- Click "Activate Inspector" button on the page
- Ensure you're clicking visible elements

**"Failed to load elements"**
- Check that the backend is running (port 8080)
- Verify API_URL is correct
- Try clicking "Refresh" button

**Elements not showing in table**
- Click "🔍 Load Captured Elements" button
- Wait a few seconds after capturing
- Check browser console for errors

## Next Steps

After capturing elements:
1. Go to **Test Case Generation** tab (optional)
2. Generate test cases for your app
3. Return to **Test Script Generation** tab
4. Generate scripts → They'll automatically use captured elements!

## Files Modified

- [quality_engineering_agentic_framework/web/ui/app.py](quality_engineering_agentic_framework/web/ui/app.py)
  - Added `show_inspector_popup` session state
  - Added "Inspector" button in Test Script Generation tab
  - Added `render_inspector_popup()` function with modal dialog
  - Integrated with API endpoints for element retrieval

## Related Documentation

- [BROWSER_INSPECTOR.md](BROWSER_INSPECTOR.md) - Complete inspector architecture
- [INTEGRATION_WORKFLOW.md](INTEGRATION_WORKFLOW.md) - Element storage + test generation flow
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - AI agent guide
