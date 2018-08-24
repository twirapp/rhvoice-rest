#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

PACKAGES="git scons build-essential libao4 libao-dev pkg-config flite1-dev libao-dev portaudio19-dev opus-tools lame \
python3 python3-pip python3-setuptools locales locales-all"


apt-get update -y
apt-get -y install --no-install-recommends ${PACKAGES}
sudo -H python3 -m pip install --upgrade pip setuptools wheel
sudo -H pip3 install flask pymorphy2

cp app.py /opt/rhvoice-rest.py
chmod +x /opt/rhvoice-rest.py

{
echo '[Unit]'
echo 'Description=RHVoice REST API'
echo 'After=network.target'
echo '[Service]'
echo 'ExecStart=/opt/rhvoice-rest.py'
echo 'Restart=always'
echo 'User=root'
echo '[Install]'
echo 'WantedBy=multi-user.target'
} > /etc/systemd/system/rhvoice-rest.service

git clone https://github.com/Olga-Yakovleva/RHVoice.git /opt/RHVoice
cd /opt/RHVoice && git checkout dc36179 && scons && scons install && ldconfig

git clone https://github.com/vantu5z/RHVoice-dictionary.git /opt/RHVoice-dictionary && \
mkdir -p /usr/local/etc/RHVoice/dicts/Russian/ && mkdir -p /opt/data && \
cp /opt/RHVoice-dictionary/*.txt /usr/local/etc/RHVoice/dicts/Russian/ && \
cp -R /opt/RHVoice-dictionary/tools /opt/ && \
cd /opt && rm -rf /opt/RHVoice /opt/RHVoice-dictionary

systemctl enable rhvoice-rest.service
systemctl start rhvoice-rest.service