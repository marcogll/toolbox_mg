#!/usr/bin/env python3
"""Video to Audio Converter with transcription using OpenAI or OpenRouter API."""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
AUDIO_DIR = OUTPUT_DIR / "audio"
TRANSCRIPT_DIR = Path(".")

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}


def setup_directories():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Transcripts will be saved to: {Path.cwd().absolute()}")


def load_config():
    load_dotenv()
    return {
        "api_key": os.getenv("API_KEY"),
        "base_url": os.getenv("API_BASE_URL") or None,
        "model": os.getenv("WHISPER_MODEL", "whisper-1"),
    }


def detect_videos(directory: Path) -> list[Path]:
    if not directory.exists():
        print(f"Error: Input directory '{directory}' not found.")
        sys.exit(1)
    videos = [f for f in directory.iterdir() if f.suffix.lower() in VIDEO_EXTENSIONS]
    return sorted(videos)


def convert_video_to_audio(video_path: Path, audio_format: str = "mp3") -> Path:
    audio_path = AUDIO_DIR / f"{video_path.stem}.{audio_format}"
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame" if audio_format == "mp3" else "aac",
        "-ab", "192k", "-y", str(audio_path)
    ]
    print(f"Converting: {video_path.name} -> {audio_path.name}")
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def transcribe_api(audio_path: Path, config: dict, language: str = None) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai not installed. Run: pip install openai")
        sys.exit(1)

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    print(f"Transcribing via API: {audio_path.name} (model: {config['model']})")

    with open(audio_path, "rb") as f:
        params = {
            "model": config["model"],
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


def save_transcript(audio_path: Path, text: str):
    transcript_path = TRANSCRIPT_DIR / f"{audio_path.stem}.txt"
    transcript_path.write_text(text, encoding="utf-8")
    print(f"Transcript saved: {transcript_path}")


def ask_yes_no(prompt: str) -> bool:
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert video to audio and transcribe via API")
    parser.add_argument("--no-transcribe", action="store_true", help="Skip transcription")
    parser.add_argument("--language", type=str, help="Language code (e.g., 'es', 'en')")
    parser.add_argument("--model", type=str, help="Model to use (e.g., whisper-1, openai/whisper-1)")
    args = parser.parse_args()

    config = load_config()

    if not config["api_key"]:
        print("Error: API_KEY not set in .env file")
        sys.exit(1)

    if args.model:
        config["model"] = args.model

    setup_directories()
    videos = detect_videos(INPUT_DIR)

    if not videos:
        print("No video files found in input directory.")
        return

    print(f"Found {len(videos)} video(s):")
    for v in videos:
        print(f"  - {v.name}")

    audio_files = []
    for video in videos:
        try:
            audio_path = convert_video_to_audio(video)
            audio_files.append(audio_path)
        except subprocess.CalledProcessError:
            print(f"Failed to convert: {video.name}")
        except FileNotFoundError:
            print("Error: ffmpeg not found. Please install ffmpeg.")
            sys.exit(1)

    if args.no_transcribe or not audio_files:
        return

    if ask_yes_no("\nTranscribe audio to text?"):
        language = args.language
        if not language:
            language = input("Language code (e.g., 'es' for Spanish, 'en' for English, Enter for auto): ").strip()
            language = language if language else None

        print(f"\nUsing model: {config['model']}")
        if config["base_url"]:
            print(f"API endpoint: {config['base_url']}")

        for audio in audio_files:
            try:
                text = transcribe_api(audio, config, language)
                save_transcript(audio, text)
            except Exception as e:
                print(f"Transcription failed for {audio.name}: {e}")


if __name__ == "__main__":
    main()
