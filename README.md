rhvoice-rest
============
Это проект на основе синтезатора речи https://github.com/Olga-Yakovleva/RHVoice

## Установка

### Готовый докер
На aarch64 (Например Orange Pi Prime и прочие H5):

`docker run -d -p 8080:8080 aculeasis/rhvoice-rest:arm64v8`

На обычной x86_64:

`docker run -d -p 8080:8080 aculeasis/rhvoice-rest:amd64`

Конфигурация по-умолчанию, можно смонтировать `/usr/local/etc/RHVoice/` и подложить свой конфиг.

### Сборка и запуск докера
    git clone https://github.com/Aculeasis/rhvoice-rest
    cd rhvoice-rest
    # Указать Dockerfile под целевую архитектуру
    docker build -t rhvoice-rest -f Dockerfile.arm64v8 .
    docker run -d -p 8080:8080 rhvoice-rest

### Устновка скриптом на debian-based дистрибутивах в качестве сервиса
    git clone https://github.com/Aculeasis/rhvoice-rest
    cd rhvoice-rest
    chmod +x install.sh
    sudo ./install.sh
Статус сервиса `sudo systemctl status rhvoice-rest.service`

## API
    http://SERVER/say?
    text=<текст>
    & voice=<
             aleksandr|anna|elena|irina| # Russian
             alan|bdl|clb|slt| # English
             spomenka| # Esperanto
             natia| # Georgian
             azamat|nazgul| # Kyrgyz
             talgat| # Tatar
             anatol|natalia # Ukrainian
             >
    & format=<wav|mp3|opus>
`SERVER` - Адрес и порт rhvoice-rest. При дефолтной установке на локалхост будет `localhost:8080`.
Конечно, вы можете установить сервер rhvoice-rest на одной машине а клиент на другой. Особенно актуально для слабых одноплатников. 

`text` - URL-encoded строка. Обязательный параметр.

`voice` - голос из RHVoice (полный список https://github.com/Olga-Yakovleva/RHVoice/wiki/Latest-version-%28Russian%29).
Если не заданно то используется `anna`. Не все голоса могут читать русский.

`format` - Формат возвращаемого файла. Если не задано вернет `mp3`.

## Проверка
<http://localhost:8080/say?text=Привет>

<http://localhost:8080/say?text=Привет%28еще%28раз&format=opus>

## Интеграция
- Home Assistant https://github.com/mgarmash/ha-rhvoice-tts
- Пример либы для питона https://github.com/Aculeasis/rhvoice-rest/blob/master/example/rhvoice-rest.py

## Links
- https://github.com/Olga-Yakovleva/RHVoice
- https://github.com/vantu5z/RHVoice-dictionary
- https://github.com/mgarmash/rhvoice-rest