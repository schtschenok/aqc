import argparse
import datetime
import json
import os.path
import sys
from pathlib import Path

import tomli
from loguru import logger

from aqc import helpers

logger.remove()
logger.add(sys.stderr, level="SUCCESS")


def main():
    parser = argparse.ArgumentParser(description="Audio File Analyzer")
    parser.add_argument("-c", "--config-path", type=Path, required=True,
                        help="Path to the configuration TOML file")
    parser.add_argument("-i", "--input-path", nargs="+", type=Path, required=True,
                        help="Path to either the input file, directory, or multiple input files")
    parser.add_argument("-o", "--output-path", type=Path, required=True,
                        help="Path to output JSON file")
    args = parser.parse_args()

    config_path = args.config_path
    input_paths = args.input_path
    output_path = args.output_path

    try:
        config = helpers.load_config(config_path)
        logger.success(f"Loaded config from '{config_path}'")
    except (FileNotFoundError, IOError, tomli.TOMLDecodeError) as e:
        logger.error(f"Could not load config at '{config_path}'")
        raise e

    files = []
    for input_path in input_paths:
        if (file := Path(input_path)).is_file() and helpers.check_if_mime_type_is_wav(file):
            logger.info(f"Valid input file: '{file.absolute()}'")
            files.append(file.resolve())
        elif (directory := Path(input_path)).is_dir():
            logger.info(f"Input directory: '{directory.absolute()}'")
            for file in directory.rglob("*.wav"):
                if helpers.check_if_mime_type_is_wav(file):
                    logger.info(f"Valid input file: '{file.relative_to(directory)}'")
                    files.append(file.resolve())

    files = list(set(files))

    if len(files) == 0:
        raise helpers.AudioFileError("No valid input files provided")

    if len(files) == 1:
        logger.success(f"Analyzing single file '{files[0]}'")
    else:
        logger.success(f"Analyzing {len(files)} files")

    if len(files) == 1:
        parent_directory = files[0].parent
    else:
        try:
            parent_directory = Path(os.path.commonpath([str(file) for file in files])).resolve()
        except ValueError:
            parent_directory = None

    data = {}
    for file in files:
        logger.info(f"Analyzing file '{file}")
        analysis_result = helpers.analyze_file(file, config)
        data_file_path = file.relative_to(parent_directory) if parent_directory else file
        data[str(data_file_path)] = analysis_result

    output = {"date": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
              "base_directory": str(parent_directory),
              "files": data}
    logger.success(f"Writing output to '{output_path}'")
    json.dump(output, open(output_path, "w"), indent=4, cls=helpers.CustomJSONSerializer)
    logger.success("Done")
    print(Path(output_path).resolve())


if __name__ == "__main__":
    main()
