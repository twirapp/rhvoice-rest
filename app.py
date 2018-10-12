#!/usr/bin/env python3

import hashlib
import os
import shutil
import sys
import tempfile
from shlex import quote
from urllib import parse

from flask import Flask, request, make_response, Response, stream_with_context
from rhvoice_wrapper import TTS

from tools.preprocessing.text_prepare import text_prepare

DEFAULT_VOICE = 'anna'

FORMATS = {'wav': 'audio/wav', 'mp3': 'audio/mpeg', 'opus': 'audio/ogg'}
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
            with open(dst_path, 'rb') as f:
                while True:
                    chunk = f.read(2048)
                    if not chunk:
                        break
                    yield chunk
            return
        # Если клиент отвалится получим мусор во временных файлах а не в кэше
        src_path = os.path.join(TEMP_DIR, name)
        fp = open(src_path, 'wb')

    with tts.say(text, voice, format_, sets=sets or None) as read:
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
    return Response(stream_with_context(voice_streamer(text, voice, format_, sets)), mimetype=FORMATS[format_])


def _normalize_set(val):  # 0..100 -> -1.0..1
    try:
        return max(0, min(100, int(val)))/50.0-1
    except (TypeError, ValueError):
        return 0.0


def _get_sets(args):
    keys = {'rate': 'absolute_rate', 'pitch': 'absolute_pitch', 'volume': 'absolute_volume'}
    return {keys[key]: _normalize_set(args[key]) for key in keys if key in args}


def _get_def(any_, test):
    if test not in any_ and len(any_):
        return any_[0]
    return test


def _cache_enable():
    word = 'RHVOICE_FCACHE'
    if word in os.environ and os.environ[word].lower() not in ['no', 'disable', 'false']:
        path = os.path.join(os.path.abspath(sys.path[0]), 'rhvoice_rest_cache')
        os.makedirs(path, exist_ok=True)
        print('Cache enable: {}'.format(path))
        return os.path.join(os.path.abspath(sys.path[0]), 'rhvoice_rest_cache')


if __name__ == "__main__":
    tts = TTS()

    CACHE_DIR = _cache_enable()

    formats = tts.formats
    DEFAULT_FORMAT = _get_def(formats, DEFAULT_FORMAT)
    FORMATS = {key: val for key, val in FORMATS.items() if key in formats}

    SUPPORT_VOICES = tts.voices
    DEFAULT_VOICE = _get_def(SUPPORT_VOICES, DEFAULT_VOICE)
    SUPPORT_VOICES = set(SUPPORT_VOICES)

    app.run(host='0.0.0.0', port=8080, threaded=tts.thread_count > 1)
    tts.join()
