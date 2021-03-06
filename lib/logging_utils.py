# -*- coding: utf-8 -*-
import logging
import logging.handlers
import StringIO
import traceback

def setup_logging(log_path, loglevel=logging.INFO, encoding="utf-8"):
    logger = logging.getLogger("")
    logger.setLevel(loglevel)

    formatter = logging.Formatter(fmt="%(asctime)-15s %(levelname)s %(message)s")
    handler = logging.handlers.RotatingFileHandler(log_path,
            maxBytes=1024*1024, backupCount=3, encoding=encoding)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def print_stack_trace():
    io = StringIO.StringIO()
    traceback.print_exc(file=io)
    io.seek(0)
    return io.read()
