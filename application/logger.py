import logging

from application.async_logger import AsyncHandler

logger = logging.getLogger("fastapi_logger")
logger.setLevel(logging.INFO)
logger.propagate = False

logger.addHandler(AsyncHandler())
