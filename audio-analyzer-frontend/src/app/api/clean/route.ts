import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey } = await request.json();

    if (!text) {
      return NextResponse.json({ error: 'Text is required' }, { status: 400 });
    }

    if (!apiKey) {
      return NextResponse.json({ error: 'API key is required' }, { status: 400 });
    }

    const anthropic = new Anthropic({
      apiKey: apiKey,
    });

    const prompt = `Clean the following transcribed text by:
1. Correcting any obvious transcription errors or strange words
2. Fixing grammar and punctuation while preserving the original meaning
3. Removing filler words (um, uh, etc.) where appropriate
4. Making the text flow naturally as written prose
5. DO NOT summarize or remove content - just clean and correct

Return ONLY the cleaned text without any commentary or explanations.

Text to clean:
${text}`;

    const response = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4000,
      temperature: 0.2,
      messages: [{ role: 'user', content: prompt }],
    });

    const cleanedText = response.content[0].type === 'text' ? response.content[0].text : '';

    return NextResponse.json({ 
      result: cleanedText,
      status: 'success'
    });

  } catch (error) {
    console.error('Clean text error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to clean text' },
      { status: 500 }
    );
  }
}