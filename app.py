#!/usr/bin/env python3

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

FORMATS = {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'opus': 'audio/ogg'}
DEFAULT_FORMAT = 'mp3'

app = Flask(__name__, static_url_path='')
tts = TTS()


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


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, threaded=False)
