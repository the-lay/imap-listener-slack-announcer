from loguru import logger

from config import config


logger.remove(0)

log_file = f"logs/{config.smtp_user}.log"
print(f"Saving data in {log_file}")
logger.add(
    log_file,
    backtrace=True,
    diagnose=True,
    rotation="5 MB",
    enqueue=True,
)
