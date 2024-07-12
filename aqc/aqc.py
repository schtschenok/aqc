import argparse
import datetime
import json
import sys
from pathlib import Path

import tomli
from loguru import logger

from aqc import helpers

logger.remove()
logger.add(sys.stderr, level="INFO")


def main():
    parser = argparse.ArgumentParser(description="Audio File Analyzer")
    parser.add_argument("-c", "--config-path", type=Path, required=True, help="Path to the configuration TOML file")
    parser.add_argument("-i", "--input-path", type=Path, required=True, help="Path to the input file or directory")
    parser.add_argument("-o", "--output-path", type=Path, required=True, help="Path to output JSON file")
    args = parser.parse_args()

    config_path = args.config_path
    input_path = args.input_path
    output_path = args.output_path

    try:
        config = helpers.load_config(config_path)
        logger.info(f"Loaded config from '{config_path}'")
    except (FileNotFoundError, IOError, tomli.TOMLDecodeError) as e:
        logger.error(f"Could not load config at '{config_path}'")
        raise e

    files = []
    if input_path.is_dir():
        parent_directory = input_path
        logger.info(f"Input directory: '{parent_directory.absolute()}'")
        for file in input_path.rglob("*.wav"):
            if helpers.check_mime_type(file):
                logger.info(f"Valid input file: '{file.relative_to(parent_directory)}'")
                files.append(file)
    elif input_path.is_file() and helpers.check_mime_type(input_path):
        logger.info(f"Input file: '{input_path.absolute()}'")
        parent_directory = input_path.parent
        logger.info(f"Valid input file: {input_path.relative_to(parent_directory)}")
        files = [input_path]
    else:
        raise helpers.AudioFileError("No valid input files provided")

    data = {}
    for file in files:
        logger.info(f"Analyzing file '{file.relative_to(parent_directory)}")
        analysis_result = helpers.analyze_file(Path(file), config, parent_directory)
        data[str(file.relative_to(parent_directory))] = analysis_result

    output = {"date": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
              "base_directory": str(parent_directory),
              "files": data}
    logger.info(f"Writing output to '{output_path}'")
    json.dump(output, open(output_path, "w"), indent=4, cls=helpers.CustomJSONSerializer)
    logger.info("Done")


if __name__ == "__main__":
    main()
