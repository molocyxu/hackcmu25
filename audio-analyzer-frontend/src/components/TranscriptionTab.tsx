"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AudioAnalyzerState, SearchResult } from "./AudioAnalyzer";

interface TranscriptionTabProps {
  state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
}

export function TranscriptionTab({ state, updateState }: TranscriptionTabProps) {
  const [localSearchTerm, setLocalSearchTerm] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  
  const wordCount = state.transcribedText ? state.transcribedText.split(' ').filter(word => word.length > 0).length : 0;
  const charCount = state.transcribedText ? state.transcribedText.length : 0;

  const formatTimestamp = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getHighlightedText = (text: string, searchTerm: string): string => {
    if (!searchTerm || !text) {
      return text || 'Transcribed text will appear here...';
    }

    // Escape special regex characters in search term
    const escapedSearchTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    
    // Create regex for case-insensitive global search
    const regex = new RegExp(escapedSearchTerm, 'gi');
    
    // Replace matches with highlighted version
    const highlightedText = text.replace(regex, (match) => {
      return `<span style="background-color: yellow; color: black; padding: 1px 2px; border-radius: 2px;">${match}</span>`;
    });

    return highlightedText;
  };

  const handleSearch = () => {
    const searchTerm = localSearchTerm.trim().toLowerCase();
    
    if (!searchTerm) {
      updateState({ searchResults: [], searchTerm: "" });
      return;
    }

    if (!state.wordTimestamps || state.wordTimestamps.length === 0) {
      // Fallback to text-based search without timestamps
      updateState({ searchTerm, searchResults: [] });
      return;
    }

    // Find matching words in word timestamps
    const matches: SearchResult[] = [];
    const seenTimes = new Set<string>();

    state.wordTimestamps.forEach((wordInfo, index) => {
      if (wordInfo.word.toLowerCase().includes(searchTerm)) {
        const timeKey = `${wordInfo.start.toFixed(1)}`;
        if (!seenTimes.has(timeKey)) {
          seenTimes.add(timeKey);
          matches.push({
            word: wordInfo.word,
            start: wordInfo.start,
            end: wordInfo.end,
            index: index + 1
          });
        }
      }
    });

    // Limit to first 50 matches
    const limitedMatches = matches.slice(0, 50);
    
    updateState({ 
      searchResults: limitedMatches, 
      searchTerm 
    });
  };

  const clearSearch = () => {
    setLocalSearchTerm("");
    updateState({ searchResults: [], searchTerm: "" });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

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
      <CardContent className="flex-1 pt-0 flex flex-col gap-4">
        {/* Main Content: Text Area takes top 2/3 */}
        <div className="flex-1 flex flex-col">
          {/* Transcription Text Area - Takes 2/3 of the height */}
          <div className="flex-1 relative">
            {!isEditing && state.searchTerm ? (
              // Display mode with highlighting
              <div 
                className="h-full w-full p-3 text-sm leading-relaxed border border-border/50 rounded-md bg-background overflow-y-auto whitespace-pre-wrap cursor-text"
                onClick={() => setIsEditing(true)}
                dangerouslySetInnerHTML={{ 
                  __html: getHighlightedText(state.transcribedText, state.searchTerm) 
                }}
              />
            ) : (
              // Edit mode
              <Textarea
                value={state.transcribedText}
                onChange={(e) => updateState({ transcribedText: e.target.value })}
                onBlur={() => setIsEditing(false)}
                placeholder="Transcribed text will appear here..."
                className="h-full resize-none text-sm leading-relaxed"
                readOnly={state.isTranscribing}
                autoFocus={isEditing}
              />
            )}
            {state.isTranscribing && (
              <div className="absolute inset-0 bg-background/50 flex items-center justify-center">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                  <span className="text-sm">Transcribing...</span>
                </div>
              </div>
            )}
          </div>

          {/* Search Results Panel - Takes 1/3 of the height */}
          <div className="h-48 flex flex-col mt-4">
            <div className="mb-3">
              <h4 className="font-medium text-sm mb-2">
                {state.searchResults.length > 0 
                  ? `Found ${state.searchResults.length} matches` 
                  : "Search Results"}
              </h4>
            </div>
            
            {/* Search Results Display */}
            <div className="flex-1 border border-border/50 rounded-md p-3 bg-muted/20 overflow-y-auto">
              {state.searchResults.length > 0 ? (
                <div className="space-y-2">
                  {state.searchResults.map((match, i) => (
                    <div key={i} className="text-xs">
                      <div className="font-medium">
                        {i + 1}. "{match.word}" at {formatTimestamp(match.start)}
                      </div>
                      <div className="text-muted-foreground ml-2">
                        [{formatTimestamp(match.start)}]
                      </div>
                    </div>
                  ))}
                  {state.searchResults.length === 50 && (
                    <div className="text-xs text-muted-foreground mt-2">
                      ... showing first 50 matches
                    </div>
                  )}
                </div>
              ) : state.searchTerm ? (
                <div className="text-xs text-muted-foreground">
                  No matches found for "{state.searchTerm}"
                </div>
              ) : (
                <div className="text-xs text-muted-foreground">
                  Enter a word to search for timestamps
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Search Bar at Bottom */}
        <div className="flex items-center gap-2 pt-2 border-t border-border/50">
          <span className="text-sm font-medium">Search:</span>
          <Input
            value={localSearchTerm}
            onChange={(e) => setLocalSearchTerm(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter word to search..."
            className="flex-1"
          />
          <Button
            onClick={handleSearch}
            size="sm"
            className="px-4"
          >
            🔍 Search
          </Button>
          <Button
            onClick={clearSearch}
            size="sm"
            variant="outline"
            className="px-4"
          >
            Clear
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}