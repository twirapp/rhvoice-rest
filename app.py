#!/usr/bin/env python3

import os
import shutil
from shlex import quote
from urllib import parse

from flask import Flask, request, make_response, Response, stream_with_context

from rhvoice_proxy.rhvoice import TTS
from tools.preprocessing.text_prepare import text_prepare

SUPPORT_VOICES = {
    'aleksandr', 'anna', 'elena', 'irina',  # Russian
    'alan', 'bdl', 'clb', 'slt',  # English
    'spomenka',  # Esperanto
    'natia',  # Georgian
    'azamat', 'nazgul',  # Kyrgyz
    'talgat',  # Tatar
    'anatol', 'natalia'  # Ukrainian
}
DEFAULT_VOICE = 'anna'

FORMATS = {'wav': 'audio/wav'}
DEFAULT_FORMAT = 'wav'

app = Flask(__name__, static_url_path='')


@app.route('/say')
def say():
    def stream_():
        with tts.say(text, voice, format_) as read:
            for chunk in read:
                yield chunk

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
    return Response(stream_with_context(stream_()), mimetype=FORMATS[format_])


def format_support():
    base_cmd = {
        'mp3': [['lame', '-htv', '--silent', '-', '-'], 'lame', 'audio/mpeg', 'LAMEPATH'],
        'opus': [
            ['opusenc', '--quiet', '--discard-comments', '--ignorelength', '-', '-'],
            'opus-tools', 'audio/ogg', 'OPUSENCPATH'
        ]
    }
    cmd_ = {}
    formats = {'wav': 'audio/wav'}
    for key, val in base_cmd.items():
        bin_path = os.environ.get(val[3]) or val[0][0]
        if shutil.which(bin_path):
            cmd_[key] = val[0]
            cmd_[key][0] = bin_path
            formats[key] = val[2]
        else:
            print('Disable {} support - {} not found. Use apt install {}'.format(key, bin_path, val[1]))
    return cmd_, formats


def get_path():
    variables = ['RHVOICELIBPATH', 'RHVOICEDATAPATH', 'RHVOICERESOURCES']
    return [os.environ.get(x) for x in variables]


def get_threads():
    try:
        cont = int(os.environ.get('THREADED', 1))
    except ValueError:
        cont = 1
    return cont if cont > 0 else 1


if __name__ == "__main__":
    (cmd, FORMATS) = format_support()
    if 'mp3' in FORMATS:
        DEFAULT_FORMAT = 'mp3'
    threads = get_threads()
    paths = get_path()
    (tts, SUPPORT_VOICES) = TTS(cmd, threads=threads, lib_path=paths[0], data_path=paths[1], resources=paths[2])
    app.run(host='0.0.0.0', port=8080, threaded=threads > 1)
    tts.join()
