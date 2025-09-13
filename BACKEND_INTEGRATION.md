# Backend Integration - Audio Analyzer Frontend

This document describes the integration between the Next.js frontend and the Python backend functionality from the Jupyter notebook.

## Overview

The frontend has been updated to replace all mock implementations with actual backend functionality that matches the behavior of the `audioapp.ipynb` notebook.

## Changes Made

### 1. Real Whisper Transcription (`/api/transcribe`)
- **Before**: Mock transcription returning placeholder text
- **After**: Actual Whisper model transcription using Python subprocess
- **Features**:
  - Supports all Whisper models (tiny, base, small, medium, large)
  - Handles both audio and video files
  - Returns actual transcription, duration, and detected language

### 2. Real Anthropic Claude Processing (`/api/process`)
- **Before**: Mock responses based on output format
- **After**: Actual Anthropic Claude API calls using Python subprocess
- **Features**:
  - Real AI analysis and summarization
  - Support for custom prompts with `{text}` placeholder
  - All output formats: Markdown, Plain Text, JSON, Bullet Points, LaTeX PDF
  - Proper LaTeX formatting for mathematical content

### 3. Model Loading and Status (`/api/model`)
- **New**: API endpoint to check and load Whisper models
- **Features**:
  - Check if models are already downloaded
  - Load models on demand
  - Real-time status updates in the UI

### 4. Audio Recording (`Web Audio API`)
- **Before**: Mock recording functionality
- **After**: Real browser-based audio recording
- **Features**:
  - Uses `MediaRecorder` API for actual audio capture
  - Real-time recording duration display
  - Supports WebM and WAV formats
  - Proper cleanup of media streams

### 5. LaTeX PDF Compilation (`/api/latex`)
- **New**: Server-side LaTeX compilation to PDF
- **Features**:
  - Compiles LaTeX content to PDF using `pdflatex`
  - Returns PDF as downloadable file
  - Fallback to .tex file if compilation fails
  - Proper mathematical equation formatting

### 6. Enhanced Error Handling
- **Before**: Basic error logging
- **After**: Comprehensive error handling and user feedback
- **Features**:
  - User-friendly error messages
  - Error state management in UI
  - Graceful fallbacks for failed operations

## API Endpoints

### POST `/api/transcribe`
Transcribes audio files using Whisper models.

**Request**: FormData with audio file and model name
**Response**: 
```json
{
  "transcription": "transcribed text",
  "model": "base",
  "duration": 30,
  "language": "en"
}
```

### POST `/api/process`
Processes text using Anthropic Claude.

**Request**:
```json
{
  "text": "transcribed text",
  "prompt": "analysis prompt",
  "apiKey": "your-api-key",
  "wordLimit": 500,
  "outputFormat": "Markdown"
}
```

**Response**:
```json
{
  "result": "processed text",
  "prompt": "original prompt",
  "wordLimit": 500,
  "outputFormat": "Markdown",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### GET `/api/model?model=base`
Checks if a Whisper model is loaded.

**Response**:
```json
{
  "model": "base",
  "loaded": true
}
```

### POST `/api/model`
Loads a Whisper model.

**Request**:
```json
{
  "model": "base"
}
```

### POST `/api/latex`
Compiles LaTeX content to PDF.

**Request**:
```json
{
  "latexContent": "\\documentclass{article}..."
}
```

**Response**:
```json
{
  "success": true,
  "pdf": "base64-encoded-pdf",
  "filename": "analysis.pdf"
}
```

## Setup Instructions

1. **Install Python Dependencies**:
   ```bash
   python3 setup_backend.py
   ```

2. **Install LaTeX (Optional, for PDF export)**:
   - Ubuntu/Debian: `sudo apt-get install texlive-full`
   - macOS: `brew install --cask mactex`
   - Windows: Install MiKTeX or TeX Live

3. **Start the Development Server**:
   ```bash
   npm run dev
   ```

## Requirements

### Python Dependencies
- `openai-whisper==20231117`
- `anthropic>=0.18.0`
- `numpy>=1.24.0`
- `torch>=2.0.0`
- `torchaudio>=2.0.0`

### System Requirements
- Python 3.8+
- Node.js 18+
- FFmpeg (for audio processing)
- LaTeX distribution (optional, for PDF export)

## Usage

1. **File Upload**: Select audio/video files for transcription
2. **Recording**: Use the built-in recorder to capture audio
3. **Model Selection**: Choose appropriate Whisper model for your needs
4. **Transcription**: Get actual transcription from Whisper
5. **AI Processing**: Use Anthropic Claude for analysis and summarization
6. **Export**: Export results in various formats including PDF

## Error Handling

The application includes comprehensive error handling:

- **Network Errors**: Graceful handling of API failures
- **Model Loading**: Clear feedback on model status
- **Recording**: Proper microphone permission handling
- **LaTeX Compilation**: Fallback to .tex file if PDF fails
- **User Feedback**: Clear error messages and recovery options

## Performance Considerations

- **Model Loading**: Models are loaded on-demand and cached
- **Recording**: Efficient chunked recording with proper cleanup
- **Processing**: Async processing with progress indicators
- **Memory**: Proper cleanup of temporary files and streams

## Security

- **API Keys**: Stored in browser state only, not persisted
- **File Uploads**: Temporary files are automatically cleaned up
- **Process Isolation**: Python scripts run in isolated subprocesses
- **Input Validation**: All inputs are validated before processing

## Troubleshooting

### Common Issues

1. **"Python script failed"**: Ensure Python dependencies are installed
2. **"Model loading failed"**: Check internet connection for model download
3. **"Recording failed"**: Grant microphone permissions in browser
4. **"PDF compilation failed"**: Install LaTeX distribution
5. **"Processing failed"**: Verify Anthropic API key is valid

### Debug Information

Check browser console and server logs for detailed error information. The application provides verbose logging for troubleshooting.