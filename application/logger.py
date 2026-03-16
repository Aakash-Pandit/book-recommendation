import logging
from async_clickhouse_logger import AsyncClickHouseHandler

logger = logging.getLogger("fastapi_logger")
logger.setLevel(logging.INFO)

handler = AsyncClickHouseHandler()

logger.addHandler(handler)