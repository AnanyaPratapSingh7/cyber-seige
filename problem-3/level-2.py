#!/usr/bin/env python3
"""
Advanced Cut Marker Generator (Level 2)
This script enhances beat detection to generate accurate cut points for video editing,
with support for customizable parameters.
"""

import argparse
import librosa
import numpy as np
import os
import math
from datetime import timedelta

def format_timestamp(seconds):
    """
    Convert seconds to HH:MM:SS.MS format
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    
    # Format with milliseconds
    return f"{hours:02d}:{minutes:02d}:{seconds_remainder:06.3f}".replace(".", ":")

def detect_cut_markers(audio_file, sensitivity=1.1, min_gap=1.0, skip_silence=True, energy_threshold=0.05):
    """
    Generate cut markers based on beat detection with advanced parameters
    
    Args:
        audio_file (str): Path to the audio file (.wav or .mp3)
        sensitivity (float): Sensitivity multiplier for beat detection threshold
        min_gap (float): Minimum gap between cut markers in seconds
        skip_silence (bool): Whether to skip markers in low-energy sections
        energy_threshold (float): Relative energy threshold below which sections are considered silent
        
    Returns:
        list: Timestamps (in seconds) for cut points
    """
    # Load audio file
    y, sr = librosa.load(audio_file, sr=None)
    
    # Compute onset envelope using RMS energy
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # Compute RMS energy for each frame
    hop_length = 512  # Default hop length in librosa
    frame_length = 2048  # Default frame length in librosa
    rms_energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # Normalize RMS energy
    rms_energy = rms_energy / np.max(rms_energy) if np.max(rms_energy) > 0 else rms_energy
    
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
    cut_timestamps = librosa.frames_to_time(peaks, sr=sr)
    
    # Filter out markers in low-energy sections if requested
    if skip_silence:
        # Convert peaks to frame indices for energy lookup
        energy_frames = [min(len(rms_energy)-1, math.floor(peak * sr / hop_length)) for peak in peaks]
        # Filter out peaks with low energy
        energy_mask = [rms_energy[frame] >= energy_threshold for frame in energy_frames]
        cut_timestamps = cut_timestamps[energy_mask]
    
    # Apply minimum gap filtering
    if cut_timestamps.size > 0:
        filtered_timestamps = [cut_timestamps[0]]
        
        for i in range(1, len(cut_timestamps)):
            if cut_timestamps[i] - filtered_timestamps[-1] >= min_gap:
                filtered_timestamps.append(cut_timestamps[i])
        
        cut_timestamps = np.array(filtered_timestamps)
    
    return cut_timestamps.tolist()

def main():
    """Main function to parse arguments and run the cut marker generator."""
    parser = argparse.ArgumentParser(description='Generate cut markers from audio files')
    parser.add_argument('input_file', help='Path to input audio file (.wav or .mp3)')
    parser.add_argument('--sensitivity', type=float, default=1.1, 
                        help='Sensitivity for beat detection (default: 1.1)')
    parser.add_argument('--min-gap', type=float, default=1.0,
                        help='Minimum gap between markers in seconds (default: 1.0)')
    parser.add_argument('--no-skip-silence', action='store_false', dest='skip_silence',
                        help='Do not skip markers in low-energy/silent sections')
    parser.add_argument('--energy-threshold', type=float, default=0.05,
                        help='Energy threshold for silence detection (default: 0.05)')
    parser.add_argument('--output-file', help='Output file for markers (if not specified, prints to console)')
    
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
        # Generate cut markers
        markers = detect_cut_markers(
            args.input_file, 
            args.sensitivity, 
            args.min_gap, 
            args.skip_silence, 
            args.energy_threshold
        )
        
        # Format markers as HH:MM:SS.MS
        formatted_markers = [format_timestamp(time) for time in markers]
        
        if args.output_file:
            # Write markers to file
            with open(args.output_file, 'w') as f:
                for marker in formatted_markers:
                    f.write(f"{marker}\n")
            print(f"Generated {len(formatted_markers)} cut markers saved to '{args.output_file}'")
        else:
            # Print markers to console
            for marker in formatted_markers:
                print(marker)
            print(f"\nGenerated {len(formatted_markers)} cut markers from '{args.input_file}'")
        
        return 0
    
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
