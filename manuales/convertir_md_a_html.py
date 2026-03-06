#!/usr/bin/env python3
"""
Conversor MD → HTML con estilo visual DyM/WSR.
Replica el diseño del Weekly Sales Report: azul #1e3a8a, secciones con borde lateral,
tablas con headers oscuros, cajas de alerta/nota, tabla de contenidos con links internos.

Uso:
    python convertir_md_a_html.py                  # Convierte los 3 manuales
    python convertir_md_a_html.py archivo.md        # Convierte un archivo específico
"""

import re
import sys
import os
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────
# CSS: Réplica del estilo WSR DyM
# ─────────────────────────────────────────────

CSS_STYLES = """
:root {
    --primary: #1e3a8a;
    --primary-light: #3b82f6;
    --primary-bg: #f0f9ff;
    --bg: #f5f5f5;
    --white: #ffffff;
    --text: #1f2937;
    --text-light: #6b7280;
    --border: #e5e7eb;
    --positive: #059669;
    --negative: #dc2626;
    --warning-bg: #fffbeb;
    --warning-border: #fcd34d;
    --warning-text: #92400e;
    --success-bg: #f0fdf4;
    --success-border: #86efac;
    --success-text: #166534;
    --info-bg: #eff6ff;
    --info-border: #93c5fd;
    --info-text: #1e40af;
    --code-bg: #1e293b;
    --code-text: #e2e8f0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    font-size: 15px;
}

.container {
    max-width: 1100px;
    margin: 30px auto;
    background: var(--white);
    border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    overflow: hidden;
}

/* ── Header ─────────────────────────────── */
.header {
    background: linear-gradient(135deg, var(--primary) 0%, #1e40af 100%);
    color: white;
    padding: 40px 50px;
}

.header h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
}

.header .subtitle {
    font-size: 15px;
    opacity: 0.85;
    font-weight: 400;
}

.header .meta {
    margin-top: 20px;
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
    font-size: 13px;
    opacity: 0.8;
}

.header .meta span {
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ── Content ────────────────────────────── */
.content {
    padding: 40px 50px 50px;
}

/* ── TOC ────────────────────────────────── */
.toc {
    background: var(--primary-bg);
    border: 1px solid #bfdbfe;
    border-left: 4px solid var(--primary);
    border-radius: 8px;
    padding: 24px 30px;
    margin-bottom: 40px;
}

.toc h2 {
    font-size: 16px;
    color: var(--primary);
    margin-bottom: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.toc ol {
    padding-left: 20px;
}

.toc li {
    margin-bottom: 6px;
    font-size: 14px;
}

.toc li a {
    color: var(--primary);
    text-decoration: none;
    transition: color 0.2s;
}

.toc li a:hover {
    color: var(--primary-light);
    text-decoration: underline;
}

.toc ol ol {
    margin-top: 4px;
    margin-bottom: 4px;
}

.toc ol ol li {
    font-size: 13px;
    margin-bottom: 3px;
}

/* ── Sections ───────────────────────────── */
.section {
    margin-bottom: 36px;
}

h2 {
    font-size: 22px;
    color: var(--primary);
    border-bottom: 3px solid var(--primary);
    padding-bottom: 10px;
    margin-bottom: 20px;
    margin-top: 40px;
    font-weight: 700;
}

h3 {
    font-size: 18px;
    color: #1e40af;
    margin-top: 28px;
    margin-bottom: 14px;
    font-weight: 600;
    padding-left: 14px;
    border-left: 4px solid var(--primary-light);
}

h4 {
    font-size: 15px;
    color: #374151;
    margin-top: 20px;
    margin-bottom: 10px;
    font-weight: 600;
}

h5 {
    font-size: 14px;
    color: #4b5563;
    margin-top: 16px;
    margin-bottom: 8px;
    font-weight: 600;
}

p {
    margin-bottom: 14px;
}

/* ── Highlighted boxes ──────────────────── */
.info-box {
    background: var(--primary-bg);
    border-left: 4px solid var(--primary);
    border-radius: 6px;
    padding: 16px 20px;
    margin: 18px 0;
    font-size: 14px;
}

.info-box p:last-child { margin-bottom: 0; }

.warning-box {
    background: var(--warning-bg);
    border-left: 4px solid var(--warning-border);
    border-radius: 6px;
    padding: 16px 20px;
    margin: 18px 0;
    font-size: 14px;
    color: var(--warning-text);
}

.warning-box p:last-child { margin-bottom: 0; }

.success-box {
    background: var(--success-bg);
    border-left: 4px solid var(--success-border);
    border-radius: 6px;
    padding: 16px 20px;
    margin: 18px 0;
    font-size: 14px;
    color: var(--success-text);
}

.success-box p:last-child { margin-bottom: 0; }

.danger-box {
    background: #fef2f2;
    border-left: 4px solid #fca5a5;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 18px 0;
    font-size: 14px;
    color: #991b1b;
}

.danger-box p:last-child { margin-bottom: 0; }

/* ── Tables ─────────────────────────────── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 18px 0;
    font-size: 14px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

thead th {
    background: var(--primary);
    color: white;
    padding: 12px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
}

tbody td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
}

tbody tr:nth-child(even) {
    background: #f9fafb;
}

tbody tr:hover {
    background: var(--primary-bg);
}

/* ── Code blocks ────────────────────────── */
pre {
    background: var(--code-bg);
    color: var(--code-text);
    border-radius: 8px;
    padding: 18px 22px;
    margin: 16px 0;
    overflow-x: auto;
    font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
    font-size: 13px;
    line-height: 1.6;
    border: 1px solid #334155;
}

code {
    font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
    font-size: 13px;
}

p code, li code, td code {
    background: #f1f5f9;
    color: #0f172a;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 13px;
    border: 1px solid #e2e8f0;
}

/* ── Lists ──────────────────────────────── */
ul, ol {
    margin-bottom: 14px;
    padding-left: 24px;
}

li {
    margin-bottom: 6px;
}

li > ul, li > ol {
    margin-top: 4px;
    margin-bottom: 4px;
}

/* ── Horizontal rule ────────────────────── */
hr {
    border: none;
    border-top: 2px solid var(--border);
    margin: 30px 0;
}

/* ── Strong / Em ────────────────────────── */
strong {
    font-weight: 700;
    color: #111827;
}

/* ── Blockquote ─────────────────────────── */
blockquote {
    border-left: 4px solid var(--primary-light);
    background: var(--primary-bg);
    padding: 14px 20px;
    margin: 16px 0;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #374151;
}

blockquote p:last-child { margin-bottom: 0; }

/* ── ASCII diagrams ─────────────────────── */
.ascii-diagram {
    background: var(--white);
    border: 2px solid var(--primary);
    border-radius: 8px;
    padding: 20px 24px;
    margin: 18px 0;
    font-family: 'Cascadia Code', Consolas, monospace;
    font-size: 13px;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre;
    color: var(--primary);
}

/* ── Footer ─────────────────────────────── */
.footer {
    background: #f8fafc;
    border-top: 2px solid var(--border);
    padding: 24px 50px;
    font-size: 12px;
    color: var(--text-light);
    text-align: center;
}

.footer .footer-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    text-align: left;
    margin-bottom: 14px;
}

.footer strong {
    color: var(--primary);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Print ──────────────────────────────── */
@media print {
    body { background: white; }
    .container { box-shadow: none; margin: 0; border-radius: 0; }
    .header { padding: 20px 30px; }
    .content { padding: 20px 30px; }
    pre { font-size: 11px; }
    .toc { page-break-after: always; }
    h2 { page-break-before: always; }
    h2:first-of-type { page-break-before: avoid; }
    table { page-break-inside: avoid; }
}

@media (max-width: 768px) {
    .container { margin: 10px; }
    .header { padding: 24px 20px; }
    .content { padding: 20px 20px 30px; }
    .footer { padding: 16px 20px; }
    .header .meta { flex-direction: column; gap: 8px; }
    .footer .footer-grid { grid-template-columns: 1fr; }
    table { font-size: 12px; }
    thead th, tbody td { padding: 8px 10px; }
}
"""

# ─────────────────────────────────────────────
# Markdown → HTML Conversion
# ─────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert heading text to URL-friendly slug."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '-', text.strip())
    return text


def escape_html(text: str) -> str:
    """Escape HTML special characters (but preserve already-converted HTML)."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def process_inline(text: str) -> str:
    """Process inline markdown: bold, italic, code, links."""
    # Code (must be first to protect contents)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text


def detect_box_type(line: str):
    """Detect special box markers in markdown."""
    lower = line.strip().lower()
    if lower.startswith('> **nota'):
        return 'info-box'
    elif lower.startswith('> **advertencia') or lower.startswith('> **precauci'):
        return 'warning-box'
    elif lower.startswith('> **importante') or lower.startswith('> **peligro') or lower.startswith('> **critico') or lower.startswith('> **crítico'):
        return 'danger-box'
    elif lower.startswith('> **tip') or lower.startswith('> **éxito') or lower.startswith('> **exito') or lower.startswith('> **verificaci'):
        return 'success-box'
    return None


def parse_metadata(lines: list) -> dict:
    """Extract YAML-like metadata from document start."""
    meta = {}
    i = 0
    if lines and lines[0].strip() == '---':
        i = 1
        while i < len(lines) and lines[i].strip() != '---':
            match = re.match(r'^(\w[\w_-]*):\s*(.+)$', lines[i].strip())
            if match:
                meta[match.group(1).lower()] = match.group(2).strip()
            i += 1
        i += 1  # skip closing ---
    return meta, i


def convert_md_to_html(md_content: str, title: str = "", subtitle: str = "",
                        version: str = "1.0", date: str = None) -> str:
    """Convert Markdown content to styled HTML."""

    lines = md_content.split('\n')

    # Parse optional frontmatter
    meta, start_idx = parse_metadata(lines)
    title = meta.get('titulo', title) or title
    subtitle = meta.get('subtitulo', subtitle) or subtitle
    version = meta.get('version', version)
    date = meta.get('fecha', date) or date or datetime.now().strftime('%d/%m/%Y')
    audiencia = meta.get('audiencia', '')

    lines = lines[start_idx:]

    # ── Phase 1: Extract headings for TOC ──
    headings = []
    for line in lines:
        match = re.match(r'^(#{1,5})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            slug = slugify(text)
            headings.append((level, text, slug))

    # If first heading is H1 and no title set, use it
    if headings and headings[0][0] == 1 and not title:
        title = headings[0][1]

    # ── Phase 2: Build TOC HTML ──
    toc_html = '<div class="toc">\n<h2>Tabla de Contenidos</h2>\n'

    # Find the minimum heading level used (usually 2)
    h_levels = [h[0] for h in headings if h[0] >= 2]
    if h_levels:
        min_level = min(h_levels)
        current_depth = 0

        for level, text, slug in headings:
            if level < 2:
                continue
            depth = level - min_level

            while current_depth < depth:
                toc_html += '<ol>\n'
                current_depth += 1
            while current_depth > depth:
                toc_html += '</ol>\n'
                current_depth -= 1

            toc_html += f'<li><a href="#{slug}">{process_inline(text)}</a></li>\n'

        while current_depth > 0:
            toc_html += '</ol>\n'
            current_depth -= 1

    toc_html += '</div>\n'

    # ── Phase 3: Convert markdown body ──
    body_html = []
    i = 0
    in_code_block = False
    code_block_content = []
    in_table = False
    table_rows = []
    in_list = False
    list_type = None
    list_items = []
    list_depth = 0
    in_blockquote = False
    blockquote_lines = []

    def flush_list():
        nonlocal in_list, list_items, list_type, list_depth
        if not list_items:
            return
        html = build_list_html(list_items, list_type)
        body_html.append(html)
        list_items = []
        in_list = False
        list_type = None
        list_depth = 0

    def flush_blockquote():
        nonlocal in_blockquote, blockquote_lines
        if not blockquote_lines:
            return

        # Detect box type from first line
        box_type = detect_box_type('> ' + blockquote_lines[0]) if blockquote_lines else None
        css_class = box_type or 'info-box'

        content = '\n'.join(blockquote_lines)
        # Remove leading **Type:** pattern
        content = re.sub(r'^\*\*[^*]+\*\*:?\s*', '', content, count=1)

        inner_html = '<p>' + process_inline(content).replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
        body_html.append(f'<div class="{css_class}">{inner_html}</div>')

        blockquote_lines = []
        in_blockquote = False

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return

        html = '<table>\n<thead>\n<tr>'
        headers = table_rows[0]
        for h in headers:
            html += f'<th>{process_inline(h.strip())}</th>'
        html += '</tr>\n</thead>\n<tbody>\n'

        for row in table_rows[2:]:  # Skip separator row
            html += '<tr>'
            for cell in row:
                html += f'<td>{process_inline(cell.strip())}</td>'
            html += '</tr>\n'

        html += '</tbody>\n</table>\n'
        body_html.append(html)
        table_rows = []
        in_table = False

    def build_list_html(items, ltype):
        """Build nested list HTML from flat list of (depth, text) tuples."""
        tag = 'ol' if ltype == 'ol' else 'ul'
        html = f'<{tag}>\n'
        current_depth = 0

        for depth, text in items:
            while current_depth < depth:
                html += f'<{tag}>\n'
                current_depth += 1
            while current_depth > depth:
                html += f'</{tag}>\n'
                current_depth -= 1
            html += f'<li>{process_inline(text)}</li>\n'

        while current_depth > 0:
            html += f'</{tag}>\n'
            current_depth -= 1

        html += f'</{tag}>\n'
        return html

    while i < len(lines):
        line = lines[i]

        # ── Code blocks ──
        if line.strip().startswith('```'):
            if in_code_block:
                content = '\n'.join(code_block_content)
                content = escape_html(content)
                body_html.append(f'<pre><code>{content}</code></pre>')
                code_block_content = []
                in_code_block = False
            else:
                # Flush any open constructs
                flush_list()
                flush_blockquote()
                flush_table()
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_block_content.append(line)
            i += 1
            continue

        # ── Table rows ──
        if line.strip().startswith('|') and line.strip().endswith('|'):
            flush_list()
            flush_blockquote()
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not in_table:
                in_table = True
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            flush_table()

        # ── Blockquotes ──
        if line.startswith('> '):
            flush_list()
            flush_table()
            content = line[2:]
            if not in_blockquote:
                in_blockquote = True
            blockquote_lines.append(content)
            i += 1
            continue
        elif line.strip() == '>' :
            if in_blockquote:
                blockquote_lines.append('')
            i += 1
            continue
        elif in_blockquote:
            flush_blockquote()

        # ── Headings ──
        heading_match = re.match(r'^(#{1,5})\s+(.+)$', line)
        if heading_match:
            flush_list()
            flush_table()
            flush_blockquote()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            slug = slugify(text)
            body_html.append(f'<h{level} id="{slug}">{process_inline(text)}</h{level}>')
            i += 1
            continue

        # ── Horizontal rule ──
        if re.match(r'^-{3,}$|^\*{3,}$|^_{3,}$', line.strip()):
            flush_list()
            body_html.append('<hr>')
            i += 1
            continue

        # ── Lists ──
        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        ul_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)

        if ol_match or ul_match:
            flush_table()
            flush_blockquote()
            if ol_match:
                indent = len(ol_match.group(1))
                text = ol_match.group(2)
                current_type = 'ol'
            else:
                indent = len(ul_match.group(1))
                text = ul_match.group(2)
                current_type = 'ul'

            depth = indent // 2  # 2 spaces per indent level

            if not in_list:
                in_list = True
                list_type = current_type

            list_items.append((depth, text))
            i += 1
            continue
        elif in_list and line.strip() == '':
            # Blank line might end list or be between items
            # Check if next non-empty line is also a list item
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines):
                next_is_list = (re.match(r'^\s*\d+\.\s+', lines[j]) or
                                re.match(r'^\s*[-*]\s+', lines[j]))
                if not next_is_list:
                    flush_list()
            else:
                flush_list()
            i += 1
            continue
        elif in_list:
            flush_list()

        # ── Empty lines ──
        if line.strip() == '':
            i += 1
            continue

        # ── Paragraph ──
        para_lines = [line]
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            if (next_line.strip() == '' or
                next_line.startswith('#') or
                next_line.startswith('```') or
                next_line.startswith('> ') or
                next_line.startswith('| ') or
                re.match(r'^\s*\d+\.\s+', next_line) or
                re.match(r'^\s*[-*]\s+', next_line) or
                re.match(r'^-{3,}$', next_line.strip())):
                break
            para_lines.append(next_line)
            j += 1

        para_text = ' '.join(para_lines)
        body_html.append(f'<p>{process_inline(para_text)}</p>')
        i = j
        continue

    # Flush remaining
    flush_list()
    flush_table()
    flush_blockquote()
    if in_code_block and code_block_content:
        content = escape_html('\n'.join(code_block_content))
        body_html.append(f'<pre><code>{content}</code></pre>')

    # ── Phase 4: Assemble HTML ──
    meta_items = []
    if version:
        meta_items.append(f'<span>Version {version}</span>')
    if date:
        meta_items.append(f'<span>{date}</span>')
    if audiencia:
        meta_items.append(f'<span>Audiencia: {audiencia}</span>')
    meta_html = '\n'.join(meta_items)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{CSS_STYLES}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">{subtitle}</div>
            <div class="meta">
                {meta_html}
            </div>
        </div>

        <div class="content">
            {toc_html}
            {''.join(body_html)}
        </div>

        <div class="footer">
            <div class="footer-grid">
                <div>
                    <strong>Proyecto</strong><br>
                    WSR Generator DyM v3.0
                </div>
                <div>
                    <strong>Empresa</strong><br>
                    DyM &mdash; Grupo SAIV
                </div>
                <div>
                    <strong>Desarrollado por</strong><br>
                    Fabiola Bowles
                </div>
            </div>
            <div>Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} &mdash; Confidencial</div>
        </div>
    </div>
</body>
</html>"""

    return html


# ─────────────────────────────────────────────
# Main: Convert manual files
# ─────────────────────────────────────────────

MANUALS = [
    {
        'md_path': '01_manual_de_uso/MANUAL_DE_USO.md',
        'html_path': '01_manual_de_uso/MANUAL_DE_USO.html',
        'title': 'Manual de Uso',
        'subtitle': 'WSR Generator DyM — Guia completa para ejecutar el sistema e interpretar el reporte'
    },
    {
        'md_path': '02_manual_de_instalacion/MANUAL_DE_INSTALACION.md',
        'html_path': '02_manual_de_instalacion/MANUAL_DE_INSTALACION.html',
        'title': 'Manual de Instalacion',
        'subtitle': 'WSR Generator DyM — Instalacion, configuracion y puesta en marcha del sistema'
    },
    {
        'md_path': '03_manual_de_mantenimiento/MANUAL_DE_MANTENIMIENTO.md',
        'html_path': '03_manual_de_mantenimiento/MANUAL_DE_MANTENIMIENTO.html',
        'title': 'Manual de Mantenimiento',
        'subtitle': 'WSR Generator DyM — Arquitectura, diagnostico, actualizaciones y soporte'
    },
]

def main():
    script_dir = Path(__file__).parent

    if len(sys.argv) > 1:
        # Convert specific file
        md_file = Path(sys.argv[1])
        if not md_file.exists():
            print(f"Error: {md_file} no existe")
            sys.exit(1)

        md_content = md_file.read_text(encoding='utf-8')
        html_content = convert_md_to_html(md_content, title=md_file.stem)

        html_file = md_file.with_suffix('.html')
        html_file.write_text(html_content, encoding='utf-8')
        print(f"Convertido: {md_file} -> {html_file}")
        return

    # Convert all 3 manuals
    converted = 0
    for manual in MANUALS:
        md_path = script_dir / manual['md_path']
        html_path = script_dir / manual['html_path']

        if not md_path.exists():
            print(f"  Saltando (no existe): {md_path}")
            continue

        md_content = md_path.read_text(encoding='utf-8')
        html_content = convert_md_to_html(
            md_content,
            title=manual['title'],
            subtitle=manual['subtitle'],
            version='3.0'
        )

        html_path.write_text(html_content, encoding='utf-8')
        converted += 1
        print(f"  Convertido: {manual['md_path']} -> {manual['html_path']}")

    print(f"\n{converted} manual(es) convertido(s).")


if __name__ == '__main__':
    main()
