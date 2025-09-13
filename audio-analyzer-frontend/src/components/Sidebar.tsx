"use client";

import React, { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { AudioAnalyzerState } from "./AudioAnalyzer";
import { formatTime } from "@/lib/utils";

interface SidebarProps {
  state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
}

export function Sidebar({ state, updateState }: SidebarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      updateState({
        audioFilePath: url,
        audioFileName: file.name,
        transcribedText: "",
        status: `${file.type.includes('video') ? 'Video' : 'Audio'} file selected: ${file.name}`,
      });
    }
  };

  const checkModelStatus = async (model: string) => {
    try {
      const response = await fetch(`/api/model?model=${model}`);
      const data = await response.json();
      
      if (response.ok) {
        updateState({ 
          modelLoaded: data.loaded,
          status: data.loaded ? `Model ${model} ready` : `Model ${model} not loaded`
        });
      } else {
        console.error('Model check failed:', data.error);
        updateState({ 
          modelLoaded: false,
          status: `Model check failed: ${data.error}`
        });
      }
    } catch (error) {
      console.error('Model check error:', error);
      updateState({ 
        modelLoaded: false,
        status: 'Model check failed'
      });
    }
  };

  const loadModel = async (model: string) => {
    updateState({ 
      modelLoaded: false,
      status: `Loading ${model} model...`
    });

    try {
      const response = await fetch('/api/model', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model }),
      });

      const data = await response.json();
      
      if (response.ok) {
        updateState({ 
          modelLoaded: true,
          status: `Model ${model} loaded successfully`
        });
      } else {
        throw new Error(data.error || 'Model loading failed');
      }
    } catch (error) {
      console.error('Model loading error:', error);
      updateState({ 
        modelLoaded: false,
        status: `Model loading failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  };

  // Check model status when component mounts or model changes
  React.useEffect(() => {
    checkModelStatus(state.whisperModel);
  }, [state.whisperModel]);

  const handleModelChange = (value: string) => {
    updateState({ whisperModel: value, modelLoaded: false });
    // Model status will be checked by useEffect
  };

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleRecordToggle = async () => {
    if (state.isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      recordingChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/wav'
      });
      
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordingChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(recordingChunksRef.current, { 
          type: mediaRecorder.mimeType 
        });
        
        // Create a file URL for the recording
        const audioUrl = URL.createObjectURL(audioBlob);
        const filename = `recording_${Date.now()}.${mediaRecorder.mimeType.includes('webm') ? 'webm' : 'wav'}`;
        
        updateState({
          recordedFilePath: audioUrl,
          status: `Recording saved: ${filename}`,
        });

        // Clean up the media stream
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start(1000); // Collect data every second
      
      updateState({
        isRecording: true,
        recordingDuration: 0,
        status: "Recording started...",
      });

      // Start the timer
      let duration = 0;
      recordingTimerRef.current = setInterval(() => {
        duration += 1;
        updateState({ recordingDuration: duration });
      }, 1000);

    } catch (error) {
      console.error('Failed to start recording:', error);
      updateState({
        status: `Recording failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && state.isRecording) {
      mediaRecorderRef.current.stop();
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      updateState({
        isRecording: false,
        status: "Processing recording...",
      });
    }
  };

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && state.isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const handleTranscribe = async () => {
    if (!state.audioFilePath) return;
    
    updateState({
      isTranscribing: true,
      progress: 10,
      status: "Transcribing audio...",
    });

    try {
      // Create FormData with the audio file
      const formData = new FormData();
      
      // If it's a blob URL, we need to fetch it first
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
      
      // Reset progress after a delay
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

      // Reset progress after a delay
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

  const canTranscribe = state.audioFilePath && state.modelLoaded && !state.isTranscribing;
  const canProcess = state.transcribedText && state.apiKey && !state.isProcessing;

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-chart-2 bg-clip-text text-transparent">
            Audio Analyzer
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Transcribe and analyze audio with AI
          </p>
        </div>

        {/* Step 1: File Selection */}
        <Card className="gradient-card border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-primary">📁</span>
              Step 1: Select Audio File
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={() => fileInputRef.current?.click()}
              className="w-full btn-modern glow-primary hover:scale-105 transition-all"
              variant="outline"
            >
              📁 Choose Audio File
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,video/*"
              onChange={handleFileSelect}
              className="hidden"
            />
            <p className="text-sm text-muted-foreground">
              {state.audioFileName || "No file selected"}
            </p>
          </CardContent>
        </Card>

        {/* Recording Section */}
        <Card className="gradient-card border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-primary">🎤</span>
              Or Record Audio
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleRecordToggle}
              className="w-full glow-primary hover:scale-105 transition-all"
              variant={state.isRecording ? "destructive" : "outline"}
            >
              {state.isRecording ? "⏹️ Stop Recording" : "🎤 Start Recording"}
            </Button>
            
            {state.isRecording && (
              <div className="text-center">
                <Badge variant="destructive" className="animate-pulse">
                  Recording: {formatTime(state.recordingDuration)}
                </Badge>
              </div>
            )}
            
            {state.recordedFilePath && (
              <Button
                onClick={() => updateState({ 
                  audioFilePath: state.recordedFilePath,
                  audioFileName: `recording_${Date.now()}.webm`,
                  transcribedText: "",
                  status: "Using recording as input"
                })}
                className="w-full"
                variant="secondary"
                size="sm"
              >
                📂 Use Recording
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Step 2: Transcription */}
        <Card className="gradient-card border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-primary">📝</span>
              Step 2: Transcribe Audio
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="model-select">Whisper Model</Label>
              <Select
                value={state.whisperModel}
                onValueChange={handleModelChange}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tiny">Tiny</SelectItem>
                  <SelectItem value="base">Base</SelectItem>
                  <SelectItem value="small">Small</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="large">Large</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant={state.modelLoaded ? "default" : "secondary"}>
                  {state.modelLoaded ? "🟢 Ready" : "⚪ Not loaded"}
                </Badge>
                {!state.modelLoaded && (
                  <Button
                    onClick={() => loadModel(state.whisperModel)}
                    size="sm"
                    variant="outline"
                  >
                    Load Model
                  </Button>
                )}
              </div>
            </div>

            <Button
              onClick={handleTranscribe}
              disabled={!canTranscribe}
              className="w-full btn-modern glow-primary hover:scale-105 transition-all disabled:opacity-50 disabled:hover:scale-100"
            >
              🎙️ Transcribe
            </Button>
          </CardContent>
        </Card>

        {/* Step 3: AI Processing */}
        <Card className="gradient-card border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-primary">✨</span>
              Step 3: Process with AI
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="api-key">Anthropic API Key</Label>
              <div className="flex gap-2">
                <Input
                  id="api-key"
                  type="password"
                  value={state.apiKey}
                  onChange={(e) => updateState({ apiKey: e.target.value })}
                  placeholder="Enter API key..."
                  className="flex-1"
                />
                <Button
                  onClick={() => updateState({ status: "API key saved" })}
                  size="sm"
                  disabled={!state.apiKey}
                >
                  Save
                </Button>
              </div>
            </div>

            <div>
              <Label htmlFor="word-limit">Word Limit</Label>
              <Input
                id="word-limit"
                type="number"
                value={state.wordLimit}
                onChange={(e) => updateState({ wordLimit: parseInt(e.target.value) || 500 })}
                placeholder="500"
              />
            </div>

            <div>
              <Label htmlFor="output-format">Output Format</Label>
              <Select
                value={state.outputFormat}
                onValueChange={(value) => updateState({ outputFormat: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Markdown">Markdown</SelectItem>
                  <SelectItem value="Plain Text">Plain Text</SelectItem>
                  <SelectItem value="JSON">JSON</SelectItem>
                  <SelectItem value="Bullet Points">Bullet Points</SelectItem>
                  <SelectItem value="LaTeX PDF">LaTeX PDF</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleSummarize}
              disabled={!canProcess}
              className="w-full btn-modern glow-primary hover:scale-105 transition-all disabled:opacity-50 disabled:hover:scale-100"
            >
              📝 Summarize
            </Button>
          </CardContent>
        </Card>

        {/* Progress Section */}
        {state.progress > 0 && (
          <Card className="gradient-card border-border/50">
            <CardContent className="pt-6">
              <Progress value={state.progress} className="mb-2" />
              <p className="text-sm text-center text-muted-foreground">
                {state.status}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </ScrollArea>
  );
}