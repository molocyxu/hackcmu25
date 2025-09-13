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
      const formData = new FormData();
      
      if (state.audioFilePath.startsWith('blob:')) {
        const response = await fetch(state.audioFilePath);
        const blob = await response.blob();
        formData.append('audio', blob, state.audioFileName);
      }
      
      formData.append('model', state.whisperModel);
      
      updateState({ progress: 50 });

      const response = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Transcription failed');
      }

      const data = await response.json();
      
      updateState({
        transcribedText: data.transcription,
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
        transcribedText: data.result,
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
                    onClick={handleCleanText}
                    disabled={!canProcess}
                    variant="outline"
                    size="sm"
                  >
                    🧹 Clean
                  </Button>
                  <Button
                    onClick={handleNetworkPlot}
                    disabled={!canProcess}
                    variant="outline"
                    size="sm"
                  >
                    🕸️ Network
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

            {/* Side by Side Content */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[600px]">
              {/* Transcription */}
              <Card className="gradient-card border-border/50">
                <TranscriptionTab state={state} updateState={updateState} />
              </Card>

              {/* Processed Result */}
              <Card className="gradient-card border-border/50">
                <ProcessedResultTab state={state} updateState={updateState} />
              </Card>
            </div>

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