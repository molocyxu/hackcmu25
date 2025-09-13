import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { latexContent } = await request.json();
    if (!latexContent) {
      return NextResponse.json({ error: 'LaTeX content is required' }, { status: 400 });
    }

    const response = await fetch('http://localhost:8765/latex', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latexContent })
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'LaTeX PDF generation failed');
    }

    return NextResponse.json({
      pdf: result.pdf,
      filename: result.filename || 'analysis.pdf',
      message: 'LaTeX PDF generated successfully'
    });
  } catch (error) {
    console.error('LaTeX PDF error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'LaTeX PDF generation failed' 
    }, { status: 500 });
  }
}