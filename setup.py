from setuptools import setup, find_packages

setup(
    name="aqc",
    version="0.1.0",
    author="Tyoma Makeev",
    author_email="tyomamakeev@gmail.com",
    description="Audio Quality Control (AQC) - Audio File Analyzer",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    install_requires=[
        "librosa",
        "soundfile",
        "numpy<2",
        "tomli",
        "puremagic",
        "pyloudnorm",
        "soxr",
        "loguru",
    ],
    entry_points={
        "console_scripts": [
            "aqc=aqc.aqc:main",
        ],
    },
)
