#!/usr/bin/env python3
"""
Beat Detection Core (Level 1)
This script processes audio files and detects beat positions based on energy/amplitude analysis.
"""

import argparse
import librosa
import numpy as np
import os

def detect_beats(audio_file, sensitivity=1.1):
    """
    Detect beats in the given audio file and return timestamps in seconds.
    
    Args:
        audio_file (str): Path to the audio file (.wav or .mp3)
        sensitivity (float): Sensitivity multiplier for beat detection threshold
        
    Returns:
        list: Timestamps (in seconds) where beats occur
    """
    # Load audio file
    y, sr = librosa.load(audio_file, sr=None)
    
    # Compute onset envelope using RMS energy
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # Set dynamic threshold based on the median of the onset envelope
    threshold = np.median(onset_env) * sensitivity
    
    # Apply a minimum threshold for silent sections
    min_threshold = np.max(onset_env) * 0.05
    effective_threshold = max(threshold, min_threshold)
    
    # Find peaks in onset envelope (beats)
    peaks = librosa.util.peak_pick(onset_env, 
                                   pre_max=3, 
                                   post_max=3, 
                                   pre_avg=3, 
                                   post_avg=5, 
                                   delta=effective_threshold, 
                                   wait=10)
    
    # Convert frame indices to timestamps (seconds)
    timestamps = librosa.frames_to_time(peaks, sr=sr)
    
    return timestamps.tolist()

def main():
    """Main function to parse arguments and run beat detection."""
    parser = argparse.ArgumentParser(description='Detect beats in audio files')
    parser.add_argument('input_file', help='Path to input audio file (.wav or .mp3)')
    parser.add_argument('--sensitivity', type=float, default=1.1, 
                        help='Sensitivity for beat detection (default: 1.1)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: File '{args.input_file}' not found")
        return 1
    
    # Check file extension
    ext = os.path.splitext(args.input_file)[1].lower()
    if ext not in ['.wav', '.mp3']:
        print(f"Error: Unsupported file format. Only .wav and .mp3 files are supported.")
        return 1
    
    try:
        # Run beat detection
        beat_times = detect_beats(args.input_file, args.sensitivity)
        
        # Print timestamps (seconds)
        for time in beat_times:
            print(f"{time:.3f}")
        
        print(f"\nDetected {len(beat_times)} beats in '{args.input_file}'")
        return 0
    
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
