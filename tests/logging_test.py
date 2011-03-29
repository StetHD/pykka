import sys
import logging
import threading
import unittest

from pykka.actor import ThreadingActor
from pykka.registry import ActorRegistry

from tests import TestLogHandler


class LoggingNullHandlerTest(unittest.TestCase):
    def test_null_handler_is_added_to_avoid_warnings(self):
        logger = logging.getLogger('pykka')
        handler_names = [h.__class__.__name__ for h in logger.handlers]
        self.assert_('NullHandler' in handler_names)


class ActorLoggingTest(object):
    def setUp(self):
        self.on_failure_called = self.event_class()
        self.actor_ref = self.AnActor.start(self.on_failure_called)
        self.actor_proxy = self.actor_ref.proxy()
        self.log_handler = TestLogHandler(logging.DEBUG)
        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.log_handler)

    def tearDown(self):
        self.log_handler.close()
        ActorRegistry.stop_all()

    def test_exception_is_logged_when_returned_to_caller(self):
        try:
            self.actor_proxy.raise_exception().get()
            self.fail('Should raise exception')
        except Exception:
            pass
        self.assertEqual(1, len(self.log_handler.messages['debug']))
        log_record = self.log_handler.messages['debug'][0]
        self.assertEqual('Exception returned from %s to caller:' %
            self.actor_ref, log_record.getMessage())
        self.assertEqual(Exception, log_record.exc_info[0])
        self.assertEqual('foo', str(log_record.exc_info[1]))

    def test_exception_is_logged_when_not_reply_requested(self):
        self.on_failure_called.clear()
        self.actor_ref.send_one_way({'command': 'raise exception'})
        self.on_failure_called.wait()
        self.assertEqual(1, len(self.log_handler.messages['error']))
        log_record = self.log_handler.messages['error'][0]
        self.assertEqual('Unhandled exception in %s:' % self.actor_ref,
            log_record.getMessage())
        self.assertEqual(Exception, log_record.exc_info[0])
        self.assertEqual('foo', str(log_record.exc_info[1]))


class AnActor(object):
    def __init__(self, on_failure_called):
        self.on_failure_called = on_failure_called

    def react(self, message):
        if message.get('command') == 'raise exception':
            return self.raise_exception()

    def raise_exception(self):
        raise Exception('foo')

    def on_failure(self, exception_type, exception_value, traceback):
        self.on_failure_called.set()


class ThreadingActorLoggingTest(ActorLoggingTest, unittest.TestCase):
    event_class = threading.Event

    class AnActor(AnActor, ThreadingActor):
        pass


if sys.version_info < (3,):
    import gevent.event

    from pykka.gevent import GeventActor

    class GeventActorLoggingTest(ActorLoggingTest, unittest.TestCase):
        event_class = gevent.event.Event

        class AnActor(AnActor, GeventActor):
            pass
