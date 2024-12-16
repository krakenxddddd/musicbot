import socket
import json
import re
import logging

logger = logging.getLogger(__name__)

class LiqClient:
    def __init__(self, socket_path):
        self.socket_path = socket_path

    def _send_command(self, command):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                logger.info(f"Подключение к сокету: {self.socket_path}")
                sock.connect(self.socket_path)
                logger.info(f"Отправка команды: {command}")
                sock.sendall(f"{command}\n".encode())
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                return response.decode().strip()
        except (ConnectionRefusedError, OSError) as e:
            logger.error(f"Ошибка подключения к Liquidsoap: {e}")
            return None

    def command(self, command):
        response = self._send_command(command)
        return response

    def parse_metadata(self, s):
        response = self.command(s)
        if response is None:
            return None

        def dohash(a):
            h = {}
            a = list(a)
            for i in range(int(len(a) / 2)):
                a[2 * i + 1] = re.sub('^"', '', re.sub('"$', '', a[2 * i + 1]))
                if a[2 * i] in ('2nd_queue_pos', 'rid', 'source_id'):
                    h[a[2 * i]] = int(a[2 * i + 1])
                else:
                    if a[2 * i] in ('skip'):
                        h[a[2 * i]] = a[2 * i + 1] == 'true'
                    else:
                        h[a[2 * i]] = a[2 * i + 1]
            return h

        def noblank(a):
            return filter(lambda x: x != '', a)

        try:
            return [dohash(noblank(re.compile('(.+)=(".*")\n').split(e))) for e in noblank(re.compile('--- \d+ ---\n').split(response))]
        except:
            return None

    def queue(self, filepath):
        logger.info(f"Вызов queue с путем: {filepath}")
        logger.info(f"Добавление в очередь: {filepath}")  # Добавлено логирование
        item = self.command(f"request.push '{filepath}'") # Добавлена обработка пути
        try:
            return int(item) if item else None
        except ValueError:
            logger.error(f"Ошибка при получении номера из очереди: {item}")
            return None

    def queue_size(self):
        logger.info(f"Получение размера очереди...")
        response = self.command("request_queue.size()")
        try:
            return int(response)
        except ValueError:
            logger.error(f"Ошибка получения размера очереди: {response}")
            return 0

    def play_queue(self):
        logger.info(f"Запуск очереди...")
        return self.command("request_queue.play")

    def play_main_playlist(self):
        return self.command("main_playlist.play")

    def info(self, item=None):
        if item:
            return self.parse_metadata(f"request.metadata {item}")
        else:
            return self.parse_metadata(f"root.metadata")

    def np(self):
        i = self.info()
        if i is None:
            return {"title": "(неизвестное название)", "purl": "(неизвестный оригинальный URL)"}
        i.reverse()
        playing_track = [x for x in i if x.get('status') == "playing"]
        if playing_track:
            return playing_track[0]
        else:
            return {"title": "(ничего не играет)", "purl": "(ничего не играет)"}

    def skip(self):
        return self.command("root.skip") == "Done"