import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

let whisperProcess: any = null;
let modelLoaded = false;
let currentModel = 'base';

console.log('[DEBUG] PYTHON_BIN at module load:', process.env.PYTHON_BIN);
console.log('[DEBUG] process.cwd():', process.cwd());
console.log('[DEBUG] PYTHON_BIN:', process.env.PYTHON_BIN);


function startWhisperProcess(model: string) {
  const pythonPath = process.env.PYTHON_BIN || 'python3';
  console.log('[DEBUG] PYTHON_BIN:', process.env.PYTHON_BIN);
  const scriptPath = 'whisper_server.py';
  const cwd = process.cwd();

  console.log(`[DEBUG] Starting Whisper process`);
  console.log(`[DEBUG] Python path: ${pythonPath}`);
  console.log(`[DEBUG] Script path: ${scriptPath}`);
  console.log(`[DEBUG] Working directory: ${cwd}`);
  console.log(`[DEBUG] Model: ${model}`);

  if (whisperProcess && currentModel === model) {
    console.log('[DEBUG] Whisper process already running for this model.');
    return;
  }
  if (whisperProcess) {
    whisperProcess.kill();
    whisperProcess = null;
    modelLoaded = false;
    console.log('[DEBUG] Killed previous Whisper process.');
  }
  try {
    whisperProcess = spawn(
      pythonPath,
      [scriptPath, model],
      { cwd }
    );
    whisperProcess.on('error', (err: any) => {
      console.error('[ERROR] Failed to spawn Whisper process:', err);
    });
    whisperProcess.stdout.on('data', (data: Buffer) => {
      console.log('[Whisper STDOUT]', data.toString());
    });
    whisperProcess.stderr.on('data', (data: Buffer) => {
      console.error('[Whisper STDERR]', data.toString());
    });
    currentModel = model;
    modelLoaded = true;
    console.log('[DEBUG] Whisper process started.');
  } catch (err) {
    console.error('[ERROR] Exception while starting Whisper process:', err);
    throw err;
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const model = searchParams.get('model') || 'base';
  return NextResponse.json({ loaded: modelLoaded && currentModel === model });
}

export async function POST(request: NextRequest) {
  try {
    const { model } = await request.json();
    console.log(`[DEBUG] /api/model POST called with model: ${model}`);
    console.log('[DEBUG] PYTHON_BIN in POST:', process.env.PYTHON_BIN);

    startWhisperProcess(model);

    // Wait a short time to allow process to start (optional, for demonstration)
    await new Promise((resolve) => setTimeout(resolve, 500));

    if (!modelLoaded || currentModel !== model) {
      throw new Error('Model loading failed');
    }

    return NextResponse.json({
      model: model,
      loaded: true,
      message: 'Model loaded successfully'
    });
  } catch (error) {
    console.error('Model loading error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Model loading failed' 
    }, { status: 500 });
  }
}