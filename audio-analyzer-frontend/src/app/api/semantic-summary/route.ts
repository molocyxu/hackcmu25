import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey } = await request.json();
    
    if (!text || !apiKey) {
      return NextResponse.json({ 
        error: 'Text and API key are required' 
      }, { status: 400 });
    }
    
    const response = await fetch('http://localhost:8765/semantic-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, apiKey })
    });
    const result = await response.json();
    
    if (!result.success) {
      throw new Error(result.error || 'Semantic summary generation failed');
    }
    
    return NextResponse.json({
      summary: result.summary,
      message: 'Semantic summary generated successfully'
    });
  } catch (error) {
    console.error('Semantic summary error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Semantic summary generation failed' 
    }, { status: 500 });
  }
}