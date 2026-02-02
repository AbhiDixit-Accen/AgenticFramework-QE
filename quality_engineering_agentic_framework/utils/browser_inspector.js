/**
 * Browser Inspector JavaScript
 * Injected into the page to capture element interactions.
 * Can be pasted directly into browser console or injected via automation tools.
 */

const QEAF_INSPECTOR_JS = `
(function() {
    'use strict';
    
    // ============================================
    // Configuration
    // ============================================
    const CONFIG = {
        API_URL: window.QEAF_API_URL || 'http://127.0.0.1:8080',
        SESSION_ID: window.QEAF_SESSION_ID || 'session_' + Date.now(),
        OVERLAY_Z_INDEX: 999999,
        HIGHLIGHT_COLOR: '#ff6b6b',
        PANEL_WIDTH: '400px'
    };
    const LLM_CONFIG = window.QEAF_LLM_CONFIG || null;
    
    // ============================================
    // State Management
    // ============================================
    const state = {
        isActive: false,
        hoveredElement: null,
        selectedElement: null,
        currentSelectors: [],
        highlightOverlay: null,
        inspectorPanel: null
    };
    
    // ============================================
    // Element Metadata Extraction
    // ============================================
    function extractElementMetadata(element) {
        // Get all attributes
        const attributes = {};
        for (const attr of element.attributes) {
            attributes[attr.name] = attr.value;
        }
        
        // Get class list
        const classList = Array.from(element.classList);
        
        // Generate XPath
        const xpath = getXPath(element);
        
        // Get DOM path (parent chain)
        const domPath = getDOMPath(element);
        
        // Get ARIA information
        const ariaInfo = {
            role: element.getAttribute('role') || element.getAttribute('aria-role'),
            label: element.getAttribute('aria-label'),
            labelledby: element.getAttribute('aria-labelledby'),
            describedby: element.getAttribute('aria-describedby')
        };
        
        // Get computed styles (for visibility checks)
        const computedStyle = window.getComputedStyle(element);
        const isVisible = computedStyle.display !== 'none' && 
                         computedStyle.visibility !== 'hidden' &&
                         computedStyle.opacity !== '0';
        
        return {
            tagName: element.tagName.toLowerCase(),
            id: element.id || null,
            classList: classList,
            attributes: attributes,
            innerText: element.innerText ? element.innerText.substring(0, 200) : null,
            textContent: element.textContent ? element.textContent.substring(0, 200) : null,
            value: element.value || null,
            href: element.href || null,
            src: element.src || null,
            xpath: xpath,
            domPath: domPath,
            ariaInfo: ariaInfo,
            isVisible: isVisible,
            boundingRect: element.getBoundingClientRect().toJSON(),
            url: window.location.href,
            session_id: CONFIG.SESSION_ID,
            timestamp: new Date().toISOString()
        };
    }
    
    function getXPath(element) {
        if (element.id) {
            return \`//*[@id="\${element.id}"]\`;
        }
        
        const parts = [];
        let current = element;
        
        while (current && current.nodeType === Node.ELEMENT_NODE) {
            let index = 0;
            let sibling = current.previousSibling;
            
            while (sibling) {
                if (sibling.nodeType === Node.ELEMENT_NODE && 
                    sibling.nodeName === current.nodeName) {
                    index++;
                }
                sibling = sibling.previousSibling;
            }
            
            const tagName = current.nodeName.toLowerCase();
            const position = index > 0 ? \`[\${index + 1}]\` : '';
            parts.unshift(\`\${tagName}\${position}\`);
            
            current = current.parentNode;
        }
        
        return parts.length ? '/' + parts.join('/') : null;
    }
    
    function getDOMPath(element) {
        const path = [];
        let current = element;
        
        while (current && current !== document.body) {
            let selector = current.tagName.toLowerCase();
            
            if (current.id) {
                selector += '#' + current.id;
            } else if (current.className) {
                const classes = Array.from(current.classList).slice(0, 2);
                if (classes.length > 0) {
                    selector += '.' + classes.join('.');
                }
            }
            
            path.unshift(selector);
            current = current.parentElement;
        }
        
        return path.join(' > ');
    }
    
    // ============================================
    // Hover Overlay Management
    // ============================================
    function createHighlightOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'qeaf-highlight-overlay';
        overlay.style.cssText = \`
            position: absolute;
            pointer-events: none;
            border: 2px solid \${CONFIG.HIGHLIGHT_COLOR};
            background: rgba(255, 107, 107, 0.1);
            z-index: \${CONFIG.OVERLAY_Z_INDEX};
            transition: all 0.1s ease;
            box-shadow: 0 0 10px rgba(255, 107, 107, 0.5);
        \`;
        document.body.appendChild(overlay);
        return overlay;
    }
    
    function updateHighlight(element) {
        if (!state.highlightOverlay) {
            state.highlightOverlay = createHighlightOverlay();
        }
        
        const rect = element.getBoundingClientRect();
        const overlay = state.highlightOverlay;
        
        overlay.style.left = (rect.left + window.scrollX) + 'px';
        overlay.style.top = (rect.top + window.scrollY) + 'px';
        overlay.style.width = rect.width + 'px';
        overlay.style.height = rect.height + 'px';
        overlay.style.display = 'block';
    }
    
    function hideHighlight() {
        if (state.highlightOverlay) {
            state.highlightOverlay.style.display = 'none';
        }
    }
    
    // ============================================
    // Inspector Panel UI
    // ============================================
    function createInspectorPanel() {
        const panel = document.createElement('div');
        panel.id = 'qeaf-inspector-panel';
        panel.style.cssText = \`
            position: fixed;
            top: 20px;
            right: 20px;
            width: \${CONFIG.PANEL_WIDTH};
            max-height: 80vh;
            overflow-y: auto;
            background: #1e1e1e;
            color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            z-index: \${CONFIG.OVERLAY_Z_INDEX + 1};
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            padding: 16px;
        \`;
        
        panel.innerHTML = \`
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #444; padding-bottom: 8px;">
                <h3 style="margin: 0; font-size: 14px; color: #ff6b6b;">QEAF Inspector</h3>
                <button id="qeaf-close-btn" style="background: #ff6b6b; border: none; color: white; padding: 4px 12px; border-radius: 4px; cursor: pointer;">Close</button>
            </div>
            <div id="qeaf-element-info" style="margin-bottom: 12px; color: #aaa;">
                Hover over elements to inspect
            </div>
            <div id="qeaf-selectors-container" style="display: none;">
                <div style="font-weight: bold; margin-bottom: 8px; color: #fff;">Generated Selectors:</div>
                <div id="qeaf-selectors-list"></div>
            </div>
        \`;
        
        document.body.appendChild(panel);
        
        // Close button handler
        panel.querySelector('#qeaf-close-btn').addEventListener('click', () => {
            deactivateInspector();
        });
        
        return panel;
    }
    
    function updateInspectorPanel(elementData, selectors) {
        if (!state.inspectorPanel) {
            state.inspectorPanel = createInspectorPanel();
        }
        
        const infoDiv = state.inspectorPanel.querySelector('#qeaf-element-info');
        const selectorsContainer = state.inspectorPanel.querySelector('#qeaf-selectors-container');
        const selectorsList = state.inspectorPanel.querySelector('#qeaf-selectors-list');
        
        // Update element info
        infoDiv.innerHTML = \`
            <div style="margin-bottom: 8px;">
                <strong>&lt;\${elementData.tagName}&gt;</strong>
                \${elementData.id ? \` <span style="color: #4ec9b0;">#\${elementData.id}</span>\` : ''}
            </div>
            <div style="font-size: 10px; color: #888; margin-bottom: 4px;">
                \${elementData.classList.slice(0, 3).map(c => \`.\${c}\`).join(' ')}
            </div>
            \${elementData.innerText ? \`<div style="font-size: 10px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">\${elementData.innerText.substring(0, 50)}</div>\` : ''}
        \`;
        
        // Update selectors
        if (selectors && selectors.length > 0) {
            selectorsContainer.style.display = 'block';
            selectorsList.innerHTML = selectors.map(framework => \`
                <div style="margin-bottom: 16px;">
                    <div style="color: #569cd6; font-weight: bold; margin-bottom: 8px;">\${framework.framework.toUpperCase()}</div>
                    \${framework.selectors.map(sel => \`
                        <div style="background: #2d2d2d; padding: 8px; margin-bottom: 6px; border-radius: 4px; position: relative;">
                            <div style="color: #888; font-size: 10px; margin-bottom: 4px;">\${sel.type}</div>
                            <code style="color: #ce9178; font-size: 11px; word-break: break-all; display: block; margin-bottom: 6px;">\${sel.selector}</code>
                            <button class="qeaf-copy-btn" data-selector="\${sel.selector.replace(/"/g, '&quot;')}" style="background: #007acc; border: none; color: white; padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 10px;">Copy</button>
                        </div>
                    \`).join('')}
                </div>
            \`).join('');
            
            // Add copy button handlers
            selectorsList.querySelectorAll('.qeaf-copy-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const selector = this.getAttribute('data-selector');
                    navigator.clipboard.writeText(selector).then(() => {
                        this.textContent = '✓ Copied!';
                        setTimeout(() => { this.textContent = 'Copy'; }, 1500);
                    });
                });
            });
        }
    }
    
    // ============================================
    // API Communication
    // ============================================
    async function sendElementToBackend(elementData) {
        try {
            const response = await fetch(\`\${CONFIG.API_URL}/api/inspect/capture\`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'capture_element',
                    payload: elementData,
                    llm_config: LLM_CONFIG
                })
            });
            
            if (!response.ok) {
                throw new Error(\`HTTP error! status: \${response.status}\`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('QEAF Inspector: Failed to send element data:', error);
            return null;
        }
    }
    
    // ============================================
    // Event Handlers
    // ============================================
    function handleMouseMove(event) {
        if (!state.isActive) return;
        
        // Prevent inspecting our own UI
        if (event.target.closest('#qeaf-inspector-panel') || 
            event.target.id === 'qeaf-highlight-overlay') {
            return;
        }
        
        state.hoveredElement = event.target;
        updateHighlight(event.target);
    }
    
    function handleClick(event) {
        if (!state.isActive) return;
        
        // Prevent inspecting our own UI
        if (event.target.closest('#qeaf-inspector-panel') || 
            event.target.id === 'qeaf-highlight-overlay') {
            return;
        }
        
        // Prevent default action and stop propagation
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        
        state.selectedElement = event.target;
        
        // Extract metadata
        const elementData = extractElementMetadata(event.target);
        
        // Send to backend and get selectors
        sendElementToBackend(elementData).then(result => {
            if (result && result.selectors) {
                state.currentSelectors = result.selectors;
                updateInspectorPanel(elementData, result.selectors);
            }
        });
        
        return false;
    }
    
    function handleKeyPress(event) {
        // ESC to deactivate
        if (event.key === 'Escape') {
            deactivateInspector();
        }
    }
    
    // ============================================
    // Activation/Deactivation
    // ============================================
    function activateInspector() {
        if (state.isActive) return;
        
        state.isActive = true;
        state.inspectorPanel = createInspectorPanel();
        
        // Add event listeners (capture phase for click to intercept before page handlers)
        document.addEventListener('mousemove', handleMouseMove, true);
        document.addEventListener('click', handleClick, true);
        document.addEventListener('keydown', handleKeyPress, true);
        
        // Change cursor
        document.body.style.cursor = 'crosshair';
        
        console.log('QEAF Inspector activated');
    }
    
    function deactivateInspector() {
        if (!state.isActive) return;
        
        state.isActive = false;
        
        // Remove event listeners
        document.removeEventListener('mousemove', handleMouseMove, true);
        document.removeEventListener('click', handleClick, true);
        document.removeEventListener('keydown', handleKeyPress, true);
        
        // Remove UI elements
        hideHighlight();
        if (state.highlightOverlay) {
            state.highlightOverlay.remove();
            state.highlightOverlay = null;
        }
        if (state.inspectorPanel) {
            state.inspectorPanel.remove();
            state.inspectorPanel = null;
        }
        
        // Reset cursor
        document.body.style.cursor = '';
        
        console.log('QEAF Inspector deactivated');
    }
    
    // ============================================
    // Public API
    // ============================================
    window.QEAFInspector = {
        activate: activateInspector,
        deactivate: deactivateInspector,
        isActive: () => state.isActive,
        getSelectedElement: () => state.selectedElement,
        getCurrentSelectors: () => state.currentSelectors,
        extractMetadata: extractElementMetadata
    };
    
    // Auto-activate if configured
    if (window.QEAF_AUTO_ACTIVATE) {
        activateInspector();
    }
    
    console.log('QEAF Inspector loaded. Use window.QEAFInspector.activate() to start inspecting.');
})();
`;

// For Node.js/module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QEAF_INSPECTOR_JS;
}

// For browser console usage (paste the content of QEAF_INSPECTOR_JS variable)
if (typeof window !== 'undefined') {
    window.QEAF_INSPECTOR_CODE = QEAF_INSPECTOR_JS;
}
