import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey, customPrompt } = await request.json();
    if (!text || !apiKey || !customPrompt) {
      return NextResponse.json({ error: 'Text, API key, and custom prompt are required' }, { status: 400 });
    }
    const response = await fetch('http://localhost:8765/custom-prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, apiKey, customPrompt })
    });
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error || 'Custom prompt processing failed');
    }
    return NextResponse.json({
      result: result.result,
      message: 'Custom prompt processed successfully'
    });
  } catch (error) {
    console.error('Custom prompt error:', error);
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Custom prompt failed' }, { status: 500 });
  }
}
