"use client";

import { Button } from "@/components/ui/button";
import { AudioAnalyzerState } from "./AudioAnalyzer";

interface ToolbarButtonsProps {
  state: AudioAnalyzerState;
  updateState: (updates: Partial<AudioAnalyzerState>) => void;
}

export function ToolbarButtons({ state, updateState }: ToolbarButtonsProps) {
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      updateState({ status: "Copied to clipboard" });
    } catch (err) {
      updateState({ status: "Failed to copy to clipboard" });
    }
  };

  const exportText = (type: 'transcription' | 'result') => {
    let content = '';
    let filename = '';
    
    if (type === 'transcription') {
      content = state.transcribedText;
      filename = 'transcription.txt';
    } else {
      const currentResult = state.currentHistoryIndex >= 0 
        ? state.processHistory[state.currentHistoryIndex]?.result || ""
        : "";
      content = currentResult;
      filename = `processed_result.${getFileExtension()}`;
    }
    
    if (!content) {
      updateState({ status: `No ${type} to export` });
      return;
    }

    // Create and download file
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    updateState({ status: `${type} exported successfully` });
  };

  const getFileExtension = () => {
    const format = state.outputFormat.toLowerCase();
    switch (format) {
      case 'markdown': return 'md';
      case 'json': return 'json';
      case 'latex pdf': return 'tex';
      default: return 'txt';
    }
  };

  const clearAll = () => {
    if (confirm("Clear all content and history?")) {
      updateState({
        transcribedText: "",
        processHistory: [],
        currentHistoryIndex: -1,
        audioFilePath: null,
        audioFileName: "",
        status: "Cleared all content",
      });
    }
  };

  const copyCurrentTab = () => {
    // In a real implementation, you'd detect which tab is active
    // For now, we'll copy transcription if available, otherwise result
    if (state.transcribedText) {
      copyToClipboard(state.transcribedText);
    } else if (state.currentHistoryIndex >= 0) {
      const currentResult = state.processHistory[state.currentHistoryIndex]?.result || "";
      copyToClipboard(currentResult);
    } else {
      updateState({ status: "No content to copy" });
    }
  };

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Button
          onClick={copyCurrentTab}
          variant="outline"
          size="sm"
        >
          📋 Copy Current Tab
        </Button>
        <Button
          onClick={() => exportText('transcription')}
          variant="outline"
          size="sm"
          disabled={!state.transcribedText}
        >
          💾 Export Transcription
        </Button>
        <Button
          onClick={() => exportText('result')}
          variant="outline"
          size="sm"
          disabled={state.currentHistoryIndex < 0}
        >
          💾 Export Result
        </Button>
      </div>
      
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">
          {state.status}
        </span>
        <Button
          onClick={clearAll}
          variant="outline"
          size="sm"
        >
          🗑️ Clear All
        </Button>
      </div>
    </div>
  );
}