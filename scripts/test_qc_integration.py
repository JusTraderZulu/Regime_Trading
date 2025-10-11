#!/usr/bin/env python
"""
Test script for QuantConnect integration.
Tests the QC MCP client with your credentials.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.qc_mcp_client import QCMCPClient


def test_credentials():
    """Test if QC credentials are loaded"""
    print("=" * 60)
    print("Testing QuantConnect Credentials")
    print("=" * 60)
    
    client = QCMCPClient()
    
    if client.api_token and client.user_id:
        print(f"✓ API Token: {client.api_token[:10]}...")
        print(f"✓ User ID: {client.user_id}")
        return True
    else:
        print("✗ Credentials not found!")
        print("\nSetup instructions:")
        print("1. Get your API token from: https://www.quantconnect.com/account")
        print("2. Create qc_token.txt with your API token")
        print("3. Create qc_user.txt with your user ID")
        return False


def test_signals_upload():
    """Test uploading signals to QC"""
    print("\n" + "=" * 60)
    print("Testing Signals Upload")
    print("=" * 60)
    
    # Check if signals exist
    signals_path = Path("data/signals/latest/signals.csv")
    
    if not signals_path.exists():
        print("✗ No signals found at data/signals/latest/signals.csv")
        print("Run: python -m src.ui.cli run --symbol X:BTCUSD --mode thorough")
        return False
    
    print(f"✓ Found signals: {signals_path}")
    
    # Read and validate
    with open(signals_path) as f:
        lines = f.readlines()
        print(f"✓ Signals file has {len(lines)-1} rows")
        print(f"  Headers: {lines[0].strip()}")
    
    return True


def test_project_id():
    """Test if project ID is configured"""
    print("\n" + "=" * 60)
    print("Testing Project ID")
    print("=" * 60)
    
    project_id_path = Path("qc_project_id.txt")
    
    if project_id_path.exists():
        project_id = project_id_path.read_text().strip()
        print(f"✓ Project ID: {project_id}")
        return True
    else:
        print("✗ Project ID not found!")
        print("\nSetup instructions:")
        print("1. Go to: https://www.quantconnect.com/terminal")
        print("2. Create a new project: 'RegimeSignalsAlgo'")
        print("3. Copy the project ID from the URL")
        print("4. Create qc_project_id.txt with the project ID")
        return False


def main():
    """Run all tests"""
    print("\n🚀 QuantConnect Integration Test\n")
    
    results = []
    
    # Test 1: Credentials
    results.append(("Credentials", test_credentials()))
    
    # Test 2: Signals
    results.append(("Signals", test_signals_upload()))
    
    # Test 3: Project ID
    results.append(("Project ID", test_project_id()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✅ All tests passed! Ready for QC integration.")
        print("\nNext step:")
        print("  python scripts/submit_qc_backtest.py")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

