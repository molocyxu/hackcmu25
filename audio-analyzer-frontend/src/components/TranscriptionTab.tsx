"use client";

import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioAnalyzerState } from "./AudioAnalyzer";

interface TranscriptionTabProps {
  state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
  onSearchWord?: () => void;
  formatTimestamp?: (seconds: number) => string;
}

export function TranscriptionTab({ state, updateState, onSearchWord, formatTimestamp }: TranscriptionTabProps) {
  const wordCount = state.transcribedText ? state.transcribedText.split(' ').filter(word => word.length > 0).length : 0;
  const charCount = state.transcribedText ? state.transcribedText.length : 0;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchWord?.();
  };

  const clearSearch = () => {
    updateState({ searchTerm: "", searchResults: [] });
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between mb-3">
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
        
        {/* Word Search */}
        {state.wordTimestamps.length > 0 && (
          <div className="space-y-2">
            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <Input
                type="text"
                placeholder="Search for words/phrases..."
                value={state.searchTerm}
                onChange={(e) => updateState({ searchTerm: e.target.value })}
                className="flex-1"
              />
              <Button type="submit" size="sm" variant="outline">
                🔍
              </Button>
              {state.searchTerm && (
                <Button onClick={clearSearch} size="sm" variant="outline">
                  Clear
                </Button>
              )}
            </form>
            
            {state.searchResults.length > 0 && (
              <div className="text-xs text-muted-foreground">
                Found {state.searchResults.length} matches
              </div>
            )}
          </div>
        )}
      </CardHeader>
      
      <CardContent className="flex-1 pt-0 space-y-4">
        {/* Search Results */}
        {state.searchResults.length > 0 && formatTimestamp && (
          <div className="max-h-32 overflow-y-auto border rounded p-2 bg-muted/20">
            <div className="text-xs font-medium mb-2">Search Results:</div>
            <div className="space-y-1">
              {state.searchResults.map((result, index) => (
                <div key={index} className="text-xs flex justify-between items-center">
                  <span>&quot;{result.word}&quot;</span>
                  <Badge variant="outline" className="text-xs">
                    {formatTimestamp(result.start)}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Transcription Text */}
        <div className="flex-1 relative">
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
        </div>
      </CardContent>
    </Card>
  );
}