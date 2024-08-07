import inspect
import json
from pathlib import Path

import librosa
import numpy as np
import puremagic
import pyloudnorm as pyln
import soundfile as sf
import tomli
from loguru import logger


class AudioFileError(Exception):
    pass


class AudioFile:
    allowed_subtypes = ("PCM_S8", "PCM_16", "PCM_24", "PCM_32", "PCM_U8", "FLOAT", "DOUBLE")

    @classmethod
    def check_if_analyzer_exists(cls, analyzer_name: str) -> bool:
        method = cls.__dict__.get(f"_analyze_{analyzer_name}")
        return callable(method)

    @classmethod
    def check_if_analyzer_parameter_exists(cls, analyzer_name: str, analyzer_parameter_name: str) -> bool:
        method = cls.__dict__.get(f"_analyze_{analyzer_name}")
        if callable(method):
            return analyzer_parameter_name in inspect.getfullargspec(method).args
        return False

    def __init__(self, path: Path):
        self.path: Path = path

        self.peak: float | None = None
        self.true_peak: float | None = None
        self.papr: float | None = None
        self.rms: float | None = None
        self.lufs: float | None = None
        self.lra: float | None = None
        self.leading_silence: float | None = None
        self.trailing_silence: float | None = None
        self.channel_difference: float | None = None

        # Promised variables
        self.subtype: str
        self.sample_rate: int
        self.channel_count: int
        self.length_samples: int
        self.length: float
        self.data: np.ndarray

        with sf.SoundFile(self.path) as s:
            self.subtype = s.subtype
            self.sample_rate = s.samplerate
            self.channel_count = s.channels
            self.length_samples = s.frames
            self.length = s.frames / s.samplerate

            if self.subtype not in AudioFile.allowed_subtypes:
                raise AudioFileError(f"Subtype {self.subtype} is not allowed")

            self.data = s.read()
            if not self.data.size:
                raise AudioFileError(f"Can't read data from from file {self.path}")

    def run_analyzer(self, analyzer_name: str, analyzer_params: dict) -> dict:
        analyzer_result = __class__.__dict__.get(f"_analyze_{analyzer_name}")(self, **analyzer_params)

        return {analyzer_name: analyzer_result}

    def _analyze_peak(self, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "dB"

        if self.peak is None:
            self.peak = linear_to_db(np.max(self.data))

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.peak <= maximum
        elif minimum is not None:
            analysis_pass = self.peak >= minimum
        elif maximum is not None:
            analysis_pass = self.peak <= maximum

        return {"pass": analysis_pass, "value": self.peak, "unit": unit}

    def _analyze_true_peak(self, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "dBTP"

        if self.peak is None:
            self._analyze_peak()

        if self.true_peak is None:
            target_sample_rate = self.sample_rate * 2
            true_peak = 0
            for channel in np.transpose(self.data) if self.data.ndim > 1 else [self.data]:
                channel_true_peak = np.max(
                    librosa.resample(channel,
                                     orig_sr=self.sample_rate,
                                     target_sr=target_sample_rate,
                                     res_type="soxr_mq")
                )
                true_peak = channel_true_peak if channel_true_peak > true_peak else true_peak
            self.true_peak = linear_to_db(true_peak)

        self.true_peak = np.max([self.true_peak, self.peak])

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.true_peak <= maximum
        elif minimum is not None:
            analysis_pass = self.true_peak >= minimum
        elif maximum is not None:
            analysis_pass = self.true_peak <= maximum

        return {"pass": analysis_pass, "value": self.true_peak, "unit": unit}

    def _analyze_papr(self, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "dB"

        if self.rms is None:
            self._analyze_rms()
        if self.peak is None:
            self._analyze_peak()

        if self.papr is None:
            self.papr = self.peak - self.rms

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.papr <= maximum
        elif minimum is not None:
            analysis_pass = self.papr >= minimum
        elif maximum is not None:
            analysis_pass = self.papr <= maximum

        return {"pass": analysis_pass, "value": self.papr, "unit": unit}

    def _analyze_rms(self, threshold: float = -72, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "dB"

        if self.rms is None:
            self.rms = linear_to_db(
                np.sqrt(np.mean(np.square(self.data[np.abs(self.data) >= db_to_linear(threshold)]))) * np.sqrt(2)
            )

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.rms <= maximum
        elif minimum is not None:
            analysis_pass = self.rms >= minimum
        elif maximum is not None:
            analysis_pass = self.rms <= maximum

        return {"pass": analysis_pass, "value": self.rms, "unit": unit}

    def _analyze_lufs(self, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "LUFS"

        if self.channel_count not in (1, 2):
            return {"pass": None, "value": None, "unit": unit}

        if self.length < 0.2:
            return {"pass": None, "value": None, "unit": unit}
        elif self.length < 2:
            meter = pyln.Meter(self.sample_rate, block_size=0.16)
        elif self.length < 4:
            meter = pyln.Meter(self.sample_rate, block_size=0.24)
        else:
            meter = pyln.Meter(self.sample_rate)

        if self.lufs is None:
            if self.length_samples < 134217728:  # Magic number, reasonable large file threshold
                self.lufs = meter.integrated_loudness(self.data)
            else:
                self.lufs = 0.0
                chunk_size = 6144000  # Magic number, reasonable chunk size
                number_of_chunks = int(self.data.shape[0] / chunk_size) + 1

                for chunk_number in range(number_of_chunks):
                    start_idx = chunk_number * chunk_size
                    stop_idx = start_idx + chunk_size
                    chunk = self.data[start_idx:stop_idx, :]
                    loudness = meter.integrated_loudness(chunk)
                    self.lufs += loudness * (chunk.shape[0] / self.data.shape[0])

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.lufs <= maximum
        elif minimum is not None:
            analysis_pass = self.lufs >= minimum
        elif maximum is not None:
            analysis_pass = self.lufs <= maximum

        return {"pass": analysis_pass, "value": self.lufs, "unit": unit}

    def _analyze_length(self, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "Seconds"

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.length <= maximum
        elif minimum is not None:
            analysis_pass = self.length >= minimum
        elif maximum is not None:
            analysis_pass = self.length <= maximum

        return {"pass": analysis_pass, "value": self.length, "unit": unit}

    def _analyze_channel_count(self, equals: int | list[int] = None) -> dict:
        analysis_pass = None
        unit: str = "Channels"

        if equals is not None:
            equals = [equals] if not hasattr(equals, "__len__") else equals
            analysis_pass = self.channel_count in equals

        return {"pass": analysis_pass, "value": self.channel_count, "unit": unit}

    def _analyze_sample_rate(self, equals: int | list[int] = None) -> dict:
        analysis_pass = None
        unit: str = ""

        if equals is not None:
            equals = [equals] if not hasattr(equals, "__len__") else equals
            analysis_pass = self.sample_rate in equals

        return {"pass": analysis_pass, "value": self.sample_rate, "unit": unit}

    def _analyze_subtype(self, equals: str | list[str] = None) -> dict:
        analysis_pass = None
        unit: str = ""

        if equals is not None:
            equals = [equals] if not hasattr(equals, "__len__") else equals
            analysis_pass = self.subtype in equals

        return {"pass": analysis_pass, "value": self.subtype, "unit": unit}

    def _analyze_leading_silence(self, threshold: float = -72, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "Seconds"

        if self.leading_silence is None:
            for index, sample in enumerate(self.data):
                if np.max(sample) > db_to_linear(threshold):
                    self.leading_silence = index / self.sample_rate
                    break
            if self.leading_silence is None:
                self.leading_silence = self.length

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.leading_silence <= maximum
        elif minimum is not None:
            analysis_pass = self.leading_silence >= minimum
        elif maximum is not None:
            analysis_pass = self.leading_silence <= maximum

        return {"pass": analysis_pass, "value": self.leading_silence, "unit": unit}

    def _analyze_trailing_silence(self, threshold: float = -72, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "Seconds"

        if self.trailing_silence is None:
            for index, sample in enumerate(np.flip(self.data)):
                if np.max(sample) > db_to_linear(threshold):
                    self.trailing_silence = index / self.sample_rate
                    break
            if self.trailing_silence is None:
                self.trailing_silence = self.length

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.trailing_silence <= maximum
        elif minimum is not None:
            analysis_pass = self.trailing_silence >= minimum
        elif maximum is not None:
            analysis_pass = self.trailing_silence <= maximum

        return {"pass": analysis_pass, "value": self.trailing_silence, "unit": unit}

    def _analyze_channel_difference(self, minimum: float = None, maximum: float = None) -> dict:
        analysis_pass = None
        unit: str = "dB"

        if self.channel_count <= 1:
            return {"pass": None, "value": None, "unit": unit}

        if self.channel_difference is None:
            self.channel_difference = linear_to_db(np.max(np.ptp(self.data, axis=1)))

        if minimum is not None and maximum is not None:
            analysis_pass = minimum <= self.channel_difference <= maximum
        elif minimum is not None:
            analysis_pass = self.channel_difference >= minimum
        elif maximum is not None:
            analysis_pass = self.channel_difference <= maximum

        return {"pass": analysis_pass, "value": self.channel_difference, "unit": unit}


def load_config(config_path: Path) -> dict:
    with open(config_path, "rb") as f:
        return tomli.load(f)


def db_to_linear(db: float) -> float:
    return np.power(10, db / 20)


def linear_to_db(linear: float) -> float:
    return 20 * np.log10(linear) if linear > 0.0000000001 else -200


def analyze_file(file_path: Path, config: dict) -> dict:
    logger.debug(f"Creating AudioFile object for file '{file_path}'")
    audio_file = AudioFile(file_path)
    file_data = {}

    for analyzer, params in config.items():
        reference_values = params.get("reference_values", {})
        settings = params.get("settings", {})
        kwargs = reference_values | settings

        if not AudioFile.check_if_analyzer_exists(analyzer):
            logger.warning(f"Analyzer '{analyzer}' does not exist, it won't be used")
            continue

        valid_kwargs = {}
        for parameter in kwargs:
            if AudioFile.check_if_analyzer_parameter_exists(analyzer, parameter):
                valid_kwargs[parameter] = kwargs[parameter]
            else:
                logger.warning(f"Parameter '{parameter}' does not exist in '{analyzer}' analyzer, it won't be used")

        logger.debug(f"Running analyzer '{analyzer}' on file '{file_path}'")
        result = audio_file.run_analyzer(analyzer, valid_kwargs)
        logger.debug(f"Analyzed file '{file_path}' with '{analyzer}': {result}")
        file_data |= result
    return file_data


def check_if_mime_type_is_wav(file_path: Path) -> bool:
    allowed_mime_types = ('audio/wav', 'audio/wave', 'audio/x-wav', 'audio/vnd.wave')
    try:
        return puremagic.from_file(file_path, mime=True).lower() in allowed_mime_types
    except puremagic.PureError:
        return False


class CustomJSONSerializer(json.JSONEncoder):
    def default(self, obj):
        return super().encode(bool(obj)) if isinstance(obj, np.bool_) else super().default(obj)
