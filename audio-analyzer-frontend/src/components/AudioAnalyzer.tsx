"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { TranscriptionTab } from "./TranscriptionTab";
import { ProcessedResultTab } from "./ProcessedResultTab";
import { ToolbarButtons } from "./ToolbarButtons";
import { NewAudioDialog } from "./NewAudioDialog";

export interface AudioAnalyzerState {
  audioFilePath: string | null;
  audioFileName: string;
  transcribedText: string;
  isRecording: boolean;
  recordingDuration: number;
  recordedFilePath: string | null;
  whisperModel: string;
  modelLoaded: boolean;
  apiKey: string;
  wordLimit: number;
  outputFormat: string;
  isTranscribing: boolean;
  isProcessing: boolean;
  progress: number;
  status: string;
  error: string | null;
  processHistory: Array<{ prompt: string; result: string }>;
  currentHistoryIndex: number;
  customPrompt: string;
  semanticSummary: string;
  networkPlotUrl: string | null;
  targetLanguage: string;
  translationStyle: string;
  preserveFormatting: boolean;
}

export function AudioAnalyzer() {
  const [state, setState] = useState<AudioAnalyzerState>({
    audioFilePath: null,
    audioFileName: "",
    transcribedText: "",
    isRecording: false,
    recordingDuration: 0,
    recordedFilePath: null,
    whisperModel: "base",
    modelLoaded: false, // Set to false initially, will be checked by API
    apiKey: "",
    wordLimit: 500,
    outputFormat: "Markdown",
    isTranscribing: false,
    isProcessing: false,
    progress: 0,
    status: "Ready",
    error: null,
    processHistory: [],
    currentHistoryIndex: -1,
    customPrompt: "Analyze the following text and provide insights:\n\n{text}",
    semanticSummary: "",
    networkPlotUrl: null,
    targetLanguage: "None",
    translationStyle: "Natural",
    preserveFormatting: true,
  });

  const [isNewAudioDialogOpen, setIsNewAudioDialogOpen] = useState(false);

  const updateState = (updates: Partial<AudioAnalyzerState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  };

  // Add functions needed from the old sidebar
  const handleTranscribe = async () => {
    if (!state.audioFilePath) return;
    
    updateState({
      isTranscribing: true,
      progress: 10,
      status: "Transcribing audio...",
    });

    try {
      if (!state.audioFilePath) return;
      let realFilePath = state.audioFilePath;
      if (state.audioFilePath.startsWith('blob:')) {
        const response = await fetch(state.audioFilePath);
        const blob = await response.blob();
        const formData = new FormData();
        formData.append('audio', blob, state.audioFileName);

        // Upload to your backend (create an /api/upload endpoint)
        const uploadResponse = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });
        const uploadData = await uploadResponse.json();
        realFilePath = uploadData.filePath; // The backend should return the saved file path
  }
      
      updateState({ progress: 50 });

      const response = await fetch('/api/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audioPath: realFilePath,
          model: state.whisperModel,
        }),
      });

      if (!response.ok) {
        throw new Error('Transcription failed');
      }

      const data = await response.json();
      
      updateState({
        transcribedText: data.text,
        isTranscribing: false,
        progress: 100,
        status: "Transcription completed",
        error: null,
      });
      
      setTimeout(() => {
        updateState({ progress: 0 });
      }, 2000);
      
    } catch (error) {
      console.error('Transcription error:', error);
      updateState({
        isTranscribing: false,
        progress: 0,
        status: "Transcription failed",
        error: error instanceof Error ? error.message : "Transcription failed",
      });
    }
  };

  const handleSummarize = async () => {
    if (!state.transcribedText || !state.apiKey) return;
    
    updateState({
      isProcessing: true,
      progress: 30,
      status: "Processing with Claude...",
    });

    try {
      const prompt = `Please provide a comprehensive summary of the following transcribed audio content in approximately ${state.wordLimit} words. Focus on the main ideas, key points, and important details.`;

      updateState({ progress: 60 });

      const response = await fetch('/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: state.transcribedText,
          prompt: prompt,
          apiKey: state.apiKey,
          wordLimit: state.wordLimit,
          outputFormat: state.outputFormat,
        }),
      });

      if (!response.ok) {
        throw new Error('Processing failed');
      }

      const data = await response.json();
      
      const newHistory = [...state.processHistory, { 
        prompt: `Summarize in ${state.wordLimit} words`, 
        result: data.result 
      }];
      
      updateState({
        processHistory: newHistory,
        currentHistoryIndex: newHistory.length - 1,
        isProcessing: false,
        progress: 100,
        status: "Processing completed",
        error: null,
      });

      setTimeout(() => {
        updateState({ progress: 0 });
      }, 2000);
      
    } catch (error) {
      console.error('Processing error:', error);
      updateState({
        isProcessing: false,
        progress: 0,
        status: "Processing failed",
        error: error instanceof Error ? error.message : "Processing failed",
      });
    }
  };

  const handleCleanText = async () => {
    if (!state.transcribedText || !state.apiKey) return;
    
    updateState({
      isProcessing: true,
      progress: 30,
      status: "Cleaning transcription...",
    });

    try {
      const response = await fetch('/api/clean', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: state.transcribedText,
          apiKey: state.apiKey,
        }),
      });

      if (!response.ok) {
        throw new Error('Text cleaning failed');
      }

      const data = await response.json();
      updateState({
        transcribedText: data.cleaned,
        isProcessing: false,
        progress: 100,
        status: "Text cleaned successfully",
        error: null,
      });

      setTimeout(() => {
        updateState({ progress: 0 });
      }, 2000);
      
    } catch (error) {
      console.error('Clean text error:', error);
      updateState({
        isProcessing: false,
        progress: 0,
        status: "Text cleaning failed",
        error: error instanceof Error ? error.message : "Text cleaning failed",
      });
    }
  };

  const handleNetworkPlot = async () => {
    if (!state.transcribedText || !state.apiKey) return;
    
    const clusters = prompt("Enter number of clusters (2-10):", "5");
    const numClusters = clusters ? Math.max(2, Math.min(10, parseInt(clusters) || 5)) : 5;
    
    updateState({
      isProcessing: true,
      progress: 30,
      status: "Generating network plot...",
    });

    try {
      const response = await fetch('/api/network', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: state.transcribedText,
          clusters: numClusters,
        }),
      });

      if (!response.ok) {
        throw new Error('Network plot generation failed');
      }

      const data = await response.json();
      
      updateState({
        isProcessing: false,
        progress: 100,
        status: data.message || "Network plot generation completed",
        error: null,
      });

      alert(`${data.message}\n\nFor full network plot functionality with Word2Vec embeddings and interactive visualization, please use the desktop application.`);

      setTimeout(() => {
        updateState({ progress: 0 });
      }, 2000);
      
    } catch (error) {
      console.error('Network plot error:', error);
      updateState({
        isProcessing: false,
        progress: 0,
        status: "Network plot generation failed",
        error: error instanceof Error ? error.message : "Network plot generation failed",
      });
    }
  };

  const handleSemanticSummary = async () => {
    if (!state.transcribedText || !state.apiKey) return;
    
    updateState({
      isProcessing: true,
      progress: 30,
      status: "Generating semantic summary...",
    });

    try {
      const response = await fetch('/api/semantic-summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: state.transcribedText,
          apiKey: state.apiKey,
        }),
      });

      if (!response.ok) {
        throw new Error('Semantic summary generation failed');
      }

      const data = await response.json();
      
      updateState({
        semanticSummary: data.summary,
        isProcessing: false,
        progress: 100,
        status: "Semantic summary generated successfully",
        error: null,
      });

      setTimeout(() => {
        updateState({ progress: 0 });
      }, 2000);
      
    } catch (error) {
      console.error('Semantic summary error:', error);
      updateState({
        isProcessing: false,
        progress: 0,
        status: "Semantic summary generation failed",
        error: error instanceof Error ? error.message : "Semantic summary generation failed",
      });
    }
  };

  const handleTranslate = async () => {
    if (!state.transcribedText || !state.apiKey || state.targetLanguage === 'None') return;
    
    updateState({
      isProcessing: true,
      progress: 30,
      status: `Translating to ${state.targetLanguage}...`,
    });

    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: state.transcribedText,
          apiKey: state.apiKey,
          targetLanguage: state.targetLanguage,
          translationStyle: state.translationStyle,
          preserveFormatting: state.preserveFormatting,
          outputFormat: state.outputFormat,
        }),
      });
      if (!response.ok) throw new Error('Translation failed');
      const data = await response.json();
      updateState({
        transcribedText: data.result || data.translation,
        isProcessing: false,
        progress: 100,
        status: `Translation to ${state.targetLanguage} completed`,
        error: null,
      });
      setTimeout(() => { updateState({ progress: 0 }); }, 2000);
    } catch (error) {
      console.error('Translation error:', error);
      updateState({
        isProcessing: false,
        progress: 0,
        status: 'Translation failed',
        error: error instanceof Error ? error.message : 'Translation failed',
      });
    }
  };

  const handleCustomPrompt = async () => {
    if (!state.transcribedText || !state.apiKey || !state.customPrompt) return;
    updateState({
      isProcessing: true,
      progress: 30,
      status: "Processing custom prompt...",
    });
    try {
      const response = await fetch('/api/custom-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: state.transcribedText,
          apiKey: state.apiKey,
          customPrompt: state.customPrompt,
        }),
      });
      if (!response.ok) throw new Error('Custom prompt failed');
      const data = await response.json();
      const newHistory = [...state.processHistory, {
        prompt: state.customPrompt,
        result: data.result
      }];
      updateState({
        processHistory: newHistory,
        currentHistoryIndex: newHistory.length - 1,
        isProcessing: false,
        progress: 100,
        status: "Custom prompt processed",
        error: null,
      });
      setTimeout(() => { updateState({ progress: 0 }); }, 2000);
    } catch (error) {
      console.error('Custom prompt error:', error);
      updateState({
        isProcessing: false,
        progress: 0,
        status: "Custom prompt failed",
        error: error instanceof Error ? error.message : "Custom prompt failed",
      });
    }
  };

  const canTranscribe = state.audioFilePath && state.modelLoaded && !state.isTranscribing;
  const canProcess = state.transcribedText && state.apiKey && !state.isProcessing;

  return (
    <div className="min-h-screen bg-background bg-pattern">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground">
              Audio Analyzer
            </h1>
            <p className="text-lg text-muted-foreground mt-2">
              Transcribe and analyze audio with AI
            </p>
          </div>
          <Button
            onClick={() => setIsNewAudioDialogOpen(true)}
            className="btn-modern glow-primary hover:scale-105 transition-all text-lg px-8 py-3"
            size="lg"
          >
            ➕ New Audio
          </Button>
        </div>

        {/* Error Alert */}
        {state.error && (
          <Alert className="mb-6 border-destructive gradient-card backdrop-blur-lg">
            <AlertDescription className="flex items-center justify-between">
              <span>{state.error}</span>
              <button 
                onClick={() => updateState({ error: null })}
                className="ml-2 text-destructive hover:text-destructive/80 transition-colors"
              >
                ✕
              </button>
            </AlertDescription>
          </Alert>
        )}

        {/* Main Content */}
        {state.audioFilePath ? (
          <div className="space-y-6">
            {/* Current Audio Info */}
            <Card className="gradient-card border-border/50 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-2xl">🎵</span>
                  <div>
                    <h3 className="font-semibold">{state.audioFileName}</h3>
                    <p className="text-sm text-muted-foreground">
                      Model: {state.whisperModel} • {state.modelLoaded ? "Ready" : "Not loaded"}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleTranscribe}
                    disabled={!canTranscribe}
                    className="btn-primary"
                  >
                    🎙️ Transcribe
                  </Button>
                  <Button
                    onClick={handleTranslate}
                    disabled={!canProcess}
                    className="btn-primary"
                  >
                    🌐 Translate
                  </Button>
                  <Button
                    onClick={handleSummarize}
                    disabled={!canProcess}
                    className="btn-primary"
                  >
                    📝 Summarize
                  </Button>
                </div>
              </div>
              {state.progress > 0 && (
                <div className="mt-4">
                  <div className="w-full bg-muted rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${state.progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    {state.status}
                  </p>
                </div>
              )}
            </Card>

            {/* Three Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[600px]">
              {/* Left: Transcription */}
              <Card className="gradient-card border-border/50">
                <TranscriptionTab state={state} updateState={updateState} />
              </Card>

              {/* Center: Processed Result */}
              <Card className="gradient-card border-border/50">
                <ProcessedResultTab state={state} updateState={updateState} />
              </Card>

              {/* Right: Visualization Panel */}
              <Card className="gradient-card border-border/50 flex flex-col">
                <div className="p-4 border-b border-border/50">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <span>🕸️</span>
                    Visualizations
                  </h3>
                </div>
                
                <div className="flex-1 flex flex-col">
                  {/* Network Plot Section */}
                  <div className="flex-1 p-4 border-b border-border/50">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium">Semantic Network</h4>
                      <div className="flex gap-2">
                        <Button
                          onClick={handleCleanText}
                          disabled={!canProcess}
                          size="sm"
                          variant="outline"
                        >
                          🧹 Clean
                        </Button>
                        <Button
                          onClick={handleNetworkPlot}
                          disabled={!canProcess}
                          size="sm"
                          variant="outline"
                        >
                          ↻ Generate
                        </Button>
                      </div>
                    </div>
                    <div className="border border-border/50 rounded-lg p-4 min-h-[200px] flex items-center justify-center bg-muted/20">
                      {state.networkPlotUrl ? (
                        <img 
                          src={state.networkPlotUrl} 
                          alt="Semantic Network Plot" 
                          className="max-w-full max-h-full object-contain"
                        />
                      ) : (
                        <div className="text-center text-muted-foreground">
                          <div className="text-2xl mb-2">🕸️</div>
                          <p className="text-sm">No network generated yet</p>
                          <p className="text-xs mt-1">Click Generate to create visualization</p>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Semantic Summary Section */}
                  <div className="flex-1 p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium">Semantic & Tone Summary</h4>
                      <Button
                        onClick={handleSemanticSummary}
                        disabled={!canProcess}
                        size="sm"
                        variant="outline"
                      >
                        ✨ Generate
                      </Button>
                    </div>
                    
                    <div className="border border-border/50 rounded-lg p-4 min-h-[150px] bg-muted/20">
                      {state.semanticSummary ? (
                        <div className="text-sm">
                          <p className="leading-relaxed">{state.semanticSummary}</p>
                          <p className="text-xs text-muted-foreground mt-2">
                            Generated at {new Date().toLocaleTimeString()}
                          </p>
                        </div>
                      ) : (
                        <div className="text-center text-muted-foreground">
                          <div className="text-2xl mb-2">📊</div>
                          <p className="text-sm">No summary generated yet</p>
                          <p className="text-xs mt-1">Click Generate to create summary</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Custom Prompt Section */}
            <Card className="gradient-card border-border/50 mt-6 p-4">
              <h3 className="text-lg font-semibold mb-2">Custom Prompt</h3>
              <textarea
                className="w-full border rounded p-2 mb-2"
                rows={3}
                value={state.customPrompt}
                onChange={e => updateState({ customPrompt: e.target.value })}
                placeholder="Enter your custom prompt. Use {text} to insert the transcript."
              />
              <Button
                onClick={handleCustomPrompt}
                disabled={!canProcess || !state.customPrompt}
                className="btn-primary"
              >
                🧠 Process Custom Prompt
              </Button>
            </Card>

            {/* Bottom Toolbar */}
            <Card className="gradient-card border-border/50 p-4">
              <ToolbarButtons state={state} updateState={updateState} />
            </Card>
          </div>
        ) : (
          /* Empty State */
          <Card className="gradient-card border-border/50 p-12 text-center">
            <div className="space-y-4">
              <div className="text-6xl">🎵</div>
              <h2 className="text-2xl font-semibold">No Audio Selected</h2>
              <p className="text-muted-foreground">
                Click &quot;New Audio&quot; to get started with transcription and analysis
              </p>
              <Button
                onClick={() => setIsNewAudioDialogOpen(true)}
                className="btn-modern glow-primary hover:scale-105 transition-all"
                size="lg"
              >
                ➕ New Audio
              </Button>
            </div>
          </Card>
        )}
      </div>

      {/* New Audio Dialog */}
      <NewAudioDialog
        open={isNewAudioDialogOpen}
        onOpenChange={setIsNewAudioDialogOpen}
        updateState={updateState}
        onCreateAudio={() => {
          // Any additional logic when creating audio
        }}
      />
    </div>
  );
}