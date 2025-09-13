"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sidebar } from "./Sidebar";
import { TranscriptionTab } from "./TranscriptionTab";
import { ProcessedResultTab } from "./ProcessedResultTab";
import { ToolbarButtons } from "./ToolbarButtons";

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
    modelLoaded: true, // Set to true for demo purposes
    apiKey: "",
    wordLimit: 500,
    outputFormat: "Markdown",
    isTranscribing: false,
    isProcessing: false,
    progress: 0,
    status: "Ready",
    processHistory: [],
    currentHistoryIndex: -1,
    customPrompt: "Analyze the following text and provide insights:\n\n{text}",
  });

  const updateState = (updates: Partial<AudioAnalyzerState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div className="w-80 border-r bg-card">
        <Sidebar state={state} updateState={updateState} />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-6">
          <Card className="h-full">
            <Tabs defaultValue="transcription" className="h-full flex flex-col">
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="transcription" className="flex items-center gap-2">
                  📝 Transcription
                </TabsTrigger>
                <TabsTrigger value="result" className="flex items-center gap-2">
                  ✨ Processed Result
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="transcription" className="flex-1">
                <TranscriptionTab state={state} updateState={updateState} />
              </TabsContent>
              
              <TabsContent value="result" className="flex-1">
                <ProcessedResultTab state={state} updateState={updateState} />
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Bottom Toolbar */}
        <div className="border-t bg-card p-4">
          <ToolbarButtons state={state} updateState={updateState} />
        </div>
      </div>
    </div>
  );
}