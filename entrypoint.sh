#!/bin/bash

echo "Setting trap PID $$"
trap cleanup INT TERM

cleanup() {
    echo 'stopping...'
    APP="$(pgrep 'python' -a | grep 'app.py' | awk '{print $1}')"
    kill -TERM "$APP"
    wait
    echo "stop"
    exit 0
}

if [ ! -f /opt/cfg/configured ]; then
    if [ -f /usr/local/etc/RHVoice/RHVoice.conf ] && [ ! -L /usr/local/etc/RHVoice/RHVoice.conf ]; then
        mv /usr/local/etc/RHVoice/RHVoice.conf /opt/cfg/RHVoice.conf
        ln -s /opt/cfg/RHVoice.conf /usr/local/etc/RHVoice/RHVoice.conf
    fi

    touch /opt/cfg/configured
fi

if [ -f /opt/app.py ]; then
    python3 /opt/app.py &
fi

wait