"use client";

import { Button } from "@/components/ui/button";
import { cleanTextForExport } from "@/lib/utils";
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
    } catch {
      updateState({ status: "Failed to copy to clipboard" });
    }
  };

  const exportText = async (type: 'transcription' | 'result') => {
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

    // Handle LaTeX PDF export specially
    if (state.outputFormat === 'LaTeX PDF' && type === 'result') {
      await exportAsPdf(content);
      return;
    }

    // Clean text before creating file
    const cleanedContent = cleanTextForExport(content);
    
    // Create and download file
    const blob = new Blob([cleanedContent], { type: 'text/plain' });
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

  const exportAsPdf = async (latexContent: string) => {
    updateState({ status: "Compiling PDF..." });
    
    try {
      const response = await fetch('/api/latex', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ latexContent }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'PDF compilation failed');
      }

      const data = await response.json();
      
      // Convert base64 to blob and download
      const pdfBlob = base64ToBlob(data.pdf, 'application/pdf');
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename || 'analysis.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      updateState({ status: "PDF exported successfully" });
    } catch (error) {
      console.error('PDF export error:', error);
      updateState({ 
        status: `PDF export failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        error: error instanceof Error ? error.message : 'PDF export failed'
      });
      
      // Fallback: offer to save as .tex file
      if (confirm('PDF compilation failed. Would you like to save as LaTeX (.tex) file instead?')) {
        const blob = new Blob([latexContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'analysis.tex';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        updateState({ status: "LaTeX file exported successfully" });
      }
    }
  };

  const base64ToBlob = (base64: string, mimeType: string) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
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