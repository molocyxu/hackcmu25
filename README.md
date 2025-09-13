# Audio Transcription & Analysis Tool

A comprehensive tool for audio transcription using OpenAI Whisper and AI-powered analysis with Claude. This project provides multiple interfaces: a Jupyter notebook, a standalone GUI application, and a Next.js web interface.

## 🎯 Features

- **Audio/Video Transcription**: Support for multiple formats (MP3, WAV, MP4, etc.) using OpenAI Whisper
- **Real-time Recording**: Record audio directly from your microphone
- **AI-Powered Analysis**: Clean, summarize, and analyze transcriptions using Claude AI
- **Multiple Export Formats**: Markdown, PDF, JSON, LaTeX, and more
- **Semantic Network Visualization**: Generate word relationship networks
- **Custom Prompt Processing**: Use your own prompts for AI analysis
- **History Tracking**: Keep track of all processed results

## 🔧 System Requirements

- **Python 3.8+** (Python 3.10+ recommended)
- **Node.js 18+** (for web interface)
- **FFmpeg** (for audio/video processing)
- **PortAudio** (for microphone recording)

### Platform-Specific Requirements

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install ffmpeg portaudio
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg portaudio19-dev python3-dev python3-pip
```

#### Windows
1. Install [FFmpeg](https://ffmpeg.org/download.html) and add to PATH
2. Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

## 📦 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd audio-transcription-tool
```

### 2. Install Python Dependencies

#### Option A: Using pip (Global Installation)
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Option B: Using Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Manual Installation (if requirements.txt fails)
```bash
pip install openai-whisper anthropic customtkinter sounddevice soundfile
pip install jupyter ipykernel pandas scipy matplotlib networkx scikit-learn
pip install gensim pillow
```

### 3. Install Node.js Dependencies (for Web Interface)
```bash
cd audio-analyzer-frontend
npm install
cd ..
```

### 4. Configure Environment Variables

#### For Web Interface
Create `audio-analyzer-frontend/.env.local`:
```bash
# Python configuration
PYTHON_BIN=/usr/bin/python3
PATH_PREFIX=/home/ubuntu/.local/bin
WORKSPACE_ROOT=/workspace

# Optional: Add your Anthropic API key
ANTHROPIC_API_KEY=your_api_key_here
```

#### For Python Applications
You'll need an Anthropic API key for AI features:
1. Get your API key from [Anthropic Console](https://console.anthropic.com/)
2. The applications will prompt you to enter it when needed

## 🚀 Usage

### Option 1: Jupyter Notebook Interface

```bash
# Start Jupyter
jupyter notebook

# Open audioapp.ipynb in your browser
# Run the cells to load the application
```

### Option 2: Standalone GUI Application

```bash
# Run the standalone Python GUI
python audioapp_standalone.py
```

### Option 3: Next.js Web Interface

```bash
# Start the development server
cd audio-analyzer-frontend
npm run dev

# Open http://localhost:3000 in your browser
```

### Option 4: Production Web Deployment

```bash
# Build the application
cd audio-analyzer-frontend
npm run build
npm start
```

## 📋 Quick Start Guide

### Basic Transcription Workflow

1. **Choose your interface** (Notebook, GUI, or Web)
2. **Select an audio/video file** or record audio directly
3. **Wait for transcription** (Whisper model will download automatically on first use)
4. **Review and edit** the transcribed text
5. **Optional**: Use AI features to clean, summarize, or analyze the text
6. **Export** your results in your preferred format

### First-Time Setup

1. **Test Whisper Installation**:
   ```bash
   python -c "import whisper; print('Whisper installed successfully')"
   ```

2. **Test Audio Recording** (optional):
   ```bash
   python -c "import sounddevice; print(sounddevice.query_devices())"
   ```

3. **Download a Whisper Model**:
   ```bash
   python -c "import whisper; whisper.load_model('tiny')"
   ```

## 🔍 Troubleshooting

### Common Issues

#### "No module named 'whisper'"
```bash
pip install openai-whisper
```

#### "spawn /usr/bin/python3 ENOENT" (Web Interface)
- Ensure Python is installed and accessible
- Check the `PYTHON_BIN` path in `.env.local`
- Try using the full path to your Python executable

#### Audio Recording Issues
```bash
# Install additional audio dependencies
pip install pyaudio  # Alternative audio backend

# On macOS, you might need:
brew install portaudio
pip install sounddevice

# On Linux:
sudo apt-get install portaudio19-dev python3-pyaudio
```

#### FFmpeg Not Found
- **macOS**: `brew install ffmpeg`
- **Ubuntu**: `sudo apt install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org) and add to PATH

#### Memory Issues with Large Models
Use smaller Whisper models for better performance:
- `tiny`: Fastest, least accurate
- `base`: Good balance (recommended)
- `small`: Better accuracy
- `medium`/`large`: Best accuracy, slower

### Performance Tips

1. **Use GPU acceleration** (if available):
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Choose appropriate model size**:
   - For quick testing: `tiny` model
   - For production: `base` or `small` model
   - For highest accuracy: `medium` or `large` model

3. **Optimize audio files**:
   - Convert to WAV format for best compatibility
   - Use 16kHz sample rate for Whisper
   - Mono audio is sufficient

## 📁 Project Structure

```
audio-transcription-tool/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── audioapp.ipynb                    # Jupyter notebook interface
├── audioapp_standalone.py            # Standalone GUI application
├── audio-analyzer-frontend/          # Next.js web interface
│   ├── src/app/api/                  # API routes
│   ├── src/components/               # React components
│   ├── package.json                  # Node.js dependencies
│   └── .env.local                    # Environment configuration
└── notebooks/                        # Additional notebooks and backups
```

## 🔑 API Keys

### Anthropic API Key (Required for AI Features)

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Add it to your environment or enter it in the application when prompted

**Security Note**: Never commit API keys to version control. Use environment variables or the application's secure input fields.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Verify all dependencies** are installed correctly
3. **Test with a small audio file** first
4. **Check Python and Node.js versions** meet requirements
5. **Review console/terminal output** for specific error messages

For additional help, please open an issue with:
- Your operating system and version
- Python version (`python --version`)
- Node.js version (`node --version`)
- Complete error messages
- Steps to reproduce the issue

## 🎉 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Anthropic Claude](https://www.anthropic.com/) for AI text processing
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for modern GUI components
- [Next.js](https://nextjs.org/) for the web framework