#!/usr/bin/env python3

import threading
import requests
import urllib3
import time
import sys


class Worker(threading.Thread):
    BUFF_SIZE = 1024

    def __init__(self, url=None, voice=None, text=None, format_=None):
        super().__init__()
        self.__params = {
            'voice': voice or 'spomenka',
            'text': text or 'Kaj mi ankaŭ parolas Esperanton',
            'format': format_ or 'wav',
        }
        self._url = url or 'http://127.0.0.1:8080/say'
        self._size = 0
        self._time = 0
        self.start()

    def run(self):
        self._time = time.perf_counter()
        try:
            rq = requests.get(self._url, params=self.__params, stream=True, timeout=300)
        except (
                requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                urllib3.exceptions.NewConnectionError
        ) as e:
            print(e)
        else:
            if not rq.ok:
                print('Error {}:{}'.format(rq.status_code, rq.reason))
            else:
                for chunk in rq.iter_content(chunk_size=self.BUFF_SIZE):
                    self._size += len(chunk)
        self._time = time.perf_counter() - self._time

    @property
    def size(self):
        return self._size

    @property
    def time(self):
        return self._time


def test(count):
    text = 'Внимание! Включён режим разработчика. Для возврата в обычный режим скажите \'выход\''
    voice = 'anna'
    time.sleep(0.1)
    w_time = time.perf_counter()
    workers = [Worker(text=text, voice=voice) for _ in range(count)]
    _ = [x.join() for x in workers]
    w_time = time.perf_counter() - w_time
    avg_time = w_time / count

    sizes = [x.size for x in workers]
    size = sizes[0]
    for test_size in sizes:
        assert size == test_size

    times = [x.time for x in workers]
    real_w_time = sum(times)
    real_avg_time = real_w_time / count
    return count, w_time, avg_time, real_w_time, real_avg_time, size


def print_result(count, w_time, avg_time, real_w_time, real_avg_time, size, boost):
    print('Threads: {}'.format(count))
    print('Work time: {:.4f}, avg: {:.4f}'.format(w_time, avg_time))
    print('In thread work time: {:.4f}, avg: {:.4f}'.format(real_w_time, real_avg_time))
    print('Boost: x {:.4f}'.format(boost))
    print('Data size: {}'.format(size))


if __name__ == '__main__':
    threads = 6
    if len(sys.argv) > 1:
        threads = int(sys.argv[1])
    test(threads)  # Прогрев
    one = test(1)[2]  # Время одного потока
    oll = test(threads)
    print_result(*oll, one / oll[2])
