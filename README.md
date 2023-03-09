[rhvoice-rest](https://github.com/Aculeasis/rhvoice-rest)
============
[![Docker Pulls](https://img.shields.io/docker/pulls/aculeasis/rhvoice-rest.svg)](https://hub.docker.com/r/aculeasis/rhvoice-rest/)
[![Tests](https://github.com/Aculeasis/rhvoice-rest/actions/workflows/tests.yml/badge.svg)](https://github.com/Aculeasis/rhvoice-rest/actions/workflows/tests.yml)

Это веб-сервис на основе flask и синтезатора речи [RHVoice](https://github.com/Olga-Yakovleva/RHVoice). Благодаря REST API его легко интегрировать в качестве TTS-провайдера.

## Docker
```bash
docker run -d \
  --name=rhvoice-rest \
  -p 8080:8080 \
  --restart unless-stopped \
  aculeasis/rhvoice-rest:latest
```
Для автоматического обновления можно использовать [Watchtower](https://github.com/containrrr/watchtower).

## API
    http://SERVER/say?
    text=<текст>
    & voice=<
             aleksandr|anna|arina|artemiy|elena|irina|pavel| # Russian
             alan|bdl|clb|slt| # English
             spomenka| # Esperanto
             natia| # Georgian
             azamat|nazgul| # Kyrgyz
             talgat| # Tatar
             anatol|natalia| # Ukrainian
             kiko| # Macedonian
             letícia-f123 # Portuguese
             >
    & format=<wav|mp3|opus|flac>
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

    http://SERVER/info - выводит различную информацию о сервере в JSON.

### Rhasspy Voice Assistant
Для интеграции в [Rhasspy](https://rhasspy.readthedocs.io/en/latest/) через [Remote](https://rhasspy.readthedocs.io/en/latest/text-to-speech/#remote) замените `/say` на `/rhasspy`. Аргументы `text` и `format` игнорируются (формат всегда wav, а текст передается в теле POST).
```
"text_to_speech": {
  "system": "remote",
  "remote": {
      "url": "http://localhost:8080/rhasspy?voice=anna"
  }
}
```

## Нативный запуск
Для начала нужно установить зависимости:

`pip3 install flask pymorphy2 rhvoice-wrapper`

Собрать и установить [RHVoice](https://github.com/Olga-Yakovleva/RHVoice) или установить [rhvoice-wrapper-bin](https://github.com/Aculeasis/rhvoice-wrapper-bin) предоставляющий библиотеки и данные RHVoice. Второй вариант рекомендуется для Windows т.к. не требует сборки.

И еще рядом с app.py положить `rhvoice_tools` - переименовав `preprocessing` из [RHVoice-dictionary/tools](https://github.com/vantu5z/RHVoice-dictionary/tree/master/tools).

Для поддержки `mp3`, `opus` и `flac` нужно установить `lame`, `opus-tools` и `flac`

### Устновка скриптом на debian-based дистрибутивах в качестве сервиса
    git clone https://github.com/Aculeasis/rhvoice-rest
    cd rhvoice-rest
    chmod +x install.sh
    sudo ./install.sh
Статус сервиса `sudo systemctl status rhvoice-rest.service`

### Особенности запуска в Windows
Нужно задать пути через переменные окружения. Если вы используете `rhvoice-wrapper-bin` то первые 2 задавать не нужно:

**RHVOICELIBPATH** до `RHVoice.dll` той же архитектуры что и питон и **RHVOICEDATAPATH** до папки с languages и voices. По умолчанию они ставятся в `C:\Program Files (x86)\RHVoice\data`

Не обязательно: **LAMEPATH**, **OPUSENCPATH** и **FLACPATH** для поддержки соответствующих форматов.

Протестировано на Windows 10 и Python 3.6.

## Настройки
Все настройки задаются через переменные окружения, до запуска скрипта или при создании докер-контейнера (через `-e`):
- **RHVOICELIBPATH**: Путь до библиотеки RHVoice. По умолчанию `RHVoice.dll` в Windows и `libRHVoice.so` в Linux.
- **RHVOICEDATAPATH**:  Путь до данных RHVoice. По умолчанию `/usr/local/share/RHVoice`.
- **THREADED**: Количество запущенных процессов синтеза, определяет количество запросов которые могут быть обработаны одновременно. Если `> 1` генераторы будут запущены в качестве отдельных процессов что существенно увеличит потребление памяти. Рекомендуемое максимальное значение `1.5 * core count`. По умолчанию `1`.
- **LAMEPATH**: Путь до `lame` или `lame.exe`, если файл не найден поддержка `mp3` будет отключена. По умолчанию `lame`.
- **OPUSENCPATH**: Путь до `opusenc` или `opusenc.exe`, если файл не найден поддержка `opus` будет отключена. По умолчанию `opusenc`.
- **FLACPATH**: Путь до `flac` или `flac.exe`, если файл не найден поддержка `flac` будет отключена. По умолчанию `flac`.
- **RHVOICE_DYNCACHE**: Если задано и не равно `no`, `disable` или `false` кэширует результат запроса на время его генерации. Включается автоматически вместе с **RHVOICE_FCACHE**.
- **RHVOICE_FCACHE**: Если задано и не равно `no`, `disable` или `false` будет включен файловый кэш. Чтение из кэша почти не увеличивает скорость реакции, но значительно уменьшает время загрузки всех данных. Может некорректно работать в Windows. По умолчанию кэш отключен.
- **RHVOICE_FCACHE_LIFETIME**: Если кэш включен задает время жизни файлов кэша в часах, исчисляется от времени последнего доступа к файлу. Если FS смонтирована с `noatime` (а почти всегда это так) то `atime` будет обновляться принудительно. Может некорректно работать в Windows. По умолчанию `0` (файлы кэша живут вечно).
- **CHUNKED_TRANSFER**: Если задано и не равно `no`, `disable` или `false` включает [Chunked transfer encoding](https://en.wikipedia.org/wiki/Chunked_transfer_encoding). По умолчанию отключен.

## Проверка
<http://localhost:8080/say?text=Привет>

<http://localhost:8080/say?text=Привет%20еще%20раз&format=opus>

<http://localhost:8080/say?text=Kaj%20mi%20ankaŭ%20parolas%20Esperanton&voice=spomenka&format=opus>

## Интеграция
- [Home Assistant](https://github.com/definitio/ha-rhvoice)
- [Примеры](https://github.com/Aculeasis/rhvoice-rest/tree/master/example)
