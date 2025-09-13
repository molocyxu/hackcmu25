import os
import sys
import json
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import Counter
import re
import customtkinter as ctk
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
from anthropic import Anthropic
from typing import Optional, Dict, Any, List, Tuple
import queue
import time
import subprocess
import tempfile

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AudioAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Audio Transcription & Analysis Tool")
        self.geometry("1400x800")
        
        # Make window resizable with minimum size
        self.minsize(1200, 600)
        self.resizable(True, True)
        
        # Initialize variables
        self.audio_file_path = None
        self.transcribed_text = ""
        self.api_key = None
        self.whisper_model = None
        self.error_queue = queue.Queue()
        self.model_loading = False
        
        # History for processed results (prompt, output) pairs
        self.process_history: List[Tuple[str, str]] = []
        self.current_history_index = -1
        
        # Recording variables
        self.is_recording = False
        self.recording_data = []
        self.word_timestamps = []
        self.recording_samplerate = 44100
        self.recording_thread = None
        self.recording_start_time = None
        self.recorded_file_path = None
        self.recording_process = None
        
        # Time segment variables
        self.audio_duration = None
        self.last_transcription_segment = (None, None)
        
        # Network plot variables
        self.current_network_plot_path = None
        self.word2vec_model = None
        self.network_photo = None  # Store the photo reference
        
        # Configure grid weight for resizing
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create main container with proper scaling
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=0)  # Sidebar doesn't resize
        self.main_container.grid_columnconfigure(1, weight=3)  # Main content scales
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Create UI components
        self.create_sidebar()
        self.create_main_panel()
        
        # Bind resize event for network plot
        self.bind("<Configure>", self.on_window_resize)
        
        # Start checking for errors from background threads
        self.check_error_queue()
        
        # Initialize Whisper model in background
        self.load_whisper_model()

    def toggle_time_segment(self):
        """Toggle between full audio and time segment selection"""
        if self.use_full_audio_var.get():
            # Disable time inputs
            self.start_time_entry.configure(state="disabled")
            self.end_time_entry.configure(state="disabled")
            self.duration_info_label.configure(text="Duration: Full audio")
        else:
            # Enable time inputs
            self.start_time_entry.configure(state="normal")
            self.end_time_entry.configure(state="normal")
            self.update_duration_info()
        
        # Update button states since we may need to re-transcribe
        self.update_button_states()
    
    def update_duration_info(self):
        """Update the duration info label based on selected time segment"""
        if self.use_full_audio_var.get():
            self.duration_info_label.configure(text="Duration: Full audio")
        else:
            try:
                start = float(self.start_time_var.get() or 0)
                end = float(self.end_time_var.get() or 0)
                
                if end > start:
                    duration = end - start
                    mins, secs = divmod(int(duration), 60)
                    self.duration_info_label.configure(
                        text=f"Duration: {mins:02d}:{secs:02d} ({duration:.1f}s)",
                        text_color=("green", "lightgreen")
                    )
                else:
                    self.duration_info_label.configure(
                        text="Invalid range: End must be after Start",
                        text_color=("red", "lightcoral")
                    )
            except ValueError:
                self.duration_info_label.configure(
                    text="Invalid input: Enter numbers only",
                    text_color=("red", "lightcoral")
                )
    
    def get_audio_duration(self, file_path):
        """Get the duration of an audio/video file in seconds"""
        try:
            # Try with soundfile first
            import soundfile as sf
            info = sf.info(file_path)
            return info.duration
        except:
            try:
                # Try with ffmpeg as fallback
                import subprocess
                import json
                
                cmd = [
                    'ffprobe', '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    file_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    duration = float(data['format']['duration'])
                    return duration
            except:
                pass
        
        # If all methods fail, return None
        return None
    
    def update_valid_range(self):
        """Update the valid range label based on loaded audio file"""
        if self.audio_file_path:
            duration = self.get_audio_duration(self.audio_file_path)
            if duration:
                mins, secs = divmod(int(duration), 60)
                self.valid_range_label.configure(
                    text=f"Valid range: 0 - {duration:.1f}s ({mins:02d}:{secs:02d})",
                    text_color=("blue", "lightblue")
                )
                
                # Update end time to match duration if using full audio
                if self.use_full_audio_var.get():
                    self.end_time_var.set(str(int(duration)))
                
                # Store duration for validation
                self.audio_duration = duration
            else:
                self.valid_range_label.configure(
                    text="Valid range: Unable to determine",
                    text_color=("orange", "darkorange")
                )
                self.audio_duration = None
        else:
            self.valid_range_label.configure(
                text="Valid range: No file loaded",
                text_color=("gray50", "gray50")
            )
            self.audio_duration = None
    
    def validate_time_segment(self):
        """Validate the selected time segment"""
        if self.use_full_audio_var.get():
            return True
        
        try:
            start = float(self.start_time_var.get() or 0)
            end = float(self.end_time_var.get() or 0)
            
            if start < 0:
                messagebox.showwarning("Invalid Time", "Start time cannot be negative")
                return False
            
            if end <= start:
                messagebox.showwarning("Invalid Time", "End time must be after start time")
                return False
            
            if hasattr(self, 'audio_duration') and self.audio_duration:
                if end > self.audio_duration:
                    messagebox.showwarning("Invalid Time", f"End time exceeds audio duration ({self.audio_duration:.1f}s)")
                    return False
            
            return True
            
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numbers for time segment")
            return False
    
    def get_time_segment_params(self):
        """Get the time segment parameters for transcription"""
        if self.use_full_audio_var.get():
            return None, None
        
        try:
            start = float(self.start_time_var.get() or 0)
            end = float(self.end_time_var.get() or 0)
            return start, end
        except ValueError:
            return None, None

    def search_word(self):
        """Search for a word in the transcription and display timestamps"""
        search_term = self.search_entry.get().strip().lower()
        
        if not search_term:
            messagebox.showwarning("Empty Search", "Please enter a word to search")
            return
        
        if not hasattr(self, 'word_timestamps') or not self.word_timestamps:
            messagebox.showwarning("No Timestamps", "No word timestamps available. Please transcribe audio first.")
            return
        
        # Find matching words
        matches = []
        for word_info in self.word_timestamps:
            if search_term in word_info["word"].lower():
                matches.append(word_info)
        
        # Display results
        self.search_results_text.configure(state="normal")
        self.search_results_text.delete("1.0", "end")
        
        if matches:
            self.search_results_label.configure(text=f"Found {len(matches)} matches")
            
            # Group by unique occurrences (first occurrence of each instance)
            seen_times = set()
            unique_matches = []
            
            for match in matches:
                time_key = f"{match['start']:.1f}"
                if time_key not in seen_times:
                    seen_times.add(time_key)
                    unique_matches.append(match)
            
            # Display matches with timestamps
            for i, match in enumerate(unique_matches[:50], 1):  # Limit to first 50 matches
                time_str = self.format_timestamp(match["start"])
                self.search_results_text.insert("end", f"{i}. \"{match['word']}\" at {time_str}\n")
                
                # Add click binding to jump to position (future enhancement)
                self.search_results_text.insert("end", f"   [{time_str}]\n", "timestamp")
            
            if len(unique_matches) > 50:
                self.search_results_text.insert("end", f"\n... and {len(unique_matches) - 50} more matches")
            
            # Highlight first occurrence in main text
            self.highlight_search_term(search_term)
            
        else:
            self.search_results_label.configure(text="No matches found")
            self.search_results_text.insert("end", f"No matches found for \"{search_term}\"")
        
        self.search_results_text.configure(state="disabled")
    
    def clear_search(self):
        """Clear search results and highlighting"""
        self.search_entry.delete(0, "end")
        self.search_results_text.configure(state="normal")
        self.search_results_text.delete("1.0", "end")
        self.search_results_text.insert("1.0", "Search Results")
        self.search_results_text.configure(state="disabled")
        self.search_results_label.configure(text="Search Results")
        
        # Clear highlighting in main text
        self.trans_text.tag_remove("highlight", "1.0", "end")
    
    def highlight_search_term(self, search_term):
        """Highlight search term in transcription text"""
        self.trans_text.tag_remove("highlight", "1.0", "end")
        
        if not search_term:
            return
        
        # Configure highlight tag
        self.trans_text.tag_config("highlight", background="yellow", foreground="black")
        
        # Search and highlight
        start_pos = "1.0"
        while True:
            pos = self.trans_text.search(search_term, start_pos, stopindex="end", nocase=True)
            if not pos:
                break
            
            end_pos = f"{pos}+{len(search_term)}c"
            self.trans_text.tag_add("highlight", pos, end_pos)
            start_pos = end_pos
    
    def format_timestamp(self, seconds):
        """Format timestamp in MM:SS format"""
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def create_network_plot(self):
        """Create a network plot using Word2Vec embeddings with user-selectable clustering"""
        if not self.transcribed_text:
            messagebox.showwarning("No Content", "No transcription available for network plot")
            return
        
        api_key = self.api_key_entry.get() or self.api_key
        if not api_key:
            messagebox.showwarning("API Key Required", "Please enter your Anthropic API key")
            return
        
        # Ask user for number of clusters
        cluster_dialog = ctk.CTkInputDialog(
            text="Enter number of clusters (2-10):",
            title="Cluster Configuration"
        )
        n_clusters_str = cluster_dialog.get_input()
        
        try:
            n_clusters = int(n_clusters_str) if n_clusters_str else 5
            n_clusters = max(2, min(10, n_clusters))
        except:
            n_clusters = 5
        
        def generate_plot():
            try:
                self.after(0, lambda: self.network_button.configure(state="disabled"))
                self.after(0, lambda: self.update_status("Loading Word2Vec model..."))
                self.after(0, lambda: self.progress_bar.set(0.1))
                
                # Load or cache Word2Vec model with better error handling
                if self.word2vec_model is None:
                    try:
                        import gensim.downloader as api
                        # Try to load a smaller, faster model first
                        self.after(0, lambda: self.update_status("Downloading Word2Vec model (first time only)..."))
                        self.word2vec_model = api.load('glove-wiki-gigaword-50')
                    except Exception as e:
                        self.error_queue.put(("Model Error", f"Failed to load Word2Vec model: {str(e)}\nPlease install: pip install gensim"))
                        return
                
                self.after(0, lambda: self.update_status("Processing text with Word2Vec..."))
                self.after(0, lambda: self.progress_bar.set(0.3))
                
                # Preprocess text
                text = self.transcribed_text.lower()
                words = re.findall(r'\b[a-z]+\b', text)
                
                # Enhanced stop words list
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                             'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                             'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                             'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can',
                             'need', 'dare', 'ought', 'used', 'i', 'you', 'he', 'she', 'it', 'we',
                             'they', 'them', 'their', 'this', 'that', 'these', 'those'}
                
                # Filter words and keep only those in Word2Vec vocabulary
                filtered_words = []
                for w in words:
                    if w not in stop_words and len(w) > 2:
                        try:
                            # Check if word is in model vocabulary
                            if hasattr(self.word2vec_model, 'key_to_index'):
                                if w in self.word2vec_model.key_to_index:
                                    filtered_words.append(w)
                            elif w in self.word2vec_model:
                                filtered_words.append(w)
                        except:
                            pass
                
                if len(filtered_words) < 5:
                    self.error_queue.put(("Insufficient Data", "Not enough words found in the Word2Vec vocabulary. The text may be too short or contain specialized terms."))
                    return
                
                # Get most frequent words that have embeddings
                word_freq = Counter(filtered_words)
                top_words = [word for word, freq in word_freq.most_common(150)]
                
                if len(top_words) < 5:
                    self.error_queue.put(("Insufficient Data", "Not enough words with embeddings found. Try with longer text."))
                    return
                
                # Get Word2Vec embeddings
                embeddings = []
                valid_words = []
                for word in top_words:
                    try:
                        if hasattr(self.word2vec_model, 'get_vector'):
                            embeddings.append(self.word2vec_model.get_vector(word))
                        else:
                            embeddings.append(self.word2vec_model[word])
                        valid_words.append(word)
                    except:
                        pass
                
                if len(embeddings) < 5:
                    self.error_queue.put(("Insufficient Embeddings", "Not enough word embeddings found. The text may be too specialized."))
                    return
                
                embeddings = np.array(embeddings)
                
                self.after(0, lambda: self.update_status("Clustering words in embedding space..."))
                self.after(0, lambda: self.progress_bar.set(0.4))
                
                # Perform clustering in high-dimensional space
                from sklearn.cluster import KMeans
                n_clusters_actual = min(n_clusters, len(valid_words) // 2)
                kmeans = KMeans(n_clusters=n_clusters_actual, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(embeddings)
                
                # Create co-occurrence information for edge weights
                window_size = 7
                co_occurrences = {}
                word_positions = {word: [] for word in valid_words}
                
                # Record positions of valid words
                for i, word in enumerate(filtered_words):
                    if word in valid_words:
                        word_positions[word].append(i)
                
                # Calculate co-occurrences with distance weighting
                for word1 in valid_words:
                    for word2 in valid_words:
                        if word1 != word2:
                            pair = tuple(sorted([word1, word2]))
                            if pair not in co_occurrences:
                                co_occurrences[pair] = 0
                                for pos1 in word_positions[word1]:
                                    for pos2 in word_positions[word2]:
                                        distance = abs(pos1 - pos2)
                                        if distance <= window_size:
                                            # Weight by inverse distance
                                            co_occurrences[pair] += 1.0 / (1 + distance)
                
                self.after(0, lambda: self.update_status("Projecting to 2D space..."))
                self.after(0, lambda: self.progress_bar.set(0.5))
                
                # Project to 2D using t-SNE for better visualization
                from sklearn.manifold import TSNE
                from sklearn.decomposition import PCA
                
                if len(embeddings) > 30:
                    # Use PCA first for dimensionality reduction if many words
                    pca = PCA(n_components=min(30, len(embeddings)-1))
                    embeddings_reduced = pca.fit_transform(embeddings)
                    tsne = TSNE(n_components=2, perplexity=min(30, len(embeddings)-1), 
                               random_state=42, n_iter=1000)
                    coords_2d = tsne.fit_transform(embeddings_reduced)
                else:
                    perplexity = min(5, len(embeddings)-1)  # Ensure perplexity is valid
                    tsne = TSNE(n_components=2, perplexity=perplexity, 
                               random_state=42, n_iter=1000)
                    coords_2d = tsne.fit_transform(embeddings)
                
                # Create network graph
                import networkx as nx
                G = nx.Graph()
                
                # Add nodes with positions and attributes
                for i, word in enumerate(valid_words):
                    G.add_node(word, 
                              pos=(coords_2d[i, 0], coords_2d[i, 1]),
                              cluster=cluster_labels[i],
                              weight=word_freq[word])
                
                # Add edges based only on co-occurrence from the transcript
                for i, word1 in enumerate(valid_words):
                    for j, word2 in enumerate(valid_words[i+1:], i+1):
                        pair = tuple(sorted([word1, word2]))
                        co_occur = co_occurrences.get(pair, 0)
                        
                        # Add edge only if words co-occur in the transcript
                        if co_occur > 0.25:  # Threshold for meaningful co-occurrence
                            G.add_edge(word1, word2, weight=co_occur)
                
                self.after(0, lambda: self.update_status("Creating visualization..."))
                self.after(0, lambda: self.progress_bar.set(0.7))
                
                # Create visualization
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(10, 8))
                fig.patch.set_facecolor('#f0f0f0')
                ax.set_facecolor('#ffffff')
                
                # Use positions from t-SNE (semantic positioning)
                pos = nx.get_node_attributes(G, 'pos')
                
                # Color scheme for clusters
                colors = plt.cm.Set3(np.linspace(0, 1, n_clusters_actual))
                node_colors = [colors[G.nodes[node]['cluster']] for node in G.nodes()]
                
                # Node sizes based on word frequency
                node_sizes = [200 + G.nodes[node]['weight'] * 20 for node in G.nodes()]
                
                # Draw edges with varying thickness based on co-occurrence strength
                edges = G.edges()
                if edges:
                    edge_weights = [G[u][v]['weight'] for u, v in edges]
                    max_weight = max(edge_weights) if edge_weights else 1
                    
                    # Draw edges with thickness proportional to co-occurrence
                    for (u, v), weight in zip(edges, edge_weights):
                        alpha = 0.3 + (weight / max_weight) * 0.5
                        width = 0.5 + (weight / max_weight) * 3
                        nx.draw_networkx_edges(G, pos, [(u, v)], alpha=alpha, 
                                             width=width, edge_color='#666666', ax=ax)
                
                # Draw nodes
                nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                                     node_size=node_sizes, alpha=0.85,
                                     edgecolors='black', linewidths=1.5, ax=ax)
                
                # Draw labels
                labels = {node: node for node in G.nodes()}
                nx.draw_networkx_labels(G, pos, labels, font_size=8, 
                                       font_weight='bold', ax=ax)
                
                # Add title
                ax.set_title("Semantic Network: Word2Vec Similarity & Co-occurrence", 
                            fontsize=12, fontweight='bold', pad=20)
                ax.axis('off')
                
                # Add cluster legend
                for i in range(n_clusters_actual):
                    cluster_words = [w for w in valid_words if cluster_labels[valid_words.index(w)] == i][:3]
                    label = f"Cluster {i+1}: {', '.join(cluster_words[:3])}..."
                    ax.scatter([], [], c=[colors[i]], s=150, label=label, alpha=0.85)
                
                ax.legend(loc='upper left', frameon=True, fancybox=True, 
                         shadow=True, fontsize=8)
                
                plt.tight_layout()
                
                # Save plot
                plot_path = Path("network_analysis.png")
                plt.savefig(plot_path, dpi=150, bbox_inches='tight', 
                           facecolor='#f0f0f0', edgecolor='none')
                plt.close()
                
                # Display plot in the panel instead of new window
                self.after(0, lambda: self.show_network_plot_in_panel(plot_path))
                self.after(0, lambda: self.update_status("Network plot generated successfully"))
                self.after(0, lambda: self.progress_bar.set(1.0))
                
            except Exception as e:
                self.error_queue.put(("Plot Error", f"Failed to generate network plot: {str(e)}"))
            finally:
                self.after(0, lambda: self.progress_bar.set(0))
                self.after(0, lambda: self.network_button.configure(state="normal"))
                if hasattr(self, 'refresh_network_btn'):
                    self.after(0, lambda: self.refresh_network_btn.configure(state="normal"))
        
        threading.Thread(target=generate_plot, daemon=True).start()

def main():
    """Main entry point"""
    # Check for required packages
    required_packages = {
        'whisper': 'openai-whisper',
        'anthropic': 'anthropic',
        'customtkinter': 'customtkinter',
        'sounddevice': 'sounddevice',
        'soundfile': 'soundfile'
    }
    
    missing_packages = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages. Please install them using:")
        print(f"pip install {' '.join(missing_packages)}")
        print("\nFor macOS, you may also need:")
        print("brew install ffmpeg portaudio")  # Added portaudio
        print("\nFor LaTeX PDF export (optional):")
        print("- Windows: Install MiKTeX or TeX Live")
        print("- macOS: Install MacTeX")
        print("- Linux: sudo apt-get install texlive-full")
        sys.exit(1)
    
    # Run the application
    app = AudioAnalyzerApp()
    app.mainloop()

if __name__ == "__main__":
    main()