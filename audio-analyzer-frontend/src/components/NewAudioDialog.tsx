"use client";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
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
  const [cleanText, setCleanText] = useState(false);
  
  // Local state for dialog
  const [localAudioFile, setLocalAudioFile] = useState<string | null>(null);
  const [localAudioFileName, setLocalAudioFileName] = useState("");
  const [localRecordedFile, setLocalRecordedFile] = useState<string | null>(null);
  const [localWhisperModel, setLocalWhisperModel] = useState("base");
  const [localModelLoaded, setLocalModelLoaded] = useState(false);
  const [localApiKey, setLocalApiKey] = useState("");
  const [localWordLimit, setLocalWordLimit] = useState(500);
  const [localOutputFormat, setLocalOutputFormat] = useState("Markdown");
  const [summaryTemplate, setSummaryTemplate] = useState("Standard");
  const [summaryTone, setSummaryTone] = useState("Professional");
  
  // Translation state
  const [targetLanguage, setTargetLanguage] = useState("None");
  const [translationStyle, setTranslationStyle] = useState("Natural");
  const [preserveFormatting, setPreserveFormatting] = useState(true);
  
  // Time segment state
  const [useFullAudio, setUseFullAudio] = useState(true);
  const [startTime, setStartTime] = useState("0");
  const [endTime, setEndTime] = useState("0");
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  
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
      
      // Get audio duration
      const audio = new Audio(url);
      audio.addEventListener('loadedmetadata', () => {
        const duration = audio.duration;
        setAudioDuration(duration);
        if (useFullAudio) {
          setEndTime(duration.toString());
        }
      });
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    });
    const data = await response.json();
    console.log('[DEBUG] loadModel response:', data);
    if (response.ok && data.loaded) {
      setLocalModelLoaded(true);
    } else {
      console.error('[DEBUG] Model load failed:', data.error);
      throw new Error(data.error || 'Model loading failed');
    }
  } catch (err) {
    console.error('[DEBUG] loadModel network error:', err);
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

  const handleUseFullAudioChange = (checked: boolean) => {
    setUseFullAudio(checked);
    if (checked && audioDuration) {
      setStartTime("0");
      setEndTime(audioDuration.toString());
    }
  };

  const handleTimeChange = (field: 'start' | 'end', value: string) => {
    if (field === 'start') {
      setStartTime(value);
    } else {
      setEndTime(value);
    }
    
    // If user manually changes time, uncheck full audio
    if (useFullAudio) {
      setUseFullAudio(false);
    }
  };

  const validateTimeSegment = (): boolean => {
    if (useFullAudio) return true;
    
    const start = parseFloat(startTime);
    const end = parseFloat(endTime);
    
    if (isNaN(start) || isNaN(end)) return false;
    if (start < 0 || end <= start) return false;
    if (audioDuration && end > audioDuration) return false;
    
    return true;
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
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

  // Timer effect for recording duration
  React.useEffect(() => {
    if (isRecording) {
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    };
  }, [isRecording]);

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
      targetLanguage,
      translationStyle,
      preserveFormatting,
      // Time segment features
      useFullAudio: useFullAudio,
      startTime: parseFloat(startTime) || 0,
      endTime: parseFloat(endTime) || 0,
      audioDuration: audioDuration,
      // Word timestamps for search
      wordTimestamps: [],
      searchTerm: "",
      searchResults: [],
    });
    onCreateAudio();
    onOpenChange(false);
  };

  const canCreate = (localAudioFile || localRecordedFile) && localModelLoaded;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-center">
            New Audio Analysis
          </DialogTitle>
        </DialogHeader>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
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
              
              {(localAudioFile || localRecordedFile) && (
                <>
                  <Separator className="my-4" />
                  
                  <div>
                    <Label>Time Segment Selection</Label>
                    
                    <div className="flex items-center space-x-2 mt-2">
                      <input
                        type="checkbox"
                        id="use-full-audio"
                        checked={useFullAudio}
                        onChange={(e) => handleUseFullAudioChange(e.target.checked)}
                        className="rounded"
                      />
                      <Label htmlFor="use-full-audio" className="text-sm">
                        Use full audio
                      </Label>
                    </div>
                    
                    {!useFullAudio && (
                      <div className="grid grid-cols-2 gap-2 mt-3">
                        <div>
                          <Label className="text-xs">Start (seconds)</Label>
                          <Input
                            type="number"
                            value={startTime}
                            onChange={(e) => handleTimeChange('start', e.target.value)}
                            placeholder="0"
                            className="mt-1"
                            min="0"
                            step="0.1"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">End (seconds)</Label>
                          <Input
                            type="number"
                            value={endTime}
                            onChange={(e) => handleTimeChange('end', e.target.value)}
                            placeholder="0"
                            className="mt-1"
                            min="0"
                            step="0.1"
                          />
                        </div>
                      </div>
                    )}
                    
                    {audioDuration && (
                      <div className="mt-2 space-y-1">
                        <p className="text-xs text-muted-foreground">
                          Valid range: 0 - {audioDuration.toFixed(1)}s ({formatDuration(audioDuration)})
                        </p>
                        {!useFullAudio && (
                          <p className="text-xs text-muted-foreground">
                            Duration: {validateTimeSegment() ? 
                              formatDuration(parseFloat(endTime) - parseFloat(startTime)) : 
                              'Invalid range'}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}
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

              {/* Moved audio player here */}
              {(localAudioFile || localRecordedFile) && (
                <div className="mt-4">
                  <Label>Preview & Listen</Label>
                  <audio
                    controls
                    src={localAudioFile || localRecordedFile || undefined}
                    className="w-full mt-2"
                  >
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}
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

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="template-dialog">Template</Label>
                  <Select
                    value={summaryTemplate}
                    onValueChange={setSummaryTemplate}
                  >
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Standard">Standard</SelectItem>
                      <SelectItem value="Executive Summary">Executive Summary</SelectItem>
                      <SelectItem value="Academic Paper">Academic Paper</SelectItem>
                      <SelectItem value="Meeting Minutes">Meeting Minutes</SelectItem>
                      <SelectItem value="Podcast Notes">Podcast Notes</SelectItem>
                      <SelectItem value="Lecture Notes">Lecture Notes</SelectItem>
                      <SelectItem value="Interview Summary">Interview Summary</SelectItem>
                      <SelectItem value="Technical Report">Technical Report</SelectItem>
                      <SelectItem value="News Article">News Article</SelectItem>
                      <SelectItem value="Research Brief">Research Brief</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="tone-dialog">Tone</Label>
                  <Select
                    value={summaryTone}
                    onValueChange={setSummaryTone}
                  >
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Professional">Professional</SelectItem>
                      <SelectItem value="Casual">Casual</SelectItem>
                      <SelectItem value="Academic">Academic</SelectItem>
                      <SelectItem value="Technical">Technical</SelectItem>
                      <SelectItem value="Creative">Creative</SelectItem>
                      <SelectItem value="Formal">Formal</SelectItem>
                      <SelectItem value="Conversational">Conversational</SelectItem>
                      <SelectItem value="Analytical">Analytical</SelectItem>
                      <SelectItem value="Persuasive">Persuasive</SelectItem>
                      <SelectItem value="Objective">Objective</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
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

          {/* Section 4: Translation */}
          <Card className="gradient-card border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <span className="text-primary">🌐</span>
                Translation
                <Badge variant="secondary" className="text-xs">Optional</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="target-language-dialog">Target Language</Label>
                <Select
                  value={targetLanguage}
                  onValueChange={setTargetLanguage}
                >
                  <SelectTrigger className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="None">None</SelectItem>
                    <SelectItem value="Spanish">Spanish</SelectItem>
                    <SelectItem value="French">French</SelectItem>
                    <SelectItem value="German">German</SelectItem>
                    <SelectItem value="Italian">Italian</SelectItem>
                    <SelectItem value="Portuguese">Portuguese</SelectItem>
                    <SelectItem value="Dutch">Dutch</SelectItem>
                    <SelectItem value="Russian">Russian</SelectItem>
                    <SelectItem value="Chinese (Simplified)">Chinese (Simplified)</SelectItem>
                    <SelectItem value="Chinese (Traditional)">Chinese (Traditional)</SelectItem>
                    <SelectItem value="Japanese">Japanese</SelectItem>
                    <SelectItem value="Korean">Korean</SelectItem>
                    <SelectItem value="Arabic">Arabic</SelectItem>
                    <SelectItem value="Hindi">Hindi</SelectItem>
                    <SelectItem value="Bengali">Bengali</SelectItem>
                    <SelectItem value="Turkish">Turkish</SelectItem>
                    <SelectItem value="Polish">Polish</SelectItem>
                    <SelectItem value="Vietnamese">Vietnamese</SelectItem>
                    <SelectItem value="Thai">Thai</SelectItem>
                    <SelectItem value="Indonesian">Indonesian</SelectItem>
                    <SelectItem value="Swedish">Swedish</SelectItem>
                    <SelectItem value="Norwegian">Norwegian</SelectItem>
                    <SelectItem value="Danish">Danish</SelectItem>
                    <SelectItem value="Finnish">Finnish</SelectItem>
                    <SelectItem value="Greek">Greek</SelectItem>
                    <SelectItem value="Hebrew">Hebrew</SelectItem>
                    <SelectItem value="Czech">Czech</SelectItem>
                    <SelectItem value="Hungarian">Hungarian</SelectItem>
                    <SelectItem value="Romanian">Romanian</SelectItem>
                    <SelectItem value="Ukrainian">Ukrainian</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="translation-style-dialog">Translation Style</Label>
                <Select
                  value={translationStyle}
                  onValueChange={setTranslationStyle}
                >
                  <SelectTrigger className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Natural">Natural</SelectItem>
                    <SelectItem value="Literal">Literal</SelectItem>
                    <SelectItem value="Professional">Professional</SelectItem>
                    <SelectItem value="Colloquial">Colloquial</SelectItem>
                    <SelectItem value="Technical">Technical</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="preserve-formatting"
                  checked={preserveFormatting}
                  onChange={(e) => setPreserveFormatting(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="preserve-formatting" className="text-sm">
                  Preserve original formatting
                </Label>
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
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    disabled={!canCreate}
                    className="btn-modern"
                    onClick={handleCreate}
                    style={!canCreate ? { pointerEvents: "none" } : {}}
                  >
                    Create
                  </Button>
                </span>
              </TooltipTrigger>
              {!canCreate && (
                <TooltipContent>
                  {!localModelLoaded
                    ? "Model is not loaded. Please load a model first."
                    : !(localAudioFile || localRecordedFile)
                    ? "Please upload or record an audio file."
                    : ""}
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        </div>
      </DialogContent>
    </Dialog>
  );
}