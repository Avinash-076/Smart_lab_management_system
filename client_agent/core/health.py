from core.logger import logger


def safe_run(module_name, function):

    try:
        result = function()

        logger.info(f"{module_name} collected successfully")

        return result

    except Exception as e:

        logger.error(f"{module_name} failed: {e}")

        return None