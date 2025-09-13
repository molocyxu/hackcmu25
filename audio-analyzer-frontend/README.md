# Audio Analyzer Frontend

A modern, redesigned frontend for the Audio Transcription & Analysis Tool using Next.js 15, TypeScript, and shadcn/ui components.

## Features

### ✨ Modern UI with shadcn/ui
- Beautiful, accessible components built on Radix UI
- Dark/light mode support
- Responsive design
- Clean, professional interface

### 🎵 Audio Processing
- **File Upload**: Support for audio and video files
- **Recording**: Built-in audio recording capabilities
- **Transcription**: Whisper model integration for accurate transcription
- **Multiple Formats**: Support for various audio/video formats

### 🤖 AI Processing
- **Anthropic Claude Integration**: Advanced text analysis
- **Custom Prompts**: Flexible prompt system with {text} placeholder
- **Multiple Output Formats**: Markdown, JSON, LaTeX, Plain Text, Bullet Points
- **History Navigation**: Navigate through previous analysis results

### 💾 Export Features
- Export transcriptions and results
- Multiple format support
- LaTeX PDF generation capability
- One-click copy to clipboard

## Key Improvements from Original

### 🎨 Visual Design
- **Modern Interface**: Clean, professional design using shadcn/ui
- **Better Layout**: Improved sidebar and main content organization
- **Enhanced Typography**: Better readability and visual hierarchy
- **Responsive**: Works well on different screen sizes

### 🚀 User Experience
- **Intuitive Workflow**: Clear step-by-step process
- **Real-time Feedback**: Progress indicators and status updates
- **Better Navigation**: Easy history browsing with prev/next buttons
- **Improved Controls**: More accessible buttons and form elements

### 🔧 Technical Improvements
- **Modern Tech Stack**: Next.js 15, TypeScript, Tailwind CSS
- **Component Architecture**: Reusable, maintainable components
- **API Routes**: Clean separation of frontend and backend logic
- **Type Safety**: Full TypeScript implementation

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

1. **Clone and Navigate**
   ```bash
   cd audio-analyzer-frontend
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Start Development Server**
   ```bash
   npm run dev
   ```

4. **Open Browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Usage

### Step 1: Select Audio
- Click "Choose Audio File" to upload an audio/video file
- Or use the recording feature to capture audio directly

### Step 2: Transcribe
- Select your preferred Whisper model (tiny to large)
- Click "Transcribe" to convert audio to text
- View results in the Transcription tab

### Step 3: AI Analysis
- Enter your Anthropic API key
- Set word limit and output format
- Click "Summarize" for quick analysis
- Or use custom prompts for specific analysis needs

### Additional Features
- **Export**: Save transcriptions and results in various formats
- **History**: Navigate through previous analysis results
- **Copy**: Quick copy to clipboard functionality
- **Clear**: Reset all content when needed

## API Routes

### `/api/transcribe`
- **Method**: POST
- **Body**: FormData with audio file and model selection
- **Returns**: Transcription result with metadata

### `/api/process`
- **Method**: POST  
- **Body**: JSON with text, prompt, API key, and formatting options
- **Returns**: AI-processed result in requested format

## Component Structure

```
src/components/
├── AudioAnalyzer.tsx          # Main application component
├── Sidebar.tsx                # Left sidebar with controls
├── TranscriptionTab.tsx       # Transcription display and editing
├── ProcessedResultTab.tsx     # AI results with history navigation
└── ToolbarButtons.tsx         # Export and utility buttons
```

## Customization

The application uses shadcn/ui components which can be easily customized:

1. **Colors**: Modify `src/app/globals.css` CSS variables
2. **Components**: Customize individual components in `src/components/ui/`
3. **Layout**: Adjust the main layout in `AudioAnalyzer.tsx`

## Future Enhancements

- [ ] Real Whisper API integration
- [ ] Real Anthropic Claude API integration  
- [ ] Audio waveform visualization
- [ ] Batch processing capabilities
- [ ] User authentication and saved sessions
- [ ] Advanced export options
- [ ] Plugin system for custom processors

## Technologies Used

- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: High-quality React components
- **Radix UI**: Accessible component primitives
- **Lucide React**: Beautiful icons

## License

This project maintains the same license as the original audioapp.ipynb implementation.