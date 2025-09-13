#!/usr/bin/env python3
"""
Advanced Speaker Diarization using Multiple Techniques
Based on diarize_improved.py with enhanced VAD, clustering, and postprocessing
"""

import os
import argparse
import numpy as np
import soundfile as sf
import librosa
import webrtcvad
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler, normalize
from scipy.ndimage import median_filter
from scipy.signal import lfilter

def vad_webrtc(audio, sr, frame_ms=30, mode=2):
    """WebRTC VAD => returns list of (start_sec, end_sec)"""
    target_sr = 16000
    audio16 = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
    pcm16 = (audio16 * 32768).astype(np.int16).tobytes()
    vad = webrtcvad.Vad(mode)
    n_bytes_per_frame = int(target_sr * (frame_ms / 1000.0) * 2)
    
    frames = []
    for start in range(0, len(pcm16), n_bytes_per_frame):
        chunk = pcm16[start:start + n_bytes_per_frame]
        if len(chunk) < n_bytes_per_frame:
            break
        is_speech = vad.is_speech(chunk, sample_rate=target_sr)
        time_start = start / 2 / target_sr
        frames.append((time_start, is_speech))

    # Collapse consecutive frames
    segments = []
    in_speech = False
    seg_start = 0.0
    for i, (t, is_speech) in enumerate(frames):
        if is_speech and not in_speech:
            in_speech = True
            seg_start = t
        elif (not is_speech) and in_speech:
            in_speech = False
            seg_end = t
            segments.append((seg_start * sr / target_sr, seg_end * sr / target_sr))
    
    if in_speech:
        segments.append((seg_start * sr / target_sr, (len(audio16)/target_sr) * sr / target_sr))
    
    # Post-filter: min length 0.2s, merge gaps < 0.2s
    merged = []
    for s, e in segments:
        if e - s < 0.2:
            continue
        if not merged:
            merged.append((s,e))
        else:
            ps, pe = merged[-1]
            if s - pe < 0.2:
                merged[-1] = (ps, max(pe, e))
            else:
                merged.append((s,e))
    return merged

def vad_energy(audio, sr, top_db=40, min_silence_len=0.2):
    """Librosa-based VAD fallback"""
    intervals = librosa.effects.split(audio, top_db=top_db)
    segments = []
    for s, e in intervals:
        dur = (e - s) / sr
        if dur >= min_silence_len:
            segments.append((s / sr, e / sr))
    
    # Merge small gaps
    merged = []
    for s, e in segments:
        if not merged:
            merged.append((s,e))
        else:
            ps, pe = merged[-1]
            if s - pe < 0.2:
                merged[-1] = (ps, e)
            else:
                merged.append((s,e))
    return merged

def frame_audio(audio, sr, win_s=1.2, hop_s=0.6):
    """Yield frames of audio (start_time_sec, frame_signal)"""
    win = int(win_s * sr)
    hop = int(hop_s * sr)
    frames = []
    for start in range(0, len(audio) - win + 1, hop):
        frame = audio[start:start+win]
        frames.append((start / sr, frame))
    return frames

def extract_lpc_coeffs(frame, order=12):
    """Use librosa.lpc to extract LPC coefficients"""
    try:
        coeffs = librosa.lpc(frame, order=order)
        return coeffs[1:]  # Drop leading 1
    except Exception:
        return np.zeros(order)

def extract_mfcc_features(frame, sr, n_mfcc=13):
    try:
        mf = librosa.feature.mfcc(y=frame, sr=sr, n_mfcc=n_mfcc, 
                                 n_fft=min(2048,len(frame)), hop_length=len(frame)//4)
        mf_mean = np.mean(mf, axis=1)
        mf_delta = np.mean(librosa.feature.delta(mf), axis=1)
        mf_delta2 = np.mean(librosa.feature.delta(mf, order=2), axis=1)
        return np.hstack([mf_mean, mf_delta, mf_delta2])
    except Exception:
        return np.zeros(n_mfcc*3)

def make_frame_embeddings(audio, sr, win_s=1.2, hop_s=0.6, use_lpc=True, lpc_order=10, use_mfcc=True):
    frames = frame_audio(audio, sr, win_s=win_s, hop_s=hop_s)
    feats = []
    times = []
    for t, frame in frames:
        if np.mean(frame**2) < 1e-6:
            continue
        parts = []
        if use_lpc:
            lpc = extract_lpc_coeffs(frame, order=lpc_order)
            parts.append(lpc)
        if use_mfcc:
            mf = extract_mfcc_features(frame, sr, n_mfcc=13)
            parts.append(mf)
        feat = np.hstack(parts)
        feat = np.nan_to_num(feat)
        feats.append(feat)
        times.append(t)
    
    if len(feats) == 0:
        return np.empty((0,)), np.array([])
    feats = np.vstack(feats)
    feats = StandardScaler().fit_transform(feats)
    return feats, np.array(times)

def cluster_agglomerative(embeddings, n_speakers=2, metric='cosine', linkage='average'):
    model = AgglomerativeClustering(n_clusters=n_speakers, metric=metric, linkage=linkage)
    labels = model.fit_predict(embeddings)
    return labels

def labels_to_segments(labels, times, win_s, hop_s, min_dur=0.5):
    """Convert per-frame labels into time segments"""
    if len(labels) == 0:
        return []
    segments = []
    cur_label = labels[0]
    cur_start = times[0]
    for i in range(1, len(labels)):
        if labels[i] != cur_label:
            cur_end = times[i] + win_s
            if cur_end - cur_start >= min_dur:
                segments.append((cur_start, cur_end, int(cur_label)))
            else:
                if segments:
                    ps, pe, pl = segments[-1]
                    segments[-1] = (ps, cur_end, pl)
                else:
                    segments.append((cur_start, cur_end, int(cur_label)))
            cur_label = labels[i]
            cur_start = times[i]
    
    # Add last segment
    cur_end = times[-1] + win_s
    if cur_end - cur_start >= min_dur:
        segments.append((cur_start, cur_end, int(cur_label)))
    elif segments:
        ps, pe, pl = segments[-1]
        segments[-1] = (ps, cur_end, pl)
    return segments

def smooth_and_merge_segments(segments, merge_gap=0.4, min_dur=0.5):
    """Merge same-speaker segments separated by small gaps"""
    if not segments:
        return []
    out = []
    for s, e, sp in segments:
        if not out:
            out.append((s,e,sp))
            continue
        ps, pe, psp = out[-1]
        if sp == psp and s - pe <= merge_gap:
            out[-1] = (ps, max(pe, e), psp)
        elif (e - s) < min_dur:
            if out:
                ps, pe, psp = out[-1]
                out[-1] = (ps, max(pe, e), psp)
            else:
                out.append((s,e,sp))
        else:
            out.append((s,e,sp))
    return out

def remove_overlaps(segments):
    """Remove overlapping segments by creating non-overlapping sequential segments"""
    if not segments:
        return []
    
    # Sort segments by start time
    segments = sorted(segments, key=lambda x: x[0])
    
    non_overlapping = []
    
    for i, (start, end, speaker) in enumerate(segments):
        # For the first segment, just add it
        if i == 0:
            non_overlapping.append((start, end, speaker))
            continue
        
        prev_start, prev_end, prev_speaker = non_overlapping[-1]
        
        # If this segment starts before the previous one ends, we have overlap
        if start < prev_end:
            # Split the overlap - give first half to previous speaker, second half to current
            split_time = (start + prev_end) / 2
            
            # Adjust the previous segment to end at split time
            if split_time > prev_start:  # Make sure we don't create invalid segments
                non_overlapping[-1] = (prev_start, split_time, prev_speaker)
                
                # Add current segment starting from split time
                if split_time < end:  # Make sure we don't create invalid segments
                    non_overlapping.append((split_time, end, speaker))
            else:
                # If split would be invalid, just use the current segment
                non_overlapping.append((start, end, speaker))
        else:
            # No overlap, just add the segment
            non_overlapping.append((start, end, speaker))
    
    # Filter out very short segments (less than 0.1 seconds)
    filtered = []
    for start, end, speaker in non_overlapping:
        if end - start >= 0.1:
            filtered.append((start, end, speaker))
        elif filtered:
            # Merge very short segments with the previous one
            prev_start, prev_end, prev_speaker = filtered[-1]
            filtered[-1] = (prev_start, end, prev_speaker)
    
    return filtered

def diarize_unsupervised(audio, sr, n_speakers=2, win_s=1.2, hop_s=0.6):
    """Main diarization function"""
    # 1) VAD
    try:
        vad_segments = vad_webrtc(audio, sr)
    except Exception:
        vad_segments = vad_energy(audio, sr)
    if not vad_segments:
        vad_segments = [(0, len(audio)/sr)]

    # 2) Frame embeddings from voice regions
    frames_all = []
    times_all = []
    for s, e in vad_segments:
        s_idx = int(s*sr)
        e_idx = int(e*sr)
        feats, times = make_frame_embeddings(audio[s_idx:e_idx], sr, win_s=win_s, hop_s=hop_s)
        times += s  # Adjust to global timeline
        if feats.shape[0] > 0:
            frames_all.append(feats)
            times_all.append(times)
    
    if not frames_all:
        print("No frames extracted.")
        return []
    
    embeddings = np.vstack(frames_all)
    times = np.hstack(times_all)

    # 3) Cluster 
    labels = cluster_agglomerative(embeddings, n_speakers=n_speakers)

    # 4) Smooth labels
    labels = median_filter(labels, size=3).astype(int)

    # 5) Convert to segments + postprocess
    segments = labels_to_segments(labels, times, win_s, hop_s, min_dur=0.5)
    segments = smooth_and_merge_segments(segments, merge_gap=0.4, min_dur=0.5)
    
    # 6) Remove overlaps to create sequential non-overlapping segments
    segments = remove_overlaps(segments)
    
    return segments

def create_visualization(segments, audio_file, output_file):
    """Create visualization of speaker diarization results"""
    try:
        # Load audio for duration info
        audio, sr = librosa.load(audio_file, sr=None)
        duration = len(audio) / sr
        
        plt.figure(figsize=(14, 8))
        
        # Color map for speakers
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
        speaker_colors = {}
        
        # Plot segments
        added_speakers = set()
        for start, end, speaker in segments:
            speaker_name = f"SPEAKER_{speaker:02d}"
            if speaker not in speaker_colors:
                speaker_colors[speaker] = colors[len(speaker_colors) % len(colors)]
            
            # Only add label once per speaker
            label = speaker_name if speaker not in added_speakers else None
            if label:
                added_speakers.add(speaker)
            
            plt.barh(0, end - start, left=start, height=0.8, 
                    color=speaker_colors[speaker], alpha=0.8, label=label)
        
        # Formatting
        plt.xlabel('Time (seconds)', fontsize=12)
        plt.ylabel('Speaker Diarization', fontsize=12)
        plt.title(f'Advanced Speaker Diarization Results: {os.path.basename(audio_file)}', fontsize=14)
        plt.xlim(0, duration)
        plt.ylim(-0.5, 0.5)
        plt.yticks([])
        
        # Add legend
        plt.legend(loc='upper right')
        
        # Add grid
        plt.grid(True, alpha=0.3, axis='x')
        
        # Add segment boundaries and labels
        for start, end, speaker in segments:
            plt.axvline(x=start, color='black', linestyle='--', alpha=0.3, linewidth=0.5)
            plt.axvline(x=end, color='black', linestyle='--', alpha=0.3, linewidth=0.5)
            
            # Add speaker labels
            mid_time = (start + end) / 2
            plt.text(mid_time, 0, str(speaker), 
                    ha='center', va='center', fontsize=10, fontweight='bold')
        
        # Save visualization
        viz_file = output_file.replace('.txt', '_visualization.png')
        plt.tight_layout()
        plt.savefig(viz_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"   - Visualization saved to '{viz_file}'")
        
    except Exception as e:
        print(f"   - Warning: Could not create visualization: {e}")

def run_advanced_diarization(audio_file: str, output_file: str = "advanced_result.txt", n_speakers: int = 2):
    """Run advanced speaker diarization with comprehensive output"""
    if not os.path.exists(audio_file):
        print(f"❌ Error: Audio file not found at '{audio_file}'")
        return

    print("✅ Starting advanced speaker diarization...")

    try:
        # Load audio
        print(f"   - Loading audio file: {os.path.basename(audio_file)}...")
        audio, sr = sf.read(audio_file)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        duration = len(audio) / sr
        print(f"   - Audio loaded: {duration:.1f}s, {sr}Hz")

        # Perform diarization
        print("   - Performing advanced diarization with WebRTC VAD + LPC/MFCC features...")
        segments = diarize_unsupervised(audio, sr, n_speakers=n_speakers)
        
        if not segments:
            print("❌ No speaker segments detected")
            return

        # Format results
        result_str = "Speaker Diarization Results (Advanced Multi-Algorithm):\n"
        result_str += f"Source File: {os.path.basename(audio_file)}\n"
        result_str += f"Analysis Method: WebRTC VAD + LPC/MFCC + Agglomerative Clustering\n"
        result_str += f"Expected Speakers: {n_speakers}\n"
        result_str += "----------------------------------------\n"
        
        # Convert segments to standard format
        formatted_segments = []
        for start, end, speaker in segments:
            speaker_name = f"SPEAKER_{speaker:02d}"
            result_str += f"[{start:05.1f}s -> {end:05.1f}s] {speaker_name}\n"
            formatted_segments.append((start, end, speaker_name))

        # Save results
        with open(output_file, "w") as f:
            f.write(result_str)

        print(f"✅ Advanced diarization complete! Results saved to '{output_file}'")
        
        # Analysis summary
        speaker_durations = {}
        total_speech_time = 0
        for start, end, speaker_name in formatted_segments:
            duration_seg = end - start
            total_speech_time += duration_seg
            if speaker_name not in speaker_durations:
                speaker_durations[speaker_name] = 0
            speaker_durations[speaker_name] += duration_seg
        
        print(f"   - Identified {len(formatted_segments)} speaking segments")
        print(f"   - Total speech time: {total_speech_time:.1f}s")
        for speaker, duration_seg in sorted(speaker_durations.items()):
            percentage = (duration_seg / total_speech_time) * 100
            print(f"   - {speaker}: {duration_seg:.1f}s ({percentage:.1f}%)")
        
        # Check for alternating pattern
        speaker_sequence = [seg[2] for seg in formatted_segments]
        transitions = len([i for i in range(1, len(speaker_sequence)) if speaker_sequence[i] != speaker_sequence[i-1]])
        print(f"   - Speaker transitions: {transitions}")
        print(f"   - Average segment duration: {total_speech_time/len(formatted_segments):.1f}s")

        # Create visualization
        create_visualization([(s,e,int(sp.split('_')[1])) for s,e,sp in formatted_segments], 
                           audio_file, output_file)

    except Exception as e:
        print(f"❌ An error occurred during diarization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform advanced speaker diarization.")
    parser.add_argument("audio_file", type=str, help="Path to the input audio file")
    parser.add_argument("-o", "--output_file", type=str, default="advanced_result.txt", 
                       help="Path to the output text file")
    parser.add_argument("-n", "--n_speakers", type=int, default=2,
                       help="Expected number of speakers")

    args = parser.parse_args()
    run_advanced_diarization(args.audio_file, args.output_file, args.n_speakers)
