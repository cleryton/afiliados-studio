"""Process-owned, bounded logs; HTTP responses never depend on a parent pipe."""
import io
import logging
from logging.handlers import RotatingFileHandler
import sys


class Writer(io.TextIOBase):
    def __init__(self,logger,handler):
        self.logger,self.handler=logger,handler

    @property
    def encoding(self):return 'utf-8'

    def write(self,value):
        text=value.rstrip('\r\n')
        if text:self.logger.info(text[:4000])
        return len(value)

    def flush(self):self.handler.flush()


def install(directory):
    logger=logging.Logger('studio-background-output')
    handler=RotatingFileHandler(directory/'background.log',maxBytes=2_000_000,backupCount=1,encoding='utf-8')
    logger.addHandler(handler)
    # A full/unwritable log must not recurse through our redirected stderr.
    logging.raiseExceptions=False
    sys.stdout=sys.stderr=Writer(logger,handler)
