#!/usr/bin/env python
"""
One-time setup: Upload strategy library and main.py to QC project.
Run this once, then only signals/params get updated on each run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.qc_mcp_client import QCMCPClient


def main():
    print("=" * 60)
    print("🔧 QuantConnect Project Setup")
    print("=" * 60)
    print()
    
    # Load project ID
    project_id_path = Path("qc_project_id.txt")
    if not project_id_path.exists():
        print("❌ Project ID not found!")
        print("Create qc_project_id.txt with your project ID")
        return 1
    
    project_id = project_id_path.read_text().strip()
    print(f"Project ID: {project_id}")
    print()
    
    # Create client
    client = QCMCPClient()
    
    if not client.api_token or not client.user_id:
        print("❌ QC credentials not found!")
        return 1
    
    print("✓ Credentials loaded")
    print()
    
    # Upload files
    files_to_upload = [
        ("lean/strategies_library.py", "strategies_library.py"),
        ("lean/main.py", "main.py"),
    ]
    
    for local_path, qc_filename in files_to_upload:
        local_file = Path(local_path)
        
        if not local_file.exists():
            print(f"❌ File not found: {local_path}")
            continue
        
        print(f"📤 Uploading {qc_filename}...")
        
        success = client.upload_algorithm(local_file, project_id, qc_filename)
        
        if success:
            print(f"✅ {qc_filename} uploaded successfully")
        else:
            print(f"❌ Failed to upload {qc_filename}")
        
        print()
    
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()
    print("Your QC project now has:")
    print("  - strategies_library.py (all 9 strategies)")
    print("  - main.py (signal processor)")
    print()
    print("Next steps:")
    print("1. Run your pipeline to generate signals:")
    print("   python -m src.ui.cli run --symbol X:BTCUSD --mode thorough")
    print()
    print("2. Submit backtest (will auto-update signals):")
    print("   python scripts/submit_qc_backtest.py")
    print()
    print(f"3. View: https://www.quantconnect.com/terminal/{project_id}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

