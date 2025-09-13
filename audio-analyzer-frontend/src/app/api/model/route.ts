import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { spawnPython } from '@/lib/python-env';

export const runtime = 'nodejs'; // ensure NOT edge

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const model = searchParams.get('model') || 'base';
  
  try {
    const modelStatus = await checkModelStatus(model);
    
    return NextResponse.json({
      model: model,
      loaded: modelStatus.loaded,
      error: modelStatus.error
    });
  } catch (error) {
    console.error('Model check error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Model check failed' 
    }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const { model } = await request.json();
    
    if (!model) {
      return NextResponse.json({ error: 'Model name is required' }, { status: 400 });
    }
    
    const loadResult = await loadModel(model);
    
    if (!loadResult.success) {
      throw new Error(loadResult.error || 'Model loading failed');
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

interface ModelResult {
  success?: boolean;
  loaded?: boolean;
  error?: string;
}

// Removed resolvePython function - now using spawnPython utility

function checkModelStatus(model: string): Promise<ModelResult> {
  return new Promise((resolve) => {
    const pythonScript = `
import sys
import json
import os
import whisper
from pathlib import Path

def check_model_status(model_name):
    try:
        # Check if model is already downloaded
        model_path = whisper._MODELS[model_name]
        download_root = os.getenv("XDG_CACHE_HOME", os.path.join(os.path.expanduser("~"), ".cache"))
        download_root = os.path.join(download_root, "whisper")
        
        expected_path = os.path.join(download_root, os.path.basename(model_path))
        
        if os.path.exists(expected_path):
            return {
                "success": True,
                "loaded": True
            }
        else:
            return {
                "success": True,
                "loaded": False
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"success": False, "error": "Invalid arguments"}))
        sys.exit(1)
    
    model_name = sys.argv[1]
    result = check_model_status(model_name)
    print(json.dumps(result))
`;

    const proc = spawnPython(pythonScript, [model]);

    let stdout = '';
    let stderr = '';

    if (proc.stdout) {
      proc.stdout.on('data', (data) => {
        stdout += data.toString();
      });
    }

    if (proc.stderr) {
      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });
    }

    proc.on('close', (code) => {
      console.log(`[DEBUG] Python process closed with code: ${code}`);
      console.log(`[DEBUG] Python stdout:`, stdout);
      console.log(`[DEBUG] Python stderr:`, stderr);
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
          error: 'Failed to parse model status'
        });
      }
    });

    proc.on('error', (error) => {
      console.error('Failed to spawn Python process:', error);
      resolve({
        success: false,
        error: `Failed to start Python process: ${error.message}`
      });
    });
  });
}

function loadModel(model: string): Promise<ModelResult> {
  return new Promise((resolve) => {
    const pythonScript = `
import sys
import json
import whisper
import warnings
warnings.filterwarnings("ignore")

def load_model(model_name):
    try:
        # Load the model (this will download it if not present)
        # This is the same approach as used in audioapp.ipynb
        model = whisper.load_model(model_name)
        return {
            "success": True,
            "loaded": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"success": False, "error": "Invalid arguments"}))
        sys.exit(1)
    
    model_name = sys.argv[1]
    result = load_model(model_name)
    print(json.dumps(result))
`;

    const proc = spawnPython(pythonScript, [model]);

    let stdout = '';
    let stderr = '';

    if (proc.stdout) {
      proc.stdout.on('data', (data) => {
        stdout += data.toString();
      });
    }

    if (proc.stderr) {
      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });
    }

    proc.on('close', (code) => {
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
          error: 'Failed to parse model loading result'
        });
      }
    });

    proc.on('error', (error) => {
      console.error('Failed to spawn Python process:', error);
      resolve({
        success: false,
        error: `Failed to start Python process: ${error.message}`
      });
    });
  });
}