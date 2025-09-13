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

    def create_sidebar(self):
        """Updated create_sidebar method with new features integrated"""
        # Create a scrollable sidebar container
        sidebar_container = ctk.CTkFrame(self.main_container, width=320)
        sidebar_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar_container.grid_propagate(False)
        sidebar_container.grid_rowconfigure(0, weight=1)
        sidebar_container.grid_columnconfigure(0, weight=1)
        
        # Create scrollable frame
        self.sidebar_scroll = ctk.CTkScrollableFrame(
            sidebar_container,
            width=300,
            corner_radius=0
        )
        self.sidebar_scroll.grid(row=0, column=0, sticky="nsew")
        
        # Use self.sidebar_scroll as the parent for all sidebar content
        self.sidebar = self.sidebar_scroll  # For compatibility with existing code
        
        # Title
        title_label = ctk.CTkLabel(
            self.sidebar, 
            text="DeScribe.AI", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 20))
        
        # Step 1: File Selection Section
        step1_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        step1_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            step1_frame, 
            text="Step 1: Select Audio File",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self.file_button = ctk.CTkButton(
            step1_frame,
            text="📁 Choose Audio File",
            command=self.select_audio_file,
            height=40
        )
        self.file_button.pack(fill="x", pady=(0, 5))
        
        self.file_label = ctk.CTkLabel(
            step1_frame, 
            text="No file selected", 
            wraplength=250,
            font=ctk.CTkFont(size=11)
        )
        self.file_label.pack(anchor="w")
        
        # Recording Section (between Step 1 and Step 2)
        recording_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        recording_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            recording_frame,
            text="Or Record Audio:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Recording controls frame
        record_controls = ctk.CTkFrame(recording_frame)
        record_controls.pack(fill="x")
        
        self.record_button = ctk.CTkButton(
            record_controls,
            text="🎤 Start Recording",
            command=self.toggle_recording,
            height=40,
            fg_color=("gray75", "gray25")
        )
        self.record_button.pack(fill="x", pady=(0, 5))
        
        # Recording status
        self.recording_status = ctk.CTkLabel(
            record_controls,
            text="Ready to record",
            font=ctk.CTkFont(size=11)
        )
        self.recording_status.pack(anchor="w", pady=(0, 5))
        
        # Recording timer
        self.recording_timer = ctk.CTkLabel(
            record_controls,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("red", "lightcoral")
        )
        self.recording_timer.pack(anchor="w")
        
        # Use recording button
        self.use_recording_button = ctk.CTkButton(
            record_controls,
            text="📂 Use Recording",
            command=self.use_recording,
            height=32,
            state="disabled"
        )
        self.use_recording_button.pack(fill="x", pady=(5, 0))
        
        # Time Segment Selection
        time_segment_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        time_segment_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            time_segment_frame,
            text="Time Segment Selection:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Use full audio checkbox
        self.use_full_audio_var = ctk.BooleanVar(value=True)
        self.use_full_audio_check = ctk.CTkCheckBox(
            time_segment_frame,
            text="Use full audio",
            variable=self.use_full_audio_var,
            command=self.toggle_time_segment,
            font=ctk.CTkFont(size=12)
        )
        self.use_full_audio_check.pack(anchor="w", pady=(0, 10))
        
        # Time range inputs
        time_input_frame = ctk.CTkFrame(time_segment_frame)
        time_input_frame.pack(fill="x")
        
        # Start time
        start_frame = ctk.CTkFrame(time_input_frame)
        start_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(start_frame, text="Start (seconds):", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 10))
        self.start_time_var = ctk.StringVar(value="0")
        self.start_time_entry = ctk.CTkEntry(
            start_frame,
            width=80,
            textvariable=self.start_time_var,
            state="disabled"
        )
        self.start_time_entry.pack(side="left")
        
        # End time
        end_frame = ctk.CTkFrame(time_input_frame)
        end_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(end_frame, text="End (seconds):", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 10))
        self.end_time_var = ctk.StringVar(value="0")
        self.end_time_entry = ctk.CTkEntry(
            end_frame,
            width=80,
            textvariable=self.end_time_var,
            state="disabled"
        )
        self.end_time_entry.pack(side="left")
        
        # Duration info label
        self.duration_info_label = ctk.CTkLabel(
            time_segment_frame,
            text="Duration: Full audio",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray50")
        )
        self.duration_info_label.pack(anchor="w", pady=(5, 0))
        
        # Valid range label
        self.valid_range_label = ctk.CTkLabel(
            time_segment_frame,
            text="Valid range: No file loaded",
            font=ctk.CTkFont(size=11),
            text_color=("blue", "lightblue")
        )
        self.valid_range_label.pack(anchor="w", pady=(2, 0))
        
        # Step 2: Transcription Section
        step2_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        step2_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            step2_frame,
            text="Step 2: Transcribe Audio",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Whisper Model Selection
        model_container = ctk.CTkFrame(step2_frame)
        model_container.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(model_container, text="Whisper Model:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(5, 5))
        
        model_select_frame = ctk.CTkFrame(model_container)
        model_select_frame.pack(fill="x")
        
        self.model_var = ctk.StringVar(value="base")
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_menu = ctk.CTkOptionMenu(
            model_select_frame,
            values=models,
            variable=self.model_var,
            command=self.on_model_change,
            width=140
        )
        self.model_menu.pack(side="left", pady=(0, 5))
        
        # Model status indicator inline
        self.model_status = ctk.CTkLabel(
            model_select_frame, 
            text="⚪ Not loaded",
            font=ctk.CTkFont(size=11)
        )
        self.model_status.pack(side="left", padx=(10, 0))
        
        # Transcribe Button
        self.transcribe_button = ctk.CTkButton(
            step2_frame,
            text="🎙️ Transcribe",
            command=self.start_transcription,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            fg_color=("gray75", "gray25")
        )
        self.transcribe_button.pack(fill="x", pady=(5, 0))
        
        # Clean Text Button
        self.clean_button = ctk.CTkButton(
            step2_frame,
            text="🧹 Clean Text",
            command=self.clean_transcribed_text,
            height=35,
            state="disabled",
            fg_color=("gray75", "gray25")
        )
        self.clean_button.pack(fill="x", pady=(5, 0))
        
        # Network Plot Button
        self.network_button = ctk.CTkButton(
            step2_frame,
            text="🕸️ Generate Network Plot",
            command=self.create_network_plot,
            height=35,
            state="disabled",
            fg_color=("gray75", "gray25")
        )
        self.network_button.pack(fill="x", pady=(5, 0))
        
        # Step 3: Processing Section
        step3_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        step3_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            step3_frame,
            text="Step 3: Process with AI",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # API Key Entry
        api_container = ctk.CTkFrame(step3_frame)
        api_container.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(api_container, text="Anthropic API Key:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(5, 5))
        
        api_entry_frame = ctk.CTkFrame(api_container)
        api_entry_frame.pack(fill="x")
        
        self.api_key_entry = ctk.CTkEntry(api_entry_frame, show="*", width=180)
        self.api_key_entry.pack(side="left", pady=(0, 5))
        
        self.save_api_button = ctk.CTkButton(
            api_entry_frame,
            text="Save",
            command=self.save_api_key,
            width=60,
            height=28
        )
        self.save_api_button.pack(side="left", padx=(5, 0))
        
        # Create the new summarize section with templates and tones
        self.create_summarize_section(step3_frame)
        
        # Create the translation section
        self.create_translation_section(self.sidebar)
        
        # Output Format
        format_frame = ctk.CTkFrame(step3_frame)
        format_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(format_frame, text="Output Format:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 10))
        
        self.output_format = ctk.StringVar(value="Markdown")
        formats = ["Markdown", "Plain Text", "JSON", "Bullet Points", "LaTeX PDF"]
        self.format_menu = ctk.CTkOptionMenu(
            format_frame,
            values=formats,
            variable=self.output_format,
            width=140,
            height=28
        )
        self.format_menu.pack(side="left", fill="x", expand=True)
        
        # Progress Section
        progress_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(20, 20))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(
            progress_frame, 
            text="Ready", 
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack()

    def create_summarize_section(self, parent_frame):
        """Create the summarize section with templates and tones"""
        # Summarize Options
        summarize_frame = ctk.CTkFrame(parent_frame)
        summarize_frame.pack(fill="x", pady=(10, 0))
        
        # Template selection
        template_frame = ctk.CTkFrame(summarize_frame)
        template_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(template_frame, text="Template:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        self.summary_template_var = ctk.StringVar(value="Standard")
        templates = [
            "Standard",
            "Executive Summary",
            "Academic Paper",
            "Meeting Minutes",
            "Podcast Notes",
            "Lecture Notes",
            "Interview Summary",
            "Technical Report",
            "News Article",
            "Research Brief"
        ]
        self.template_menu = ctk.CTkOptionMenu(
            template_frame,
            values=templates,
            variable=self.summary_template_var,
            width=140,
            height=28
        )
        self.template_menu.pack(side="left", fill="x", expand=True)
        
        # Tone selection
        tone_frame = ctk.CTkFrame(summarize_frame)
        tone_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(tone_frame, text="Tone:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        self.summary_tone_var = ctk.StringVar(value="Professional")
        tones = [
            "Professional",
            "Casual",
            "Academic",
            "Technical",
            "Creative",
            "Formal",
            "Conversational",
            "Analytical",
            "Persuasive",
            "Objective"
        ]
        self.tone_menu = ctk.CTkOptionMenu(
            tone_frame,
            values=tones,
            variable=self.summary_tone_var,
            width=140,
            height=28
        )
        self.tone_menu.pack(side="left", fill="x", expand=True)
        
        # Word limit setting
        word_limit_frame = ctk.CTkFrame(summarize_frame)
        word_limit_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(word_limit_frame, text="Word Limit:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        self.word_limit_var = ctk.StringVar(value="500")
        self.word_limit_entry = ctk.CTkEntry(
            word_limit_frame,
            width=80,
            textvariable=self.word_limit_var,
            placeholder_text="500"
        )
        self.word_limit_entry.pack(side="left")
        
        ctk.CTkLabel(word_limit_frame, text="words", font=ctk.CTkFont(size=11)).pack(side="left", padx=(5, 0))
        
        # Summarize Button
        self.summarize_button = ctk.CTkButton(
            summarize_frame,
            text="📝 Summarize",
            command=self.summarize_transcription,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray75", "gray25")
        )
        self.summarize_button.pack(fill="x", pady=(5, 0))
        
        return summarize_frame

    def create_translation_section(self, parent_frame):
        """Create the translation section in the sidebar"""
        # Translation Section (add after Summarize section)
        translation_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        translation_frame.pack(fill="x", padx=20, pady=(15, 0))
        
        ctk.CTkLabel(
            translation_frame,
            text="Translation",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Language selection
        lang_select_frame = ctk.CTkFrame(translation_frame)
        lang_select_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(lang_select_frame, text="Target Language:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 5))
        
        self.target_language_var = ctk.StringVar(value="Spanish")
        languages = [
            "Spanish", "French", "German", "Italian", "Portuguese", "Dutch",
            "Russian", "Chinese (Simplified)", "Chinese (Traditional)", 
            "Japanese", "Korean", "Arabic", "Hindi", "Bengali",
            "Turkish", "Polish", "Vietnamese", "Thai", "Indonesian",
            "Swedish", "Norwegian", "Danish", "Finnish", "Greek",
            "Hebrew", "Czech", "Hungarian", "Romanian", "Ukrainian"
        ]
        self.language_menu = ctk.CTkOptionMenu(
            lang_select_frame,
            values=languages,
            variable=self.target_language_var,
            width=180,
            height=32
        )
        self.language_menu.pack(fill="x")
        
        # Translation style options
        style_frame = ctk.CTkFrame(translation_frame)
        style_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(style_frame, text="Translation Style:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 5))
        
        self.translation_style_var = ctk.StringVar(value="Natural")
        styles = ["Natural", "Literal", "Professional", "Colloquial", "Technical"]
        self.style_menu = ctk.CTkOptionMenu(
            style_frame,
            values=styles,
            variable=self.translation_style_var,
            width=180,
            height=28
        )
        self.style_menu.pack(fill="x")
        
        # Preserve formatting checkbox
        self.preserve_formatting_var = ctk.BooleanVar(value=True)
        self.preserve_formatting_check = ctk.CTkCheckBox(
            translation_frame,
            text="Preserve original formatting",
            variable=self.preserve_formatting_var,
            font=ctk.CTkFont(size=12)
        )
        self.preserve_formatting_check.pack(anchor="w", pady=(5, 10))
        
        # Translate button
        self.translate_button = ctk.CTkButton(
            translation_frame,
            text="🌐 Translate",
            command=self.translate_transcription,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray75", "gray25")
        )
        self.translate_button.pack(fill="x")
        
        return translation_frame"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Continue with the rest of the methods...\n",
    "\n",
    "def main():\n",
    "    \"\"\"Main entry point\"\"\"\n",
    "    # Check for required packages\n",
    "    required_packages = {\n",
    "        'whisper': 'openai-whisper',\n",
    "        'anthropic': 'anthropic',\n",
    "        'customtkinter': 'customtkinter',\n",
    "        'sounddevice': 'sounddevice',\n",
    "        'soundfile': 'soundfile'\n",
    "    }\n",
    "    \n",
    "    missing_packages = []\n",
    "    for module, package in required_packages.items():\n",
    "        try:\n",
    "            __import__(module)\n",
    "        except ImportError:\n",
    "            missing_packages.append(package)\n",
    "    \n",
    "    if missing_packages:\n",
    "        print(\"Missing required packages. Please install them using:\")\n",
    "        print(f\"pip install {' '.join(missing_packages)}\")\n",
    "        print(\"\\nFor macOS, you may also need:\")\n",
    "        print(\"brew install ffmpeg portaudio\")  # Added portaudio\n",
    "        print(\"\\nFor LaTeX PDF export (optional):\")\n",
    "        print(\"- Windows: Install MiKTeX or TeX Live\")\n",
    "        print(\"- macOS: Install MacTeX\")\n",
    "        print(\"- Linux: sudo apt-get install texlive-full\")\n",
    "        sys.exit(1)\n",
    "    \n",
    "    # Run the application\n",
    "    app = AudioAnalyzerApp()\n",
    "    app.mainloop()\n",
    "\n",
    "if __name__ == \"__main__\":\n",
    "    main()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.8.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}