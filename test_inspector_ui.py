#!/usr/bin/env python3
"""
Quick test to verify the inspector popup UI is properly integrated.
This script checks if the necessary components are in place.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_ui_components():
    """Check if all inspector UI components are present in app.py."""
    
    app_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'quality_engineering_agentic_framework',
        'web',
        'ui',
        'app.py'
    )
    
    if not os.path.exists(app_path):
        print("❌ app.py not found!")
        return False
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "Inspector button": '🔍 Inspector',
        "Session state init": 'show_inspector_popup',
        "Popup function": 'def render_inspector_popup',
        "Dialog decorator": '@st.dialog',
        "Inspector dialog call": 'inspector_dialog()',
        "Close button": 'Close Inspector',
        "Load elements button": 'Load Captured Elements',
        "Refresh button": 'refresh_elements',
        "Session ID": 'inspector_session_id',
        "API call to get script": '/api/inspect/script',
        "API call to get session": '/api/inspect/session',
    }
    
    results = {}
    for name, check in checks.items():
        results[name] = check in content
    
    print("\n🔍 Inspector UI Component Checks:\n")
    all_passed = True
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*50)
    
    if all_passed:
        print("✅ All inspector UI components are properly integrated!")
    else:
        print("❌ Some components are missing. Please check the implementation.")
    
    return all_passed

def check_api_endpoints():
    """Check if inspector API endpoints exist."""
    
    inspector_endpoints_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'quality_engineering_agentic_framework',
        'web',
        'api',
        'inspector_endpoints.py'
    )
    
    if not os.path.exists(inspector_endpoints_path):
        print("\n⚠️  inspector_endpoints.py not found - endpoints might be in main endpoints.py")
        return False
    
    with open(inspector_endpoints_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    endpoints = [
        '/api/inspect/capture',
        '/api/inspect/script',
        '/api/inspect/session',
    ]
    
    print("\n🔌 API Endpoint Checks:\n")
    all_found = True
    for endpoint in endpoints:
        found = endpoint in content
        status = "✅" if found else "❌"
        print(f"{status} {endpoint}")
        if not found:
            all_found = False
    
    return all_found

def main():
    """Run all checks."""
    print("="*50)
    print("QEAF Browser Inspector UI Integration Test")
    print("="*50)
    
    ui_ok = check_ui_components()
    api_ok = check_api_endpoints()
    
    print("\n" + "="*50)
    print("OVERALL STATUS")
    print("="*50)
    
    if ui_ok and api_ok:
        print("✅ ALL CHECKS PASSED! Inspector is ready to use.")
        print("\nTo test:")
        print("1. Run: qeaf web")
        print("2. Navigate to Test Script Generation tab")
        print("3. Click the '🔍 Inspector' button")
        print("4. Follow the popup instructions")
        return 0
    elif ui_ok:
        print("✅ UI components OK")
        print("⚠️  API endpoints need verification")
        return 1
    else:
        print("❌ UI integration incomplete")
        return 1

if __name__ == "__main__":
    sys.exit(main())
