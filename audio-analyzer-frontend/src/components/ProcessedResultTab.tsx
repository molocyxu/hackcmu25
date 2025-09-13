"use client";

import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AudioAnalyzerState } from "./AudioAnalyzer";

interface ProcessedResultTabProps {
  state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
}

export function ProcessedResultTab({ state, updateState }: ProcessedResultTabProps) {
  const currentResult = state.currentHistoryIndex >= 0 
    ? state.processHistory[state.currentHistoryIndex]?.result || ""
    : "";

  const currentPrompt = state.currentHistoryIndex >= 0
    ? state.processHistory[state.currentHistoryIndex]?.prompt || state.customPrompt
    : state.customPrompt;

  const navigatePrev = () => {
    if (state.currentHistoryIndex > 0) {
      updateState({ currentHistoryIndex: state.currentHistoryIndex - 1 });
    }
  };

  const navigateNext = () => {
    if (state.currentHistoryIndex < state.processHistory.length - 1) {
      updateState({ currentHistoryIndex: state.currentHistoryIndex + 1 });
    }
  };

  const processCustomPrompt = async () => {
    if (!state.transcribedText || !state.apiKey) return;

    updateState({
      isProcessing: true,
      status: "Processing custom prompt...",
    });

    try {
      const processedPrompt = state.customPrompt.replace("{text}", state.transcribedText);

      const response = await fetch('/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: state.transcribedText,
          prompt: processedPrompt,
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
        prompt: state.customPrompt, 
        result: data.result 
      }];
      
      updateState({
        processHistory: newHistory,
        currentHistoryIndex: newHistory.length - 1,
        isProcessing: false,
        status: "Custom prompt processed",
      });
      
    } catch (error) {
      console.error('Processing error:', error);
      updateState({
        isProcessing: false,
        status: "Custom prompt processing failed",
      });
    }
  };

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Upper Section - API Output */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={navigatePrev}
                disabled={state.currentHistoryIndex <= 0}
              >
                ◀
              </Button>
              <Badge variant="outline">
                {state.processHistory.length > 0 
                  ? `${state.currentHistoryIndex + 1}/${state.processHistory.length}`
                  : "0/0"
                }
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={navigateNext}
                disabled={state.currentHistoryIndex >= state.processHistory.length - 1}
              >
                ▶
              </Button>
            </div>
            <Badge 
              variant={currentResult ? "default" : "secondary"}
              className={currentResult ? "bg-green-500" : ""}
            >
              {currentResult ? "Processing complete" : "No processed result yet"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="flex-1 pt-0">
          <div className="relative h-full">
            <Textarea
              value={currentResult}
              readOnly
              placeholder="Processed results will appear here..."
              className="h-full resize-none text-sm leading-relaxed"
            />
            {state.isProcessing && (
              <div className="absolute inset-0 bg-background/50 flex items-center justify-center">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                  <span className="text-sm">Processing...</span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Lower Section - Custom Prompt */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Custom Prompt (use {"{text}"} for transcription)</h3>
          </div>
        </CardHeader>
        <CardContent className="flex-1 pt-0 space-y-3">
          <Textarea
            value={state.customPrompt}
            onChange={(e) => updateState({ customPrompt: e.target.value })}
            placeholder="Enter your custom prompt here..."
            className="flex-1 resize-none text-sm"
            rows={4}
          />
          <Button
            onClick={processCustomPrompt}
            disabled={!state.transcribedText || !state.apiKey || state.isProcessing}
            className="w-full"
          >
            ▶ Process Custom Prompt
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}