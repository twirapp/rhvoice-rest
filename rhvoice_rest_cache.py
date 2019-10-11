import collections
import hashlib
import os
import tempfile
import threading
import time


class BaseInstance:
    def found(self):
        raise NotImplementedError

    def put(self, _):
        raise NotImplementedError

    def put_end(self):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def end(self):
        raise NotImplementedError


class CacheWorker(threading.Thread):
    # TODO: Make file operations thread safe
    def __init__(self, cache_path):
        self._run = False
        self._path = cache_path
        self._lifetime = self._get_lifetime()
        self._noatime = False
        self._tmp = tempfile.gettempdir()
        self._dyn_cache = DynCache(self._path)
        print('Dynamic cache: enable.')
        if self._path:
            print('File cache: {}'.format(self._path))
        if self._path and self._lifetime:
            super().__init__()
            self._check_interval = 60 * 60
            self._wait = threading.Event()
            self._run = True
            self._noatime = self._noatime_enable()
            self.start()

    def _noatime_enable(self):
        test = os.path.join(self._path, 'atime.test')
        with open(test, 'wb') as fp:
            fp.write(b'test')
        old_atime = os.stat(test).st_atime
        time.sleep(3)
        with open(test, 'rb') as fp:
            _ = fp.read()
        new_atime = os.stat(test).st_atime
        os.remove(test)
        if old_atime == new_atime:
            print('FS mount with noatime, atime will update manually')
        return old_atime == new_atime

    @staticmethod
    def _get_lifetime():
        try:
            lifetime = int(os.environ.get('RHVOICE_FCACHE_LIFETIME', 0))
        except (TypeError, ValueError):
            return 0
        return lifetime if lifetime > 0 else 0

    def join(self, timeout=None):
        if self._run:
            self._run = False
            self._wait.set()
            super().join(timeout)

    def run(self):
        print('Cache lifetime: {} hours'.format(self._lifetime))
        self._lifetime *= 60 * 60
        while self._run:
            current_time = time.time()
            for file in os.listdir(self._path):
                file_path = os.path.join(self._path, file)
                if os.path.isfile(file_path):
                    last_read = os.path.getatime(file_path)
                    diff = current_time - last_read
                    if diff > self._lifetime:
                        self.remove(file_path)
            self._wait.wait(self._check_interval)

    def _update_atime(self, path):
        if self._noatime:  # Обновляем atime и mtime вручную
            timestamp = time.time()
            os.utime(path, times=(timestamp, timestamp))

    def file_found(self, path):
        if os.path.isfile(path):
            self._update_atime(path)
            return True
        return False

    @staticmethod
    def remove(path):
        try:
            os.remove(path)
        except OSError as e:
            print('Error deleting {}: {}'.format(path, e))

    def get(self, text, voice, format_, sets) -> BaseInstance:
        str_sets = '.'.join(str(sets.get(k, 0.0)) for k in ['absolute_rate', 'absolute_pitch', 'absolute_volume'])
        name = hashlib.sha1('.'.join([text, voice, format_, str_sets]).encode()).hexdigest() + '.cache'
        path = os.path.join(self._path, name) if self._path else None
        if path and self.file_found(path):
            return FileCacheReaderInstance(path)
        return self._dyn_cache.get(name, path)


class DynCache:
    def __init__(self, path):
        self._path = path
        self._lock = threading.Lock()
        self._data = {}

    def get(self, name: str, path: str):
        def cb():
            del self._data[name]

        found = True
        with self._lock:
            if name not in self._data:
                self._data[name] = BeQueue()
                found = False
            self._data[name].acquire()
            return DynCacheInstance(path, self._lock, self._data[name], found, cb)


class BeQueue:
    def __init__(self):
        self._mutex = threading.Condition(threading.Lock())
        self._queue = collections.deque()
        self._ended = False
        self._locked = False
        self._users = 0

    def put_end(self):
        with self._mutex:
            self._ended = True
            self._mutex.notify_all()

    def put(self, data):
        self._queue.append(data)
        with self._mutex:
            self._mutex.notify_all()

    def read(self):
        pos = 0
        with self._mutex:
            while True:
                size = len(self._queue)
                while pos < size:
                    yield self._queue[pos]
                    pos += 1
                if self._ended and size == len(self._queue):
                    break
                self._mutex.wait()

    def locked(self):
        return self._locked

    def acquire(self):
        if self._locked:
            raise RuntimeError('Queue reached end of life')
        self._users += 1
        return self

    def release(self):
        self._users -= 1
        if not self._users:
            self._locked = True


class DynCacheInstance(BaseInstance):
    def __init__(self, file_path, lock, data: BeQueue, found, clear_callback):
        self._path = file_path
        self._lock = lock
        self._data = data
        self._found = found
        self._cb = clear_callback

    def found(self):
        return self._found

    def put(self, data):
        self._data.put(data)

    def put_end(self):
        self._data.put_end()

    def read(self):
        return self._data.read()

    def end(self):
        save = False
        with self._lock:
            self._data.release()
            if self._data.locked():
                save = True
                self._cb()
        if save:
            self._save()

    def _save(self):
        if self._path:
            try:
                with open(self._path, 'wb') as fd:
                    for chunk in self._data.read():
                        fd.write(chunk)
            except OSError as e:
                print('Write error {}: {}'.format(self._path, e))


class FileCacheReaderInstance(BaseInstance):
    def __init__(self, path):
        self._path = path

    def found(self):
        return True

    def put(self, _):
        pass

    def put_end(self):
        pass

    def read(self):
        try:
            with open(self._path, 'rb') as f:
                while True:
                    chunk = f.read(2048)
                    if not chunk:
                        break
                    yield chunk
        except OSError as e:
            print('Read error {}: {}'.format(self._path, e))

    def end(self):
        pass
