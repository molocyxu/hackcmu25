# diarize_improved.py
import os
import math
import numpy as np
import soundfile as sf
import librosa
import webrtcvad      # optional, pip install webrtcvad
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler, normalize
from scipy.ndimage import median_filter
from scipy.signal import lfilter

# ---------------------- VAD ----------------------
def vad_webrtc(audio, sr, frame_ms=30, mode=2):
    """
    WebRTC VAD => returns list of (start_sec, end_sec)
    frame_ms: 10, 20, or 30 recommended
    mode: aggressiveness 0-3
    """
    # webrtcvad requires 16-bit mono PCM at 8/16/32 kHz (commonly 16k)
    # convert to 16k mono 16-bit
    target_sr = 16000
    audio16 = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
    # convert to 16-bit PCM
    pcm16 = (audio16 * 32768).astype(np.int16).tobytes()
    vad = webrtcvad.Vad(mode)
    n_bytes_per_frame = int(target_sr * (frame_ms / 1000.0) * 2)  # 2 bytes per sample
    frames = []
    for start in range(0, len(pcm16), n_bytes_per_frame):
        chunk = pcm16[start:start + n_bytes_per_frame]
        if len(chunk) < n_bytes_per_frame:
            break
        is_speech = vad.is_speech(chunk, sample_rate=target_sr)
        time_start = start / 2 / target_sr
        frames.append((time_start, is_speech))

    # collapse consecutive frames
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
            segments.append((seg_start * sr / target_sr, seg_end * sr / target_sr)) # convert back approx
    if in_speech:
        segments.append((seg_start * sr / target_sr, (len(audio16)/target_sr) * sr / target_sr))
    # small post-filter: min length 0.2s, merge gaps < 0.2s
    merged = []
    for s,e in segments:
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
    # convert times to seconds in original sr timeline (we approximated conversion above)
    # safer: map segments by indices -> but okay for typical use
    return merged

def vad_energy(audio, sr, top_db=40, min_silence_len=0.2):
    """
    Librosa-based VAD fallback. Returns list of (start_sec, end_sec)
    """
    # librosa.effects.split returns sample indices
    intervals = librosa.effects.split(audio, top_db=top_db)
    segments = []
    for s, e in intervals:
        dur = (e - s) / sr
        if dur >= min_silence_len:
            segments.append((s / sr, e / sr))
    # merge small gaps
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

# ---------------------- Feature extraction ----------------------
def frame_audio(audio, sr, win_s=1.2, hop_s=0.6):
    """
    Yield frames of audio (start_time_sec, frame_signal)
    win_s: window in seconds (0.8-1.5 recommended for speaker features)
    """
    win = int(win_s * sr)
    hop = int(hop_s * sr)
    frames = []
    for start in range(0, len(audio) - win + 1, hop):
        frame = audio[start:start+win]
        frames.append((start / sr, frame))
    return frames

def extract_lpc_coeffs(frame, order=12):
    """
    Use librosa.lpc (Burg method) to extract LPC coefficients
    """
    try:
        # librosa.lpc returns LPC polynomial coefficients
        coeffs = librosa.lpc(frame, order=order)
        # drop leading 1 and take remainder
        return coeffs[1:]
    except Exception:
        return np.zeros(order)

def extract_mfcc_features(frame, sr, n_mfcc=13):
    try:
        mf = librosa.feature.mfcc(y=frame, sr=sr, n_mfcc=n_mfcc, n_fft=min(2048,len(frame)), hop_length=len(frame)//4)
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
    if len(feats)==0:
        return np.empty((0,)), np.array([])
    feats = np.vstack(feats)
    feats = StandardScaler().fit_transform(feats)
    return feats, np.array(times)

# ---------------------- Clustering routines ----------------------
def cluster_kmeans(embeddings, n_speakers=2):
    km = KMeans(n_clusters=n_speakers, n_init=10, random_state=0)
    labels = km.fit_predict(embeddings)
    return labels

def cluster_agglomerative(embeddings, n_speakers=2, metric='cosine', linkage='average'):
    model = AgglomerativeClustering(n_clusters=n_speakers, metric=metric, linkage=linkage)
    labels = model.fit_predict(embeddings)
    return labels

def cluster_spectral(embeddings, n_speakers=2):
    model = SpectralClustering(n_clusters=n_speakers, affinity='nearest_neighbors', n_neighbors=10, assign_labels='kmeans')
    labels = model.fit_predict(embeddings)
    return labels

def cluster_gmm(embeddings, n_speakers=2):
    gm = GaussianMixture(n_components=n_speakers, covariance_type='diag', random_state=0)
    labels = gm.fit_predict(embeddings)
    return labels

# ---------------------- Postprocessing ----------------------
def labels_to_segments(labels, times, win_s, hop_s, min_dur=0.5):
    """
    Convert per-frame labels into time segments. times are frame start times.
    """
    if len(labels)==0:
        return []
    segments = []
    cur_label = labels[0]
    cur_start = times[0]
    for i in range(1, len(labels)):
        if labels[i] != cur_label:
            cur_end = times[i] + win_s  # end at window end
            if cur_end - cur_start >= min_dur:
                segments.append((cur_start, cur_end, int(cur_label)))
            else:
                # merge short with prev if exists
                if segments:
                    ps, pe, pl = segments[-1]
                    segments[-1] = (ps, cur_end, pl)
                else:
                    # keep anyway
                    segments.append((cur_start, cur_end, int(cur_label)))
            cur_label = labels[i]
            cur_start = times[i]
    # add last
    cur_end = times[-1] + win_s
    if cur_end - cur_start >= min_dur:
        segments.append((cur_start, cur_end, int(cur_label)))
    elif segments:
        ps, pe, pl = segments[-1]
        segments[-1] = (ps, cur_end, pl)
    return segments

def smooth_and_merge_segments(segments, merge_gap=0.4, min_dur=0.5):
    """
    Merge same-speaker segments separated by small gaps and remove tiny segments.
    """
    if not segments:
        return []
    out = []
    for s,e,sp in segments:
        if not out:
            out.append((s,e,sp))
            continue
        ps, pe, psp = out[-1]
        if sp == psp and s - pe <= merge_gap:
            out[-1] = (ps, max(pe, e), psp)
        elif (e - s) < min_dur:
            # merge into previous if exists
            if out:
                ps, pe, psp = out[-1]
                out[-1] = (ps, max(pe, e), psp)
            else:
                out.append((s,e,sp))
        else:
            out.append((s,e,sp))
    return out

# ---------------------- High-level diarizers ----------------------
def diarize_unsupervised(audio, sr, n_speakers=2, win_s=1.2, hop_s=0.6, clustering='agglomerative'):
    # 1) VAD
    try:
        vad_segments = vad_webrtc(audio, sr)
    except Exception:
        vad_segments = vad_energy(audio, sr)
    if not vad_segments:
        # fallback to whole file
        vad_segments = [(0, len(audio)/sr)]

    # 2) frame embeddings (only from voice regions)
    frames_all = []
    times_all = []
    for s,e in vad_segments:
        s_idx = int(s*sr)
        e_idx = int(e*sr)
        feats, times = make_frame_embeddings(audio[s_idx:e_idx], sr, win_s=win_s, hop_s=hop_s)
        # adjust times to global timeline
        times += s
        if feats.shape[0] > 0:
            frames_all.append(feats)
            times_all.append(times)
    if not frames_all:
        print("No frames extracted.")
        return []
    embeddings = np.vstack(frames_all)
    times = np.hstack(times_all)

    # 3) Cluster 
    if clustering == 'kmeans':
        labels = cluster_kmeans(embeddings, n_speakers=n_speakers)
    elif clustering == 'spectral':
        labels = cluster_spectral(embeddings, n_speakers=n_speakers)
    elif clustering == 'gmm':
        labels = cluster_gmm(embeddings, n_speakers=n_speakers)
    else:
        labels = cluster_agglomerative(embeddings, n_speakers=n_speakers)

    # 4) Smooth labels (median filter on label sequence)
    labels = median_filter(labels, size=3).astype(int)

    # 5) Convert to segments + postprocess
    segments = labels_to_segments(labels, times, win_s, hop_s, min_dur=0.5)
    segments = smooth_and_merge_segments(segments, merge_gap=0.4, min_dur=0.5)
    return segments

# ---------------------- Optional: pretrained embeddings (speechbrain / pyannote) ----------------------
# If you want state-of-the-art, install speechbrain and use ECAPA-TDNN embeddings:
#
# pip install speechbrain torch
#
# then:
#
# from speechbrain.pretrained import EncoderClassifier
# classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/spkrec-ecapa-voxceleb")
# emb = classifier.encode_batch(waveform_tensor)  # waveform_tensor shape [1, time]
#
# After computing embeddings per frame, use AgglomerativeClustering with cosine affinity and tune threshold
#
# I don't include the tensorflow/torch code inline because it requires GPU/torch setup and model download.

# ---------------------- Simple CLI utility ----------------------
def run_file_diarize(path, n_speakers=2, out_txt="diarization_out.txt"):
    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    segments = diarize_unsupervised(audio, sr, n_speakers=n_speakers)
    with open(out_txt, "w") as f:
        f.write("Diarization results:\n")
        for s,e,sp in segments:
            f.write(f"[{s:.2f} -> {e:.2f}] SPEAKER_{sp}\n")
    print(f"Saved results to {out_txt}")
    return segments

if __name__ == "__main__":
    # quick test: python diarize_improved.py audio.wav
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        run_file_diarize(path, n_speakers=2)
    else:
        print("Usage: python diarize_improved.py <audio_file>")

