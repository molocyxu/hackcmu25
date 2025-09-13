import { NextRequest, NextResponse } from 'next/server';

async function transcribeWithWhisper(audioPath: string, model: string, startTime?: number, endTime?: number): Promise<any> {
  try {
    const payload = { 
      audio_path: audioPath, 
      model,
      ...(startTime !== undefined && { startTime }),
      ...(endTime !== undefined && { endTime })
    };
    console.log('[DEBUG] Sending request to whisper server:', payload);
    
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    const res = await fetch('http://localhost:8765/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    console.log('[DEBUG] Response status:', res.status, res.statusText);
    
    if (!res.ok) {
      const errorText = await res.text();
      console.error('[ERROR] Whisper server error:', res.status, errorText);
      return { 
        error: `Whisper server error: ${res.status} ${res.statusText}`, 
        details: errorText 
      };
    }
    
    const text = await res.text();
    console.log('[DEBUG] Raw response from whisper server (length: ' + text.length + '):', text);
    
    if (!text || text.trim() === '') {
      console.error('[ERROR] Empty response from Whisper server');
      return { error: 'Empty response from Whisper server' };
    }
    
    try {
      return JSON.parse(text);
    } catch (err) {
      console.error('[ERROR] Failed to parse JSON:', err);
      console.error('[ERROR] Raw text that failed to parse:', JSON.stringify(text));
      return { 
        error: 'Invalid JSON response from Whisper server', 
        raw: text,
        parseError: err instanceof Error ? err.message : String(err)
      };
    }
  } catch (err) {
    console.error('[ERROR] Network error connecting to Whisper server:', err);
    return { 
      error: 'Failed to connect to Whisper server', 
      details: err instanceof Error ? err.message : String(err)
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const { audioPath, model, startTime, endTime } = await request.json();
    
    if (!audioPath) {
      return NextResponse.json({ error: 'Audio path is required' }, { status: 400 });
    }
    
    if (!model) {
      return NextResponse.json({ error: 'Model is required' }, { status: 400 });
    }
    
    console.log('[DEBUG] Transcription request:', { audioPath, model, startTime, endTime });
    
    const result = await transcribeWithWhisper(audioPath, model, startTime, endTime);
    
    // Check if the result contains an error
    if (result.error) {
      console.error('[ERROR] Transcription failed:', result.error);
      return NextResponse.json(result, { status: 500 });
    }
    
    return NextResponse.json(result);
  } catch (err) {
    console.error('[ERROR] Transcription API error:', err);
    return NextResponse.json({ 
      error: 'Internal server error', 
      details: err instanceof Error ? err.message : String(err) 
    }, { status: 500 });
  }
}