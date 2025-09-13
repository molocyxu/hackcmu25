"use client";

import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AudioAnalyzerState } from "./AudioAnalyzer";

interface TranscriptionTabProps {
  state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
}

export function TranscriptionTab({ state, updateState }: TranscriptionTabProps) {
  const wordCount = state.transcribedText ? state.transcribedText.split(' ').filter(word => word.length > 0).length : 0;
  const charCount = state.transcribedText.length;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Badge variant="outline">
              Words: {wordCount}
            </Badge>
            <Badge variant="outline">
              Characters: {charCount}
            </Badge>
          </div>
          <Badge 
            variant={state.transcribedText ? "default" : "secondary"}
            className={state.transcribedText ? "bg-green-500" : ""}
          >
            {state.transcribedText ? "Transcription complete" : "No transcription yet"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        <Textarea
          value={state.transcribedText}
          onChange={(e) => updateState({ transcribedText: e.target.value })}
          placeholder="Transcribed text will appear here..."
          className="h-full resize-none text-sm leading-relaxed"
          readOnly={state.isTranscribing}
        />
        {state.isTranscribing && (
          <div className="absolute inset-0 bg-background/50 flex items-center justify-center">
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
              <span className="text-sm">Transcribing...</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}