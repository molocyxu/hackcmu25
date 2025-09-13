import { NextRequest, NextResponse } from 'next/server';

async function translateWithWhisperServer(
  text: string,
  apiKey: string,
  targetLanguage: string,
  translationStyle: string,
  preserveFormatting: boolean,
  outputFormat: string
): Promise<unknown> {
  const res = await fetch('http://localhost:8765/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      apiKey,
      targetLanguage,
      translationStyle,
      preserveFormatting,
      outputFormat,
    }),
  });
  const responseText = await res.text();
  try {
    return JSON.parse(responseText);
  } catch (err) {
    console.error('[ERROR] Failed to parse JSON:', err, responseText);
    return { error: 'Invalid response from Whisper server', raw: responseText };
  }
}

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey, targetLanguage, translationStyle, preserveFormatting, outputFormat } = await request.json();
    
    if (!text || !apiKey || !targetLanguage) {
      return NextResponse.json({ 
        error: 'Text, API key, and target language are required' 
      }, { status: 400 });
    }
    
    const result = await translateWithWhisperServer(
      text,
      apiKey,
      targetLanguage,
      translationStyle,
      preserveFormatting,
      outputFormat
    ) as { success: boolean; error?: string; translation?: string };
    
    if (!result.success) {
      throw new Error(result.error || 'Translation failed');
    }
    
    return NextResponse.json({
      result: result.translation,
      message: `Translation to ${targetLanguage} completed successfully`
    });
  } catch (error) {
    console.error('Translation error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Translation failed' 
    }, { status: 500 });
  }
}