import asyncio
import os
from highrise import *
from highrise.models import *
import random
from youtubesearchpython import VideosSearch
import yt_dlp
import subprocess
import socket
import json
import re
from liquidsoap_client import LiqClient

class Mybot(BaseBot):

    async def on_start(self, session_metadata: SessionMetadata) -> None:
        await self.highrise.walk_to(Position(16.5, 0.5, 7.5))

    async def on_user_join(self, user: User, position: Position | AnchorPosition) -> None:
        await self.highrise.send_whisper(user.id, f"\nПривет, я DJ Kraken управляющий радиостанцией\n/queue название - добавить трек в очередь")

    async def on_chat(self, user: User, message: str) -> None:
        print(f"Received: {message} from {user.username}")
        message = message.lower()
        cli = LiqClient('/tmp/liquidsoap.sock')

        try:
            if message.startswith("/queue "):
                track_name = message[7:]  # Extract track name after "/queue "
                download_directory = "/home/user/Загрузки/RadioKraken/downloads"
                filepath = await self.search_youtube(track_name, download_directory)
                if filepath:
                    cli.queue(filepath)
                    if cli.queue_size() > 0: # Проверяем, не пуста ли очередь после добавления
                        if cli.np() is None:  # Проверяем, играет ли что-то
                            cli.play_queue()
                    await self.highrise.send_whisper(user.id, f"Added '{track_name}' to queue.")
                else:
                    await self.highrise.send_whisper(user.id, f"Could not find '{track_name}'.")

            elif message == "/info":
                playing_track = cli.np()
                if playing_track:
                    title = playing_track.get('title', playing_track.get('filename', "(неизвестное название)"))
                    orig = playing_track.get('purl', playing_track.get('initial_uri', "(неизвестный оригинальный URL)")).replace('youtube-dl:', '')
                    await self.highrise.send_whisper(user.id, f"Сейчас играет: {title}\nОригинал: {orig}")
                else:
                    await self.highrise.send_whisper(user.id, "Ничего не играет.")

            elif message.startswith("/info "):
                try:
                    track_number = int(message[6:])
                    info = cli.info(track_number)
                    if info:
                        status_message = self.format_track_info(info[0])
                        await self.highrise.send_whisper(user.id, status_message)
                    else:
                        await self.highrise.send_whisper(user.id, f"Track number {track_number} not found.")
                except ValueError:
                    await self.highrise.send_whisper(user.id, "Invalid track number.")

            elif message == "/skip":
                if cli.skip():
                    await self.highrise.send_whisper(user.id, "Пропущен трек.")
                else:
                    await self.highrise.send_whisper(user.id, "Ошибка пропуска трека.")

            elif message == "/np":
                playing_track = cli.np()
                if playing_track:
                    title = playing_track.get('title', playing_track.get('filename', "(неизвестное название)"))
                    orig = playing_track.get('purl', playing_track.get('initial_uri', "(неизвестный оригинальный URL)")).replace('youtube-dl:', '')
                    await self.highrise.send_whisper(user.id, f"Сейчас играет: {title}\nОригинал: {orig}")
                else:
                    await self.highrise.send_whisper(user.id, "Ничего не играет.")

            elif message.startswith("/tipmes "): # пример новой команды
                tip_message = message[8:] # извлечение сообщения после /tipmes
                await self.highrise.send_whisper(user.id, f"Подсказка: {tip_message}")
            else:
                await self.highrise.send_whisper(user.id, f"Unknown command: {message}")

        except Exception as e:
            await self.highrise.send_whisper(user.id, f"An error occurred: {type(e).__name__}: {e}")



    async def search_youtube(self, query: str, download_dir: str) -> str | None: # Добавили download_dir
        try:
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'noplaylist': True,
                'nocheckcertificate': True,
                'quiet': True,
                'proxy': 'http://83.171.234.6:30018:4d3afc56:dbe75d46ac' # Замените на ваш прокси
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(f'ytsearch1:{query}', download=False)
                if info_dict and info_dict['entries']:
                    video = info_dict['entries'][0]
                    # Создаем имя файла и проверяем наличие директории
                    filename = os.path.join(download_dir, f"{video['id']}.m4a")
                    os.makedirs(download_dir, exist_ok=True) # Создаем директорию, если её нет
                    ydl_opts['outtmpl'] = filename  # Устанавливаем полный путь
                    logger.info(f"Скачивание трека: {query}, путь: {filename}")
                    ydl.download([video])  # Скачиваем, используя полный путь
                    logger.info(f"Трек скачан: {filename}")

                    return filename
                else:
                    return None

        except yt_dlp.DownloadError as e:
            logger.error(f"yt-dlp DownloadError: {e}")
            await self.highrise.send_whisper(user.id, f"Ошибка загрузки с YouTube: {e}")
            return None
        except Exception as e:
            logger.exception(f"Ошибка в search_youtube: {e}")
            await self.highrise.send_whisper(user.id, f"Непредвиденная ошибка: {type(e).__name__}: {e}")
            return None

    def format_track_info(self, track_info):
        title = track_info.get('title', track_info['initial_uri'])
        status_messages = {
            "destroyed": "Статус 'уничтожен'. Вы ввели неверный URL?",
            "resolving": "Скачивание этого трека сейчас! Пожалуйста, подождите!",
            "ready": "Трек готов! Ждите...",
            "playing": "Трек сейчас играет."
        }
        description = status_messages.get(track_info['status'], f"Трек в статусе {track_info['status']}.")
        return f"**{title}**\n{description}"