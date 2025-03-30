import os
import logging
import argparse
import time

def setup_logging(log_file):
    """Setup logging configuration."""
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger()
    return logger

def cleanup_files(directory, max_files, logger):
    """Remove the oldest files in the directory if the number of files exceeds max_files."""
    try:
        # Get a list of all files in the directory
        files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        
        # Sort files by modification time (oldest first)
        files.sort(key=os.path.getmtime)

        # If the number of files exceeds the limit, remove the oldest ones
        if len(files) > max_files:
            files_to_remove = files[:len(files) - max_files]
            for file in files_to_remove:
                os.remove(file)
                logger.info(f"Removed file: {file}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Cleanup script to manage files in a directory.")
    parser.add_argument("directory", help="Path to the directory to monitor.")
    parser.add_argument("max_files", type=int, help="Maximum number of files to keep in the directory.")
    parser.add_argument("--logfile", help="Path to the log file. If not provided, a default log file will be created in the current directory.")
    args = parser.parse_args()

    # Set up the log file
    log_file = args.logfile if args.logfile else os.path.join(os.getcwd(), "cleanup.log")
    logger = setup_logging(log_file)

    logger.info(f"Starting cleanup script for directory: {args.directory}")
    logger.info(f"Maximum files allowed: {args.max_files}")
    logger.info(f"Log file: {log_file}")

    # Run the cleanup process
    while True:
        cleanup_files(args.directory, args.max_files, logger)
        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    main()