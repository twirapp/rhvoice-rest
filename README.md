[rhvoice-rest](https://github.com/Aculeasis/rhvoice-rest)
============
[![Docker Pulls](https://img.shields.io/docker/pulls/aculeasis/rhvoice-rest.svg)](https://hub.docker.com/r/aculeasis/rhvoice-rest/) [![Build Status](https://travis-ci.org/Aculeasis/rhvoice-rest.svg?branch=master)](https://travis-ci.org/Aculeasis/rhvoice-rest) [![Build status](https://ci.appveyor.com/api/projects/status/29ytf0mctba4akox/branch/master?svg=true)](https://ci.appveyor.com/project/Aculeasis/rhvoice-rest/branch/master)

Это веб-сервис на основе flask и синтезатора речи [RHVoice](https://github.com/Olga-Yakovleva/RHVoice). Благодаря REST API его легко интегрировать в качестве TTS-провайдера.

## Docker
### Через скрипт docker_starter
Запуск\обновление из хаба: `./rhvoice_rest.py --upgrade`

Полное описание [тут](https://github.com/Aculeasis/docker-starter)

### Готовые докеры
- aarch64 `docker run -d -p 8080:8080 aculeasis/rhvoice-rest:arm64v8`
- armv7l `docker run -d -p 8080:8080 aculeasis/rhvoice-rest:arm32v7`
- x86_64 `docker run -d -p 8080:8080 aculeasis/rhvoice-rest:amd64`

### Сборка и запуск докера
    git clone https://github.com/Aculeasis/rhvoice-rest
    cd rhvoice-rest
    # Указать Dockerfile под целевую архитектуру
    docker build -t rhvoice-rest -f Dockerfile.arm64v8 .
    docker run -d -p 8080:8080 rhvoice-rest

`Dockerfile.arm64v8` использует заранее собранный `rhvoice-wrapper-bin` (зеро часто не хватает памяти на сборку), для полной сборки используйте `Dockerfile.arm64v8.src`
    
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
    & rate=0..100
    & pitch=0..100
    & volume=0..100
`SERVER` - Адрес и порт rhvoice-rest. При дефолтной установке на локалхост будет `localhost:8080`.
Конечно, вы можете установить сервер rhvoice-rest на одной машине а клиент на другой. Особенно актуально для слабых одноплатников. 

`text` - URL-encoded строка. Обязательный параметр.

`voice` - Голос из RHVoice [полный список](https://github.com/Olga-Yakovleva/RHVoice/wiki/Latest-version-%28Russian%29).
`anna` используется по умолчанию и в качестве альтернативного спикера.

`format` - Формат возвращаемого файла. По умолчанию `mp3`.

`rate` - Темп речи. По умолчанию `50`.

`pitch` - Высота голоса. По умолчанию `50`.

`volume` - Громкость голоса. По умолчанию `50`.

## Нативный запуск
Для начала нужно установить [rhvoice-wrapper](https://github.com/Aculeasis/rhvoice-proxy):

`pip3 install rhvoice-wrapper>=0.3.1`

Собрать и установить [RHVoice](https://github.com/Olga-Yakovleva/RHVoice) или установить [rhvoice-wrapper-bin](https://github.com/Aculeasis/rhvoice-wrapper-bin) предоставляющий библиотеки и данные RHVoice. Второй вариант рекомендуется для Windows т.к. не требует сборки.

И еще рядом с app.py положить `tools` из [RHVoice-dictionary](https://github.com/vantu5z/RHVoice-dictionary).

Для поддержки `mp3` и `opus` нужно установить `lame` и `opus-tools`

### Устновка скриптом на debian-based дистрибутивах в качестве сервиса
    git clone https://github.com/Aculeasis/rhvoice-rest
    cd rhvoice-rest
    chmod +x install.sh
    sudo ./install.sh
Статус сервиса `sudo systemctl status rhvoice-rest.service`

### Особенности запуска в Windows
Нужно задать пути через переменные окружения. Если вы используете `rhvoice-wrapper-bin` то первые 2 задавать не нужно:

**RHVOICELIBPATH** до `RHVoice.dll` той же архитектуры что и питон и **RHVOICEDATAPATH** до папки с languages и voices. По умолчанию они ставятся в `C:\Program Files (x86)\RHVoice\data`

Не обязательно: **LAMEPATH** до `lame.exe` для поддержки `mp3` и **OPUSENCPATH** до `opusenc.exe` для поддержки `opus`. Возможно, использование `opusenc.exe` может вызывать переполнение буфера и зависание процесса синтеза. В Linux проблем не замечено.

Протестировано на Windows 10 и Python 3.6.

## Настройки
Все настройки задаются через переменные окружения, до запуска скрипта или при создании докер-контейнера (через `-e`):
- **RHVOICELIBPATH**: Путь до библиотеки RHVoice. По умолчанию `RHVoice.dll` в Windows и `libRHVoice.so` в Linux.
- **RHVOICEDATAPATH**:  Путь до данных RHVoice. По умолчанию `/usr/local/share/RHVoice`.
- **RHVOICERESOURCES**: Путь до неких ресурсов, я не знаю что это. По умолчанию `/usr/local/etc/RHVoice/dicts/Russian/`.
- **THREADED**: Количество запущенных процессов синтеза, определяет количество запросов которые могут быть обработаны одновременно. Если `> 1` генеработы будут запущены в качестве отдельных процессов что существенно увеличит потребление памяти. Рекомендуемое максимальное значение `1.5 * core count`. По умолчанию `1`.
- **LAMEPATH**: Путь до `lame` или `lame.exe`, если файл не найден поддержка `mp3` будет отключена. По умолчанию `lame`.
- **OPUSENCPATH**: Путь до `opusenc` или `opusenc.exe`, если файл не найден поддержка `opus` будет отключена. По умолчанию `opusenc`.
- **RHVOICE_FCACHE**: Если задано и не равно `no`, `disable` или `false` будет включен файловый кэш. Чтение из кэша почти не увеличивает скорость реакции, но значительно уменьшает время загрузки всех данных. Может некорректно работать в Windows. По умолчанию кэш отключен.
- **RHVOICE_FCACHE_LIFETIME**: Если кэш включен задает время жизни файлов кэша в часах, исчисляется от времени последнего доступа к файлу. Если FS смонтирована с `noatime` (а почти всегда это так) то `atime` будет обновляться принудительно. Может некорректно работать в Windows. По умолчанию `0` (файлы кэша живут вечно).

## Проверка
<http://localhost:8080/say?text=Привет>

<http://localhost:8080/say?text=Привет%20еще%20раз&format=opus>

<http://localhost:8080/say?text=Kaj%20mi%20ankaŭ%20parolas%20Esperanton&voice=spomenka&format=opus>

## Интеграция
- Home Assistant https://github.com/mgarmash/ha-rhvoice-tts
- [Примеры](https://github.com/Aculeasis/rhvoice-rest/tree/master/example)

## Links
- https://github.com/Olga-Yakovleva/RHVoice
- https://github.com/vantu5z/RHVoice-dictionary
- https://github.com/mgarmash/rhvoice-rest
