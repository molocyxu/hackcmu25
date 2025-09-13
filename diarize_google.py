#!/usr/bin/env python3
"""
Google Cloud Speech-to-Text Speaker Diarization
Uses Google's production speech diarization service for accurate speaker detection.
"""

import os
import argparse
import librosa
import numpy as np
import matplotlib.pyplot as plt
from google.cloud import speech
import tempfile
import soundfile as sf

def convert_audio_for_google(audio_file_path):
    """
    Convert audio file to format required by Google Speech-to-Text API.
    
    Args:
        audio_file_path: Path to input audio file
        
    Returns:
        temp_file_path: Path to converted audio file
        sample_rate: Sample rate of the converted audio
    """ 
    print(f"   - Converting audio format for Google API...")
    
    # Load audio file
    audio, original_sr = librosa.load(audio_file_path, sr=None)
    
    # Google Speech-to-Text works best with specific sample rates
    # Common rates: 8000, 16000, 22050, 44100, 48000 Hz
    target_sr = 16000  # 16kHz is optimal for speech recognition
    
    # Resample if necessary
    if original_sr != target_sr:
        audio = librosa.resample(audio, orig_sr=original_sr, target_sr=target_sr)
        print(f"   - Resampled from {original_sr}Hz to {target_sr}Hz")
    
    # Convert to 16-bit PCM format
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Save to temporary WAV file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio_int16, target_sr)
    
    print(f"   - Audio converted and saved to temporary file")
    return temp_file.name, target_sr

def transcribe_diarization_local(audio_file_path: str, n_speakers: int = 2) -> dict:
    """
    Transcribe a local audio file using Google Speech-to-Text with speaker diarization.
    
    Args:
        audio_file_path (str): Path to the local audio file
        n_speakers (int): Expected number of speakers
        
    Returns:
        dict: Diarization results with word-level speaker information
    """
    print("   - Initializing Google Cloud Speech client...")
    
    try:
        client = speech.SpeechClient()
    except Exception as e:
        print(f"❌ Error: Could not initialize Google Cloud Speech client: {e}")
        print("   Make sure you have:")
        print("   1. Google Cloud credentials set up (GOOGLE_APPLICATION_CREDENTIALS)")
        print("   2. Speech-to-Text API enabled in your Google Cloud project")
        print("   3. Billing enabled for your Google Cloud project")
        return None
    
    # Convert audio to Google-compatible format
    temp_audio_path, sample_rate = convert_audio_for_google(audio_file_path)
    
    try:
        # Configure speaker diarization
        speaker_diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=max(1, n_speakers - 1),  # Allow some flexibility
            max_speaker_count=n_speakers + 1,  # Allow for one extra speaker
        )

        # Configure recognition
        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code="en-US",
            sample_rate_hertz=sample_rate,
            diarization_config=speaker_diarization_config,
            # Enable automatic punctuation for better transcription
            enable_automatic_punctuation=True,
            # Enable word-level confidence
            enable_word_confidence=True,
            # Enable word time offsets
            enable_word_time_offsets=True,
        )

        # Read the audio file
        with open(temp_audio_path, 'rb') as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)

        print("   - Sending request to Google Speech-to-Text API...")
        
        # Check file size to decide between sync and async API
        audio_duration = len(librosa.load(audio_file_path, sr=None)[0]) / librosa.load(audio_file_path, sr=None)[1]
        
        if audio_duration > 60:  # Use long-running for files > 1 minute
            print(f"   - Using long-running API for {audio_duration:.1f}s audio file...")
            operation = client.long_running_recognize(config=recognition_config, audio=audio)
            print("   - Waiting for operation to complete (this may take a while)...")
            response = operation.result(timeout=300)  # Wait up to 5 minutes
        else:
            # Use synchronous recognize for shorter audio files (< 1 minute)
            response = client.recognize(config=recognition_config, audio=audio)

        if not response.results:
            print("   - No speech detected in audio")
            return None

        # Extract word-level speaker information
        result = response.results[-1]  # Get the final result with all words
        words_info = result.alternatives[0].words

        print(f"   - Received {len(words_info)} words with speaker information")
        
        # Process the results
        diarization_data = {
            'words': [],
            'segments': [],
            'transcript': result.alternatives[0].transcript
        }
        
        for word_info in words_info:
            word_data = {
                'word': word_info.word,
                'speaker_tag': word_info.speaker_tag,
                'start_time': word_info.start_time.total_seconds(),
                'end_time': word_info.end_time.total_seconds(),
                'confidence': getattr(word_info, 'confidence', 1.0)
            }
            diarization_data['words'].append(word_data)
        
        # Clean up temporary file
        os.unlink(temp_audio_path)
        
        return diarization_data
        
    except Exception as e:
        print(f"❌ Error during Google Speech API call: {e}")
        # Clean up temporary file
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
        return None

def create_segments_from_google_results(words_data):
    """
    Convert word-level speaker information to speaking segments.
    
    Args:
        words_data: List of word information from Google API
        
    Returns:
        segments: List of (start_time, end_time, speaker) tuples
    """
    if not words_data:
        return []
    
    segments = []
    current_speaker = words_data[0]['speaker_tag']
    segment_start = words_data[0]['start_time']
    
    for i, word in enumerate(words_data):
        # Check if speaker changed or if we're at the end
        if word['speaker_tag'] != current_speaker or i == len(words_data) - 1:
            # End current segment
            if i == len(words_data) - 1:
                segment_end = word['end_time']
            else:
                segment_end = words_data[i-1]['end_time']
            
            segments.append((segment_start, segment_end, f"SPEAKER_{current_speaker:02d}"))
            
            # Start new segment (if not at end)
            if i < len(words_data) - 1:
                current_speaker = word['speaker_tag']
                segment_start = word['start_time']
    
    return segments

def create_visualization(segments, audio_file, output_file):
    """
    Create a visualization of the speaker diarization results.
    
    Args:
        segments: List of (start_time, end_time, speaker) tuples
        audio_file: Path to original audio file
        output_file: Base name for output file
    """
    try:
        # Load audio for duration info
        audio, sr = librosa.load(audio_file, sr=None)
        duration = len(audio) / sr
        
        plt.figure(figsize=(14, 8))
        
        # Color map for speakers
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
        speaker_colors = {}
        
        # Plot segments with proper legend handling
        added_speakers = set()
        for start, end, speaker in segments:
            if speaker not in speaker_colors:
                speaker_colors[speaker] = colors[len(speaker_colors) % len(colors)]
            
            # Only add label once per speaker
            label = speaker if speaker not in added_speakers else None
            if label:
                added_speakers.add(speaker)
            
            plt.barh(0, end - start, left=start, height=0.8, 
                    color=speaker_colors[speaker], alpha=0.8, label=label)
        
        # Formatting
        plt.xlabel('Time (seconds)', fontsize=12)
        plt.ylabel('Speaker Diarization', fontsize=12)
        plt.title(f'Speaker Diarization Results: {os.path.basename(audio_file)}', fontsize=14)
        plt.xlim(0, duration)
        plt.ylim(-0.5, 0.5)
        plt.yticks([])
        
        # Add legend
        plt.legend(loc='upper right')
        
        # Add grid
        plt.grid(True, alpha=0.3, axis='x')
        
        # Add segment boundaries
        for start, end, speaker in segments:
            plt.axvline(x=start, color='black', linestyle='--', alpha=0.3, linewidth=0.5)
            plt.axvline(x=end, color='black', linestyle='--', alpha=0.3, linewidth=0.5)
            
            # Add speaker labels
            mid_time = (start + end) / 2
            plt.text(mid_time, 0, speaker.split('_')[1], 
                    ha='center', va='center', fontsize=10, fontweight='bold')
        
        # Save visualization
        viz_file = output_file.replace('.txt', '_visualization.png')
        plt.tight_layout()
        plt.savefig(viz_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"   - Visualization saved to '{viz_file}'")
        
    except Exception as e:
        print(f"   - Warning: Could not create visualization: {e}")

def run_google_diarization(audio_file: str, output_file: str = "diarization_result0.txt", n_speakers: int = 2):
    """
    Perform speaker diarization using Google Cloud Speech-to-Text API.

    Args:
        audio_file (str): Path to the input audio file.
        output_file (str): Path to save the output text file.
        n_speakers (int): Expected number of speakers to identify.
    """
    # Check if the audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Error: Audio file not found at '{audio_file}'")
        return

    print("✅ Starting speaker diarization using Google Cloud Speech-to-Text...")

    try:
        # Load audio file info
        print(f"   - Loading audio file: {os.path.basename(audio_file)}...")
        audio, sr = librosa.load(audio_file, sr=None)
        duration = len(audio) / sr
        print(f"   - Audio loaded: {duration:.1f}s, {sr}Hz")

        # Perform diarization using Google API
        print("   - Performing speaker diarization...")
        diarization_data = transcribe_diarization_local(audio_file, n_speakers)
        
        if diarization_data is None:
            print("❌ Diarization failed")
            return
        
        # Convert to segments
        segments = create_segments_from_google_results(diarization_data['words'])
        
        if not segments:
            print("❌ No speaker segments detected")
            return

        # Format the results
        result_str = "Speaker Diarization Results (Google Cloud Speech-to-Text):\n"
        result_str += f"Source File: {os.path.basename(audio_file)}\n"
        result_str += f"Analysis Method: Google Cloud Speaker Diarization\n"
        result_str += f"Expected Speakers: {n_speakers}\n"
        result_str += f"Transcript: {diarization_data['transcript']}\n"
        result_str += "----------------------------------------\n"
        
        for start, end, speaker in segments:
            result_str += f"[{start:05.1f}s -> {end:05.1f}s] {speaker}\n"

        # Save results to file
        with open(output_file, "w") as f:
            f.write(result_str)

        print(f"✅ Diarization complete! Results saved to '{output_file}'")
        
        # Analysis summary
        speaker_durations = {}
        total_speech_time = 0
        for start, end, speaker in segments:
            duration = end - start
            total_speech_time += duration
            if speaker not in speaker_durations:
                speaker_durations[speaker] = 0
            speaker_durations[speaker] += duration
        
        print(f"   - Identified {len(segments)} speaking segments")
        print(f"   - Total speech time: {total_speech_time:.1f}s")
        for speaker, duration in sorted(speaker_durations.items()):
            percentage = (duration / total_speech_time) * 100
            print(f"   - {speaker}: {duration:.1f}s ({percentage:.1f}%)")
        
        # Check for alternating pattern
        speaker_sequence = [seg[2] for seg in segments]
        transitions = len([i for i in range(1, len(speaker_sequence)) if speaker_sequence[i] != speaker_sequence[i-1]])
        print(f"   - Speaker transitions: {transitions}")
        print(f"   - Average segment duration: {total_speech_time/len(segments):.1f}s")

        # Create visualization
        create_visualization(segments, audio_file, output_file)

        # Print word-level details if requested (first 20 words)
        print(f"   - Sample transcription with speakers:")
        for i, word_data in enumerate(diarization_data['words'][:20]):
            print(f"     [{word_data['start_time']:.1f}s] SPEAKER_{word_data['speaker_tag']:02d}: {word_data['word']}")
        if len(diarization_data['words']) > 20:
            print(f"     ... and {len(diarization_data['words']) - 20} more words")

    except Exception as e:
        print(f"❌ An error occurred during diarization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Perform speaker diarization using Google Cloud Speech-to-Text.")
    parser.add_argument("audio_file", type=str, help="Path to the input audio file (e.g., recording.wav).")
    parser.add_argument("-o", "--output_file", type=str, default="diarization_result0.txt", 
                       help="Path to the output text file (default: diarization_result0.txt).")
    parser.add_argument("-n", "--n_speakers", type=int, default=2,
                       help="Expected number of speakers to identify (default: 2).")

    args = parser.parse_args()

    # Run the main function with the provided arguments
    run_google_diarization(args.audio_file, args.output_file, args.n_speakers)
