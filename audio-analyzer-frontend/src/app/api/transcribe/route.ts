import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import { writeFile, unlink, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import os from 'os';

export async function POST(request: NextRequest) {
  let tempFilePath: string | null = null;
  
  try {
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File;
    const model = formData.get('model') as string || 'base';

    if (!audioFile) {
      return NextResponse.json({ error: 'No audio file provided' }, { status: 400 });
    }

    // Create temp directory if it doesn't exist
    const tempDir = path.join(os.tmpdir(), 'audio-transcription');
    if (!existsSync(tempDir)) {
      await mkdir(tempDir, { recursive: true });
    }

    // Save the uploaded file temporarily
    const buffer = Buffer.from(await audioFile.arrayBuffer());
    const fileExtension = path.extname(audioFile.name) || '.wav';
    tempFilePath = path.join(tempDir, `${Date.now()}${fileExtension}`);
    
    await writeFile(tempFilePath, buffer);

    // Use Python script to transcribe with Whisper
    const transcriptionResult = await transcribeWithWhisper(tempFilePath, model);
    
    if (!transcriptionResult.success) {
      throw new Error(transcriptionResult.error || 'Transcription failed');
    }

    return NextResponse.json({ 
      transcription: transcriptionResult.text,
      model: model,
      duration: transcriptionResult.duration,
      language: transcriptionResult.language || 'en'
    });

  } catch (error) {
    console.error('Transcription error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Transcription failed' 
    }, { status: 500 });
  } finally {
    // Clean up temp file
    if (tempFilePath) {
      try {
        await unlink(tempFilePath);
      } catch (e) {
        console.warn('Failed to clean up temp file:', e);
      }
    }
  }
}

interface TranscriptionResult {
  success: boolean;
  text?: string;
  duration?: number;
  language?: string;
  error?: string;
}

function transcribeWithWhisper(audioPath: string, model: string): Promise<TranscriptionResult> {
  return new Promise((resolve) => {
    const pythonScript = `
import sys
import json
import whisper
import warnings
warnings.filterwarnings("ignore")

def transcribe_audio(file_path, model_name):
    try:
        # Load the Whisper model
        model = whisper.load_model(model_name)
        
        # Transcribe the audio
        result = model.transcribe(file_path)
        
        return {
            "success": True,
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "duration": result.get("duration", 0)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"success": False, "error": "Invalid arguments"}))
        sys.exit(1)
    
    file_path = sys.argv[1]
    model_name = sys.argv[2]
    
    result = transcribe_audio(file_path, model_name)
    print(json.dumps(result))
`;

    const python = spawn('/usr/bin/python3', ['-c', pythonScript, audioPath, model], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: '/workspace',
      env: {
        ...process.env,
        PATH: '/home/ubuntu/.local/bin:' + process.env.PATH,
        PYTHONPATH: '/home/ubuntu/.local/lib/python3.13/site-packages'
      }
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code !== 0) {
        console.error('Python script error:', stderr);
        resolve({
          success: false,
          error: `Python script failed with code ${code}: ${stderr}`
        });
        return;
      }

      try {
        const result = JSON.parse(stdout.trim());
        resolve(result);
      } catch (e) {
        console.error('Failed to parse Python output:', stdout);
        resolve({
          success: false,
          error: 'Failed to parse transcription result'
        });
      }
    });

    python.on('error', (error) => {
      console.error('Failed to spawn Python process:', error);
      resolve({
        success: false,
        error: `Failed to start Python process: ${error.message}`
      });
    });
  });
}