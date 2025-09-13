import sys
import json as json_module
import whisper
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from anthropic import Anthropic

# Set environment variables before importing matplotlib and sklearn
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from collections import Counter, defaultdict
import re
import base64
import io

# Import sklearn components with error handling
try:
    from sklearn.manifold import TSNE
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: sklearn not available: {e}")
    SKLEARN_AVAILABLE = False

MODEL = None
MODEL_NAME = None

def load_model(model_name):
    global MODEL, MODEL_NAME
    if MODEL is None or MODEL_NAME != model_name:
        MODEL = whisper.load_model(model_name)
        MODEL_NAME = model_name

def create_network_plot(text, num_clusters=5):
    """
    Create semantic network visualization based on text co-occurrence and clustering.
    Returns base64 encoded image of the network plot.
    """
    try:
        # Clean and preprocess text
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            raise ValueError("Text is too short for network analysis")
        
        # Tokenize and filter words
        words = []
        for sentence in sentences:
            # Simple tokenization - remove punctuation and convert to lowercase
            sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            words.extend(sentence_words)
        
        if len(set(words)) < 5:
            raise ValueError("Not enough unique words for network analysis")
        
        # Calculate word frequencies and filter common words
        word_freq = Counter(words)
        # Remove very common words and keep top words
        stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        filtered_words = [word for word in words if word not in stopwords and word_freq[word] >= 2]
        
        if len(set(filtered_words)) < 5:
            # If after filtering we have too few words, use original words
            filtered_words = [word for word in words if word_freq[word] >= 1]
        
        # Get most frequent words for the network
        unique_words = list(set(filtered_words))
        word_freq_filtered = {word: word_freq[word] for word in unique_words}
        top_words = sorted(word_freq_filtered.items(), key=lambda x: x[1], reverse=True)[:min(100, len(unique_words))]
        network_words = [word for word, freq in top_words]
        
        # Create co-occurrence matrix
        co_occurrence = defaultdict(lambda: defaultdict(int))
        window_size = 5
        
        for sentence in sentences:
            sentence_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower()) if w in network_words]
            
            for i, word1 in enumerate(sentence_words):
                for j in range(max(0, i-window_size), min(len(sentence_words), i+window_size+1)):
                    if i != j:
                        word2 = sentence_words[j]
                        co_occurrence[word1][word2] += 1
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes with word frequency as weight
        for word in network_words:
            G.add_node(word, weight=word_freq[word])
        
        # Add edges based on co-occurrence
        for word1 in co_occurrence:
            for word2 in co_occurrence[word1]:
                if word1 != word2 and co_occurrence[word1][word2] > 0:
                    G.add_edge(word1, word2, weight=co_occurrence[word1][word2])
        
        if len(G.nodes()) < 3:
            raise ValueError("Not enough connected words for network visualization")
        
        # Simplified clustering and positioning to avoid segfaults
        clusters = list(range(len(network_words)))  # Default: each word its own cluster
        word_order = network_words
        
        # Use simple clustering if sklearn is available
        if SKLEARN_AVAILABLE and len(network_words) > 3:
            try:
                # Simple frequency-based clustering as fallback
                word_freqs = [word_freq[word] for word in network_words]
                freq_array = np.array(word_freqs).reshape(-1, 1)
                
                n_clusters = min(num_clusters, len(network_words) // 2, 5)
                if n_clusters > 1:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    clusters = kmeans.fit_predict(freq_array)
                else:
                    clusters = [0] * len(network_words)
            except Exception as e:
                print(f"Clustering failed, using simple assignment: {e}")
                clusters = [i % num_clusters for i in range(len(network_words))]
        else:
            # Simple modulo-based clustering
            clusters = [i % num_clusters for i in range(len(network_words))]
        
        # Use NetworkX spring layout (more stable than t-SNE)
        try:
            pos = nx.spring_layout(G, k=1, iterations=50, seed=42)
        except Exception as e:
            print(f"Spring layout failed, using circular: {e}")
            pos = nx.circular_layout(G)
        
        # Create the plot with error handling
        try:
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
            
            # Define colors for clusters
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#FFB347']
            
            # Create cluster mapping
            cluster_colors = {}
            for i, word in enumerate(word_order):
                cluster_id = clusters[i] if i < len(clusters) else 0
                cluster_colors[word] = colors[cluster_id % len(colors)]
            
            # Draw nodes
            node_colors = [cluster_colors.get(node, colors[0]) for node in G.nodes()]
            node_sizes = [word_freq[node] * 100 + 300 for node in G.nodes()]
            
            nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8, ax=ax)
            
            # Draw edges
            edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
            if edge_weights:
                max_weight = max(edge_weights) if edge_weights else 1
                edge_widths = [max(0.5, w / max_weight * 3) for w in edge_weights]
                nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.6, edge_color='gray', ax=ax)
            
            # Draw labels
            nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', ax=ax)
            
            ax.set_title('Semantic Network Visualization', fontsize=16, fontweight='bold')
            ax.axis('off')
            plt.tight_layout()
            
            # Convert plot to base64 image
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Clean up
            plt.close(fig)
            plt.clf()
            
            return img_base64
            
        except Exception as plot_error:
            print(f"Plotting error: {plot_error}")
            # Create a simple fallback plot
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, f'Network Analysis\n{len(network_words)} words\n{len(G.edges())} connections', 
                   ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.set_title('Semantic Network (Simplified)', fontsize=16)
            ax.axis('off')
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)
            return img_base64
        
    except Exception as e:
        print(f"Error creating network plot: {e}")
        # Create minimal error plot
        try:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.text(0.5, 0.5, f'Network Generation Error\n{str(e)[:100]}...', 
                   ha='center', va='center', fontsize=12, transform=ax.transAxes)
            ax.set_title('Network Analysis Failed', fontsize=14)
            ax.axis('off')
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)
            return img_base64
        except:
            raise Exception(f"Network plot generation failed: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"[WHISPER_SERVER] do_POST called for path: {self.path}")
        print(f"[WHISPER_SERVER] Headers: {dict(self.headers)}")
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(length)
            print(f"[WHISPER_SERVER] Raw request data: {raw_data}")
            data = json_module.loads(raw_data)
            print(f"[WHISPER_SERVER] Parsed JSON: {data}")
        except Exception as e:
            print(f"[WHISPER_SERVER] Failed to parse request: {e}")
            self.send_response(400)
            self.end_headers()
            resp = {"success": False, "error": f"Bad request: {str(e)}"}
            print(f"[WHISPER_SERVER] Sending response [400]: {resp}")
            self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [200]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /load: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {'loaded': False, 'error': str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
        elif self.path == '/transcribe':
            try:
                file_path = data.get('audio_path') or data.get('audioPath')
                if file_path is None:
                    raise ValueError("No audio_path or audioPath provided in request")
                model_name = data.get('model', 'base')
                start_time = data.get('startTime', 0)
                end_time = data.get('endTime', 0)
                
                print(f"[WHISPER_SERVER] /transcribe model_name: {model_name}, file_path: {file_path}, start_time: {start_time}, end_time: {end_time}")
                load_model(model_name)
                
                # Handle time segment extraction if needed
                if start_time > 0 or end_time > 0:
                    # Use time segment - need to extract the audio segment first
                    import tempfile
                    import subprocess
                    
                    # Create temporary file for segment
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        temp_path = temp_file.name
                    
                    try:
                        # Extract segment using ffmpeg
                        duration = end_time - start_time if end_time > start_time else None
                        cmd = ['ffmpeg', '-i', file_path]
                        
                        if start_time > 0:
                            cmd.extend(['-ss', str(start_time)])
                        
                        if duration:
                            cmd.extend(['-t', str(duration)])
                        
                        cmd.extend([
                            '-acodec', 'pcm_s16le',
                            '-ar', '16000',
                            '-ac', '1',
                            '-y',  # Overwrite output file
                            temp_path
                        ])
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        
                        if result.returncode != 0:
                            print(f"[WHISPER_SERVER] FFmpeg error: {result.stderr}")
                            # Fallback to full file transcription
                            transcription_result = MODEL.transcribe(file_path)
                        else:
                            # Transcribe the extracted segment with word timestamps
                            transcription_result = MODEL.transcribe(temp_path, word_timestamps=True)
                        
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                else:
                    # Transcribe full audio with word timestamps
                    transcription_result = MODEL.transcribe(file_path, word_timestamps=True)
                
                # Extract word timestamps if available
                word_timestamps = []
                if 'segments' in transcription_result:
                    for segment in transcription_result['segments']:
                        if 'words' in segment:
                            for word_info in segment['words']:
                                word_timestamps.append({
                                    'word': word_info.get('word', '').strip(),
                                    'start': word_info.get('start', 0),
                                    'end': word_info.get('end', 0)
                                })
                
                self.send_response(200)
                self.end_headers()
                resp = {
                    'success': True, 
                    'text': transcription_result['text'], 
                    'language': transcription_result.get('language', 'en'),
                    'word_timestamps': word_timestamps
                }
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [200]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /transcribe: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {'success': False, 'error': str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [{self.command}]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /translate: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
                print(f"[WHISPER_SERVER] Sending response [200]: {resp}")
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /summary: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Sending response [500]: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /semantic-summary: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /clean: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
        elif self.path == '/network':
            try:
                text = data.get('text')
                clusters = data.get('clusters', 5)
                print(f"[WHISPER_SERVER] /network clusters: {clusters}")
                
                if not text or len(text.strip()) < 50:
                    raise ValueError("Text is too short for network analysis")
                
                # Generate network plot
                img_base64 = create_network_plot(text, clusters)
                
                self.send_response(200)
                self.end_headers()
                resp = {
                    "success": True, 
                    "message": "Network plot generated successfully", 
                    "image": img_base64,
                    "clusters": clusters, 
                    "wordCount": len(text.split())
                }
                print(f"[WHISPER_SERVER] Response: Network plot generated with {len(text.split())} words")
                self.wfile.write(json_module.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /network: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /latex: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
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
                self.wfile.write(json_module.dumps(resp).encode())
            except Exception as e:
                print(f"[WHISPER_SERVER] Error in /custom-prompt: {e}")
                self.send_response(500)
                self.end_headers()
                resp = {"success": False, "error": str(e)}
                print(f"[WHISPER_SERVER] Response: {resp}")
                self.wfile.write(json_module.dumps(resp).encode())
        else:
            print(f"[WHISPER_SERVER] Unknown endpoint: {self.path}")
            self.send_response(404)
            self.end_headers()
            resp = {"success": False, "error": f"Unknown endpoint: {self.path}"}
            print(f"[WHISPER_SERVER] Sending response [404]: {resp}")
            self.wfile.write(json_module.dumps(resp).encode())

def run():
    server = HTTPServer(('localhost', 8765), Handler)
    print('Whisper server running on port 8765')
    server.serve_forever()

if __name__ == '__main__':
    run()