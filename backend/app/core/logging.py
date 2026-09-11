import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configures application-wide logging with consistent format."""
    log_format = (
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logger = logging.getLogger("doc_intelligence")
    return logger


logger = setup_logging()
