#!/usr/bin/env python3

import subprocess
from shlex import quote
from urllib import parse

from flask import Flask, request, make_response, Response, stream_with_context

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

FORMATS = {
    'mp3':  ['echo {text} | RHVoice-test -p {voice} -o - | lame -h -V 4 -t - -',        'audio/mpeg'],
    'wav':  ['echo {text} | RHVoice-test -p {voice} -o -',                              'audio/wav'],
    'opus': ['echo {text} | RHVoice-test -p {voice} -o - | opusenc --ignorelength - -', 'audio/ogg'],
}
DEFAULT_FORMAT = 'mp3'

app = Flask(__name__, static_url_path='')


@app.route('/say')
def say():
    def stream_():
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).stdout as fp:
            while fp.readable():
                data = fp.read(2048)
                if not data:
                    break
                yield data

    text = request.args.get('text', '')
    voice = request.args.get('voice', DEFAULT_VOICE)
    format_ = request.args.get('format', DEFAULT_FORMAT)

    if voice not in SUPPORT_VOICES:
        return make_response('Unknown voice: \'{}\'. Support: {}.'.format(voice, ', '.join(SUPPORT_VOICES)), 400)
    if format_ not in FORMATS:
        return make_response('Unknown format: \'{}\'. Support: {}.'.format(format_, ', '.join(FORMATS)), 400)
    if not text:
        return make_response('Unset \'text\'.', 400)

    text = quote(text_prepare(parse.unquote(text).replace('\r\n', ' ').replace('\n', ' ')))
    cmd = FORMATS[format_][0].format(text=text, voice=voice), FORMATS[format_][1]
    return Response(stream_with_context(stream_()), mimetype=FORMATS[format_][1])


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
