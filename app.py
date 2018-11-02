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

TEMP_DIR = tempfile.gettempdir()

app = Flask(__name__, static_url_path='')


def voice_streamer(text, voice, format_, sets):
    fp, src_path, dst_path = None, None, None
    if CACHE_DIR:  # Режим с кэшем
        str_sets = '.'.join(str(sets.get(k, 0.0)) for k in ['absolute_rate', 'absolute_pitch', 'absolute_volume'])
        name = hashlib.sha1('.'.join([text, voice, format_, str_sets]).encode()).hexdigest() + '.cache'
        dst_path = os.path.join(CACHE_DIR, name)
        if os.path.isfile(dst_path):
            if FS_NOATIME:  # Обновляем atime и mtime вручную
                timestamp = time.time()
                os.utime(dst_path, times=(timestamp, timestamp))
            with open(dst_path, 'rb') as f:
                while True:
                    chunk = f.read(2048)
                    if not chunk:
                        break
                    yield chunk
            return
        # Если клиент отвалится получим мусор во временных файлах а не в кэше
        src_path = os.path.join(TEMP_DIR, hashlib.sha1(os.urandom(32)).hexdigest())
        fp = open(src_path, 'wb')

    with tts.say(text, voice, format_, None, sets or None) as read:
        for chunk in read:
            if fp:
                fp.write(chunk)
            yield chunk

    if fp:
        fp.close()
        if src_path and os.path.isfile(src_path):
            try:
                shutil.move(src_path, dst_path)
            except OSError as e:
                print('Cache error: {}'.format(e))


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


def _cache_enable():
    if _check_env('RHVOICE_FCACHE'):
        path = os.path.join(os.path.abspath(sys.path[0]), 'rhvoice_rest_cache')
        os.makedirs(path, exist_ok=True)
        print('Cache enable: {}'.format(path))
        return os.path.join(os.path.abspath(sys.path[0]), 'rhvoice_rest_cache')


def _noatime_enable():
    test = os.path.join(CACHE_DIR, 'atime.test')
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


class CacheLifeTime(threading.Thread):
    def __init__(self, cache_path, lifetime=None):
        self._run = False
        try:
            if lifetime is None:
                lifetime = int(os.environ.get('RHVOICE_FCACHE_LIFETIME', 0))
        except (TypeError, ValueError):
            lifetime = 0
        if lifetime and cache_path:
            super().__init__()
            self._check_interval = 60 * 60
            self._lifetime = lifetime
            self._path = cache_path
            self._wait = threading.Event()
            self._run = True
            self.start()

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
                        try:
                            os.remove(file_path)
                        except OSError as e:
                            print('Error deleting {}: {}'.format(file_path, e))
            self._wait.wait(self._check_interval)


if __name__ == "__main__":
    tts = TTS()

    CACHE_DIR = _cache_enable()
    cache_lifetime = CacheLifeTime(cache_path=CACHE_DIR)
    FS_NOATIME = cache_lifetime.work and _noatime_enable()
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
    cache_lifetime.join()
    tts.join()
