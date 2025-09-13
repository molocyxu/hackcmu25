import { NextRequest, NextResponse } from 'next/server';

async function transcribeWithWhisper(audioPath: string, model: string): Promise<any> {
  const res = await fetch('http://localhost:8765/transcribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ audio_path: audioPath, model }),
  });
  const text = await res.text();
  console.log('[DEBUG] Raw response from whisper server:', text);
  try {
    return JSON.parse(text);
  } catch (err) {
    console.error('[ERROR] Failed to parse JSON:', err, text);
    return { error: 'Invalid response from Whisper server', raw: text };
  }
}

export async function POST(request: NextRequest) {
  const { audioPath, model } = await request.json();
  const result = await transcribeWithWhisper(audioPath, model);
  return NextResponse.json(result);
}