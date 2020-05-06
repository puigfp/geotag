import logging
import sys


def __create_logger():
    log = logging.getLogger("geotag")
    log_sh = logging.StreamHandler(sys.stderr)
    log_sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    log.addHandler(log_sh)
    log.setLevel(logging.DEBUG)
    return log


log = __create_logger()
