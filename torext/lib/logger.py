#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import logging
from torext.lib.utils import kwgs_filter

print 'torext.lib.logger module loading, NOTE something about logging will be changed'


# borrow from tornado.options._LogFormatter.__init__
def _color(lvl, s):
    try:
        import curses
    except ImportError:
        curses = None
    color = False
    if curses and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except:
            pass
    if not color:
        return s
    # The curses module has some str/bytes confusion in
    # python3.  Until version 3.2.3, most methods return
    # bytes, but only accept strings.  In addition, we want to
    # output these strings with the logging module, which
    # works with unicode strings.  The explicit calls to
    # unicode() below are harmless in python2 but will do the
    # right conversion in python 3.
    fg_color = (curses.tigetstr("setaf") or
                curses.tigetstr("setf") or "")
    if (3, 0) < sys.version_info < (3, 2, 3):
        fg_color = unicode(fg_color, "ascii")
    colors_map = {
        logging.DEBUG: unicode(curses.tparm(fg_color, 4),  # Blue
                               "ascii"),
        logging.INFO: unicode(curses.tparm(fg_color, 2),  # Green
                              "ascii"),
        logging.WARNING: unicode(curses.tparm(fg_color, 3),  # Yellow
                                 "ascii"),
        logging.ERROR: unicode(curses.tparm(fg_color, 1),  # Red
                               "ascii"),
    }
    _normal = unicode(curses.tigetstr("sgr0"), "ascii")

    return colors_map.get(lvl, _normal) + s + _normal

################
#  formatters  #
################

FORMATS = {
    'detailed': '. {levelname:<4} {asctime} {module_with_lineno:<10} {funcName}(. {message}',
    'simple': '. {message:<50} {asctime}',
    'testcase': '- {message}'
}


LEVELNAMES = {
    'DEBUG': 'DEBG',
    'WARNING': 'WARN',
    'ERROR': 'ERRO'
}


class BaseFormatter(logging.Formatter):
    def __init__(self,
        fmt=FORMATS['detailed'],
        datefmt='%Y-%m-%d %H:%M:%S',
        color=False,
        newlinetab='  ',
        **kwgs):
        """
        ::params:kwarg fmt
        ::params:kwarg datefmt
        ::params:kwarg color
        ::params:kwarg newlinetab
        """
        # as origin __init__ function is very simple (store two attributes on self: _fmt & datafmt),
        # execute it firstly
        logging.Formatter.__init__(self)

        self._fmt = fmt
        self.datefmt = datefmt
        self.color = color
        self.newlinetab = newlinetab

    def format(self, record):
        """
        Discard using of old format way ( '%(asctime)' ) and turing into new way '{asctime}'

        add a new format argument: module_with_lineno
        """
        # handle record firstly
        _message = record.getMessage()
        if isinstance(_message, unicode):
            _message = _message.encode('utf8')
        record.message = _message

        if '{asctime' in self._fmt:
            record.asctime = self.formatTime(record, self.datefmt)

        if '{secs' in self._fmt:
            record.secs = record.msecs / 1000

        record.levelname = LEVELNAMES.get(record.levelname, record.levelname)
        if self.color:
            record.levelname = _color(record.levelno, record.levelname)

        record.module_with_lineno = '%s-%s' % (record.module, record.lineno)

        log = self._fmt.format(**record.__dict__)

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if log[-1:] != '\n':
                log += '\n'
            log += record.exc_text

        if self.newlinetab:
            log = log.replace('\n', '\n' + self.newlinetab)

        return log


class BaseStreamHandler(logging.StreamHandler):
    def __init__(self, *args, **kwgs):
        _kwgs = kwgs_filter(('fmt', 'datefmt', 'color', 'newlinetab'), kwgs)

        super(BaseStreamHandler, self).__init__(*args, **kwgs)

        self.setFormatter(BaseFormatter(**_kwgs))

#############
#  loggers  #
#############
# 1. test - propagate 0
# 2. system - propagate 1 - for seperately output system level logs


def enable_logger(name, level=logging.DEBUG, propagate=1, **kwgs):
    # NOTE before logging is set detaily(eg. add a handler), it will be added
    # a handler automatically if it was used (eg. logging.debug),
    # pre-set handlers to [], to ensure no unexpected handler is on root logger
    disable_logger(name)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
    logger.addHandler(BaseStreamHandler(**kwgs))


def disable_logger(name):
    logging.getLogger(name).handlers = []


# test_logger = logging.getLogger('test')
# test_logger.propagate = 0
# test_logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    def test_all():
        root_logger = logging.getLogger()
        # root_logger.setLevel(logging.INFO)
        # streamHandler = logging.StreamHandler()
        # streamHandler.setFormatter(BaseFormatter(color=True))
        # root_logger.addHandler(streamHandler)
        enable_logger('', level=logging.DEBUG, color=True)

        root_logger.debug('bug..')
        root_logger.info('hello')
        root_logger.warning('\nholy a shit')
        try:
            tuple()[0]
        except Exception, e:
            root_logger.error(e, exc_info=True)

        # this logger's log will be handled only once, due to the bool False value
        # of testLogger's attribute `propagate`
        # testLogger.addHandler(logging.StreamHandler())
        # testLogger.info('my name is testLogger')

        # this logger's log will be handled twice, one by its self, with uncustomized StreamHandler instance,
        # the other by rootLogger, which is the parent of otherLogger, see quote below::
        #
        # http://docs.python.org/howto/logging.html#loggers
        #
        #     " Child loggers propagate messages up to the handlers associated
        #     with their ancestor loggers. Because of this, it is unnecessary to
        #     define and configure handlers for all the loggers an application
        #     uses. It is sufficient to configure handlers for a top-level
        #     logger and create child loggers as needed. (You can, however, turn
        #     off propagation by setting the propagate attribute of a logger to
        #     False.) "
        otherLogger = logging.getLogger('other')
        # otherLogger.addHandler(BaseStreamHandler(fmt=FORMATS['simple']))
        fmter = logging.Formatter(fmt='%(message)s %(msecs)s')
        hdr = logging.StreamHandler()
        hdr.setFormatter(fmter)
        otherLogger.addHandler(hdr)
        otherLogger.info('here is otherLogger')

        # and this logger, its log will ofcoursely be handled three times
        otherBabyLogger = logging.getLogger('other.baby')
        otherBabyLogger.addHandler(hdr)
        otherBabyLogger.info('here is otherBabyLogger')

    test_all()