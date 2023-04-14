import sys
from pathlib import Path
import helpers
import json
from loguru import logger
import tomli


# Consumes up to 10x the size of the audio file in memory with true peak disabled, and up to 20x with true peak enabled
def main():


    config_path = Path("config/test_config.toml")

    try:
        config = helpers.load_config(config_path)
    except (FileNotFoundError, IOError, tomli.TOMLDecodeError) as e:
        logger.error(f"Could not load config at '{config_path}'")
        raise e

    input_path = Path("test_files/mono.wav")
    single_file_mode = False
    files = []
    if input_path.is_dir():
        parent_directory = input_path
        for file in input_path.rglob("*.wav"):
            if helpers.check_mime_type(file):
                logger.info(f"Valid input file: '{file.relative_to(parent_directory)}'")
                files.append(file)
    elif input_path.is_file() and helpers.check_mime_type(input_path):
        single_file_mode = True
        parent_directory = input_path.parent
        logger.info(f"Valid input file: {input_path.relative_to(parent_directory)}")
        files = [input_path]
    else:
        raise helpers.AudioFileError("No valid input files provided")

    logger.info(f"Base directory: '{parent_directory.absolute()}'")
    data = {}
    for file in files:
        logger.info(f"Analyzing file '{file.relative_to(parent_directory)}")
        analysis_result = helpers.analyze_file(Path(file), config, parent_directory)
        data[str(file.relative_to(parent_directory))] = analysis_result

    print(data)
    print(json.dumps(data, indent=4, cls=helpers.CustomJSONSerializer))

    if single_file_mode:
        sys.exit(helpers.return_code(data))


if __name__ == "__main__":
    main()
