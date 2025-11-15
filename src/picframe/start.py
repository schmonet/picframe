"""
This is the main entry point for the picframe application.
It sets up logging, parses arguments, and starts the controller loop.
"""

import sys
import os
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler

from picframe import model, viewer_display, controller, __version__

# Define the project root as two levels up from this file (src/picframe -> src -> project_root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
def_config_file = os.path.join(PROJECT_ROOT, 'configuration.yaml')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file",
                        help="specify a configuration file (defaults to {})".format(def_config_file))
    parser.add_argument("-v", "--version", action='version', version='%(prog)s ' + __version__)
    parser.add_argument("-s", "--start_paused", help="start in paused mode", action="store_true")
    parser.add_argument("-i", "--image", help="display a single image and exit")
    parser.add_argument("-d", "--duration", type=float, default=10.0,
                        help="duration to display a single image (default: 10s)")
    return parser.parse_args()


def setup_logger(log_level, log_file, log_to_console):
    """
    Sets up the logger.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a rotating file handler
    if log_file:
        log_file_path = os.path.expanduser(log_file)
        try:
            # Use TimedRotatingFileHandler to rotate logs daily and keep 7 backups
            file_handler = TimedRotatingFileHandler(log_file_path, when="midnight", interval=1, backupCount=7)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Error setting up log file handler at {log_file_path}: {e}")
            # Continue without file logging

    # Create a console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Suppress verbose logging from PIL
    logging.getLogger('PIL').setLevel(logging.INFO)


def main():
    """
    Main function to run the application.
    """
    args = get_args()
    config_file = args.config_file if args.config_file else def_config_file

    try:
        m = model.Model(config_file)
    except Exception as e:
        print(f"Error initializing model with config file {config_file}: {e}")
        sys.exit(1)

    model_config = m.get_model_config()
    viewer_config = m.get_viewer_config()

    # Setup logging
    log_level = model_config.get('log_level', 'INFO').upper()
    log_file = model_config.get('log_file', None)
    log_to_console = model_config.get('log_to_console', True)
    setup_logger(log_level, log_file, log_to_console)

    logger = logging.getLogger("start.main")
    logger.info("picframe version: %s", __version__)
    logger.info("using config file: %s", config_file)

    try:
        v = viewer_display.ViewerDisplay(viewer_config)
    except Exception as e:
        logger.error("Error initializing viewer: %s", e)
        sys.exit(1)

    # Handle single image display mode
    if args.image:
        image_path = os.path.expanduser(args.image)
        if not os.path.isfile(image_path):
            logger.error("Image file not found: %s", image_path)
            sys.exit(1)
        
        # Create a temporary pic object for the viewer
        from picframe.get_image_meta import GetImageMeta
        pic = GetImageMeta(image_path)
        
        try:
            v.show_one_image_and_exit(pic, args.duration)
        except Exception as e:
            logger.error("Error displaying single image: %s", e)
            sys.exit(1)
        sys.exit(0)

    # Normal slideshow mode
    c = controller.Controller(m, v)

    if args.start_paused:
        c.paused = True

    c.start()
    exit_code = c.loop()
    c.stop()
    
    logger.info("Exiting picframe with code %d.", exit_code)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()