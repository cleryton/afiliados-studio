"""Observable, serial background cycles with bounded waits after failures."""
import threading
import time
import core


class Service:
    def __init__(self, name, action, interval, stop, slow_after=600):
        self.name, self.action, self.interval, self.stop = name, action, interval, stop
        self.slow_after = slow_after
        self.lock = threading.Lock()
        self.status = 'starting'
        self.failures = 0
        self.last_success = None
        self.started = None
        self.retry_seconds = 0
        self.thread = None

    def step(self):
        with self.lock:
            self.status = 'running'
            self.started = time.monotonic()
            self.retry_seconds = 0
        try:
            self.action()
        except Exception as error:
            with self.lock:
                self.failures += 1
                self.retry_seconds = (5, 15, 60, 300)[min(self.failures - 1, 3)]
                self.status = 'retry'
            # Exception messages can contain URLs, response bodies or credentials.
            print(f'Serviço {self.name}: {type(error).__name__}; nova tentativa em {self.retry_seconds}s.', flush=True)
            return self.retry_seconds
        else:
            with self.lock:
                self.failures = 0
                self.last_success = core.stamp()
                self.status = 'waiting'
            return self.interval
        finally:
            with self.lock:
                self.started = None

    def run(self):
        try:
            while not self.stop.is_set():
                self.stop.wait(self.step())
        finally:
            with self.lock:
                self.status = 'stopped'

    def start(self):
        self.thread = threading.Thread(target=self.run, name='studio-' + self.name, daemon=True)
        self.thread.start()
        return self

    def state(self):
        with self.lock:
            status = self.status
            if self.started is not None and time.monotonic() - self.started > self.slow_after:
                status = 'slow'
            return {'name': self.name, 'status': status, 'failures': self.failures,
                    'last_success': self.last_success, 'retry_seconds': self.retry_seconds}


_services = []


def start(actions, stop):
    """Call once, after the instance lock and database initialization."""
    global _services
    if any(s.thread and s.thread.is_alive() for s in _services):
        raise RuntimeError('Os serviços locais já estão em execução.')
    _services = [Service(name, action, interval, stop, slow_after) for name, action, interval, slow_after in actions]
    for service in _services:
        service.start()


def state():
    return [service.state() for service in _services]
