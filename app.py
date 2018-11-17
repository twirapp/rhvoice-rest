#!/usr/bin/env python3

import hashlib
import os
import shutil
import sys
import tempfile
import threading
import time
from shlex import quote
from urllib import parse

from flask import Flask, request, make_response, Response, stream_with_context
from rhvoice_wrapper import TTS

try:
    from tools.preprocessing.text_prepare import text_prepare
except ImportError as err:
    print('Warning! Preprocessing disable: {}'.format(err))

    def text_prepare(text):
        return text

DEFAULT_VOICE = 'anna'

FORMATS = {'wav': 'audio/wav', 'mp3': 'audio/mpeg', 'opus': 'audio/ogg', 'flac': 'audio/flac'}
DEFAULT_FORMAT = 'mp3'

app = Flask(__name__, static_url_path='')


def voice_streamer(text, voice, format_, sets):
    fp, src_path = None, None
    dst_path = cache.get_file_path(text, voice, format_, sets)
    if dst_path:
        if cache.file_found(dst_path):
            with open(dst_path, 'rb') as f:
                while True:
                    chunk = f.read(2048)
                    if not chunk:
                        break
                    yield chunk
            return
        # Если клиент отвалится получим мусор во временных файлах а не в кэше
        src_path = cache.tmp_file_path
        fp = open(src_path, 'wb')

    with tts.say(text, voice, format_, None, sets or None) as read:
        for chunk in read:
            if fp:
                fp.write(chunk)
            yield chunk

    if fp:
        fp.close()
        if src_path and os.path.isfile(src_path):
            cache.move(src_path, dst_path)


def chunked_stream(stream):
    b_break = b'\r\n'
    for chunk in stream:
        yield format(len(chunk), 'x').encode() + b_break + chunk + b_break
    yield b'0' + b_break * 2


def set_headers():
    if CHUNKED_TRANSFER:
        return {'Transfer-Encoding': 'chunked', 'Connection': 'keep-alive'}


@app.route('/say')
def say():
    text = ' '.join([x for x in parse.unquote(request.args.get('text', '')).splitlines() if x])
    voice = request.args.get('voice', DEFAULT_VOICE)
    format_ = request.args.get('format', DEFAULT_FORMAT)

    if voice not in SUPPORT_VOICES:
        return make_response('Unknown voice: \'{}\'. Support: {}.'.format(voice, ', '.join(SUPPORT_VOICES)), 400)
    if format_ not in FORMATS:
        return make_response('Unknown format: \'{}\'. Support: {}.'.format(format_, ', '.join(FORMATS)), 400)
    if not text:
        return make_response('Unset \'text\'.', 400)

    text = quote(text_prepare(text))
    sets = _get_sets(request.args)
    stream = voice_streamer(text, voice, format_, sets)
    if CHUNKED_TRANSFER:
        stream = chunked_stream(stream)
    return Response(stream_with_context(stream), mimetype=FORMATS[format_], headers=set_headers())


def _normalize_set(val):  # 0..100 -> -1.0..1
    try:
        return max(0, min(100, int(val)))/50.0-1
    except (TypeError, ValueError):
        return 0.0


def _get_sets(args):
    keys = {'rate': 'absolute_rate', 'pitch': 'absolute_pitch', 'volume': 'absolute_volume'}
    return {keys[key]: _normalize_set(args[key]) for key in keys if key in args}


def _get_def(any_, test, def_=None):
    if test not in any_ and len(any_):
        return def_ if def_ and def_ in any_ else next(iter(any_))
    return test


def _check_env(word: str) -> bool:
    return word in os.environ and os.environ[word].lower() not in ['no', 'disable', 'false']


class CacheWorker(threading.Thread):
    # TODO: Make file operations thread safe
    def __init__(self):
        self._run = False
        self._path = self._get_cache_path()
        self._lifetime = self._get_lifetime()
        self._noatime = False
        self._tmp = tempfile.gettempdir()
        if self._path and self._lifetime:
            super().__init__()
            self._check_interval = 60 * 60
            self._wait = threading.Event()
            self._run = True
            self._noatime = self._noatime_enable()
            self.start()

    @staticmethod
    def _get_cache_path():  # Включаем поддержку кэша и возвращаем путь до него, или None
        if _check_env('RHVOICE_FCACHE'):
            path = os.path.join(os.path.abspath(sys.path[0]), 'rhvoice_rest_cache')
            os.makedirs(path, exist_ok=True)
            print('Cache enable: {}'.format(path))
            return path

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

    @property
    def work(self):
        return self._run

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

    def get_file_path(self, text, voice, format_, sets):
        if not self._path:
            return None
        str_sets = '.'.join(str(sets.get(k, 0.0)) for k in ['absolute_rate', 'absolute_pitch', 'absolute_volume'])
        name = hashlib.sha1('.'.join([text, voice, format_, str_sets]).encode()).hexdigest() + '.cache'
        return os.path.join(self._path, name)

    @property
    def tmp_file_path(self):
        return os.path.join(self._tmp, hashlib.sha1(os.urandom(32)).hexdigest())

    def file_found(self, path):
        if os.path.isfile(path):
            self._update_atime(path)
            return True
        return False

    @staticmethod
    def move(src, dst):
        try:
            shutil.move(src, dst)
        except OSError as e:
            print('Cache move error: {}'.format(e))

    @staticmethod
    def remove(path):
        try:
            os.remove(path)
        except OSError as e:
            print('Error deleting {}: {}'.format(path, e))


if __name__ == "__main__":
    tts = TTS()

    cache = CacheWorker()
    CHUNKED_TRANSFER = _check_env('CHUNKED_TRANSFER')
    print('Chunked transfer encoding: {}'.format(CHUNKED_TRANSFER))

    formats = tts.formats
    DEFAULT_FORMAT = _get_def(formats, DEFAULT_FORMAT, 'wav')
    FORMATS = {key: val for key, val in FORMATS.items() if key in formats}

    SUPPORT_VOICES = tts.voices
    DEFAULT_VOICE = _get_def(SUPPORT_VOICES, DEFAULT_VOICE)
    SUPPORT_VOICES = set(SUPPORT_VOICES)

    print('Threads: {}'.format(tts.thread_count))
    app.run(host='0.0.0.0', port=8080, threaded=True)
    cache.join()
    tts.join()
