"use client";

import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { AudioAnalyzerState } from "./AudioAnalyzer";
import { formatTime } from "@/lib/utils";

interface NewAudioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  // state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
  onCreateAudio: () => void;
}

export function NewAudioDialog({ 
  open, 
  onOpenChange, 
  updateState, 
  onCreateAudio 
}: NewAudioDialogProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [generateNetworkPlot, setGenerateNetworkPlot] = useState(false);
  
  // Local state for dialog
  const [localAudioFile, setLocalAudioFile] = useState<string | null>(null);
  const [localAudioFileName, setLocalAudioFileName] = useState("");
  const [localRecordedFile, setLocalRecordedFile] = useState<string | null>(null);
  const [localWhisperModel, setLocalWhisperModel] = useState("base");
  const [localModelLoaded, setLocalModelLoaded] = useState(false);
  const [localApiKey, setLocalApiKey] = useState("");
  const [localWordLimit, setLocalWordLimit] = useState(500);
  const [localOutputFormat, setLocalOutputFormat] = useState("Markdown");
  
  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Reset local state when dialog opens
  React.useEffect(() => {
    if (open) {
      setLocalAudioFile(null);
      setLocalAudioFileName("");
      setLocalRecordedFile(null);
      setLocalWhisperModel("base");
      setLocalModelLoaded(false);
      setLocalApiKey("");
      setLocalWordLimit(500);
      setLocalOutputFormat("Markdown");
      setGenerateNetworkPlot(false);
      setIsRecording(false);
      setRecordingDuration(0);
    }
  }, [open]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setLocalAudioFile(url);
      setLocalAudioFileName(file.name);
    }
  };

  const checkModelStatus = async (model: string) => {
    try {
      const response = await fetch(`/api/model?model=${model}`);
      const data = await response.json();
      
      if (response.ok) {
        setLocalModelLoaded(data.loaded);
      } else {
        setLocalModelLoaded(false);
      }
    } catch {
      setLocalModelLoaded(false);
    }
  };

  const loadModel = async (model: string) => {
    setLocalModelLoaded(false);
    
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
        setLocalModelLoaded(true);
      } else {
        throw new Error(data.error || 'Model loading failed');
      }
    } catch {
      setLocalModelLoaded(false);
    }
  };

  // Check model status when model changes
  React.useEffect(() => {
    if (open) {
      checkModelStatus(localWhisperModel);
    }
  }, [localWhisperModel, open]);

  const handleModelChange = (value: string) => {
    setLocalWhisperModel(value);
    setLocalModelLoaded(false);
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
        
        const audioUrl = URL.createObjectURL(audioBlob);
        const filename = `recording_${Date.now()}.${mediaRecorder.mimeType.includes('webm') ? 'webm' : 'wav'}`;
        
        // Automatically use the recording
        setLocalRecordedFile(audioUrl);
        setLocalAudioFile(audioUrl);
        setLocalAudioFileName(filename);

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setRecordingDuration(0);

      let duration = 0;
      recordingTimerRef.current = setInterval(() => {
        duration += 1;
        setRecordingDuration(duration);
      }, 1000);

    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      setIsRecording(false);
    }
  };

  const handleRecordToggle = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, [isRecording]);

  const handleCreate = () => {
    // Update the main state with the dialog values
    updateState({
      audioFilePath: localAudioFile,
      audioFileName: localAudioFileName,
      recordedFilePath: localRecordedFile,
      whisperModel: localWhisperModel,
      modelLoaded: localModelLoaded,
      apiKey: localApiKey,
      wordLimit: localWordLimit,
      outputFormat: localOutputFormat,
      transcribedText: "",
      processHistory: [],
      currentHistoryIndex: -1,
      status: "Ready to transcribe",
    });
    
    onCreateAudio();
    onOpenChange(false);
  };

  const canCreate = (localAudioFile || localRecordedFile) && localModelLoaded;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-center">
            New Audio Analysis
          </DialogTitle>
        </DialogHeader>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Section 1: Audio */}
          <Card className="gradient-card border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <span className="text-primary">🎵</span>
                Audio
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Upload File</Label>
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full mt-2"
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
                {localAudioFileName && (
                  <p className="text-sm text-muted-foreground mt-2">
                    {localAudioFileName}
                  </p>
                )}
              </div>
              
              <Separator className="my-4" />
              
              <div>
                <Label>Or Record Audio</Label>
                <Button
                  onClick={handleRecordToggle}
                  className="w-full mt-2"
                  variant={isRecording ? "destructive" : "outline"}
                >
                  {isRecording ? "⏹️ Stop Recording" : "🎤 Start Recording"}
                </Button>
                
                {isRecording && (
                  <div className="text-center mt-2">
                    <Badge variant="destructive" className="animate-pulse">
                      Recording: {formatTime(recordingDuration)}
                    </Badge>
                  </div>
                )}
                
                {localRecordedFile && (
                  <p className="text-sm text-green-600 mt-2">
                    ✓ Recording ready to use
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Model Selection */}
          <Card className="gradient-card border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <span className="text-primary">🤖</span>
                Select Model
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="model-select">Whisper Model</Label>
                <Select
                  value={localWhisperModel}
                  onValueChange={handleModelChange}
                >
                  <SelectTrigger className="mt-2">
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
                  <Badge variant={localModelLoaded ? "default" : "secondary"}>
                    {localModelLoaded ? "🟢 Ready" : "⚪ Not loaded"}
                  </Badge>
                  {!localModelLoaded && (
                    <Button
                      onClick={() => loadModel(localWhisperModel)}
                      size="sm"
                      variant="outline"
                    >
                      Load Model
                    </Button>
                  )}
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="network-plot"
                  checked={generateNetworkPlot}
                  onChange={(e) => setGenerateNetworkPlot(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="network-plot" className="text-sm">
                  Generate network plot
                </Label>
              </div>
            </CardContent>
          </Card>

          {/* Section 3: AI Processing (Optional) */}
          <Card className="gradient-card border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <span className="text-primary">✨</span>
                Process with AI
                <Badge variant="secondary" className="text-xs">Optional</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="api-key-dialog">Anthropic API Key</Label>
                <Input
                  id="api-key-dialog"
                  type="password"
                  value={localApiKey}
                  onChange={(e) => setLocalApiKey(e.target.value)}
                  placeholder="Enter API key..."
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="word-limit-dialog">Word Limit</Label>
                <Input
                  id="word-limit-dialog"
                  type="number"
                  value={localWordLimit}
                  onChange={(e) => setLocalWordLimit(parseInt(e.target.value) || 500)}
                  placeholder="500"
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="output-format-dialog">Output Format</Label>
                <Select
                  value={localOutputFormat}
                  onValueChange={setLocalOutputFormat}
                >
                  <SelectTrigger className="mt-2">
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
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={!canCreate}
            className="btn-modern"
          >
            Create
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}