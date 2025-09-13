import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch('http://localhost:8765/summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Summary failed');
    }

    return NextResponse.json({
      result: result.summary,
      message: `Summary completed successfully`
    });
  } catch (error) {
    console.error('Summary error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Summary failed' 
    }, { status: 500 });
  }
}
