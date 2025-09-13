import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

export const runtime = 'nodejs'; // ensure NOT edge

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey } = await request.json();
    
    if (!text || !apiKey) {
      return NextResponse.json({ 
        error: 'Text and API key are required' 
      }, { status: 400 });
    }
    
    const result = await generateSemanticSummary(text, apiKey);
    
    if (!result.success) {
      throw new Error(result.error || 'Semantic summary generation failed');
    }
    
    return NextResponse.json({
      summary: result.summary,
      message: 'Semantic summary generated successfully'
    });
  } catch (error) {
    console.error('Semantic summary error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Semantic summary generation failed' 
    }, { status: 500 });
  }
}

interface SemanticSummaryResult {
  success?: boolean;
  summary?: string;
  error?: string;
}

function resolvePython() {
  const fromEnv = process.env.PYTHON_BIN;
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;

  const guesses = [
    '/usr/bin/python3',
    '/usr/local/bin/python3',
    '/opt/homebrew/bin/python3',
    'python3',
    'python',
  ];
  for (const g of guesses) {
    try {
      if (g.includes('/') && fs.existsSync(g)) return g;
    } catch {}
  }
  return '/usr/bin/python3'; // Use absolute path that we know exists
}

function generateSemanticSummary(text: string, apiKey: string): Promise<SemanticSummaryResult> {
  return new Promise((resolve) => {
    const pythonScript = `
import sys
import json
import warnings
warnings.filterwarnings("ignore")

def generate_semantic_summary(text, api_key):
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=api_key)
        
        prompt = f"""You will receive a transcript. Write EXACTLY ONE sentence (≤ 30 words) that captures BOTH:
- the core meaning/topic, and
- the overall tone/affect/delivery style (e.g., enthusiastic, cautious, frustrated, formal).

Rules:
- Single sentence only; end with a period.
- ≤ 30 words.
- No quotes, labels, lists, JSON, or extra commentary.
- No markdown.

Transcript:
{text}"""
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            temperature=0.2,
            messages=[{{"role": "user", "content": prompt}}]
        )
        
        raw = response.content[0].text.strip()
        
        # Post-process to enforce one sentence and ≤ 30 words
        s = raw.replace("\\n", " ").strip()
        s = s.strip(' "\\'')  # remove leading/trailing quotes if any
        
        import re
        # Keep only the first sentence boundary encountered
        parts = re.split(r'(?<=[.!?])\\s+', s)
        s = parts[0].strip() if parts else s
        
        # Ensure it ends with a sentence terminator
        if not s.endswith(('.', '!', '?')):
            s += '.'
        
        # Enforce ≤ 30 words
        words = s.split()
        if len(words) > 30:
            s = " ".join(words[:30]).rstrip('.,;:!?') + "."
        
        return {{
            "success": True,
            "summary": s
        }}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e)
        }}

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({{"success": False, "error": "Invalid arguments"}}))
        sys.exit(1)
    
    text = sys.argv[1]
    api_key = sys.argv[2]
    result = generate_semantic_summary(text, api_key)
    print(json.dumps(result))
`;

    const pythonBin = resolvePython();
    const pathPrefix = process.env.PATH_PREFIX || '/home/ubuntu/.local/bin';
    const workspaceRoot = process.env.WORKSPACE_ROOT || '/workspace';

    const proc = spawn(pythonBin, ['-c', pythonScript, text, apiKey], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: workspaceRoot,
      env: {
        ...process.env,
        PATH: `${pathPrefix}:${process.env.PATH || ''}`,
        PYTHONPATH: `/home/ubuntu/.local/lib/python3.13/site-packages:${process.env.PYTHONPATH || ''}`,
        HOME: '/home/ubuntu'
      }
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

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
          error: 'Failed to parse semantic summary result'
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