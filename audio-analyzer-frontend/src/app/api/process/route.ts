import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

export async function POST(request: NextRequest) {
  try {
    const { text, prompt, apiKey, wordLimit, outputFormat } = await request.json();

    if (!text || !prompt || !apiKey) {
      return NextResponse.json({ 
        error: 'Missing required fields: text, prompt, or apiKey' 
      }, { status: 400 });
    }

    // Process with Claude using Python script
    const processResult = await processWithClaude(text, prompt, apiKey, wordLimit, outputFormat);
    
    if (!processResult.success) {
      throw new Error(processResult.error || 'Processing failed');
    }

    return NextResponse.json({ 
      result: processResult.result,
      prompt: prompt,
      wordLimit: wordLimit,
      outputFormat: outputFormat,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Processing error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Processing failed' 
    }, { status: 500 });
  }
}

interface ProcessResult {
  success: boolean;
  result?: string;
  error?: string;
}

function processWithClaude(text: string, prompt: string, apiKey: string, wordLimit: number, outputFormat: string): Promise<ProcessResult> {
  return new Promise((resolve) => {
    const pythonScript = [
      "import sys",
      "import json", 
      "import os",
      "from anthropic import Anthropic",
      "import re",
      "",
      "def ensure_latex_format(text):",
      '    """Ensure text is in proper LaTeX format with beautiful math rendering"""',
      "    ",
      "    # Clean up problematic characters",
      "    text = text.replace('\\\\u2019', \"'\")",
      "    text = text.replace('\\\\u201c', '``')",
      "    text = text.replace('\\\\u201d', \"''\")",
      "    text = text.replace('\\\\u2013', '--')",
      "    text = text.replace('\\\\u2014', '---')",
      "    ",
      "    # Simple text processing for LaTeX formatting",
      "    # Convert basic markdown elements",
      "    lines = text.split('\\\\n')",
      "    processed_lines = []",
      "    ",
      "    for line in lines:",
      "        # Convert headers",
      "        if line.startswith('### '):",
      "            line = '\\\\\\\\\\\\\\\\subsection{' + line[4:] + '}'",
      "        elif line.startswith('## '):",
      "            line = '\\\\\\\\\\\\\\\\section{' + line[3:] + '}'",
      "        elif line.startswith('# '):",
      "            line = '\\\\\\\\\\\\\\\\chapter{' + line[2:] + '}'",
      "        elif line.startswith('- '):",
      "            line = '\\\\\\\\\\\\\\\\item ' + line[2:]",
      "        ",
      "        processed_lines.append(line)",
      "    ",
      "    text = '\\\\n'.join(processed_lines)",
      "    ",
      "    if not text.startswith('\\\\\\\\\\\\\\\\documentclass'):",
      "        # Create a complete LaTeX document",
      "        latex_header = '''\\\\\\\\\\\\\\\\documentclass[11pt]{article}",
      "\\\\\\\\\\\\\\\\usepackage[utf8]{inputenc}",
      "\\\\\\\\\\\\\\\\usepackage[T1]{fontenc}",
      "\\\\\\\\\\\\\\\\usepackage{lmodern}",
      "\\\\\\\\\\\\\\\\usepackage{amsmath}",
      "\\\\\\\\\\\\\\\\usepackage{amssymb}",
      "\\\\\\\\\\\\\\\\usepackage{amsfonts}",
      "\\\\\\\\\\\\\\\\usepackage{amsthm}",
      "\\\\\\\\\\\\\\\\usepackage{mathtools}",
      "\\\\\\\\\\\\\\\\usepackage{geometry}",
      "\\\\\\\\\\\\\\\\usepackage{enumitem}",
      "\\\\\\\\\\\\\\\\usepackage{hyperref}",
      "\\\\\\\\\\\\\\\\geometry{a4paper, margin=1in}",
      "",
      "\\\\\\\\\\\\\\\\title{Audio Transcription Analysis}",
      "\\\\\\\\\\\\\\\\author{Generated Analysis}",
      "\\\\\\\\\\\\\\\\date{\\\\\\\\\\\\\\\\today}",
      "",
      "\\\\\\\\\\\\\\\\begin{document}",
      "\\\\\\\\\\\\\\\\maketitle",
      "",
      "'''",
      "        latex_footer = '''",
      "",
      "\\\\\\\\\\\\\\\\end{document}'''",
      "        return latex_header + text + latex_footer",
      "    ",
      "    return text",
      "",
      "def get_summarize_prompt(text, word_limit, output_format):",
      '    """Generate summarization prompt with word limit"""',
      "    format_instructions = {",
      '        "markdown": "Format your response in clean Markdown with appropriate headers and structure.",',
      '        "plain text": "Provide a plain text response without any formatting.",',
      '        "json": "Return your response as a well-structured JSON object.",',
      '        "bullet points": "Structure your response as clear bullet points.",',
      '        "latex pdf": "Format your response in LaTeX document format with proper document class, sections, and formatting."',
      "    }",
      "    ",
      "    format_key = output_format.lower()",
      "    format_instruction = format_instructions.get(format_key, '')",
      "    ",
      "    prompt = f'''Please provide a comprehensive summary of the following transcribed audio content in approximately {word_limit} words. ",
      "Focus on the main ideas, key points, and important details. ",
      "{format_instruction}",
      "",
      "Transcribed text:",
      "{text}'''",
      "    ",
      "    return prompt",
      "",
      "def process_with_claude(text, prompt, api_key, word_limit, output_format):",
      "    try:",
      "        client = Anthropic(api_key=api_key)",
      "        ",
      '        # Check if this is a summarization request (simple heuristic)',
      '        if "comprehensive summary" not in prompt and "{text}" not in prompt:',
      "            # This appears to be a summarization request, use the proper prompt format",
      "            final_prompt = get_summarize_prompt(text, word_limit, output_format)",
      "        else:",
      "            # This is a custom prompt, replace {text} placeholder",
      '            final_prompt = prompt.replace("{text}", text)',
      "        ",
      "        # Add instructions for math formatting if LaTeX output is selected",
      '        if output_format.lower() == "latex pdf":',
      '            final_prompt += "\\\\n\\\\nIMPORTANT: Format all mathematical equations using proper LaTeX syntax. Use equation environments for display equations and inline math mode for inline expressions. Ensure all special symbols are properly escaped."',
      "        ",
      "        response = client.messages.create(",
      '            model="claude-3-5-sonnet-20241022",',
      "            max_tokens=4000,",
      "            temperature=0.3,",
      '            messages=[{"role": "user", "content": final_prompt}]',
      "        )",
      "        ",
      "        result_text = response.content[0].text",
      "        ",
      "        # Handle LaTeX PDF output if selected",
      '        if output_format.lower() == "latex pdf":',
      "            result_text = ensure_latex_format(result_text)",
      "        ",
      "        return {",
      '            "success": True,',
      '            "result": result_text',
      "        }",
      "        ",
      "    except Exception as e:",
      "        return {",
      '            "success": False,',
      '            "error": str(e)',
      "        }",
      "",
      'if __name__ == "__main__":',
      "    if len(sys.argv) != 6:",
      '        print(json.dumps({"success": False, "error": "Invalid arguments"}))',
      "        sys.exit(1)",
      "    ",
      "    text = sys.argv[1]",
      "    prompt = sys.argv[2]",
      "    api_key = sys.argv[3]",
      "    word_limit = int(sys.argv[4])",
      "    output_format = sys.argv[5]",
      "    ",
      "    result = process_with_claude(text, prompt, api_key, word_limit, output_format)",
      "    print(json.dumps(result))"
    ].join("\\n");

    const python = spawn('/workspace/venv/bin/python3', ['-c', pythonScript, text, prompt, apiKey, wordLimit.toString(), outputFormat], {
      stdio: ['pipe', 'pipe', 'pipe']
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
          error: 'Failed to parse processing result'
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