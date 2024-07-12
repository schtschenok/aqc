# AQC - Audio Quality Control

Tool for checking sets of audio files against a set of rules.

# Installation & Usage
1. Install Python v3.9+
2. Install aqc with pip:
```bash
pip install git+https://github.com/schtschenok/aqc.git
```
3. Run:
```bash
aqc -c /path/to/config.toml -i /path/to/input/folder -o /path/to/output/file.json
```

# Analyzers

## Peak
Peak volume of the audio file.  
Unit: dB.

## True Peak
True Peak volume of the audio file using two-fold oversampling.  
Unit: dBTP.

## PAPR (Peak-to-Average Power Ratio)
The difference between the Peak and RMS (Root Mean Square) levels of the audio file.  
Unit: dB.

## RMS
The Root Mean Square volume of the audio file.  
Unit: dB.

## LUFS
The integrated loudness of the audio file measured in Loudness Units relative to Full Scale. For files shorter than 4 seconds, it uses a modified algorithm that works better for short files but is not entirely standard-compliant.  
Unit: dB.

## Length
The duration of the audio file.  
Unit: Seconds.

## Channel Count
The number of audio channels in the file.  
Unit: Channels.

## Sample Rate
The number of samples of audio carried per second.  
Unit: Hz.

## Subtype
The audio file format subtype (e.g., PCM_16, PCM_24).  
Unit: N/A.

## Leading Silence
The duration of silence from the start of the audio file.  
Unit: Seconds.

## Trailing Silence
The duration of silence at the end of the audio file.  
Unit: Seconds.

## Channel Difference
The maximum difference in volume between any two channels in the audio file.  
Unit: dB.

# TODO
* Proper GUI (but do we need it?)
* Output formats
* Documentation
* Tests maybe
