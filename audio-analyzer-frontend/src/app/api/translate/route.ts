import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

export const runtime = 'nodejs'; // ensure NOT edge

export async function POST(request: NextRequest) {
  try {
    const { text, apiKey, targetLanguage, translationStyle, preserveFormatting, outputFormat } = await request.json();
    
    if (!text || !apiKey || !targetLanguage) {
      return NextResponse.json({ 
        error: 'Text, API key, and target language are required' 
      }, { status: 400 });
    }
    
    const result = await translateText(text, apiKey, targetLanguage, translationStyle, preserveFormatting, outputFormat);
    
    if (!result.success) {
      throw new Error(result.error || 'Translation failed');
    }
    
    return NextResponse.json({
      result: result.translation,
      message: `Translation to ${targetLanguage} completed successfully`
    });
  } catch (error) {
    console.error('Translation error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Translation failed' 
    }, { status: 500 });
  }
}

interface TranslationResult {
  success?: boolean;
  translation?: string;
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

function translateText(
  text: string, 
  apiKey: string, 
  targetLanguage: string, 
  translationStyle: string = 'Natural',
  preserveFormatting: boolean = true,
  outputFormat: string = 'Markdown'
): Promise<TranslationResult> {
  return new Promise((resolve) => {
    const pythonScript = `
import sys
import json
import warnings
warnings.filterwarnings("ignore")

def translate_text(text, api_key, target_language, translation_style, preserve_formatting, output_format):
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=api_key)
        
        # Style-specific instructions
        style_instructions = {
            "Natural": "Translate in a natural, fluent way that sounds native to the target language.",
            "Literal": "Provide a more literal translation that stays close to the original structure.",
            "Professional": "Use formal, professional language suitable for business or academic contexts.",
            "Colloquial": "Use everyday, conversational language with appropriate idioms.",
            "Technical": "Maintain technical terminology and precision, transliterating terms when necessary."
        }
        
        # Format-specific instructions for different languages
        format_instructions = {
            "markdown": "Maintain Markdown formatting. Translate headers, lists, and content while preserving structure.",
            "plain text": "Provide plain text translation without special formatting.",
            "json": f"Return as JSON with structure: {{\\"language\\": \\"{target_language}\\", \\"translation\\": \\"...\\", \\"notes\\": \\"...\\"}}",
            "bullet points": "Maintain bullet point structure while translating content.",
            "latex pdf": "Preserve LaTeX commands and structure. Translate content while keeping LaTeX formatting intact. Use appropriate language packages if needed (e.g., \\\\usepackage[arabic]{{babel}} for Arabic)."
        }
        
        # Special handling for certain languages
        special_instructions = ""
        if target_language in ["Arabic", "Hebrew"]:
            special_instructions = "\\nNote: This language uses right-to-left script. Ensure proper text direction in the output."
        elif target_language in ["Chinese (Simplified)", "Chinese (Traditional)", "Japanese", "Korean"]:
            special_instructions = "\\nNote: Handle character encoding carefully for East Asian languages."
        
        prompt = f"""Translate the following transcribed text to {target_language}.

TRANSLATION STYLE: {translation_style}
{style_instructions.get(translation_style, '')}

OUTPUT FORMAT: {output_format}
{format_instructions.get(output_format.lower(), '')}

{"PRESERVE ORIGINAL FORMATTING: Maintain paragraph breaks, punctuation style, and structure." if preserve_formatting else "ADAPT FORMATTING: Adjust formatting to be natural for the target language."}
{special_instructions}

Important instructions:
1. Translate all content accurately while maintaining the original meaning
2. Adapt idioms and expressions to be culturally appropriate
3. For technical terms without direct translations, provide the translation followed by the original term in parentheses
4. Ensure grammatical correctness in the target language
5. If the output format is LaTeX, include appropriate language packages in the preamble

Text to translate:
{text}"""
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            messages=[{{"role": "user", "content": prompt}}]
        )
        
        result_text = response.content[0].text
        
        return {{
            "success": True,
            "translation": result_text
        }}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e)
        }}

if __name__ == "__main__":
    if len(sys.argv) != 7:
        print(json.dumps({{"success": False, "error": "Invalid arguments"}}))
        sys.exit(1)
    
    text = sys.argv[1]
    api_key = sys.argv[2]
    target_language = sys.argv[3]
    translation_style = sys.argv[4]
    preserve_formatting = sys.argv[5] == 'true'
    output_format = sys.argv[6]
    
    result = translate_text(text, api_key, target_language, translation_style, preserve_formatting, output_format)
    print(json.dumps(result))
`;

    const pythonBin = resolvePython();
    const pathPrefix = process.env.PATH_PREFIX || '/home/ubuntu/.local/bin';
    const workspaceRoot = process.env.WORKSPACE_ROOT || '/workspace';

    const proc = spawn(pythonBin, [
      '-c', pythonScript, 
      text, 
      apiKey, 
      targetLanguage, 
      translationStyle || 'Natural',
      preserveFormatting ? 'true' : 'false',
      outputFormat || 'Markdown'
    ], {
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
          error: 'Failed to parse translation result'
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