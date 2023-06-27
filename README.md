# 4chan-webm-converter

A simple script that takes an .mp4 file and turns it into a .webm that's under 3mb and removes the audio.

Usage
-----
1. Open converter.exe
2. Browse for an .mp4 file
3. Click go and wait

Dependencies 
-----
- ffmpeg(included in release)
- ffprobe(included in release)

Known issues
-----
Progress bar starts at around 99% and it doesn't reset to 0 when the conversion is done. 
The software can't be gracefully stopped mid conversion.
