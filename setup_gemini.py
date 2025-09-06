#!/usr/bin/env python3
"""
Setup script for Google Gemini API key configuration
"""

import os
import sys

def setup_gemini_key():
    """Help user set up GEMINI_API_KEY"""

    print("🔑 Google Gemini API Setup")
    print("=" * 40)

    # Check if already configured
    current_key = os.getenv("GEMINI_API_KEY", "")
    if current_key:
        print(f"✅ GEMINI_API_KEY is already configured (ends with: ...{current_key[-4:] if current_key else 'N/A'})")
        choice = input("Do you want to update it? (y/n): ").lower().strip()
        if choice != 'y':
            print("Setup cancelled.")
            return

    print("\n📋 To get a Google Gemini API key:")
    print("1. Go to: https://makersuite.google.com/app/apikey")
    print("2. Sign in with your Google account")
    print("3. Create a new API key")
    print("4. Copy the API key")

    api_key = input("\n🔐 Enter your Google Gemini API key: ").strip()

    if not api_key:
        print("❌ No API key provided. Setup cancelled.")
        return

    # Validate key format (basic check)
    if not api_key.startswith("AIza"):
        print("⚠️  Warning: API key doesn't start with 'AIza'. This might not be a valid Gemini API key.")
        confirm = input("Continue anyway? (y/n): ").lower().strip()
        if confirm != 'y':
            return

    # Update .env file
    env_file = ".env"
    env_content = ""

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()

    # Remove existing GEMINI_API_KEY if present
    lines = env_content.split('\n')
    lines = [line for line in lines if not line.startswith('GEMINI_API_KEY=')]

    # Add new key
    lines.append(f"GEMINI_API_KEY={api_key}")

    # Write back
    with open(env_file, 'w') as f:
        f.write('\n'.join(lines))

    print("✅ GEMINI_API_KEY has been saved to .env file")
    print("🔄 Please restart your API server for changes to take effect")
    print("💡 You can restart with: python api.py")

if __name__ == "__main__":
    setup_gemini_key()
