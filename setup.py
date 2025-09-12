#!/usr/bin/env python3
"""
Audio Analyzer Environment Setup Script
Creates a new virtual environment and Jupyter kernel for the audio analyzer program
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path

class EnvironmentSetup:
    def __init__(self):
        self.env_name = "audio_analyzer_env"
        self.kernel_name = "audio_analyzer_kernel"
        self.os_type = platform.system().lower()
        self.python_executable = sys.executable
        self.base_dir = Path.cwd()
        
    def run_command(self, command, shell=True):
        """Execute a shell command and return the result"""
        try:
            result = subprocess.run(
                command, 
                shell=shell, 
                capture_output=True, 
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def create_virtual_environment(self):
        """Create a new virtual environment"""
        print(f"📦 Creating virtual environment '{self.env_name}'...")
        success, output = self.run_command(f"{self.python_executable} -m venv {self.env_name}")
        
        if success:
            print(f"✅ Virtual environment created successfully!")
            return True
        else:
            print(f"❌ Failed to create virtual environment: {output}")
            return False
    
    def get_pip_path(self):
        """Get the path to pip in the virtual environment"""
        if self.os_type == "windows":
            return os.path.join(self.env_name, "Scripts", "pip")
        else:
            return os.path.join(self.env_name, "bin", "pip")
    
    def get_python_path(self):
        """Get the path to python in the virtual environment"""
        if self.os_type == "windows":
            return os.path.join(self.env_name, "Scripts", "python")
        else:
            return os.path.join(self.env_name, "bin", "python")
    
    def install_packages(self):
        """Install required packages"""
        pip_path = self.get_pip_path()
        
        packages = [
            ("pip", "--upgrade pip"),
            ("Whisper", "openai-whisper"),
            ("Anthropic", "anthropic"),
            ("CustomTkinter", "customtkinter"),
            ("Jupyter", "jupyter ipykernel"),
            ("Audio Libraries", "librosa soundfile pydub ffmpeg-python"),
            ("Data Processing", "numpy pandas scipy matplotlib"),
            ("Utilities", "python-dotenv"),
        ]
        
        print("\n📥 Installing packages...")
        for name, package in packages:
            print(f"  Installing {name}...")
            success, output = self.run_command(f"{pip_path} install {package}")
            if success:
                print(f"  ✅ {name} installed")
            else:
                print(f"  ⚠️  Warning: Failed to install {name}")
    
    def create_jupyter_kernel(self):
        """Create a Jupyter kernel for the environment"""
        python_path = self.get_python_path()
        print(f"\n🔧 Creating Jupyter kernel '{self.kernel_name}'...")
        
        command = f"{python_path} -m ipykernel install --user --name={self.kernel_name} --display-name=\"Audio Analyzer (Python)\""
        success, output = self.run_command(command)
        
        if success:
            print(f"✅ Jupyter kernel created successfully!")
        else:
            print(f"⚠️  Warning: Failed to create Jupyter kernel")
    
    def create_requirements_file(self):
        """Create requirements.txt file"""
        requirements = """# Core Dependencies
numpy==1.26.4  # Fixed version for compatibility with PyTorch/Whisper
openai-whisper==20231117
anthropic>=0.18.0
customtkinter==5.2.0

# Audio Processing
librosa>=0.10.0
soundfile>=0.12.1
pydub>=0.25.1
ffmpeg-python>=0.2.0

# Jupyter Support
jupyter>=1.0.0
ipykernel>=6.0.0

# Data Processing
pandas>=2.0.0
scipy>=1.10.0
matplotlib>=3.7.0

# Utilities
python-dotenv>=1.0.0
"""
        
        with open("requirements.txt", "w") as f:
            f.write(requirements)
        print("📄 Created requirements.txt")
    
    def create_env_template(self):
        """Create .env.template file"""
        env_template = """# Anthropic API Configuration
ANTHROPIC_API_KEY=your_api_key_here

# Whisper Model Configuration
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large

# Application Settings
DEFAULT_OUTPUT_FORMAT=markdown
DEFAULT_PROCESS_TYPE=summarize
"""
        
        with open(".env.template", "w") as f:
            f.write(env_template)
        print("📄 Created .env.template")
    
    def create_project_structure(self):
        """Create project directory structure"""
        directories = ["audio_files", "output", "logs", "notebooks"]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        
        print("📁 Created project directories")
    
    def create_notebook_example(self):
        """Create an example Jupyter notebook"""
        notebook_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# Audio Analyzer - Jupyter Interface\n", 
                              "This notebook provides an interface to the audio analyzer tool."]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Import required libraries\n",
                        "import whisper\n",
                        "from anthropic import Anthropic\n",
                        "import os\n",
                        "from pathlib import Path\n",
                        "from IPython.display import Audio, display\n",
                        "import json"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Load environment variables\n",
                        "from dotenv import load_dotenv\n",
                        "load_dotenv()\n",
                        "\n",
                        "# Configuration\n",
                        "ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', 'your_key_here')\n",
                        "WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Load Whisper model\n",
                        "print(f\"Loading Whisper model: {WHISPER_MODEL}\")\n",
                        "model = whisper.load_model(WHISPER_MODEL)\n",
                        "print(\"Model loaded successfully!\")"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "def transcribe_audio(audio_path):\n",
                        "    \"\"\"Transcribe audio file using Whisper\"\"\"\n",
                        "    result = model.transcribe(audio_path)\n",
                        "    return result['text']\n",
                        "\n",
                        "def process_with_claude(text, prompt_type='summarize'):\n",
                        "    \"\"\"Process transcribed text with Claude\"\"\"\n",
                        "    client = Anthropic(api_key=ANTHROPIC_API_KEY)\n",
                        "    \n",
                        "    prompts = {\n",
                        "        'summarize': f\"Summarize the following text:\\n\\n{text}\",\n",
                        "        'analyze': f\"Analyze and explain the following text:\\n\\n{text}\",\n",
                        "        'keypoints': f\"Extract key points from the following text:\\n\\n{text}\"\n",
                        "    }\n",
                        "    \n",
                        "    response = client.messages.create(\n",
                        "        model=\"claude-3-5-sonnet-20241022\",\n",
                        "        max_tokens=4000,\n",
                        "        messages=[{\"role\": \"user\", \"content\": prompts[prompt_type]}]\n",
                        "    )\n",
                        "    \n",
                        "    return response.content[0].text"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Example usage\n",
                        "# audio_file = \"path/to/your/audio.mp3\"\n",
                        "# transcription = transcribe_audio(audio_file)\n",
                        "# summary = process_with_claude(transcription, 'summarize')\n",
                        "# print(summary)"
                    ]
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Audio Analyzer (Python)",
                    "language": "python",
                    "name": "audio_analyzer_kernel"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.9.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        
        with open("notebooks/audio_analyzer_notebook.ipynb", "w") as f:
            json.dump(notebook_content, f, indent=2)
        
        print("📓 Created example Jupyter notebook")
    
    def display_ffmpeg_instructions(self):
        """Display FFmpeg installation instructions"""
        print("\n" + "="*50)
        print("⚠️  IMPORTANT: FFmpeg Installation Required")
        print("="*50)
        
        if self.os_type == "windows":
            print("""
For Windows:
1. Download ffmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract the archive
3. Add the 'bin' folder to your system PATH
   OR
Use Chocolatey: choco install ffmpeg
            """)
        elif self.os_type == "darwin":  # macOS
            print("""
For macOS:
Install using Homebrew:
  brew install ffmpeg

If you don't have Homebrew:
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            """)
        else:  # Linux
            print("""
For Linux:
  Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg
  CentOS/RHEL: sudo yum install ffmpeg
  Arch Linux: sudo pacman -S ffmpeg
  Fedora: sudo dnf install ffmpeg
            """)
    
    def run_setup(self):
        """Run the complete setup process"""
        print("="*50)
        print("🚀 Audio Analyzer Environment Setup")
        print("="*50)
        print(f"Operating System: {self.os_type}")
        print(f"Python Version: {sys.version.split()[0]}")
        print(f"Base Directory: {self.base_dir}\n")
        
        # Create virtual environment
        if not self.create_virtual_environment():
            print("Setup failed. Please check the error messages above.")
            return False
        
        # Install packages
        self.install_packages()
        
        # Create Jupyter kernel
        self.create_jupyter_kernel()
        
        # Create project files and structure
        print("\n📁 Creating project files...")
        self.create_requirements_file()
        self.create_env_template()
        self.create_project_structure()
        self.create_notebook_example()
        
        # Display FFmpeg instructions
        self.display_ffmpeg_instructions()
        
        # Display completion message
        print("\n" + "="*50)
        print("✨ Setup Complete!")
        print("="*50)
        print(f"""
Next steps:
1. Activate the environment:
   {'source ' if self.os_type != 'windows' else ''}{self.env_name}/{'bin' if self.os_type != 'windows' else 'Scripts'}/activate

2. Set your Anthropic API key:
   - Copy .env.template to .env
   - Add your API key to the .env file

3. Run the GUI application:
   python audio_analyzer.py

4. Or use Jupyter Notebook:
   jupyter notebook notebooks/audio_analyzer_notebook.ipynb

Available Jupyter kernel: {self.kernel_name}
        """)
        
        return True

def main():
    """Main entry point"""
    setup = EnvironmentSetup()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        sys.exit(1)
    
    # Run setup
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()