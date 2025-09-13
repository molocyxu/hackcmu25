import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File;
    const model = formData.get('model') as string || 'base';

    if (!audioFile) {
      return NextResponse.json({ error: 'No audio file provided' }, { status: 400 });
    }

    // In a real implementation, you would:
    // 1. Save the audio file temporarily
    // 2. Use OpenAI's Whisper API or a local Whisper model to transcribe
    // 3. Return the transcription result

    // For now, return a mock transcription
    const mockTranscription = `This is a mock transcription of the uploaded audio file. 
    In a real implementation, this would use the Whisper ${model} model to transcribe the actual audio content. 
    The transcription would include all spoken words, proper punctuation, and formatting.`;

    return NextResponse.json({ 
      transcription: mockTranscription,
      model: model,
      duration: 30, // mock duration in seconds
      language: 'en'
    });

  } catch (error) {
    console.error('Transcription error:', error);
    return NextResponse.json({ error: 'Transcription failed' }, { status: 500 });
  }
}