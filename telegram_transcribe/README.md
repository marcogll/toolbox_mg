# Video to Audio Converter

Herramienta para convertir videos a audio MP3 y transcribir el contenido de audio a texto usando APIs de reconocimiento de voz (OpenAI Whisper o OpenRouter).

## Características

- **Conversión de video a audio**: Soporta MP4, MKV, AVI, MOV, WMV, FLV, WebM, M4V
- **Transcripción automática**: Usa OpenAI Whisper API o modelos compatibles vía OpenRouter
- **Timestamps**: La transcripción incluye marcas de tiempo en formato `[HH:MM:SS.mmm --> HH:MM:SS.mmm]`
- **Procesamiento por lotes**: Procesa todos los videos en la carpeta `input/` automáticamente
- **Múltiples idiomas**: Soporte para transcripción en diferentes idiomas

## Requisitos

- Python 3.12+
- ffmpeg (para conversión de video)
- Cuenta en OpenAI o OpenRouter con API key

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Instalar ffmpeg (si no está instalado):
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

## Configuración

Copia el archivo de ejemplo y configura tus credenciales:

```bash
cp .env.template .env
```

Edita `.env` con tu configuración:

```
API_KEY=tu_api_key_aqui
API_BASE_URL=https://openrouter.ai/api/v1  # Opcional: dejar vacío para OpenAI
WHISPER_MODEL=whisper-1
```

## Uso

### Conversión y transcripción

1. Coloca tus videos en la carpeta `input/`
2. Ejecuta el script:

```bash
python video-tool-audio2text.py
```

3. El script te preguntará si deseas transcribir el audio
4. Los archivos generados se guardarán en:
   - `output/audio/` - Archivos MP3 convertidos
   - `./` - Archivos de transcripción `.txt` con timestamps

### Opciones de línea de comandos

```bash
# Solo convertir, sin transcribir
python video-tool-audio2text.py --no-transcribe

# Especificar idioma (código ISO)
python video-tool-audio2text.py --language es

# Usar un modelo específico
python video-tool-audio2text.py --model openai/whisper-1
```

## Estructura del proyecto

```
video to audio converter/
├── video-tool-audio2text.py    # Script principal
├── requirements.txt            # Dependencias Python
├── .env.template              # Plantilla de configuración
├── .env                        # Configuración (no incluir en git)
├── input/                      # Colocar videos aquí
│   ├── video1.mp4
│   └── video2.mkv
└── output/
    ├── audio/                  # Audios MP3 generados
    │   ├── video1.mp3
    │   └── video2.mp3
    └── transcripts/            # Transcripciones (opcional)
        ├── video1.txt
        └── video2.txt
```

## Notas

- La transcripción requiere conexión a internet y una API key válida
- OpenRouter permite usar modelos alternativos además de Whisper
- Los archivos de audio se generan a 192kbps de calidad
- Las transcripciones se guardan con codificación UTF-8
