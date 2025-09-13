import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text, clusters = 5 } = await request.json();

    if (!text) {
      return NextResponse.json({ error: 'Text is required' }, { status: 400 });
    }

    const response = await fetch('http://localhost:8765/network', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, clusters })
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Network plot generation failed');
    }

    return NextResponse.json(result);

  } catch (error) {
    console.error('Network plot error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate network plot' },
      { status: 500 }
    );
  }
}