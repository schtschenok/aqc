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

# Example
This config (`config_examples/test_config.toml`)
```toml
# Peak
[peak]
reference_values.maximum = -3  # dB
reference_values.minimum = -9  # dB

# True Peak
[true_peak]
reference_values.maximum = -1  # dB

# Peak-to-Average Power ratio in dB, also known as Crest Factor
[papr]
reference_values.minimum = 3  # dB
```
can produce this `output.json`
```json
{
    "date": "2024-07-12T17:03:03.707922+04:00",
    "base_directory": "D:\\Projects\\Python\\Git\\aqc\\test_files",
    "files": {
        "short.wav": {
            "peak": {
                "pass": "true",
                "value": -6.000037678251388,
                "unit": "dB"
            },
            "true_peak": {
                "pass": "true",
                "value": -3.915757140377444,
                "unit": "dBTP"
            },
            "papr": {
                "pass": "false",
                "value": 2.884500243168704,
                "unit": "dB"
            }
        }
    }
}
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
* DC offset analyzer (learned the hard way)
* Better exclude silence from PAPR calculation
* Proper GUI (but do we need it?)
* Output formats
* Documentation
* Tests maybe

# Thanks
The development of this tool has been supported by [Konstantin Knerik Studio](https://www.linkedin.com/company/konstantin-knerik-studio/).
