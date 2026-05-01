#!/usr/bin/env python3
"""Telegram bot for handling channel media, sending questions to forum group topics."""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from openai import OpenAI

load_dotenv()

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")
TARGET_GROUP_ID = os.getenv("TARGET_GROUP_ID")
TARGET_TOPIC_ID = os.getenv("TARGET_TOPIC_ID")
API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or None
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")

# Directories
TEMP_DIR = Path("temp_media")
TEMP_DIR.mkdir(exist_ok=True)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}


def get_openai_client():
    return OpenAI(api_key=API_KEY, base_url=API_BASE_URL)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot iniciado. Monitoreando canal de origen...")


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def convert_video_to_audio(video_path: Path, audio_format: str = "mp3") -> Path:
    audio_path = TEMP_DIR / f"{video_path.stem}.{audio_format}"
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame" if audio_format == "mp3" else "aac",
        "-ab", "192k", "-y", str(audio_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path


def transcribe_audio(audio_path: Path, language: str = None) -> str:
    client = get_openai_client()
    with open(audio_path, "rb") as f:
        params = {
            "model": WHISPER_MODEL,
            "file": f,
            "response_format": "verbose_json",
            "timestamp_granularities": ["segment"]
        }
        if language:
            params["language"] = language
        response = client.audio.transcriptions.create(**params)
    lines = []
    for segment in response.segments:
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        lines.append(f"[{start} --> {end}] {segment.text.strip()}")
    return "\n".join(lines)


async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
    
    message = update.channel_post
    chat = message.chat
    
    # Check if message is from source channel
    source_id = SOURCE_CHANNEL_ID
    if source_id.startswith("@"):
        # Username format
        if chat.username and f"@{chat.username}" != source_id:
            return
    else:
        # Numeric ID format (handle -100 prefix)
        try:
            source_numeric = int(source_id.replace("@", ""))
            if chat.id != source_numeric:
                return
        except ValueError:
            return
    
    # Detect media
    media_type = None
    file_id = None
    if message.video:
        media_type = "video"
        file_id = message.video.file_id
    elif message.audio:
        media_type = "audio"
        file_id = message.audio.file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("video/"):
        media_type = "video"
        file_id = message.document.file_id
    else:
        return
    
    # Store media info in context for the target group
    # Using bot_data to share across users in group
    if "pending_media" not in context.bot_data:
        context.bot_data["pending_media"] = []
    
    context.bot_data["pending_media"].append({
        "file_id": file_id,
        "media_type": media_type,
        "channel_msg_id": message.id
    })
    
    keyboard = [
        [InlineKeyboardButton("Transcribir audio", callback_data="transcribe")],
        [InlineKeyboardButton("Descargar video", callback_data="download_video")],
        [InlineKeyboardButton("Procesar red social", callback_data="social_media")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        message_thread_id=int(TARGET_TOPIC_ID) if TARGET_TOPIC_ID else None,
        text=f"Nuevo medio recibido en canal: {media_type.upper()}",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Get the most recent media from bot_data
    pending = context.bot_data.get("pending_media", [])
    if not pending:
        await query.edit_message_text("Error: No se encontró medio asociado.")
        return
    
    media_info = pending[-1]  # Get the last received media
    media_file_id = media_info["file_id"]
    
    await query.edit_message_text(f"Procesando acción: {data}...")
    
    try:
        if data == "transcribe":
            await handle_transcribe(media_file_id, query, context)
        elif data == "download_video":
            await handle_download_video(media_file_id, query, context)
        elif data == "social_media":
            await handle_social_media(media_file_id, query, context)
    except Exception as e:
        await query.edit_message_text(f"Error: {str(e)}")


async def handle_transcribe(file_id: str, query, context: ContextTypes.DEFAULT_TYPE):
    # Download file from Telegram
    file = await context.bot.get_file(file_id)
    file_path = TEMP_DIR / f"{file_id}.tmp"
    await file.download_to_drive(file_path)
    
    # Convert to audio if video
    if file_path.suffix.lower() in VIDEO_EXTENSIONS:
        audio_path = convert_video_to_audio(file_path)
    else:
        audio_path = file_path
    
    # Transcribe
    transcript = transcribe_audio(audio_path)
    
    # Send transcript
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        message_thread_id=int(TARGET_TOPIC_ID) if TARGET_TOPIC_ID else None,
        text=f"Transcripción:\n{transcript[:4000]}"
    )
    await query.edit_message_text("Transcripción completada.")
    
    # Cleanup
    file_path.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)


async def handle_download_video(file_id: str, query, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(file_id)
    download_path = TEMP_DIR / f"video_{file_id}"
    await file.download_to_drive(download_path)
    await query.edit_message_text(f"Video descargado: {download_path.name}")
    # Add more logic for specific URL downloads here


async def handle_social_media(file_id: str, query, context: ContextTypes.DEFAULT_TYPE):
    await query.edit_message_text("Procesando red social...")
    # Add social media processing logic here


def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN no configurado.")
        sys.exit(1)
    if not SOURCE_CHANNEL_ID or not TARGET_GROUP_ID or not TARGET_TOPIC_ID:
        print("Error: Configura SOURCE_CHANNEL_ID, TARGET_GROUP_ID, TARGET_TOPIC_ID.")
        sys.exit(1)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot iniciado. Presiona Ctrl+C para detener.")
    application.run_polling(allowed_updates=["channel_post", "callback_query"])


if __name__ == "__main__":
    main()
