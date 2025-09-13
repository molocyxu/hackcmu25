import { NextRequest, NextResponse } from 'next/server';

async function transcribeWithWhisper(
  audioPath: string, 
  model: string, 
  useFullAudio: boolean = true,
  startTime?: number,
  endTime?: number,
  includeWordTimestamps: boolean = false
): Promise<any> {
  const requestBody = {
    audio_path: audioPath,
    model,
    use_full_audio: useFullAudio,
    start_time: startTime,
    end_time: endTime,
    include_word_timestamps: includeWordTimestamps
  };

  const res = await fetch('http://localhost:8765/transcribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
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
  const { 
    audioPath, 
    model, 
    useFullAudio = true, 
    startTime, 
    endTime, 
    includeWordTimestamps = false 
  } = await request.json();
  
  const result = await transcribeWithWhisper(
    audioPath, 
    model, 
    useFullAudio, 
    startTime, 
    endTime, 
    includeWordTimestamps
  );
  return NextResponse.json(result);
}