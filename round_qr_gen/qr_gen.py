import qrcode
import os
from urllib.parse import urlparse
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Input, Button, Label, Static
from textual.events import Key
from textual import work

def obtener_nombre_dominio(url):
    if not url.startswith(('http://', 'https://')):
        url_temp = 'http://' + url
    else:
        url_temp = url
    try:
        parsed_uri = urlparse(url_temp)
        dominio = parsed_uri.netloc
    except Exception:
        dominio = ""
    if not dominio:
        dominio = url.strip().replace('/', '_').replace(':', '')
    return dominio.replace(':', '-') or "qr_output"

def is_eye(r, c, border, version_size):
    if border <= r < border + 7 and border <= c < border + 7:
        return True
    if border <= r < border + 7 and border + version_size - 7 <= c < border + version_size:
        return True
    if border + version_size - 7 <= r < border + version_size and border <= c < border + 7:
        return True
    return False

def rect_path(px, py, pw, ph, rx):
    return (
        f"M {px+rx},{py} "
        f"L {px+pw-rx},{py} Q {px+pw},{py} {px+pw},{py+rx} "
        f"L {px+pw},{py+ph-rx} Q {px+pw},{py+ph} {px+pw-rx},{py+ph} "
        f"L {px+rx},{py+ph} Q {px},{py+ph} {px},{py+ph-rx} "
        f"L {px},{py+rx} Q {px},{py} {px+rx},{py} Z"
    )

def dibujar_ojo_svg(x, y, size=7):
    gap   = 1.0
    r_out = 1.8
    r_in  = 1.3
    r_dot = 0.9

    outer = rect_path(x,         y,         size,         size,         r_out)
    inner = rect_path(x+gap,     y+gap,     size-gap*2,   size-gap*2,   r_in)
    dot   = rect_path(x+gap*2,   y+gap*2,   size-gap*4,   size-gap*4,   r_dot)

    return [
        f'<path d="{outer} {inner}" fill="black" fill-rule="evenodd"/>',
        f'<path d="{dot}" fill="black"/>',
    ]

def get_neighbors(matrix, r, c):
    rows = len(matrix)
    cols = len(matrix[0])
    top    = r > 0      and bool(matrix[r-1][c])
    bottom = r < rows-1 and bool(matrix[r+1][c])
    left   = c > 0      and bool(matrix[r][c-1])
    right  = c < cols-1 and bool(matrix[r][c+1])
    return top, bottom, left, right

def modulo_blob_path(r, c, top, bottom, left, right):
    R   = 0.45
    EXP = 0.15

    x1 = c       - (EXP if left   else 0)
    y1 = r       - (EXP if top    else 0)
    x2 = c + 1.0 + (EXP if right  else 0)
    y2 = r + 1.0 + (EXP if bottom else 0)

    tl = 0.0 if (top or left)     else R
    tr = 0.0 if (top or right)    else R
    br = 0.0 if (bottom or right) else R
    bl = 0.0 if (bottom or left)  else R

    d = (
        f"M {x1+tl:.3f},{y1:.3f} "
        f"L {x2-tr:.3f},{y1:.3f} "
        f"Q {x2:.3f},{y1:.3f} {x2:.3f},{y1+tr:.3f} "
        f"L {x2:.3f},{y2-br:.3f} "
        f"Q {x2:.3f},{y2:.3f} {x2-br:.3f},{y2:.3f} "
        f"L {x1+bl:.3f},{y2:.3f} "
        f"Q {x1:.3f},{y2:.3f} {x1:.3f},{y2-bl:.3f} "
        f"L {x1:.3f},{y1+tl:.3f} "
        f"Q {x1:.3f},{y1:.3f} {x1+tl:.3f},{y1:.3f} Z"
    )
    return f'<path d="{d}" fill="black"/>'

def generar_svg(matrix, filename, box_size=10, border=4):
    matrix_size  = len(matrix)
    version_size = matrix_size - 2 * border
    W = matrix_size * box_size
    H = matrix_size * box_size

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {matrix_size} {matrix_size}">',
    ]

    lines.extend(dibujar_ojo_svg(border, border))
    lines.extend(dibujar_ojo_svg(border + version_size - 7, border))
    lines.extend(dibujar_ojo_svg(border, border + version_size - 7))

    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c] and not is_eye(r, c, border, version_size):
                top, bottom, left, right = get_neighbors(matrix, r, c)
                lines.append(modulo_blob_path(r, c, top, bottom, left, right))

    lines.append('</svg>')

    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def normalizar_url(data):
    texto = data.strip()
    parece_url = '.' in texto and ' ' not in texto
    if parece_url and not texto.startswith(('http://', 'https://', 'mailto:', 'tel:')):
        texto = 'https://' + texto
    return texto

def obtener_nombre_archivo(data):
    nombre_base = obtener_nombre_dominio(data)
    if not nombre_base or nombre_base in ['http', 'https']:
        nombre_base = data.strip()[:40].replace('/', '_').replace(':', '').replace(' ', '_')
    return nombre_base

def resolver_conflicto(nombre_base, extension):
    nombre_archivo = f"{nombre_base}.{extension}"
    if not os.path.exists(nombre_archivo):
        return nombre_archivo
    return None, True

class QRGenerator(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #container {
        width: 60;
        height: auto;
        align: center middle;
    }
    .title {
        text: bold;
        color: $primary;
        text-align: center;
    }
    .label {
        color: $text;
    }
    #url_input {
        margin-bottom: 1;
    }
    #name_input {
        margin-bottom: 2;
    }
    .buttons {
        align: center middle;
        height: auto;
    }
    #status {
        text-align: center;
        color: $text-muted;
    }
    .success {
        color: $success;
    }
    .error {
        color: $error;
    }
    .warning {
        color: $warning;
    }
    """

    def __init__(self):
        super().__init__()
        self.url = ""
        self.suggested_name = ""
        self.status_message = ""
        self.status_class = ""

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            yield Static("╔══════════════════════════════════════╗", classes="title")
            yield Static("║     Generador de QR Codes SVG       ║", classes="title")
            yield Static("╚══════════════════════════════════════╝", classes="title")
            yield Label("")
            yield Label("URL / Texto:", classes="label")
            yield Input(placeholder="https://ejemplo.com", id="url_input")
            yield Label("")
            yield Label("Nombre del archivo (opcional):", classes="label")
            yield Input(placeholder="Enter para nombre por defecto", id="name_input")
            yield Label("")
            with Horizontal(classes="buttons"):
                yield Button("Generar QR", variant="primary", id="generate")
                yield Button("Salir", variant="default", id="quit")
            yield Label("")
            yield Label(id="status")

    def on_mount(self) -> None:
        self.query_one("#url_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url_input":
            self.url = event.value.strip()
            if self.url:
                self.url = normalizar_url(self.url)
                self.suggested_name = obtener_nombre_archivo(self.url)
                self.query_one("#name_input", Input).placeholder = self.suggested_name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.exit()
        elif event.button.id == "generate":
            self.generar_qr()

    def generar_qr(self) -> None:
        url_input = self.query_one("#url_input", Input)
        name_input = self.query_one("#name_input", Input)
        status = self.query_one("#status", Label)

        url = url_input.value.strip()
        if not url:
            status.update("⚠️  Ingresa una URL o texto")
            status.classes = "warning"
            return

        url = normalizar_url(url)
        nombre_base = obtener_nombre_archivo(url)

        nombre_personalizado = name_input.value.strip()
        if not nombre_personalizado:
            nombre_archivo = f"{nombre_base}.svg"
            if os.path.exists(nombre_archivo):
                status.update(f"⚠️  '{nombre_archivo}' ya existe. ¿Sobrescribir? [S/N]")
                status.classes = "warning"
                self.url = url
                self.pending_name = nombre_base
                self.action_overwrite_mode()
                return
        else:
            if not nombre_personalizado.endswith('.svg'):
                nombre_personalizado += '.svg'
            nombre_base_custom = nombre_personalizado[:-4]
            nombre_archivo = f"{nombre_base_custom}.svg"
            if os.path.exists(nombre_archivo):
                status.update(f"⚠️  '{nombre_archivo}' ya existe. ¿Sobrescribir? [S/N]")
                status.classes = "warning"
                self.url = url
                self.pending_name = nombre_base_custom
                self.action_overwrite_mode()
                return

        self._do_generate(url, nombre_archivo, status)

    def action_overwrite_mode(self) -> None:
        self.push_screen(OverwritePrompt(self.url, self.pending_name, self._on_overwrite_result))

    def _on_overwrite_result(self, result: tuple) -> None:
        status = self.query_one("#status", Label)
        if result[0] is None:
            status.update("❌ Cancelado")
            status.classes = "error"
        elif result[1]:
            url_input = self.query_one("#url_input", Input)
            url = normalizar_url(url_input.value.strip())
            self._do_generate(url, result[0], status)
        else:
            status.update("❌ Cancelado")
            status.classes = "error"

    def _do_generate(self, url: str, nombre_archivo: str, status: Label) -> None:
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            generar_svg(qr.get_matrix(), nombre_archivo)
            status.update(f"✅ ¡Listo! → {nombre_archivo}")
            status.classes = "success"

            url_input = self.query_one("#url_input", Input)
            name_input = self.query_one("#name_input", Input)
            url_input.value = ""
            name_input.value = ""
            url_input.focus()

        except Exception as e:
            status.update(f"❌ Error: {e}")
            status.classes = "error"


class OverwritePrompt(App):
    def __init__(self, url: str, nombre_base: str, callback):
        super().__init__()
        self.url = url
        self.nombre_base = nombre_base
        self.callback = callback

    CSS = """
    Screen {
        background: $surface;
    }
    #container {
        width: 50;
        height: auto;
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            yield Label(f"⚠️  '{self.nombre_base}.svg' ya existe", classes="warning")
            yield Label("")
            yield Label("[O] Sobrescribir  [D] Dejar ambos  [C] Cancelar")
            yield Label("")
            yield Input(placeholder="Elige opción...", id="option")

    def on_mount(self) -> None:
        self.query_one("#option", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        opcion = event.value.strip().lower()
        if opcion in ('o', 's'):
            self.callback((f"{self.nombre_base}.svg", True))
            self.exit()
        elif opcion in ('d'):
            contador = 1
            while True:
                nuevo_nombre = f"{self.nombre_base}_{contador}.svg"
                if not os.path.exists(nuevo_nombre):
                    self.callback((nuevo_nombre, True))
                    break
                contador += 1
            self.exit()
        elif opcion in ('c'):
            self.callback((None, False))
            self.exit()
        else:
            self.query_one("#option", Input).value = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "overwrite":
            self.callback((f"{self.nombre_base}.svg", True))
        elif event.button.id == "duplicate":
            contador = 1
            while True:
                nuevo_nombre = f"{self.nombre_base}_{contador}.svg"
                if not os.path.exists(nuevo_nombre):
                    self.callback((nuevo_nombre, True))
                    break
                contador += 1
        else:
            self.callback((None, False))
        self.exit()


if __name__ == "__main__":
    app = QRGenerator()
    app.run()