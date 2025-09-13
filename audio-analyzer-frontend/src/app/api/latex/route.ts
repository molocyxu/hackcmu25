import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import { writeFile, unlink, mkdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import os from 'os';

export async function POST(request: NextRequest) {
  let tempDir: string | null = null;
  
  try {
    const { latexContent } = await request.json();

    if (!latexContent) {
      return NextResponse.json({ error: 'LaTeX content is required' }, { status: 400 });
    }

    // Create temp directory
    tempDir = path.join(os.tmpdir(), `latex-${Date.now()}`);
    await mkdir(tempDir, { recursive: true });

    // Write LaTeX file
    const texFile = path.join(tempDir, 'document.tex');
    await writeFile(texFile, latexContent, 'utf8');

    // Compile with pdflatex
    const pdfResult = await compileToPdf(texFile, tempDir);
    
    if (!pdfResult.success) {
      throw new Error(pdfResult.error || 'PDF compilation failed');
    }

    // Read the generated PDF
    const pdfPath = path.join(tempDir, 'document.pdf');
    const pdfBuffer = await readFile(pdfPath);

    // Return PDF as base64
    return NextResponse.json({
      success: true,
      pdf: pdfBuffer.toString('base64'),
      filename: 'analysis.pdf'
    });

  } catch (error) {
    console.error('LaTeX compilation error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'LaTeX compilation failed' 
    }, { status: 500 });
  } finally {
    // Clean up temp directory
    if (tempDir && existsSync(tempDir)) {
      try {
        // Remove all files in temp directory
        const files = ['document.tex', 'document.pdf', 'document.log', 'document.aux'];
        for (const file of files) {
          const filePath = path.join(tempDir, file);
          if (existsSync(filePath)) {
            await unlink(filePath);
          }
        }
        // Note: We don't remove the directory itself as it might cause issues
      } catch (e) {
        console.warn('Failed to clean up temp files:', e);
      }
    }
  }
}

interface CompileResult {
  success: boolean;
  error?: string;
}

function compileToPdf(texFile: string, workingDir: string): Promise<CompileResult> {
  return new Promise((resolve) => {
    // Try different pdflatex paths
    const pdflatexPaths = [
      '/usr/bin/pdflatex',
      '/usr/local/bin/pdflatex',
      '/usr/local/texlive/2024/bin/x86_64-linux/pdflatex',
      '/usr/local/texlive/2023/bin/x86_64-linux/pdflatex',
      'pdflatex'
    ];

    let pdflatexCmd = 'pdflatex';
    
    // Find available pdflatex
    for (const cmd of pdflatexPaths) {
      if (existsSync(cmd) || cmd === 'pdflatex') {
        pdflatexCmd = cmd;
        break;
      }
    }

    const args = [
      '-interaction=nonstopmode',
      '-output-directory', workingDir,
      texFile
    ];

    const pdflatex = spawn(pdflatexCmd, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: workingDir,
      env: { ...process.env, LANG: 'en_US.UTF-8' }
    });

    let stdout = '';
    let stderr = '';

    pdflatex.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pdflatex.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pdflatex.on('close', (code) => {
      if (code !== 0) {
        console.error('pdflatex error:', stderr);
        resolve({
          success: false,
          error: `pdflatex failed with code ${code}. Make sure LaTeX is installed.`
        });
        return;
      }

      // Check if PDF was created
      const pdfPath = path.join(workingDir, 'document.pdf');
      if (existsSync(pdfPath)) {
        resolve({ success: true });
      } else {
        resolve({
          success: false,
          error: 'PDF file was not generated'
        });
      }
    });

    pdflatex.on('error', (error) => {
      console.error('Failed to spawn pdflatex:', error);
      resolve({
        success: false,
        error: `Failed to start pdflatex: ${error.message}. Make sure LaTeX is installed.`
      });
    });

    // Run pdflatex twice to resolve references
    pdflatex.on('close', (code) => {
      if (code === 0) {
        // Run second pass
        const secondPass = spawn(pdflatexCmd, args, {
          stdio: ['pipe', 'pipe', 'pipe'],
          cwd: workingDir,
          env: { ...process.env, LANG: 'en_US.UTF-8' }
        });

        secondPass.on('close', (secondCode) => {
          const pdfPath = path.join(workingDir, 'document.pdf');
          if (existsSync(pdfPath)) {
            resolve({ success: true });
          } else {
            resolve({
              success: false,
              error: 'PDF file was not generated after second pass'
            });
          }
        });

        secondPass.on('error', () => {
          // If second pass fails, still check if PDF exists from first pass
          const pdfPath = path.join(workingDir, 'document.pdf');
          if (existsSync(pdfPath)) {
            resolve({ success: true });
          } else {
            resolve({
              success: false,
              error: 'PDF compilation failed'
            });
          }
        });
      }
    });
  });
}