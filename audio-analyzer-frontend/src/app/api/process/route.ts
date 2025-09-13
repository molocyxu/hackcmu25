import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text, prompt, apiKey, wordLimit, outputFormat } = await request.json();

    if (!text || !prompt || !apiKey) {
      return NextResponse.json({ 
        error: 'Missing required fields: text, prompt, or apiKey' 
      }, { status: 400 });
    }

    // Call persistent Python backend instead of spawning
    let response, result, rawText;
    try {
      response = await fetch('http://localhost:8765/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          apiKey,
          wordLimit,
          outputFormat,
          prompt
        })
      });
      rawText = await response.text();
      console.log('[API/process] Raw backend response:', rawText);
      try {
        result = JSON.parse(rawText);
      } catch (jsonErr) {
        console.error('[API/process] JSON parse error:', jsonErr, 'Raw:', rawText);
        return NextResponse.json({
          error: 'Backend returned invalid JSON',
          details: rawText,
          status: response.status
        }, { status: 502 });
      }
    } catch (fetchErr) {
      console.error('[API/process] Fetch error:', fetchErr);
      return NextResponse.json({
        error: 'Failed to reach backend',
        details: fetchErr instanceof Error ? fetchErr.message : String(fetchErr)
      }, { status: 502 });
    }

    if (!result.success) {
      console.error('[API/process] Backend error:', result.error);
      return NextResponse.json({
        error: result.error || 'Processing failed',
        backend: result,
        status: response.status
      }, { status: 502 });
    }

    return NextResponse.json({
      result: result.summary,
      prompt: prompt,
      wordLimit: wordLimit,
      outputFormat: outputFormat,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Processing error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Processing failed' 
    }, { status: 500 });
  }
}