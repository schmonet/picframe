"""This script is a standalone process for displaying a single image."""

import sys
import logging
from picframe.model import Model
from picframe.get_image_meta import GetImageMeta
from picframe.viewer_display import ViewerDisplay

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("viewer_process")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        logger.error("Usage: viewer_process.py <config_file> <image_path> <duration>")
        sys.exit(1)

    config_file = sys.argv[1]
    image_path = sys.argv[2]
    duration = float(sys.argv[3])

    try:
        logger.info(f"Starting single image display for {image_path} with duration {duration}s")
        
        # Create a model to load the configuration
        model = Model(config_file)
        viewer_config = model.get_viewer_config()
        
        # Create a temporary image object (normally done in model)
        image_meta = GetImageMeta(image_path)
        
        # Create a viewer instance and call the new method
        viewer = ViewerDisplay(viewer_config)
        viewer.show_one_image_and_exit(image_meta, duration)
        
        logger.info("Single image display finished successfully.")
        sys.exit(0)
        
    except Exception as e:
        logger.error("An error occurred during single image display:", exc_info=True)
        sys.exit(1)
