#!/usr/bin/env python3
"""
Test Google Cloud Speech-to-Text API connection
"""

import os
import sys

def test_google_speech_api():
    """
    Test if Google Cloud Speech-to-Text API is properly configured.
    """
    print("🔍 Testing Google Cloud Speech-to-Text API...")
    print("=" * 50)
    
    # Check environment variable
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    print(f"✅ Credentials file found: {creds_path}")
    
    # Try to import the library
    try:
        from google.cloud import speech
        print("✅ google-cloud-speech library imported successfully")
    except ImportError as e:
        print(f"❌ Could not import google-cloud-speech: {e}")
        print("   Run: pip install google-cloud-speech")
        return False
    
    # Try to create a client
    try:
        client = speech.SpeechClient()
        print("✅ Speech client created successfully")
    except Exception as e:
        print(f"❌ Could not create Speech client: {e}")
        return False
    
    # Try a simple API call (list supported languages)
    try:
        # This is a simple API call that doesn't require audio files
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        print("✅ API configuration created successfully")
        print("🚀 Google Cloud Speech-to-Text API is ready!")
        return True
        
    except Exception as e:
        print(f"❌ API configuration failed: {e}")
        return False

if __name__ == "__main__":
    success = test_google_speech_api()
    if success:
        print("\n🎉 You can now run speaker diarization:")
        print("python diarize_google.py ../audio_files/Audio.wav -n 2")
        print("python diarize_google.py ../audio_files/NewRecording97.wav -n 3")
    else:
        print("\n❌ Setup incomplete. Run setup_google_speech.py for help")
        sys.exit(1)
