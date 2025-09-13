import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey } = await request.json();
    if (!text || !apiKey) {
      return NextResponse.json({ error: 'Text and API key are required' }, { status: 400 });
    }
    const response = await fetch('http://localhost:8765/clean', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, apiKey })
    });
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error || 'Text cleaning failed');
    }
    return NextResponse.json({
      cleaned: result.cleaned,
      message: 'Text cleaned successfully'
    });
  } catch (error) {
    console.error('Text cleaning error:', error);
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Text cleaning failed' }, { status: 500 });
  }
}