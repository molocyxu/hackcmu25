import sys
import json
import whisper
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from anthropic import Anthropic

MODEL = None
MODEL_NAME = None

def load_model(model_name):
    global MODEL, MODEL_NAME
    if MODEL is None or MODEL_NAME != model_name:
        MODEL = whisper.load_model(model_name)
        MODEL_NAME = model_name

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"[WHISPER_SERVER] do_POST called for path: {self.path}")
        print(f"[WHISPER_SERVER] Headers: {dict(self.headers)}")
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(length)
            print(f"[WHISPER_SERVER] Raw request data: {raw_data}")
            data = json.loads(raw_data)
            print(f"[WHISPER_SERVER] Parsed JSON: {data}")
        except Exception as e:
            print(f"[WHISPER_SERVER] Failed to parse request: {e}")
            self.send_response(400)
            self.end_headers()
            resp = {"success": False, "error": f"Bad request: {str(e)}"}
            print(f"[WHISPER_SERVER] Sending response [400]: {resp}")
            self.wfile.write(json.dumps(resp).encode())
            return

        if self.path == '/load':
            try:
                model_name = data.get('model', 'base')
                print(f"[WHISPER_SERVER] /load model_name: {model_name}")
                load_model(model_name)
                self.send_response(200)
                self.end_headers()
                resp = {'loaded': True}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [200]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /load: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {'loaded': False, 'error': str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/transcribe':
            try:
                file_path = data.get('audio_path') or data.get('audioPath')
                if file_path is None:
                    raise ValueError("No audio_path or audioPath provided in request")
                model_name = data.get('model', 'base')
                use_full_audio = data.get('use_full_audio', True)
                start_time = data.get('start_time', 0)
                end_time = data.get('end_time', None)
                include_word_timestamps = data.get('include_word_timestamps', False)
                
                print(f"[WHISPER_SERVER] /transcribe model_name: {model_name}, file_path: {file_path}")
                print(f"[WHISPER_SERVER] use_full_audio: {use_full_audio}, start_time: {start_time}, end_time: {end_time}")
                print(f"[WHISPER_SERVER] include_word_timestamps: {include_word_timestamps}")
                
                load_model(model_name)
                
                # Prepare transcription options
                transcribe_options = {}
                
                # Handle time segments
                if not use_full_audio and start_time is not None and end_time is not None:
                    # For time segments, we'll pass the full file and let Whisper handle it
                    # Whisper doesn't have built-in segment support, so we'll note this for the response
                    transcribe_options['verbose'] = True
                
                # Handle word timestamps
                if include_word_timestamps:
                    try:
                        # Try with word_timestamps parameter (newer Whisper versions)
                        transcribe_options['word_timestamps'] = True
                    except:
                        # Fallback for older versions
                        pass
                
                result = MODEL.transcribe(file_path, **transcribe_options)
                
                # Extract text
                text = result['text']
                
                # Get audio duration if possible
                audio_duration = None
                try:
                    import soundfile as sf
                    info = sf.info(file_path)
                    audio_duration = info.duration
                except:
                    try:
                        # Try with ffmpeg
                        import subprocess
                        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path]
                        result_probe = subprocess.run(cmd, capture_output=True, text=True)
                        if result_probe.returncode == 0:
                            import json
                            probe_data = json.loads(result_probe.stdout)
                            audio_duration = float(probe_data['format']['duration'])
                    except:
                        pass
                
                # Process word timestamps
                word_timestamps = []
                if include_word_timestamps and 'segments' in result:
                    for segment in result['segments']:
                        if 'words' in segment:
                            # Word-level timestamps available
                            for word_info in segment['words']:
                                word_timestamps.append({
                                    'word': word_info.get('word', '').strip(),
                                    'start': word_info.get('start', 0),
                                    'end': word_info.get('end', 0)
                                })
                        else:
                            # Fallback: segment-level timestamps with word interpolation
                            segment_text = segment.get('text', '').strip()
                            words = segment_text.split()
                            if words:
                                seg_start = segment.get('start', 0)
                                seg_end = segment.get('end', seg_start + 1)
                                word_duration = (seg_end - seg_start) / len(words) if len(words) > 0 else 0
                                
                                for i, word in enumerate(words):
                                    word_start = seg_start + (i * word_duration)
                                    word_end = word_start + word_duration
                                    word_timestamps.append({
                                        'word': word,
                                        'start': word_start,
                                        'end': word_end
                                    })
                
                # If time segment was requested but not natively supported, note it
                segment_info = None
                if not use_full_audio:
                    segment_info = {
                        'requested_start': start_time,
                        'requested_end': end_time,
                        'note': 'Time segment selection processed on full audio. For precise segment extraction, use desktop application.'
                    }
                
                self.send_response(200)
                self.end_headers()
                resp = {
                    'success': True, 
                    'text': text, 
                    'language': result.get('language', 'en'),
                    'audioDuration': audio_duration,
                    'wordTimestamps': word_timestamps,
                    'segmentInfo': segment_info
                }
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [200]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /transcribe: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {'success': False, 'error': str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/translate':
            try:
                text = data.get('text')
                api_key = data.get('apiKey')
                target_language = data.get('targetLanguage', 'English')
                translation_style = data.get('translationStyle', 'Natural')
                preserve_formatting = data.get('preserveFormatting', True)
                output_format = data.get('outputFormat', 'Markdown')
                print(f"[WHISPER_SERVER] /translate target_language: {target_language}, translation_style: {translation_style}")
                
                client = Anthropic(api_key=api_key)
                style_instructions = {
                    "Natural": "Translate in a natural, fluent way that sounds native to the target language.",
                    "Literal": "Provide a more literal translation that stays close to the original structure.",
                    "Professional": "Use formal, professional language suitable for business or academic contexts.",
                    "Colloquial": "Use everyday, conversational language with appropriate idioms.",
                    "Technical": "Maintain technical terminology and precision, transliterating terms when necessary."
                }
                format_instructions = {
                    "markdown": "Maintain Markdown formatting. Translate headers, lists, and content while preserving structure.",
                    "plain text": "Provide plain text translation without special formatting.",
                    "json": f"Return as JSON with structure: {{'language': '{target_language}', 'translation': '...', 'notes': '...'}}",
                    "bullet points": "Maintain bullet point structure while translating content.",
                    "latex pdf": "Preserve LaTeX commands and structure. Translate content while keeping LaTeX formatting intact. Use appropriate language packages if needed (e.g., \\usepackage[arabic]{{babel}} for Arabic)."
                }
                special_instructions = ""
                if target_language in ["Arabic", "Hebrew"]:
                    special_instructions = "\nNote: This language uses right-to-left script. Ensure proper text direction in the output."
                elif target_language in ["Chinese (Simplified)", "Chinese (Traditional)", "Japanese", "Korean"]:
                    special_instructions = "\nNote: Handle character encoding carefully for East Asian languages."
                prompt = f"""Translate the following transcribed text to {target_language}.

TRANSLATION STYLE: {translation_style}
{style_instructions.get(translation_style, '')}

OUTPUT FORMAT: {output_format}
{format_instructions.get(output_format.lower(), '')}

{'PRESERVE ORIGINAL FORMATTING: Maintain paragraph breaks, punctuation style, and structure.' if preserve_formatting else 'ADAPT FORMATTING: Adjust formatting to be natural for the target language.'}
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
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
                self.send_response(200)
                self.end_headers()
                resp = {"success": True, "translation": result_text}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [{self.command}]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /translate: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/summary':
            print(f"[WHISPER_SERVER] Handling /summary endpoint")
            try:
                text = data.get('text')
                api_key = data.get('apiKey')
                word_limit = data.get('wordLimit', 500)
                output_format = data.get('outputFormat', 'Markdown').lower()
                print(f"[WHISPER_SERVER] /summary word_limit: {word_limit}, output_format: {output_format}")
                
                client = Anthropic(api_key=api_key)
                format_instructions = {
                    "markdown": "Format your response in clean Markdown with appropriate headers and structure.",
                    "plain text": "Provide a plain text response without any formatting.",
                    "json": "Return your response as a well-structured JSON object.",
                    "bullet points": "Structure your response as clear bullet points.",
                    "latex pdf": "Format your response in LaTeX document format with proper document class, sections, and formatting."
                }
                prompt = f"""Please provide a comprehensive summary of the following transcribed audio content in {word_limit} words or less. \nFocus on the main ideas, key points, and important details. Do not print out anything else. \n{format_instructions.get(output_format, '')}\n\nTranscribed text:\n{text}"""
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                summary_text = response.content[0].text
                self.send_response(200)
                self.end_headers()
                resp = {"success": True, "summary": summary_text}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [200]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /summary: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Sending response [500]: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/semantic-summary':
            try:
                text = data.get('text')
                api_key = data.get('apiKey')
                print(f"[WHISPER_SERVER] /semantic-summary")
                
                client = Anthropic(api_key=api_key)
                prompt = (
                    "You will receive a transcript. Write EXACTLY ONE sentence (≤ 30 words) that captures BOTH:\n"
                    "- the core meaning/topic, and\n"
                    "- the overall tone/affect/delivery style (e.g., enthusiastic, cautious, frustrated, formal).\n\n"
                    "Rules:\n"
                    "- Single sentence only; end with a period.\n"
                    "- ≤ 30 words.\n"
                    "- No quotes, labels, lists, JSON, or extra commentary.\n"
                    "- No markdown.\n\n"
                    "Transcript:\n"
                    f"{text}"
                )
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=150,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = response.content[0].text.strip()
                import re
                s = raw.replace("\n", " ").strip()
                s = s.strip(' "\'')
                parts = re.split(r'(?<=[.!?])\s+', s)
                s = parts[0].strip() if parts else s
                if not s.endswith(('.', '!', '?')):
                    s += '.'
                words = s.split()
                if len(words) > 30:
                    s = " ".join(words[:30]).rstrip('.,;:!?') + "."
                self.send_response(200)
                self.end_headers()
                resp = {"success": True, "summary": s}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /semantic-summary: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/clean':
            try:
                text = data.get('text')
                api_key = data.get('apiKey')
                print(f"[WHISPER_SERVER] /clean")
                if not text:
                    raise ValueError("No text provided for cleaning")
                if not api_key:
                    raise ValueError("No apiKey provided for cleaning")
                client = Anthropic(api_key=api_key)
                prompt = f"""Clean the following transcribed text by:\n    1. Correcting any obvious transcription errors or strange words\n    2. Fixing grammar and punctuation while preserving the original meaning\n    3. Removing filler words (um, uh, etc.) where appropriate\n    4. Making the text flow naturally as written prose\n    5. DO NOT summarize or remove content - just clean and correct\n\n    Return ONLY the cleaned text without any commentary or explanations.\n\n    Text to clean:\n    {text}"""
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                cleaned_text = response.content[0].text
                self.send_response(200)
                self.end_headers()
                resp = {"success": True, "cleaned": cleaned_text}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /clean: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/network':
            try:
                text = data.get('text')
                clusters = data.get('clusters', 5)
                print(f"[WHISPER_SERVER] /network clusters: {clusters}")
                
                if not text:
                    raise ValueError("No text provided for network generation")
                
                # Try to generate a simple network plot
                try:
                    import matplotlib
                    matplotlib.use('Agg')  # Use non-interactive backend
                    import matplotlib.pyplot as plt
                    import networkx as nx
                    from collections import Counter
                    import re
                    import os
                    from pathlib import Path
                    
                    # Simple text processing
                    words = re.findall(r'\b[a-z]+\b', text.lower())
                    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                                 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                                 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                                 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can',
                                 'need', 'dare', 'ought', 'used', 'i', 'you', 'he', 'she', 'it', 'we',
                                 'they', 'them', 'their', 'this', 'that', 'these', 'those'}
                    
                    # Filter words
                    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
                    
                    if len(filtered_words) < 5:
                        raise ValueError("Not enough meaningful words for network generation")
                    
                    # Get most frequent words
                    word_freq = Counter(filtered_words)
                    top_words = [word for word, freq in word_freq.most_common(min(20, len(word_freq)))]
                    
                    # Create simple co-occurrence network
                    G = nx.Graph()
                    
                    # Add nodes
                    for word in top_words:
                        G.add_node(word, weight=word_freq[word])
                    
                    # Add edges based on simple co-occurrence (words appearing close together)
                    window_size = 5
                    for i, word1 in enumerate(filtered_words):
                        if word1 in top_words:
                            for j in range(max(0, i-window_size), min(len(filtered_words), i+window_size+1)):
                                if i != j:
                                    word2 = filtered_words[j]
                                    if word2 in top_words and word1 != word2:
                                        if G.has_edge(word1, word2):
                                            G[word1][word2]['weight'] += 1
                                        else:
                                            G.add_edge(word1, word2, weight=1)
                    
                    # Create visualization
                    plt.figure(figsize=(10, 8))
                    plt.clf()
                    
                    # Layout
                    pos = nx.spring_layout(G, k=1, iterations=50)
                    
                    # Node sizes based on frequency
                    node_sizes = [200 + G.nodes[node]['weight'] * 50 for node in G.nodes()]
                    
                    # Draw network
                    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                                         node_color='lightblue', alpha=0.7)
                    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
                    
                    # Draw edges with varying thickness
                    edges = G.edges()
                    if edges:
                        edge_weights = [G[u][v]['weight'] for u, v in edges]
                        max_weight = max(edge_weights) if edge_weights else 1
                        
                        for (u, v), weight in zip(edges, edge_weights):
                            width = 0.5 + (weight / max_weight) * 3
                            alpha = 0.3 + (weight / max_weight) * 0.5
                            nx.draw_networkx_edges(G, pos, [(u, v)], width=width, alpha=alpha, edge_color='gray')
                    
                    plt.title("Word Co-occurrence Network", fontsize=14, fontweight='bold')
                    plt.axis('off')
                    plt.tight_layout()
                    
                    # Save plot
                    plot_filename = f"network_plot_{hash(text[:100]) % 10000}.png"
                    plot_path = Path("uploads") / plot_filename
                    plot_path.parent.mkdir(exist_ok=True)
                    plt.savefig(plot_path, dpi=150, bbox_inches='tight', facecolor='white')
                    plt.close()
                    
                    # Return URL to the plot
                    plot_url = f"/uploads/{plot_filename}"
                    
                    self.send_response(200)
                    self.end_headers()
                    resp = {
                        "success": True, 
                        "message": "Network plot generated successfully", 
                        "plotUrl": plot_url,
                        "clusters": clusters, 
                        "wordCount": len(filtered_words),
                        "nodeCount": len(G.nodes()),
                        "edgeCount": len(G.edges())
                    }
                    print(f"[WHISPER_SERVER] Response: {resp}")
                    self.wfile.write(json.dumps(resp).encode())
                    
                except ImportError as ie:
                    # Missing dependencies for network generation
                    self.send_response(200)
                    self.end_headers()
                    resp = {
                        "success": True, 
                        "message": f"Network plot generation requires additional packages: {str(ie)}. Basic word analysis completed instead.", 
                        "clusters": clusters, 
                        "wordCount": len(text.split()),
                        "note": "For full network plot functionality with Word2Vec embeddings, please use the desktop application."
                    }
                    print(f"[WHISPER_SERVER] Response: {resp}")
                    self.wfile.write(json.dumps(resp).encode())
                    
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /network: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/latex':
            try:
                latex_content = data.get('latexContent')
                print(f"[WHISPER_SERVER] /latex")
                
                # Dummy: return base64 of LaTeX content
                import base64
                pdf = base64.b64encode(latex_content.encode()).decode()
                self.send_response(200)
                self.end_headers()
                resp = {"success": True, "pdf": pdf, "filename": "analysis.pdf"}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /latex: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        elif self.path == '/custom-prompt':
            try:
                text = data.get('text')
                api_key = data.get('apiKey')
                custom_prompt = data.get('customPrompt')
                print(f"[WHISPER_SERVER] /custom-prompt")
                if not text:
                    raise ValueError("No text provided for custom prompt")
                if not api_key:
                    raise ValueError("No apiKey provided for custom prompt")
                if not custom_prompt:
                    raise ValueError("No customPrompt provided for custom prompt")
                client = Anthropic(api_key=api_key)
                prompt = custom_prompt.replace('{text}', text)
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
                self.send_response(200)
                self.end_headers()
                resp = {"success": True, "result": result_text}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /custom-prompt: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json.dumps(resp).encode())
        else:
            print(f"[WHISPER_SERVER] Unknown endpoint: {self.path}")
            self.send_response(404)
            self.end_headers()
            resp = {"success": False, "error": f"Unknown endpoint: {self.path}"}
            print(f"[WHISPER_SERVER] Sending response [404]: {resp}")
            self.wfile.write(json.dumps(resp).encode())

def run():
    server = HTTPServer(('localhost', 8765), Handler)
    print('Whisper server running on port 8765')
    server.serve_forever()

if __name__ == '__main__':
    run()