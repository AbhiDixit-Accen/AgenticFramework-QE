/**
 * QEAF Browser Inspector - Standalone Version
 * Injected into the page to capture element interactions.
 * Can be loaded via script tag or pasted into browser console.
 */

(function() {
    'use strict';
    
    // Prevent double-loading
    if (window.QEAFInspector && window.QEAFInspector.isActive && window.QEAFInspector.isActive()) {
        console.log('QEAF Inspector already active');
        return;
    }
    
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
            return '//*[@id="' + element.id + '"]';
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
            const position = index > 0 ? '[' + (index + 1) + ']' : '';
            parts.unshift(tagName + position);
            
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
        overlay.style.cssText = 
            'position: absolute;' +
            'pointer-events: none;' +
            'border: 2px solid ' + CONFIG.HIGHLIGHT_COLOR + ';' +
            'background: rgba(255, 107, 107, 0.1);' +
            'z-index: ' + CONFIG.OVERLAY_Z_INDEX + ';' +
            'transition: all 0.1s ease;' +
            'box-shadow: 0 0 10px rgba(255, 107, 107, 0.5);';
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
        panel.style.cssText = 
            'position: fixed;' +
            'top: 20px;' +
            'right: 20px;' +
            'width: ' + CONFIG.PANEL_WIDTH + ';' +
            'max-height: 80vh;' +
            'overflow-y: auto;' +
            'background: #1e1e1e;' +
            'color: #ffffff;' +
            'border-radius: 8px;' +
            'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);' +
            'z-index: ' + (CONFIG.OVERLAY_Z_INDEX + 1) + ';' +
            'font-family: Monaco, Menlo, monospace;' +
            'font-size: 12px;' +
            'padding: 16px;';
        
        panel.innerHTML = 
            '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #444; padding-bottom: 8px;">' +
                '<h3 style="margin: 0; font-size: 14px; color: #ff6b6b;">QEAF Inspector</h3>' +
                '<div style="display: flex; gap: 6px;">' +
                    '<button id="qeaf-export-btn" style="background: #28a745; border: none; color: white; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">Export</button>' +
                    '<button id="qeaf-clear-btn" style="background: #6c757d; border: none; color: white; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">Clear</button>' +
                    '<button id="qeaf-close-btn" style="background: #ff6b6b; border: none; color: white; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">Close</button>' +
                '</div>' +
            '</div>' +
            '<div style="background: #2d2d2d; padding: 6px 8px; border-radius: 4px; margin-bottom: 8px;">' +
                '<div style="font-size: 9px; color: #888; margin-bottom: 2px;">Session ID (copy for Streamlit):</div>' +
                '<div style="display: flex; align-items: center; gap: 6px;">' +
                    '<code id="qeaf-session-display" style="font-size: 10px; color: #4ec9b0; word-break: break-all; flex: 1;">' + CONFIG.SESSION_ID + '</code>' +
                    '<button id="qeaf-copy-session" style="background: #007acc; border: none; color: white; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 9px;">Copy</button>' +
                '</div>' +
            '</div>' +
            '<div id="qeaf-capture-count" style="font-size: 11px; color: #4ec9b0; margin-bottom: 8px; font-weight: bold;">Captured: 0 elements</div>' +
            '<div id="qeaf-element-info" style="margin-bottom: 12px; color: #aaa;">' +
                'Hover over elements to inspect' +
            '</div>' +
            '<div id="qeaf-selectors-container" style="display: none;">' +
                '<div style="font-weight: bold; margin-bottom: 8px; color: #fff;">Generated Selectors:</div>' +
                '<div id="qeaf-selectors-list"></div>' +
            '</div>';
        
        document.body.appendChild(panel);
        
        // Close button handler
        panel.querySelector('#qeaf-close-btn').addEventListener('click', function() {
            deactivateInspector();
        });
        
        // Export button handler - downloads captured elements as JSON
        panel.querySelector('#qeaf-export-btn').addEventListener('click', function() {
            var elements = getLocalElements();
            if (elements.length === 0) {
                showNotification('No elements to export');
                return;
            }
            
            var exportData = {
                session_id: CONFIG.SESSION_ID,
                url: window.location.href,
                exported_at: new Date().toISOString(),
                elements: elements
            };
            
            var blob = new Blob([JSON.stringify(exportData, null, 2)], {type: 'application/json'});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'qeaf_elements_' + CONFIG.SESSION_ID + '.json';
            a.click();
            URL.revokeObjectURL(url);
            
            showNotification('Exported ' + elements.length + ' elements');
        });
        
        // Clear button handler
        panel.querySelector('#qeaf-clear-btn').addEventListener('click', function() {
            localStorage.removeItem('qeaf_captured_elements');
            var countDiv = document.getElementById('qeaf-capture-count');
            if (countDiv) countDiv.textContent = 'Captured: 0 elements';
            showNotification('Cleared all captured elements');
        });
        
        // Copy session ID button handler
        panel.querySelector('#qeaf-copy-session').addEventListener('click', function() {
            var btn = this;
            navigator.clipboard.writeText(CONFIG.SESSION_ID).then(function() {
                btn.textContent = '✓';
                setTimeout(function() { btn.textContent = 'Copy'; }, 1500);
            });
        });
        
        // Update count
        var localCount = getLocalElements().length;
        var countDiv = panel.querySelector('#qeaf-capture-count');
        if (countDiv && localCount > 0) {
            countDiv.textContent = 'Captured: ' + localCount + ' elements (local)';
        }
        
        return panel;
    }
    
    function updateInspectorPanel(elementData, selectors) {
        if (!state.inspectorPanel) {
            state.inspectorPanel = createInspectorPanel();
        }
        
        // Update capture count
        var localCount = getLocalElements().length;
        var countDiv = state.inspectorPanel.querySelector('#qeaf-capture-count');
        if (countDiv) {
            countDiv.textContent = 'Captured: ' + localCount + ' elements' + (localCount > 0 ? ' (local)' : '');
        }
        
        const infoDiv = state.inspectorPanel.querySelector('#qeaf-element-info');
        const selectorsContainer = state.inspectorPanel.querySelector('#qeaf-selectors-container');
        const selectorsList = state.inspectorPanel.querySelector('#qeaf-selectors-list');
        
        // Update element info
        let infoHtml = '<div style="margin-bottom: 8px;">' +
            '<strong>&lt;' + elementData.tagName + '&gt;</strong>';
        if (elementData.id) {
            infoHtml += ' <span style="color: #4ec9b0;">#' + elementData.id + '</span>';
        }
        infoHtml += '</div>';
        
        if (elementData.classList && elementData.classList.length > 0) {
            infoHtml += '<div style="font-size: 10px; color: #888; margin-bottom: 4px;">';
            infoHtml += elementData.classList.slice(0, 3).map(function(c) { return '.' + c; }).join(' ');
            infoHtml += '</div>';
        }
        
        if (elementData.innerText) {
            infoHtml += '<div style="font-size: 10px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' +
                elementData.innerText.substring(0, 50) + '</div>';
        }
        
        infoDiv.innerHTML = infoHtml;
        
        // Update selectors
        if (selectors && selectors.length > 0) {
            selectorsContainer.style.display = 'block';
            
            let selectorsHtml = '';
            selectors.forEach(function(framework) {
                selectorsHtml += '<div style="margin-bottom: 16px;">';
                selectorsHtml += '<div style="color: #569cd6; font-weight: bold; margin-bottom: 8px;">' + 
                    framework.framework.toUpperCase() + '</div>';
                
                framework.selectors.forEach(function(sel) {
                    const escapedSelector = sel.selector.replace(/"/g, '&quot;');
                    selectorsHtml += '<div style="background: #2d2d2d; padding: 8px; margin-bottom: 6px; border-radius: 4px; position: relative;">';
                    selectorsHtml += '<div style="color: #888; font-size: 10px; margin-bottom: 4px;">' + sel.type + '</div>';
                    selectorsHtml += '<code style="color: #ce9178; font-size: 11px; word-break: break-all; display: block; margin-bottom: 6px;">' + sel.selector + '</code>';
                    selectorsHtml += '<button class="qeaf-copy-btn" data-selector="' + escapedSelector + '" style="background: #007acc; border: none; color: white; padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 10px;">Copy</button>';
                    selectorsHtml += '</div>';
                });
                
                selectorsHtml += '</div>';
            });
            
            selectorsList.innerHTML = selectorsHtml;
            
            // Add copy button handlers
            selectorsList.querySelectorAll('.qeaf-copy-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    const selector = this.getAttribute('data-selector');
                    const button = this;
                    navigator.clipboard.writeText(selector).then(function() {
                        button.textContent = '✓ Copied!';
                        setTimeout(function() { button.textContent = 'Copy'; }, 1500);
                    });
                });
            });
        }
    }
    
    // ============================================
    // API Communication with CSP Fallback
    // ============================================
    
    // Local storage for elements when CSP blocks API calls
    function getLocalElements() {
        try {
            var stored = localStorage.getItem('qeaf_captured_elements');
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            return [];
        }
    }
    
    function saveLocalElement(elementData, selectors) {
        try {
            var elements = getLocalElements();
            elements.push({
                element: elementData,
                selectors: selectors || [],
                capturedAt: new Date().toISOString()
            });
            localStorage.setItem('qeaf_captured_elements', JSON.stringify(elements));
            return elements.length;
        } catch (e) {
            console.error('QEAF: Failed to save locally:', e);
            return 0;
        }
    }
    
    function generateLocalSelectors(elementData) {
        // Generate basic selectors locally when API is blocked
        var selectors = [];
        var attrs = elementData.attributes || {};
        var tagName = elementData.tagName || 'div';
        
        // Test attributes
        if (attrs['data-testid']) {
            selectors.push({ type: 'data-testid', selector: "[data-testid='" + attrs['data-testid'] + "']", priority: 1 });
        }
        if (attrs['data-cy']) {
            selectors.push({ type: 'data-cy', selector: "[data-cy='" + attrs['data-cy'] + "']", priority: 1 });
        }
        
        // ID
        if (elementData.id) {
            selectors.push({ type: 'id', selector: '#' + elementData.id, priority: 2 });
        }
        
        // Name
        if (attrs.name) {
            selectors.push({ type: 'name', selector: "[name='" + attrs.name + "']", priority: 3 });
        }
        
        // ARIA
        var ariaLabel = (elementData.ariaInfo && elementData.ariaInfo.label) || attrs['aria-label'];
        if (ariaLabel) {
            selectors.push({ type: 'aria-label', selector: "[aria-label='" + ariaLabel + "']", priority: 4 });
        }
        
        // CSS with classes
        var classList = elementData.classList || [];
        if (classList.length > 0) {
            var stableClasses = classList.filter(function(c) {
                return !/css-|sc-|jsx-|emotion-|\d{5,}/.test(c);
            }).slice(0, 2);
            if (stableClasses.length > 0) {
                selectors.push({ type: 'css', selector: tagName + '.' + stableClasses.join('.'), priority: 5 });
            }
        }
        
        // XPath
        if (elementData.xpath) {
            selectors.push({ type: 'xpath', selector: elementData.xpath, priority: 6 });
        }
        
        // DOM path based
        if (elementData.domPath) {
            selectors.push({ type: 'css_path', selector: elementData.domPath, priority: 7 });
        }
        
        return [
            { framework: 'playwright', selectors: selectors.map(function(s) { 
                return { type: s.type, selector: "page.locator('" + s.selector + "')", priority: s.priority }; 
            })},
            { framework: 'selenium', selectors: selectors.map(function(s) { 
                var by = s.type === 'id' ? 'ID' : s.type === 'xpath' ? 'XPATH' : 'CSS_SELECTOR';
                var val = s.type === 'id' ? elementData.id : s.selector;
                return { type: s.type, selector: "driver.find_element(By." + by + ", '" + val + "')", priority: s.priority }; 
            })},
            { framework: 'cypress', selectors: selectors.map(function(s) { 
                return { type: s.type, selector: "cy.get('" + s.selector + "')", priority: s.priority }; 
            })}
        ];
    }
    
    async function sendElementToBackend(elementData) {
        try {
            const response = await fetch(CONFIG.API_URL + '/api/inspect/capture', {
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
                throw new Error('HTTP error! status: ' + response.status);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.warn('QEAF Inspector: API blocked (CSP), using local storage:', error.message);
            
            // Generate selectors locally
            var localSelectors = generateLocalSelectors(elementData);
            var count = saveLocalElement(elementData, localSelectors);
            
            // Show notification
            showNotification('Element saved locally (' + count + ' total). Use Export to get data.');
            
            return {
                success: true,
                data: { selectors: localSelectors },
                selectors: localSelectors,
                local: true
            };
        }
    }
    
    function showNotification(message) {
        var existing = document.getElementById('qeaf-notification');
        if (existing) existing.remove();
        
        var notif = document.createElement('div');
        notif.id = 'qeaf-notification';
        notif.style.cssText = 'position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); ' +
            'background: #ff9800; color: #000; padding: 10px 20px; border-radius: 4px; z-index: 1000000; ' +
            'font-family: sans-serif; font-size: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);';
        notif.textContent = message;
        document.body.appendChild(notif);
        
        setTimeout(function() { notif.remove(); }, 4000);
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
        console.log('QEAF Inspector: Capturing element', elementData.tagName, elementData.id || '(no id)');
        
        // Send to backend and get selectors
        sendElementToBackend(elementData).then(function(result) {
            console.log('QEAF Inspector: Backend response', result);
            if (result && result.data && result.data.selectors) {
                state.currentSelectors = result.data.selectors;
                state.captureCount = (state.captureCount || 0) + 1;
                
                // Update counter in panel
                var countDiv = document.getElementById('qeaf-capture-count');
                if (countDiv) {
                    countDiv.textContent = 'Captured: ' + state.captureCount + ' elements (Session: ' + (result.data.session_id || 'unknown').substring(0, 8) + '...)';
                    countDiv.style.color = '#4ec9b0';
                }
                
                updateInspectorPanel(elementData, result.data.selectors);
            } else if (result && result.selectors) {
                // Old response format fallback
                state.currentSelectors = result.selectors;
                updateInspectorPanel(elementData, result.selectors);
            } else {
                console.error('QEAF Inspector: Invalid response format', result);
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
        isActive: function() { return state.isActive; },
        getSelectedElement: function() { return state.selectedElement; },
        getCurrentSelectors: function() { return state.currentSelectors; },
        extractMetadata: extractElementMetadata
    };
    
    // Auto-activate if configured
    if (window.QEAF_AUTO_ACTIVATE) {
        activateInspector();
    }
    
    console.log('QEAF Inspector loaded. Use window.QEAFInspector.activate() to start inspecting.');
})();
