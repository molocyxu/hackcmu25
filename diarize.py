import os
import numpy as np
import librosa
from scipy.signal import spectrogram
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform
from scipy.ndimage import binary_erosion, binary_dilation, median_filter
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import argparse

def extract_spectral_features(audio, sr, window_size=2.0, hop_size=0.5):
    """
    Extract spectral features from audio using Short-Time Fourier Transform (STFT).
    
    Args:
        audio: Audio time series
        sr: Sample rate
        window_size: Window size in seconds
        hop_size: Hop size in seconds
    
    Returns:
        features: Array of spectral features for each time window
        times: Time stamps for each window
    """
    # Convert window and hop sizes to samples
    window_samples = int(window_size * sr)
    hop_samples = int(hop_size * sr)
    
    # Adjust FFT size based on window size
    n_fft = min(2048, window_samples) if window_samples > 512 else 512
    if window_samples > n_fft:
        window_samples = n_fft
    
    # Compute Short-Time Fourier Transform
    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_samples, win_length=window_samples)
    magnitude = np.abs(stft)
    
    # Extract features for each time frame
    features = []
    
    for frame_idx in range(magnitude.shape[1]):
        frame_mag = magnitude[:, frame_idx]
        
        # Avoid division by zero
        if np.sum(frame_mag) == 0:
            continue
            
        # Get corresponding time-domain frame
        start_sample = frame_idx * hop_samples
        end_sample = min(start_sample + window_samples, len(audio))
        frame_audio = audio[start_sample:end_sample]
        
        # Skip frames with very low energy (likely silence)
        energy = np.mean(frame_audio ** 2)
        if energy < 1e-6:
            continue
            
        # Frequency-domain features
        freq_bins = np.linspace(0, sr/2, len(frame_mag))
        
        # Spectral centroid (weighted mean frequency)
        spectral_centroid = np.sum(freq_bins * frame_mag) / np.sum(frame_mag)
        
        # Spectral rolloff (85th percentile frequency)
        cumsum = np.cumsum(frame_mag)
        total_energy = cumsum[-1]
        if total_energy > 0:
            spectral_rolloff = np.where(cumsum >= 0.85 * total_energy)[0]
            spectral_rolloff = freq_bins[spectral_rolloff[0]] if len(spectral_rolloff) > 0 else freq_bins[-1]
        else:
            spectral_rolloff = 0
        
        # Spectral bandwidth (weighted standard deviation of frequencies)
        spectral_bandwidth = np.sqrt(np.sum(((freq_bins - spectral_centroid) ** 2) * frame_mag) / np.sum(frame_mag))
        
        # Spectral flatness (measure of how tone-like vs noise-like the spectrum is)
        geometric_mean = np.exp(np.mean(np.log(frame_mag + 1e-10)))
        arithmetic_mean = np.mean(frame_mag)
        spectral_flatness = geometric_mean / (arithmetic_mean + 1e-10)
        
        # Spectral slope (tilt of the spectrum)
        freqs_log = np.log(freq_bins + 1)
        mags_log = np.log(frame_mag + 1e-10)
        spectral_slope = np.polyfit(freqs_log, mags_log, 1)[0]
        
        # Low-frequency energy ratio (below 1kHz)
        low_freq_idx = int(1000 * len(frame_mag) / (sr/2))
        low_freq_energy = np.sum(frame_mag[:low_freq_idx])
        total_freq_energy = np.sum(frame_mag)
        low_freq_ratio = low_freq_energy / (total_freq_energy + 1e-10)
        
        # High-frequency energy ratio (above 4kHz)  
        high_freq_idx = int(4000 * len(frame_mag) / (sr/2))
        high_freq_energy = np.sum(frame_mag[high_freq_idx:])
        high_freq_ratio = high_freq_energy / (total_freq_energy + 1e-10)
        
        # Time-domain features
        if len(frame_audio) > 1:
            # Zero crossing rate
            zcr = np.mean(librosa.feature.zero_crossing_rate(frame_audio[np.newaxis, :]))
            
            # Energy
            rms_energy = np.sqrt(np.mean(frame_audio ** 2))
            
            # Autocorrelation-based pitch estimation (simplified)
            autocorr = np.correlate(frame_audio, frame_audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find peak in autocorrelation (excluding lag 0)
            min_lag = int(sr / 400)  # 400 Hz max
            max_lag = int(sr / 80)   # 80 Hz min
            if max_lag < len(autocorr):
                peak_idx = np.argmax(autocorr[min_lag:max_lag]) + min_lag
                pitch_freq = sr / peak_idx if peak_idx > 0 else 0
            else:
                pitch_freq = 0
        else:
            zcr = 0
            rms_energy = 0
            pitch_freq = 0
        
        # MFCCs (Mel-frequency cepstral coefficients) - most important for speaker identification
        try:
            # Use longer frame for better MFCC estimation
            if len(frame_audio) > sr // 50:  # At least 20ms
                mfcc = librosa.feature.mfcc(y=frame_audio, sr=sr, n_mfcc=13, n_fft=n_fft, 
                                          hop_length=len(frame_audio)//4, n_mels=26)
                mfcc_features = np.mean(mfcc, axis=1) if mfcc.shape[1] > 0 else np.zeros(13)
                
                # Delta MFCCs (first derivatives) - important for speaker recognition
                delta_mfcc = librosa.feature.delta(mfcc, order=1)
                delta_mfcc_features = np.mean(delta_mfcc, axis=1) if delta_mfcc.shape[1] > 0 else np.zeros(13)
            else:
                mfcc_features = np.zeros(13)
                delta_mfcc_features = np.zeros(13)
        except:
            mfcc_features = np.zeros(13)
            delta_mfcc_features = np.zeros(13)
        
        # Combine all features - emphasize speaker-discriminative features
        feature_vector = np.concatenate([
            # Spectral features (weighted less)
            0.5 * np.array([spectral_centroid, spectral_rolloff, spectral_bandwidth, spectral_flatness, spectral_slope]),
            0.5 * np.array([low_freq_ratio, high_freq_ratio, zcr, rms_energy, pitch_freq]),
            # MFCC features (weighted more heavily for speaker discrimination)
            2.0 * mfcc_features,
            1.5 * delta_mfcc_features
        ])
        
        # Handle NaN and infinite values
        feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=1.0, neginf=0.0)
        
        features.append(feature_vector)
    
    if len(features) == 0:
        return np.array([]), np.array([])
    
    # Convert to numpy array
    features = np.array(features)
    
    # Generate time stamps for actual features (not all time windows)
    times = np.arange(len(features)) * hop_size
    
    return features, times

def detect_voice_activity(audio, sr, threshold=0.001):
    """
    Enhanced voice activity detection based on energy and spectral characteristics.
    
    Args:
        audio: Audio time series
        sr: Sample rate
        threshold: Energy threshold for voice detection
    
    Returns:
        voice_segments: List of (start_time, end_time) tuples for voice segments
    """
    # Compute energy in overlapping windows
    window_size = int(0.2 * sr)  # 0.2 second windows (shorter for better resolution)
    hop_size = int(0.05 * sr)    # 0.05 second hop (more overlap)
    
    energy = []
    spectral_features = []
    times = []
    
    for i in range(0, len(audio) - window_size, hop_size):
        window = audio[i:i + window_size]
        
        # Energy-based features
        rms_energy = np.sqrt(np.mean(window ** 2))
        energy.append(rms_energy)
        
        # Spectral features for better voice detection
        if len(window) > 0:
            # Zero crossing rate (higher for unvoiced speech)
            zcr = np.mean(librosa.feature.zero_crossing_rate(window[np.newaxis, :]))
            
            # Spectral centroid
            try:
                stft = librosa.stft(window, n_fft=512, hop_length=len(window)//4)
                spec_cent = np.mean(librosa.feature.spectral_centroid(S=np.abs(stft), sr=sr))
            except:
                spec_cent = 0
            
            spectral_features.append([zcr, spec_cent])
        else:
            spectral_features.append([0, 0])
            
        times.append(i / sr)
    
    energy = np.array(energy)
    spectral_features = np.array(spectral_features)
    times = np.array(times)
    
    # Multi-criteria voice activity detection
    # 1. Energy-based detection
    energy_threshold = np.percentile(energy[energy > 0], 10)  # 10th percentile as baseline
    energy_threshold = max(energy_threshold, threshold * np.max(energy))
    energy_voice = energy > energy_threshold
    
    # 2. Spectral-based detection (voices typically have certain ZCR and spectral centroid patterns)
    zcr_mean = np.mean(spectral_features[:, 0])
    zcr_std = np.std(spectral_features[:, 0])
    zcr_voice = (spectral_features[:, 0] > zcr_mean - 0.5 * zcr_std) & (spectral_features[:, 0] < zcr_mean + 2 * zcr_std)
    
    # Combined voice detection
    voice_mask = energy_voice & zcr_voice
    
    # Apply morphological operations to clean up the voice mask
    from scipy.ndimage import binary_erosion, binary_dilation
    
    # Remove very short voice segments
    voice_mask = binary_erosion(voice_mask, iterations=1)
    voice_mask = binary_dilation(voice_mask, iterations=2)
    
    # Find continuous voice segments
    voice_segments = []
    in_voice = False
    start_time = 0
    
    for i, is_voice in enumerate(voice_mask):
        if is_voice and not in_voice:
            start_time = times[i]
            in_voice = True
        elif not is_voice and in_voice:
            end_time = times[i]
            if end_time - start_time > 0.2:  # Minimum segment length (200ms)
                voice_segments.append((start_time, end_time))
            in_voice = False
    
    # Handle case where audio ends with voice
    if in_voice and len(times) > 0:
        voice_segments.append((start_time, times[-1]))
    
    return voice_segments

def merge_short_segments(segments, min_duration=1.0):
    """
    Merge very short segments with adjacent longer segments.
    
    Args:
        segments: List of (start_time, end_time, speaker) tuples
        min_duration: Minimum duration in seconds for a segment
    
    Returns:
        merged_segments: List of merged segments
    """
    if len(segments) == 0:
        return segments
    
    merged = []
    i = 0
    
    while i < len(segments):
        start, end, speaker = segments[i]
        duration = end - start
        
        # If this segment is too short, try to merge it
        if duration < min_duration and len(merged) > 0:
            # Merge with the previous segment
            prev_start, prev_end, prev_speaker = merged[-1]
            merged[-1] = (prev_start, end, prev_speaker)
        elif duration < min_duration and i + 1 < len(segments):
            # Merge with the next segment
            next_start, next_end, next_speaker = segments[i + 1]
            merged.append((start, next_end, next_speaker))
            i += 1  # Skip the next segment since we merged it
        else:
            # Keep the segment as is
            merged.append((start, end, speaker))
        
        i += 1
    
    return merged
    """
    Post-process speaker labels to create more reasonable speaking segments.
    
    Args:
        labels: Array of speaker labels
        times: Array of time stamps corresponding to labels
        min_duration: Minimum duration in seconds for a speaking segment
    
    Returns:
        processed_labels: Post-processed speaker labels
    """
    if len(labels) == 0 or len(times) == 0:
        return labels
    
    # Calculate time per frame
    if len(times) > 1:
        time_per_frame = (times[-1] - times[0]) / (len(times) - 1)
        min_frames = int(min_duration / time_per_frame)
    else:
        return labels
    
    processed = labels.copy()
    
    # Find segment boundaries
    changes = np.where(np.diff(labels) != 0)[0] + 1
    segment_starts = np.concatenate([[0], changes])
    segment_ends = np.concatenate([changes, [len(labels)]])
    
    # Group nearby segments of the same speaker
    merged_segments = []
    i = 0
    while i < len(segment_starts):
        current_start = segment_starts[i]
        current_end = segment_ends[i]
        current_speaker = labels[current_start]
        
        # Look ahead to merge segments of the same speaker that are close together
        j = i + 1
        while j < len(segment_starts):
            next_start = segment_starts[j]
            next_speaker = labels[next_start]
            
            # Calculate gap between segments
            gap_frames = next_start - current_end
            gap_duration = gap_frames * time_per_frame
            
            # If it's the same speaker and the gap is small, merge
            if (next_speaker == current_speaker and gap_duration < 0.3) or \
               (gap_duration < 0.1):  # Very small gaps should be merged regardless
                current_end = segment_ends[j]
                j += 1
            else:
                break
        
        merged_segments.append((current_start, current_end, current_speaker))
        i = j
    
    # Apply merged segments back to the labels
    processed = labels.copy()
    for start, end, speaker in merged_segments:
        processed[start:end] = speaker
    
    return processed

def merge_segments_intelligently(segments, min_duration=2.0, merge_gap=0.5):
    """
    Intelligently merge segments to create realistic speaking turns.
    
    Args:
        segments: List of (start_time, end_time, speaker) tuples
        min_duration: Minimum duration for a speaking turn
        merge_gap: Maximum gap to merge segments of same speaker
    
    Returns:
        merged_segments: List of merged segments with realistic speaking turns
    """
    if len(segments) <= 1:
        return segments
    
    merged = []
    current_start, current_end, current_speaker = segments[0]
    
    for i in range(1, len(segments)):
        next_start, next_end, next_speaker = segments[i]
        gap = next_start - current_end
        
        # If same speaker and small gap, extend current segment
        if next_speaker == current_speaker and gap <= merge_gap:
            current_end = next_end
        # If different speaker but current segment is too short, merge with next
        elif (current_end - current_start) < min_duration and len(merged) == 0:
            current_end = next_end
            current_speaker = next_speaker  # Take the longer speaker's identity
        # If current segment is too short, merge with previous
        elif (current_end - current_start) < min_duration and len(merged) > 0:
            # Extend the previous segment
            prev_start, prev_end, prev_speaker = merged[-1]
            merged[-1] = (prev_start, current_end, prev_speaker)
            current_start, current_end, current_speaker = next_start, next_end, next_speaker
        else:
            # Current segment is good, save it and move to next
            merged.append((current_start, current_end, current_speaker))
            current_start, current_end, current_speaker = next_start, next_end, next_speaker
    
    # Add the last segment
    if (current_end - current_start) < min_duration and len(merged) > 0:
        # Extend the previous segment
        prev_start, prev_end, prev_speaker = merged[-1]
        merged[-1] = (prev_start, current_end, prev_speaker)
    else:
        merged.append((current_start, current_end, current_speaker))
    
    return merged

def create_segments_from_voice_breaks(audio, sr, speaker_labels, voice_times, voice_segments, silence_threshold=0.3):
    """
    Create speaker segments based on natural speech breaks and voice activity detection.
    
    Args:
        audio: Audio time series
        sr: Sample rate
        speaker_labels: Speaker labels for voice frames
        voice_times: Time stamps for voice frames
        voice_segments: Detected voice segments [(start, end), ...]
        silence_threshold: Minimum silence gap to create a new segment
    
    Returns:
        segments: List of (start_time, end_time, speaker) tuples based on natural breaks
    """
    segments = []
    
    if len(voice_segments) == 0 or len(speaker_labels) == 0:
        return segments
    
    # Create a mapping from time to speaker label
    time_to_speaker = {}
    for i, time in enumerate(voice_times):
        if i < len(speaker_labels):
            time_to_speaker[time] = speaker_labels[i]
    
    # Process each voice segment
    for voice_start, voice_end in voice_segments:
        # Find speaker labels within this voice segment
        segment_speakers = []
        segment_times = []
        
        for time, speaker in time_to_speaker.items():
            if voice_start <= time <= voice_end:
                segment_speakers.append(speaker)
                segment_times.append(time)
        
        if len(segment_speakers) == 0:
            continue
        
        # Group consecutive frames of the same speaker within this voice segment
        if len(segment_speakers) > 0:
            current_speaker = segment_speakers[0]
            segment_start_time = voice_start
            
            for i in range(1, len(segment_speakers)):
                if segment_speakers[i] != current_speaker:
                    # Speaker change detected - create segment for previous speaker
                    segments.append((segment_start_time, segment_times[i-1], f"SPEAKER_{current_speaker:02d}"))
                    segment_start_time = segment_times[i]
                    current_speaker = segment_speakers[i]
            
            # Add the final segment in this voice segment
            segments.append((segment_start_time, voice_end, f"SPEAKER_{current_speaker:02d}"))
    
    # Merge very short segments that are likely noise or mis-classifications
    merged_segments = []
    for start, end, speaker in segments:
        duration = end - start
        if duration >= 0.2:  # Minimum 200ms segment
            merged_segments.append((start, end, speaker))
        elif len(merged_segments) > 0:
            # Merge with previous segment if it exists
            prev_start, prev_end, prev_speaker = merged_segments[-1]
            merged_segments[-1] = (prev_start, end, prev_speaker)
    
    return merged_segments

def cluster_speakers(features, n_speakers=2, method='kmeans'):
    """
    Cluster audio segments based on spectral features to identify different speakers.
    
    Args:
        features: Array of spectral features
        n_speakers: Number of speakers to identify
        method: Clustering method ('kmeans' or 'hierarchical')
    
    Returns:
        labels: Speaker labels for each time window
    """
    if len(features) == 0:
        return np.array([])
    
    print(f"   - Clustering {len(features)} feature vectors...")
    print(f"   - Feature statistics: mean={np.mean(features, axis=0)[:5]}, std={np.std(features, axis=0)[:5]}")
    
    # Normalize features - important for clustering
    scaler = StandardScaler()
    features_normalized = scaler.fit_transform(features)
    
    print(f"   - Normalized feature statistics: mean={np.mean(features_normalized, axis=0)[:5]}, std={np.std(features_normalized, axis=0)[:5]}")
    
    if method == 'kmeans':
        # Use K-means clustering with multiple initializations
        best_labels = None
        best_inertia = float('inf')
        
        for i in range(5):  # Try 5 different random seeds
            kmeans = KMeans(n_clusters=n_speakers, random_state=i, n_init=10, max_iter=300)
            labels = kmeans.fit_predict(features_normalized)
            
            if kmeans.inertia_ < best_inertia:
                best_inertia = kmeans.inertia_
                best_labels = labels
        
        labels = best_labels
    else:
        # Use hierarchical clustering
        # Compute pairwise distances
        distances = pdist(features_normalized, metric='euclidean')
        linkage_matrix = linkage(distances, method='ward')
        labels = fcluster(linkage_matrix, n_speakers, criterion='maxclust') - 1
    
    # Print clustering results for debugging
    unique_labels, counts = np.unique(labels, return_counts=True)
    print(f"   - Clustering results: {dict(zip([f'SPEAKER_{l:02d}' for l in unique_labels], counts))}")
    
    return labels

def smooth_speaker_labels(labels, min_segment_length=8, merge_threshold=0.5):
    """
    Smooth speaker labels to create more reasonable speaking segments.
    
    Args:
        labels: Array of speaker labels
        min_segment_length: Minimum segment length in frames to keep
        merge_threshold: Threshold in seconds for merging nearby segments
    
    Returns:
        smoothed_labels: Smoothed speaker labels
    """
    if len(labels) == 0:
        return labels
        
    smoothed = labels.copy()
    
    # First pass: Remove very short segments by merging with dominant neighbor
    changes = np.where(np.diff(labels) != 0)[0] + 1
    segment_starts = np.concatenate([[0], changes])
    segment_ends = np.concatenate([changes, [len(labels)]])
    
    for start, end in zip(segment_starts, segment_ends):
        segment_length = end - start
        if segment_length < min_segment_length:
            # Find the dominant speaker in surrounding context
            context_start = max(0, start - min_segment_length)
            context_end = min(len(labels), end + min_segment_length)
            
            if context_start < start:
                left_label = labels[context_start:start]
                left_dominant = np.bincount(left_label).argmax() if len(left_label) > 0 else None
            else:
                left_dominant = None
                
            if context_end > end:
                right_label = labels[end:context_end]
                right_dominant = np.bincount(right_label).argmax() if len(right_label) > 0 else None
            else:
                right_dominant = None
            
            # Choose the more appropriate label
            if left_dominant is not None and right_dominant is not None:
                # Choose the one that appears more in the broader context
                smoothed[start:end] = left_dominant if start - context_start > context_end - end else right_dominant
            elif left_dominant is not None:
                smoothed[start:end] = left_dominant
            elif right_dominant is not None:
                smoothed[start:end] = right_dominant
    
    # Second pass: Apply median filtering to smooth transitions
    smoothed = median_filter(smoothed.astype(float), size=5).astype(int)
    
    return smoothed

def run_diarization(audio_file: str, output_file: str = "diarization_result0.txt", n_speakers: int = 2):
    """
    Performs speaker diarization using Fourier transforms and spectral analysis.

    Args:
        audio_file (str): Path to the input audio file.
        output_file (str): Path to save the output text file.
        n_speakers (int): Number of speakers to identify.
    """
    # Check if the audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Error: Audio file not found at '{audio_file}'")
        return

    print("✅ Starting speaker diarization using Fourier transforms...")

    try:
        # Load audio file
        print(f"   - Loading audio file: {os.path.basename(audio_file)}...")
        audio, sr = librosa.load(audio_file, sr=None)
        duration = len(audio) / sr
        print(f"   - Audio loaded: {duration:.1f}s, {sr}Hz")

        # Detect voice activity
        print("   - Detecting voice activity...")
        voice_segments = detect_voice_activity(audio, sr)
        print(f"   - Found {len(voice_segments)} voice segments")

        if not voice_segments:
            print("❌ No voice activity detected in the audio file")
            return

        # Extract spectral features from the entire audio
        print("   - Extracting spectral features using STFT...")
        features, times = extract_spectral_features(audio, sr, window_size=0.5, hop_size=0.15)
        print(f"   - Extracted {len(features)} feature vectors with {features.shape[1]} dimensions each")

        # Filter features to only include voice segments
        voice_indices = []
        for i, time in enumerate(times):
            for start, end in voice_segments:
                if start <= time <= end:
                    voice_indices.append(i)
                    break

        if len(voice_indices) < 2:
            print("❌ Insufficient voice data for diarization")
            return

        voice_features = features[voice_indices]
        voice_times = times[voice_indices]

        # Perform speaker clustering using hierarchical clustering for better separation
        print(f"   - Clustering features to identify {n_speakers} speakers...")
        speaker_labels = cluster_speakers(voice_features, n_speakers=n_speakers, method='hierarchical')

        # Smooth speaker labels very lightly to preserve natural speaker changes
        speaker_labels = smooth_speaker_labels(speaker_labels, min_segment_length=1)
        
        # Skip aggressive post-processing to see raw results
        # speaker_labels = post_process_segments(speaker_labels, voice_times, min_duration=0.8)

        # Create diarization results using natural speech breaks
        print("   - Generating diarization results based on voice breaks...")
        
        # Use voice segments (natural breaks) to create speaker segments
        segments = create_segments_from_voice_breaks(audio, sr, speaker_labels, voice_times, voice_segments)
        
        # Apply minimal post-processing only to merge very short mis-classifications
        final_segments = []
        for start, end, speaker in segments:
            duration = end - start
            if duration >= 0.5:  # Keep segments >= 500ms
                final_segments.append((start, end, speaker))
            elif len(final_segments) > 0:
                # Merge very short segments with previous
                prev_start, prev_end, prev_speaker = final_segments[-1]
                final_segments[-1] = (prev_start, end, prev_speaker)
            else:
                # Keep first segment even if short
                final_segments.append((start, end, speaker))
        
        segments = final_segments

        # Format the results
        result_str = "Speaker Diarization Results (Fourier Transform Method):\n"
        result_str += f"Source File: {os.path.basename(audio_file)}\n"
        result_str += f"Analysis Method: Spectral Feature Clustering\n"
        result_str += f"Number of Speakers: {n_speakers}\n"
        result_str += "----------------------------------------\n"
        
        for start, end, speaker in segments:
            result_str += f"[{start:05.1f}s -> {end:05.1f}s] {speaker}\n"

        # Save results to file
        with open(output_file, "w") as f:
            f.write(result_str)

        print(f"✅ Diarization complete! Results saved to '{output_file}'")
        print(f"   - Identified {len(segments)} speaking segments")

        # Optional: Create a visualization
        try:
            plt.figure(figsize=(12, 6))
            colors = ['red', 'blue', 'green', 'orange', 'purple']
            
            for i, (start, end, speaker) in enumerate(segments):
                speaker_num = int(speaker.split('_')[1])
                plt.axvspan(start, end, alpha=0.3, color=colors[speaker_num % len(colors)], 
                           label=speaker if i == 0 or speaker != segments[i-1][2] else "")
            
            plt.xlabel('Time (seconds)')
            plt.ylabel('Speaker')
            plt.title(f'Speaker Diarization: {os.path.basename(audio_file)}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            viz_file = output_file.replace('.txt', '_visualization.png')
            plt.savefig(viz_file, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"   - Visualization saved to '{viz_file}'")
            
        except Exception as viz_error:
            print(f"   - Warning: Could not create visualization: {viz_error}")

    except Exception as e:
        print(f"❌ An error occurred during diarization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Perform speaker diarization using Fourier transforms.")
    parser.add_argument("audio_file", type=str, help="Path to the input audio file (e.g., recording.wav).")
    parser.add_argument("-o", "--output_file", type=str, default="diarization_result0.txt", 
                       help="Path to the output text file (default: diarization_result0.txt).")
    parser.add_argument("-n", "--n_speakers", type=int, default=2,
                       help="Number of speakers to identify (default: 2).")

    args = parser.parse_args()

    # Run the main function with the provided arguments
    run_diarization(args.audio_file, args.output_file, args.n_speakers)
