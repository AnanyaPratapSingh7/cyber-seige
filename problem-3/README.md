# Problem 3: Audio Beat Detection

This problem involves developing audio beat detection capabilities with increasing complexity across multiple levels.

## Overview of Levels

1. **Level 1: Beat Detection Core** - Basic beat detection script that outputs beat timestamps
2. **Level 2: Advanced Cut Marker Generator** - Enhanced beat detection with customizable parameters for video editing

## Setup Instructions

1. Ensure you have Python 3.8+ installed
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Dependencies

- librosa - For audio processing and analysis
- numpy - For numerical operations
- soundfile - For audio file handling
- audioread - For reading various audio formats

## Level 1: Beat Detection Core

A Python script that processes audio files and detects beat positions based on amplitude/energy analysis.

### Features

- Analyzes `.wav` and `.mp3` audio files
- Detects beat timestamps using energy-based onset detection
- Handles variable BPM and tempo changes
- Filters out false positives in quiet sections
- Works with various audio durations (30 seconds to 5+ minutes)

### How to Run

```
python level-1.py path/to/your/audiofile.wav
```

Optional parameters:
- `--sensitivity` - Adjust detection sensitivity (default: 1.1)
  ```
  python level-1.py path/to/your/audiofile.mp3 --sensitivity 1.3
  ```

### Output

The script outputs beat timestamps (in seconds) to the console, one per line. For example:

```
0.512
1.245
1.968
...
```

## Level 2: Advanced Cut Marker Generator

An enhanced version of the beat detection script that generates accurate cut points for video editing with advanced customization options.

### Features

- Outputs timestamps in `HH:MM:SS.MS` format (e.g., `00:01:15:300`)
- Provides customizable parameters for fine-tuning detection
- Filters out markers in low-energy or silent sections
- Maintains minimum gap between cut points
- Handles inconsistent BPM and subtle beats

### How to Run

```
python level-2.py path/to/your/audiofile.wav
```

Optional parameters:
- `--sensitivity` - Adjust detection sensitivity (default: 1.1)
- `--min-gap` - Minimum gap between markers in seconds (default: 1.0)
- `--no-skip-silence` - Do not skip markers in low-energy sections
- `--energy-threshold` - Threshold for silence detection (default: 0.05)
- `--output-file` - File to save markers (if not specified, prints to console)

Example with parameters:
```
python level-2.py path/to/your/audiofile.mp3 --sensitivity 1.2 --min-gap 2.5 --output-file markers.txt
```

### Output

The script outputs formatted timestamps suitable for video editing software:

```
00:00:12:430
00:00:15:125
00:00:18:750
...
```

## Assumptions Made

1. The audio file is properly formatted and not corrupted
2. For MP3 files, proper codec support is available on the system
3. Beat detection is based on energy/amplitude patterns rather than complex music theory
4. The sensitivity parameter may need adjustment for different music styles:
   - Higher values (e.g., 1.3-1.5) for subtle beats or complex music
   - Lower values (e.g., 0.8-1.0) for pronounced beats like rock or EDM
5. Level 2 provides more accurate results for video editing purposes due to its additional parameters
6. Low-energy thresholds and minimum gaps help prevent over-detection in variable audio content
