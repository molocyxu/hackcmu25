#!/usr/bin/env python3
"""
Setup script to install backend dependencies for the Audio Analyzer frontend.
This ensures all Python dependencies are available for the API endpoints.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors gracefully."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed:")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible. Need Python 3.8+")
        return False

def install_dependencies():
    """Install required Python packages."""
    requirements = [
        "openai-whisper==20231117",
        "anthropic>=0.18.0",
        "numpy>=1.24.0",
        "torch>=2.0.0",
        "torchaudio>=2.0.0",
    ]
    
    print("📦 Installing Python dependencies...")
    for req in requirements:
        success = run_command(f"pip install {req}", f"Installing {req}")
        if not success:
            print(f"⚠️  Failed to install {req}, but continuing...")
    
    return True

def test_imports():
    """Test if required modules can be imported."""
    modules = {
        'whisper': 'OpenAI Whisper',
        'anthropic': 'Anthropic',
        'numpy': 'NumPy',
        'torch': 'PyTorch',
    }
    
    print("\n🧪 Testing module imports...")
    all_success = True
    
    for module, name in modules.items():
        try:
            __import__(module)
            print(f"✅ {name} imported successfully")
        except ImportError as e:
            print(f"❌ {name} import failed: {e}")
            all_success = False
    
    return all_success

def download_base_model():
    """Download the base Whisper model."""
    print("\n📥 Downloading Whisper base model...")
    try:
        import whisper
        model = whisper.load_model("base")
        print("✅ Whisper base model downloaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to download Whisper model: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Audio Analyzer Backend Dependencies")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Setup failed: Incompatible Python version")
        sys.exit(1)
    
    # Install dependencies
    install_dependencies()
    
    # Test imports
    if not test_imports():
        print("\n⚠️  Some modules failed to import. The application may not work correctly.")
        print("Please check the error messages above and install missing dependencies manually.")
    
    # Download base model
    download_base_model()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Start your Next.js development server: npm run dev")
    print("2. Upload an audio file and test transcription")
    print("3. Add your Anthropic API key to test AI processing")
    print("\nNote: For LaTeX PDF export, make sure you have LaTeX installed:")
    print("- Ubuntu/Debian: sudo apt-get install texlive-full")
    print("- macOS: brew install --cask mactex")
    print("- Windows: Install MiKTeX or TeX Live")

if __name__ == "__main__":
    main()