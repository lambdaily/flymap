"""Small dependency-free PDF report generator for FlyMap.

The report is intentionally generated server-side so the downloaded file keeps
the exact specimen identity and the readings shown in the current session.
"""

from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from typing import Any


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 40

COLORS = {
    "ink": (0.08, 0.15, 0.14),
    "muted": (0.36, 0.46, 0.43),
    "teal": (0.09, 0.44, 0.40),
    "mint": (0.55, 0.91, 0.82),
    "paper": (0.96, 0.95, 0.89),
    "line": (0.83, 0.87, 0.82),
    "red": (0.88, 0.25, 0.20),
    "yellow": (0.91, 0.60, 0.08),
    "green": (0.18, 0.68, 0.39),
    "pending": (0.45, 0.52, 0.49),
}


def _pdf_text(value: object) -> str:
    """Encode a string for a PDF built-in WinAnsi font."""

    text = str(value).replace("\n", " ").replace("\r", " ")
    encoded = text.encode("cp1252", errors="replace").decode("latin-1")
    return encoded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(value: object, width: int) -> list[str]:
    words = str(value).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _rgb(rgb: tuple[float, float, float], fill: bool = True) -> str:
    operator = "rg" if fill else "RG"
    return f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} {operator}"


def _text(commands: list[str], x: float, y: float, value: object, size: float = 10, font: str = "F1", color: tuple[float, float, float] | None = None) -> None:
    if color:
        commands.append(_rgb(color))
    commands.append(f"BT /{font} {size:g} Tf {x:g} {y:g} Td ({_pdf_text(value)}) Tj ET")


def _multiline(commands: list[str], x: float, y: float, value: object, width: int, size: float = 8, leading: float = 10, color: tuple[float, float, float] | None = None) -> None:
    for line in _wrap(value, width):
        _text(commands, x, y, line, size=size, color=color)
        y -= leading


def _rect(commands: list[str], x: float, y: float, width: float, height: float, color: tuple[float, float, float], stroke: tuple[float, float, float] | None = None, line_width: float = 1) -> None:
    commands.append(_rgb(color))
    commands.append(f"{x:g} {y:g} {width:g} {height:g} re f")
    if stroke:
        commands.append(_rgb(stroke, fill=False))
        commands.append(f"{line_width:g} w {x:g} {y:g} {width:g} {height:g} re S")


def _circle(commands: list[str], x: float, y: float, radius: float, color: tuple[float, float, float]) -> None:
    # Four cubic curves approximate a circle using the standard 0.5522848 factor.
    k = radius * 0.5522848
    commands.append(_rgb(color))
    commands.append(
        f"{x + radius:g} {y:g} m {x + radius:g} {y + k:g} {x + k:g} {y + radius:g} {x:g} {y + radius:g} c "
        f"{x - k:g} {y + radius:g} {x - radius:g} {y + k:g} {x - radius:g} {y:g} c "
        f"{x - radius:g} {y - k:g} {x - k:g} {y - radius:g} {x:g} {y - radius:g} c "
        f"{x + k:g} {y - radius:g} {x + radius:g} {y - k:g} {x + radius:g} {y:g} c f"
    )


def _answer_info(result: dict[str, Any] | None) -> tuple[str, tuple[float, float, float], str]:
    answer = (result or {}).get("answer")
    labels = {"green": "Verde", "yellow": "Amarillo", "red": "Rojo"}
    color = COLORS.get(answer or "pending", COLORS["pending"])
    return labels.get(answer, "Pendiente"), color, answer or "pending"


def _build_content(profile: dict[str, Any], indicators: list[dict[str, Any]], results: dict[str, dict[str, Any]]) -> bytes:
    commands: list[str] = []
    dark = COLORS["ink"]
    white = (0.95, 0.99, 0.96)

    _rect(commands, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, COLORS["paper"])
    _rect(commands, 0, 750, PAGE_WIDTH, 92, dark)
    _text(commands, MARGIN, 806, "FlyMap", size=26, font="F2", color=COLORS["mint"])
    _text(commands, MARGIN, 785, "A Poverty Stoplight through the mind of a fly.", size=10, color=white)
    _text(commands, PAGE_WIDTH - 166, 808, "FLYMAP REPORT", size=8, font="F2", color=COLORS["mint"])
    _text(commands, PAGE_WIDTH - 166, 790, "LECTURA CONDUCTUAL SIMULADA", size=7, color=(0.66, 0.78, 0.73))

    _text(commands, MARGIN, 714, "IDENTIDAD DEL ESPECIMEN", size=8, font="F2", color=COLORS["teal"])
    _rect(commands, MARGIN, 632, PAGE_WIDTH - 2 * MARGIN, 65, (0.91, 0.95, 0.90), stroke=COLORS["line"])
    _text(commands, 56, 673, profile.get("name", "Mosca sin nombre"), size=20, font="F2", color=dark)
    _text(commands, 56, 651, f"Pais generado: {profile.get('country', 'No definido')}", size=10, color=COLORS["muted"])
    _text(commands, 285, 673, f"Lugar de nacimiento: {profile.get('birthplace', 'Moscu')}", size=10, font="F2", color=COLORS["teal"])
    _text(commands, 285, 651, f"ID: {profile.get('code', 'FM-0000')}", size=9, color=COLORS["muted"])

    _text(commands, MARGIN, 603, "INDICADORES Y SEÑALES", size=8, font="F2", color=COLORS["teal"])
    table_x = MARGIN
    table_y = 566
    table_width = PAGE_WIDTH - 2 * MARGIN
    header_h = 25
    row_h = 48
    widths = [34, 178, 163, 140]
    _rect(commands, table_x, table_y, table_width, header_h, COLORS["teal"])
    headers = ["#", "INDICADOR", "ESTIMULO", "LECTURA"]
    cursor_x = table_x
    for header, width in zip(headers, widths):
        _text(commands, cursor_x + 8, table_y + 9, header, size=7, font="F2", color=white)
        cursor_x += width

    counts = {"green": 0, "yellow": 0, "red": 0}
    for index, indicator in enumerate(indicators):
        result = results.get(indicator.get("id", ""))
        row_top = table_y - header_h - index * row_h
        row_bottom = row_top - row_h
        row_fill = (0.985, 0.98, 0.93) if index % 2 == 0 else (0.94, 0.96, 0.92)
        _rect(commands, table_x, row_bottom, table_width, row_h, row_fill, stroke=COLORS["line"], line_width=0.5)
        x = table_x
        for width in widths[:-1]:
            x += width
            commands.append(_rgb(COLORS["line"], fill=False))
            commands.append(f"0.5 w {x:g} {row_bottom:g} m {x:g} {row_top:g} l S")
        _text(commands, table_x + 10, row_top - 20, f"{index + 1:02d}", size=9, font="F2", color=COLORS["muted"])
        _multiline(commands, table_x + widths[0] + 8, row_top - 15, indicator.get("title", "Indicador"), 25, size=8.5, leading=10, color=dark)
        stimulus = (indicator.get("stimulus") or {}).get("title", "Estimulo")
        _multiline(commands, table_x + widths[0] + widths[1] + 8, row_top - 15, stimulus, 23, size=8.5, leading=10, color=COLORS["muted"])
        label, color, answer = _answer_info(result)
        _circle(commands, table_x + sum(widths[:-1]) + 16, row_top - 18, 5, color)
        _text(commands, table_x + sum(widths[:-1]) + 27, row_top - 21, label, size=9, font="F2", color=dark if answer != "pending" else COLORS["muted"])
        if result:
            if answer in counts:
                counts[answer] += 1
            confidence = round(float(result.get("confidence", 0)) * 100)
            _text(commands, table_x + sum(widths[:-1]) + 27, row_top - 35, f"Confianza {confidence}%", size=7.5, color=COLORS["muted"])
        else:
            _text(commands, table_x + sum(widths[:-1]) + 27, row_top - 35, "Aun no ejecutado", size=7.5, color=COLORS["muted"])

    bottom = table_y - header_h - len(indicators) * row_h
    _text(commands, MARGIN, bottom - 28, "RESUMEN", size=8, font="F2", color=COLORS["teal"])
    summary_y = bottom - 53
    summary_items = [("Verdes", counts["green"], COLORS["green"]), ("Amarillos", counts["yellow"], COLORS["yellow"]), ("Rojos", counts["red"], COLORS["red"])]
    for offset, (label, count, color) in enumerate(summary_items):
        x = MARGIN + offset * 120
        _circle(commands, x + 5, summary_y + 3, 5, color)
        _text(commands, x + 16, summary_y, f"{count} {label}", size=9, font="F2", color=dark)
    _text(commands, MARGIN, 86, "Esta lectura traduce la conducta de una mosca simulada a un semaforo interpretativo.", size=8, color=COLORS["muted"])
    _text(commands, MARGIN, 70, "No es una respuesta humana ni un diagnostico oficial de pobreza.", size=8, color=COLORS["muted"])
    _text(commands, PAGE_WIDTH - 150, 70, "FlyMap | surrogate-lif", size=8, color=COLORS["teal"])
    return "\n".join(commands).encode("latin-1", errors="replace")


def build_report(profile: dict[str, Any], indicators: Iterable[dict[str, Any]], results: dict[str, dict[str, Any]]) -> bytes:
    """Return a one-page PDF report suitable for direct browser download."""

    content = _build_content(profile, list(indicators), results)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{number} 0 obj\n".encode("ascii"))
        buffer.write(obj)
        buffer.write(b"\nendobj\n")
    xref_offset = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return buffer.getvalue()
