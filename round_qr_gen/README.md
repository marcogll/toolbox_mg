# Round QR Generator

Generador de códigos QR con diseño moderno y redondeado que produce archivos SVG vectoriales.

## Características

- **Diseño único**: Módulos con forma de "blob" redondeado en lugar de cuadrados tradicionales
- **Ojos estilizados**: Los tres patrones de posicionamiento tienen esquinas redondeadas
- **Formato SVG**: Salida vectorial escalable sin pérdida de calidad
- **Interfaz TUI**: Interfaz interactiva en terminal usando [Textual](https://textual.textualize.io/)
- **Nombres inteligentes**: Generación automática de nombres basada en la URL

## Requisitos

- Python 3.12+
- qrcode
- Pillow
- textual

## Instalación

```bash
python -m venv venv
source venv/bin/activate
pip install qrcode pillow textual
```

## Uso

Ejecuta la aplicación:

```bash
python qr_gen.py
```

En la interfaz:
1. Ingresa la URL o texto en el primer campo
2. Opcionalmente, especifica un nombre personalizado para el archivo
3. Presiona "Generar QR" o Enter
4. El archivo SVG se guardará en el directorio actual

## Ejemplo de salida

Los archivos generados son SVG válidos que pueden:
- Escalarse sin pérdida de calidad
- Incrustarse en páginas web
- Editarse en herramientas como Inkscape o Illustrator
- Imprimirse en alta resolución

## Estructura del proyecto

```
round_qr_gen/
├── qr_gen.py          # Script principal con la interfaz TUI
├── *.svg              # Ejemplos de QR codes generados
└── venv/              # Entorno virtual (no incluir en git)
```

## Notas

- El QR usa corrección de errores nivel M (medium)
- Version 1 (aprox. 19 caracteres para URLs cortas)
- Los archivos SVG usan un grid de unidad 1 para facilitar edición
