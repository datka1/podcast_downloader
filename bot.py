import logging
import subprocess
import glob
import os
import time

from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ChatActions


API_TOKEN = ""

FFMPEG_PATH = "/home/david/telegram_bot/ffmpeg"
DOWNLOAD_PATH = "/home/david/telegram_bot/podcast/"
LOG_PATH = "/home/david/telegram_bot/podcast/links_log.txt"
BAD_KEYWORDS = ["spotify", "ivoox"]

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply(
        "▶️ Вставляем линк \ 🎧 Бот скачивает видео и высылает как аудио с минимальным размером \ ▶️ Paste video link here \ 🎧 Bot will download video and extract audio with minimal size"
    )


@dp.message_handler()
async def download(message: types.Message):
    audio_list = []

    # Маленькое Логирование. Время/Линк/UserID
    time_now = datetime.today().strftime("%D %H:%M:%S")
    pasted_links_log = open(LOG_PATH, "a")
    pasted_links_log.write(
        f"[{time_now}] | Link : {message.text} | UserID : {message.from_user.id} \n"
    )
    pasted_links_log.close()

    # Проверяем на наличие плохих Url-ов у которых проблемы с yt-dlp. Проверяем в тексте сообщения
    bad_keyword_flag = 0

    for badkeyword in BAD_KEYWORDS:
        for badurl in message.text.split("."):
            if badkeyword == badurl or len(message.text.split(".")) <= 1:
                bad_keyword_flag = 1
                break
    if bad_keyword_flag == 1:
        await message.answer(
            "❌ Линк не поддерживается или это не линк, скачивание невозможно \ ❌ Link is not supported or its not a link, download is not possible"
        )
    else:
        await message.answer("⬇️ Скачиваю \ ⬇️ Downloading")
        # Запускаем yt-dlp скачиваем аудио из видео
        popen = subprocess.Popen(
            [
                "yt-dlp",
                "-S",
                "+size,+br,+res,+fps",
                "-x",
                "--audio-format",
                "m4a",
                str(message.text),
                "--ffmpeg-location",
                FFMPEG_PATH,
                "-o",
                f"{DOWNLOAD_PATH}{message.from_user.id}/%(title)s.%(ext)s",
            ],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )

        # Получаем дынные из popen = subprocess.Popen , Забираем оттуда проценты скачки и предеаем боту.
        messagetoedit = await bot.send_message(
            message.chat.id, "⏳ Готово \ ⏳ Done : 0%"
        )
        for line in popen.stdout:
            if "ETA" in line:
                down_percent = line.split()[1].replace("%", "")
                time.sleep(3)
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=messagetoedit.message_id,
                        text=f"⏳ Готово \ ⏳ Done : {down_percent}%",
                    )
                except:
                    pass
        # Проверяем что-бы размер файла не превышал 45 МБ. Лимит 50МБ
        for podcast in glob.glob(f"{DOWNLOAD_PATH}{message.from_user.id}/*.m4a"):
            file_size = round(os.stat(podcast).st_size / (1024 * 1024))
            if file_size > 45:
                await message.answer(
                    f"💾 Размер файла : {file_size} MB \ 📦 Фаил превышает допустимый размер \ ✂️ Обрезаю аудиофаил на части \ 💾 File size : {file_size} MB \ 📦 File is over size limit \ ✂️ Cutting in to pieces"
                )
                # Режим фаил на размер в 45 МБ.FFMPEG не работает нормально. mkvmerge в помощь.
                subprocess.run(
                    [
                        "mkvmerge",
                        "-o",
                        f'{DOWNLOAD_PATH}{message.from_user.id}/[%02d] {podcast.split("/")[6]}',
                        "--split",
                        "45M",
                        podcast,
                    ]
                )
                os.remove(podcast)
            else:
                pass
        await message.answer("⬆️ Высылаю аудиофаилы \ ⬆️ Sending Files")

        for podcast in glob.glob(f"{DOWNLOAD_PATH}{message.from_user.id}/*.m4a"):
            audio_list.append(podcast)
        audio_list.sort()

        for audio_file in audio_list:
            audio = open(audio_file, "rb")
            await bot.send_chat_action(message.from_user.id, ChatActions.UPLOAD_AUDIO)
            await bot.send_audio(message.chat.id, audio)
            audio.close()
            os.remove(audio_file)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
