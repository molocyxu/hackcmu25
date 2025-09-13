#!/usr/bin/env python3
"""
Google Cloud Speech-to-Text Setup Helper
This script helps set up Google Cloud credentials for speaker diarization.
"""

import os
import json

def setup_google_credentials():
    """
    Help set up Google Cloud credentials for Speech-to-Text API.
    """
    print("🔧 Google Cloud Speech-to-Text Setup Helper")
    print("=" * 50)
    print()
    print("To use Google Cloud Speech-to-Text API, you need:")
    print("1. A Google Cloud Project with billing enabled")
    print("2. Speech-to-Text API enabled")
    print("3. Service account credentials")
    print()
    print("Setup Steps:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project or select an existing one")
    print("3. Enable the Speech-to-Text API:")
    print("   - Go to APIs & Services > Library")
    print("   - Search for 'Speech-to-Text API'")
    print("   - Click Enable")
    print("4. Create service account credentials:")
    print("   - Go to APIs & Services > Credentials")
    print("   - Click 'Create Credentials' > 'Service Account'")
    print("   - Fill in the details and create")
    print("   - Click on the service account")
    print("   - Go to 'Keys' tab")
    print("   - Click 'Add Key' > 'Create new key' > JSON")
    print("   - Download the JSON file")
    print("5. Set the environment variable:")
    print(f"   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/your/credentials.json'")
    print()
    
    # Check if credentials are already set
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path:
        if os.path.exists(creds_path):
            print(f"✅ Credentials found at: {creds_path}")
            try:
                with open(creds_path, 'r') as f:
                    creds = json.load(f)
                    print(f"   Project ID: {creds.get('project_id', 'Unknown')}")
                    print(f"   Client Email: {creds.get('client_email', 'Unknown')}")
                    print("✅ Credentials appear to be valid")
                    return True
            except Exception as e:
                print(f"⚠️  Warning: Could not read credentials file: {e}")
        else:
            print(f"❌ Credentials file not found at: {creds_path}")
    else:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    print()
    print("After setting up credentials, you can test with:")
    print("python diarize_google.py ../audio_files/Audio.wav -n 2")
    print()
    return False

def create_sample_env():
    """
    Create a sample environment file for credentials.
    """
    env_content = """# Google Cloud Speech-to-Text Credentials
# Set this to the path of your Google Cloud service account JSON file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json

# Alternative: You can also set the project ID directly
# GOOGLE_CLOUD_PROJECT=your-project-id
"""
    
    with open('.env.google', 'w') as f:
        f.write(env_content)
    
    print("📄 Created .env.google template file")
    print("   Edit this file with your actual credentials path")

if __name__ == "__main__":
    if setup_google_credentials():
        print("\n🚀 Ready to use Google Speech-to-Text diarization!")
    else:
        print("\n📋 Please complete the setup steps above")
        create_sample_env()
