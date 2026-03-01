#!/usr/bin/env python3
"""
THE DAILY BYTE - Sender
Envia o digest via Buttondown API
v2.4: Template HTML dedicado, mobile-first
"""

import os
import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional

# v2.3: Dedup — registra itens enviados no cache
try:
    from dedup import load_cache, save_cache, register_sent
except ImportError:
    load_cache = None
    save_cache = None
    register_sent = None

# ============================================
# CONFIGURAÇÃO
# ============================================

BUTTONDOWN_API_KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
BUTTONDOWN_API_URL = "https://api.buttondown.email/v1/emails"

# ============================================
# v2.4: HTML EMAIL TEMPLATE
# ============================================
# Mobile-first, inline CSS, table-based layout
# Max-width 600px, 16px+ body text, 44px+ tap targets
# Color palette:
#   Brand orange:  #FF6B35
#   Dark bg:       #1a1a2e
#   Card bg:       #ffffff
#   Light bg:      #f4f4f8
#   Body text:     #2d2d2d
#   Muted text:    #6b7280
#   Link blue:     #2563eb
#   Section colors per category

COLORS = {
    "brand": "#FF6B35",
    "dark": "#1a1a2e",
    "card": "#ffffff",
    "bg": "#f4f4f8",
    "text": "#2d2d2d",
    "muted": "#6b7280",
    "link": "#2563eb",
    "number": "#7c3aed",      # purple for numero do dia
    "world": "#0ea5e9",       # sky blue for mundo real
    "byte": "#FF6B35",        # orange for hoje no byte
    "saas": "#10b981",        # green for saas
    "tool": "#f59e0b",        # amber for tool do dia
    "analysis": "#8b5cf6",    # violet for analise
    "quick": "#64748b",       # slate for quick links
    "video": "#ef4444",       # red for watch later
}


def _esc(text: str) -> str:
    """Escape HTML entities"""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _heat_bar(score: int) -> str:
    """Visual heat score indicator"""
    if score >= 80:
        return '<span style="color:#ef4444;font-weight:bold;">&#x1F525;&#x1F525;&#x1F525;</span>'
    elif score >= 70:
        return '<span style="color:#f97316;font-weight:bold;">&#x1F525;&#x1F525;</span>'
    return '<span style="color:#f59e0b;">&#x1F525;</span>'


def _section_header(emoji: str, title: str, color: str) -> str:
    """Generates a section header row"""
    return f'''<tr>
  <td style="padding:0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="background-color:{color};padding:12px 20px;border-radius:8px 8px 0 0;">
          <span style="font-size:20px;line-height:1;">{emoji}</span>
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;font-weight:700;color:#ffffff;letter-spacing:0.5px;text-transform:uppercase;vertical-align:middle;padding-left:6px;">{_esc(title)}</span>
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _card_start() -> str:
    return '''<tr>
  <td style="background-color:#ffffff;padding:16px 20px;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;">'''


def _card_end() -> str:
    return '''  </td>
</tr>'''


def _card_bottom() -> str:
    return '''<tr>
  <td style="background-color:#ffffff;padding:0 20px 12px 20px;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;border-radius:0 0 8px 8px;">
  </td>
</tr>'''


def _spacer(height: int = 20) -> str:
    return f'<tr><td style="padding:0;height:{height}px;line-height:{height}px;font-size:1px;">&nbsp;</td></tr>'


def _render_item_html(item: Dict) -> str:
    """Renders a single news item as HTML table row content"""
    headline = _esc(item.get('headline', 'Sem título'))
    tag = item.get('tag', '')
    why = _esc(item.get('why_it_matters', ''))
    url = item.get('source_url', '#')
    source = _esc(item.get('source_name', 'Fonte'))
    hours = item.get('hours_ago', '?')
    heat = item.get('heat_score', 0)

    tag_html = f'<span style="display:inline-block;background-color:#FF6B35;color:#ffffff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:6px;vertical-align:middle;text-transform:uppercase;">{_esc(tag)}</span>' if tag else ''
    heat_html = _heat_bar(heat)

    return f'''<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;border-bottom:1px solid #f0f0f0;padding-bottom:14px;">
  <tr>
    <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:17px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:6px;">
      {tag_html}{headline} {heat_html}
    </td>
  </tr>
  <tr>
    <td style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.55;padding-bottom:8px;">
      {why}
    </td>
  </tr>
  <tr>
    <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#6b7280;line-height:1.4;">
      <a href="{url}" style="color:#2563eb;text-decoration:none;font-weight:600;">Ver original &#x2197;</a>
      &nbsp;&middot;&nbsp; {source} &nbsp;&middot;&nbsp; &#x23F0; {hours}h
    </td>
  </tr>
</table>'''


def generate_email_html(curated: Dict) -> str:
    """Gera o conteúdo HTML do email — Template v2.4 mobile-first"""

    body_rows = []

    # ── HEADER ──────────────────────────────────
    body_rows.append(f'''<tr>
  <td style="background-color:{COLORS["dark"]};padding:24px 20px;text-align:center;border-radius:8px 8px 0 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="text-align:center;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:28px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">&#x1F525; THE DAILY BYTE</span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;padding-top:6px;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#94a3b8;letter-spacing:1px;text-transform:uppercase;">News, insights &amp; trends para C-levels</span>
        </td>
      </tr>
    </table>
  </td>
</tr>''')

    # Date subheader
    today = datetime.now()
    weekdays = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    months = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    date_str = f"{weekdays[today.weekday()]}, {today.day} de {months[today.month]} de {today.year}"

    body_rows.append(f'''<tr>
  <td style="background-color:{COLORS["dark"]};padding:0 20px 16px 20px;text-align:center;border-radius:0 0 8px 8px;">
    <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#94a3b8;">{date_str}</span>
  </td>
</tr>''')

    body_rows.append(_spacer(16))

    # ── 0. NÚMERO DO DIA ────────────────────────
    number = curated.get('number_of_day', {})
    if number and number.get('value'):
        body_rows.append(_section_header('&#x1F4CA;', 'NÚMERO DO DIA', COLORS["number"]))
        body_rows.append(f'''{_card_start()}
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="text-align:center;padding:12px 0;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:36px;font-weight:800;color:{COLORS["number"]};line-height:1.2;">{_esc(str(number.get('value', '')))}</span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;padding-bottom:8px;">
          <span style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.5;">{_esc(number.get('context', ''))}</span>
        </td>
      </tr>
    </table>
{_card_end()}''')
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 1. MUNDO REAL ───────────────────────────
    world_items = curated.get('world', [])
    if world_items:
        body_rows.append(_section_header('&#x1F30D;', 'MUNDO REAL', COLORS["world"]))
        body_rows.append(_card_start())
        for i, wi in enumerate(world_items):
            headline = _esc(wi.get('headline', ''))
            context = _esc(wi.get('context', ''))
            url = wi.get('source_url', '#')
            source = _esc(wi.get('source_name', ''))
            border = 'border-bottom:1px solid #f0f0f0;margin-bottom:12px;padding-bottom:12px;' if i < len(world_items) - 1 else ''
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="{border}">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:4px;">
          &#x2192; {headline}
        </td>
      </tr>
      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:14px;color:#2d2d2d;line-height:1.5;padding-bottom:4px;">
          {context}
        </td>
      </tr>
      <tr>
        <td style="font-size:12px;color:#6b7280;">
          <a href="{url}" style="color:#2563eb;text-decoration:none;">{source} &#x2197;</a>
        </td>
      </tr>
    </table>''')
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 2. HOJE NO BYTE ─────────────────────────
    items = curated.get('items', [])
    hoje = [i for i in items if i.get('category') == 'hoje_no_byte']
    if not hoje:
        hoje = [i for i in items if i.get('category') in ('breaking', 'ai_models', 'big_tech')]
    if hoje:
        body_rows.append(_section_header('&#x1F525;', 'HOJE NO BYTE', COLORS["byte"]))
        body_rows.append(_card_start())
        for item in hoje:
            body_rows.append(_render_item_html(item))
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 3. SaaS & ENTERPRISE ────────────────────
    saas = [i for i in items if i.get('category') == 'saas_enterprise']
    if saas:
        body_rows.append(_section_header('&#x1F4B0;', 'SaaS &amp; ENTERPRISE', COLORS["saas"]))
        body_rows.append(_card_start())
        for item in saas:
            body_rows.append(_render_item_html(item))
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 4. TOOL DO DIA ──────────────────────────
    tool = curated.get('tool_of_day', {})
    if not tool:
        tool_items = [i for i in items if i.get('category') == 'tool_of_day']
        if tool_items:
            tool = tool_items[0]

    if tool and tool.get('headline'):
        body_rows.append(_section_header('&#x1F6E0;', 'TOOL DO DIA', COLORS["tool"]))
        tool_headline = _esc(tool.get('headline', ''))
        tool_why = _esc(tool.get('why_it_matters', ''))
        tool_url = tool.get('source_url', '#')
        tool_source = _esc(tool.get('source_name', ''))
        how_to = _esc(tool.get('how_to_use', ''))
        prompt = _esc(tool.get('prompt_of_day', ''))

        body_rows.append(f'''{_card_start()}
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:18px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:8px;">
          {tool_headline}
        </td>
      </tr>
      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.55;padding-bottom:10px;">
          {tool_why}
        </td>
      </tr>
      <tr>
        <td style="padding-bottom:12px;">
          <a href="{tool_url}" style="display:inline-block;background-color:{COLORS["tool"]};color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;padding:10px 24px;border-radius:6px;text-decoration:none;">&#x1F680; Experimentar</a>
          <span style="font-size:13px;color:#6b7280;padding-left:8px;">{tool_source}</span>
        </td>
      </tr>
    </table>''')

        if how_to:
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #e5e7eb;padding-top:12px;margin-top:4px;">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;color:{COLORS["tool"]};text-transform:uppercase;letter-spacing:0.5px;padding-bottom:6px;">
          &#x1F4A1; COMO USAR HOJE
        </td>
      </tr>
      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.55;">
          {how_to}
        </td>
      </tr>
    </table>''')

        if prompt:
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #e5e7eb;padding-top:12px;margin-top:12px;">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;color:{COLORS["analysis"]};text-transform:uppercase;letter-spacing:0.5px;padding-bottom:6px;">
          &#x1F9E0; PROMPT DO DIA <span style="font-weight:400;font-style:italic;text-transform:none;letter-spacing:0;">(copy-paste ready)</span>
        </td>
      </tr>
      <tr>
        <td>
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="background-color:#f8f4ff;border-left:4px solid {COLORS["analysis"]};padding:12px 16px;font-family:'Courier New',monospace;font-size:14px;color:#1a1a2e;line-height:1.5;border-radius:0 6px 6px 0;">
                {prompt}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>''')

        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 5. ANÁLISE DO DIA ───────────────────────
    analysis = curated.get('daily_analysis', '')
    if analysis:
        body_rows.append(_section_header('&#x1F52E;', 'ANÁLISE DO DIA', COLORS["analysis"]))
        body_rows.append(_card_start())

        if isinstance(analysis, list):
            for a_item in analysis:
                a_item = re.sub(r'^#{1,6}\s*', '', a_item.strip())
                a_item = re.sub(r'^[•\-\*]\s*', '', a_item.strip())
                # Extract bold title if format is "**Title** — Text"
                bold_match = re.match(r'\*\*(.+?)\*\*\s*[—–\-]\s*(.*)', a_item)
                if bold_match:
                    a_title = _esc(bold_match.group(1))
                    a_text = _esc(bold_match.group(2))
                    body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:12px;">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:15px;line-height:1.55;color:#2d2d2d;">
          <span style="font-weight:700;color:{COLORS["analysis"]};">&#x25CF;</span>
          <span style="font-weight:700;">{a_title}</span> &#x2014; {a_text}
        </td>
      </tr>
    </table>''')
                else:
                    body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:12px;">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:15px;line-height:1.55;color:#2d2d2d;">
          <span style="font-weight:700;color:{COLORS["analysis"]};">&#x25CF;</span> {_esc(a_item)}
        </td>
      </tr>
    </table>''')
        else:
            body_rows.append(f'''    <p style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.55;">{_esc(str(analysis))}</p>''')

        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 6. QUICK LINKS ──────────────────────────
    quick_links = curated.get('quick_links', [])
    if quick_links:
        body_rows.append(_section_header('&#x26A1;', 'QUICK LINKS', COLORS["quick"]))
        body_rows.append(_card_start())
        for i, ql in enumerate(quick_links):
            headline = _esc(ql.get('headline', ''))
            url = ql.get('source_url', '#')
            source = _esc(ql.get('source_name', ''))
            border = 'border-bottom:1px solid #f0f0f0;' if i < len(quick_links) - 1 else ''
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="{border}padding:8px 0;">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;line-height:1.4;">
          &#x2192; <a href="{url}" style="color:#2563eb;text-decoration:none;font-weight:600;">{headline}</a>
          <span style="color:#6b7280;font-size:12px;"> ({source})</span>
        </td>
      </tr>
    </table>''')
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── WATCH LATER ─────────────────────────────
    videos = [i for i in items if i.get('category') == 'watch_later']
    if videos:
        body_rows.append(_section_header('&#x1F4FA;', 'WATCH LATER', COLORS["video"]))
        body_rows.append(_card_start())
        for vid in videos:
            title = _esc(vid.get('headline', 'Vídeo'))
            url = vid.get('source_url', '#')
            source = _esc(vid.get('source_name', 'Canal'))
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;font-weight:700;color:#1a1a2e;padding-bottom:4px;">
          &#x1F3AC; {title}
        </td>
      </tr>
      <tr>
        <td style="font-size:13px;color:#6b7280;padding-bottom:8px;">
          {source}
        </td>
      </tr>
      <tr>
        <td>
          <a href="{url}" style="display:inline-block;background-color:{COLORS["video"]};color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;padding:10px 24px;border-radius:6px;text-decoration:none;">&#x25B6;&#xFE0F; Assistir</a>
        </td>
      </tr>
    </table>''')
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── FOOTER ──────────────────────────────────
    body_rows.append(f'''<tr>
  <td style="background-color:{COLORS["dark"]};padding:24px 20px;text-align:center;border-radius:8px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="text-align:center;padding-bottom:8px;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#94a3b8;font-style:italic;">Curated by Tot&oacute; Busnello AI</span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;padding-bottom:12px;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#94a3b8;">
            &#x270D;&#xFE0F; <span style="color:#94a3b8;">Artigos sobre tech, AI e neg&oacute;cios</span>
          </span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;">
          <a href="https://www.linkedin.com/in/luiz-antonio-busnello/" style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;color:#64748b;text-decoration:none;">LinkedIn &#x2197;</a>
        </td>
      </tr>
    </table>
  </td>
</tr>''')

    # ── WRAP IN FULL HTML DOCUMENT ──────────────
    rows_html = "\n".join(body_rows)

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>The Daily Byte</title>
<!--[if mso]>
<style>table,td {{font-family:Arial,sans-serif !important;}}</style>
<![endif]-->
<style type="text/css">
@media only screen and (max-width: 620px) {{
  .email-container {{
    width: 100% !important;
    max-width: 100% !important;
  }}
  .mobile-padding {{
    padding-left: 12px !important;
    padding-right: 12px !important;
  }}
}}
body {{
  margin: 0;
  padding: 0;
  background-color: {COLORS["bg"]};
  -webkit-text-size-adjust: 100%;
  -ms-text-size-adjust: 100%;
}}
a {{
  color: {COLORS["link"]};
}}
</style>
</head>
<body style="margin:0;padding:0;background-color:{COLORS["bg"]};-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{COLORS["bg"]};">
  <tr>
    <td align="center" style="padding:16px 8px;" class="mobile-padding">
      <table role="presentation" class="email-container" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;margin:0 auto;">
        {rows_html}
      </table>
    </td>
  </tr>
</table>

</body>
</html>'''

    return html


# ============================================
# LEGACY MARKDOWN FORMAT (kept for --preview)
# ============================================

EMAIL_FOOTER = """

***

*Curated by Totó Busnello AI*

✍️ **Quer ir mais fundo?** Leia meus artigos sobre tech, AI e negócios no [LinkedIn](https://www.linkedin.com/in/luiz-antonio-busnello/)

*[Gerenciar assinatura]({{ unsubscribe_url }})*
"""


def format_item(item: Dict) -> str:
    """Formata um item principal com tag para o email (markdown legacy)"""
    headline = item.get('headline', 'Sem título')
    tag = item.get('tag', '')
    why = item.get('why_it_matters', '')
    url = item.get('source_url', '#')
    source = item.get('source_name', 'Fonte')
    hours = item.get('hours_ago', '?')
    heat = item.get('heat_score', 0)

    heat_emoji = "🔥🔥🔥" if heat >= 80 else "🔥🔥" if heat >= 70 else "🔥"
    tag_str = f"[{tag}] " if tag else ""

    return f"""{tag_str}**{headline}** {heat_emoji}

{why}

🔗 [Ver original]({url}) | 📍 {source} | ⏰ Há {hours}h

"""


def format_video(item: Dict) -> str:
    """Formata um vídeo para o email (markdown legacy)"""
    title = item.get('headline', 'Vídeo')
    url = item.get('source_url', '#')
    source = item.get('source_name', 'Canal')

    return f"""🎬 **{title}**
*{source}*
▶️ [Assistir]({url})

"""


def generate_email_content(curated: Dict) -> str:
    """Gera o conteúdo do email em markdown — Layout consolidado v2.2 (legacy)"""

    sections = []

    number = curated.get('number_of_day', {})
    if number and number.get('value'):
        sections.append(f"# 📊 NÚMERO DO DIA\n\n**{number.get('value', '')}** — {number.get('context', '')}")

    world_items = curated.get('world', [])
    if world_items:
        world_lines = []
        for wi in world_items:
            headline = wi.get('headline', '')
            context = wi.get('context', '')
            url = wi.get('source_url', '#')
            source = wi.get('source_name', '')
            world_lines.append(f"→ **{headline}** — {context} ([{source}]({url}))")
        sections.append(f"# 🌍 MUNDO REAL\n\n" + "\n\n".join(world_lines))

    items = curated.get('items', [])
    hoje = [i for i in items if i.get('category') == 'hoje_no_byte']
    if not hoje:
        hoje = [i for i in items if i.get('category') in ('breaking', 'ai_models', 'big_tech')]
    if hoje:
        sections.append("# 🔥 HOJE NO BYTE\n\n" + "\n".join([format_item(i) for i in hoje]))

    saas = [i for i in items if i.get('category') == 'saas_enterprise']
    if saas:
        sections.append("# 💰 SaaS & ENTERPRISE\n\n" + "\n".join([format_item(i) for i in saas]))

    tool = curated.get('tool_of_day', {})
    if not tool:
        tool_items = [i for i in items if i.get('category') == 'tool_of_day']
        if tool_items:
            tool = tool_items[0]

    if tool and tool.get('headline'):
        how_to = tool.get('how_to_use', '')
        prompt = tool.get('prompt_of_day', '')
        tool_text = f"**{tool.get('headline', '')}**\n\n{tool.get('why_it_matters', '')}\n\n🔗 [Experimentar]({tool.get('source_url', '#')}) | 📍 {tool.get('source_name', '')}"
        if how_to:
            tool_text += f"\n\n---\n\n💡 **COMO USAR HOJE**\n\n{how_to}"
        if prompt:
            tool_text += f"\n\n---\n\n🧠 **PROMPT DO DIA** *(copy-paste ready)*\n\n> {prompt}"
        sections.append(f"# 🛠️ TOOL DO DIA\n\n{tool_text}")

    analysis = curated.get('daily_analysis', '')
    if analysis:
        if isinstance(analysis, list):
            sanitized = []
            for a_item in analysis:
                a_item = re.sub(r'^#{1,6}\s*', '', a_item.strip())
                a_item = re.sub(r'^[•\-\*]\s*', '', a_item.strip())
                sanitized.append(f"• {a_item}")
            analysis_text = "\n\n".join(sanitized)
        else:
            analysis_text = analysis
        sections.append(f"# 🔮 ANÁLISE DO DIA\n\n{analysis_text}")

    quick_links = curated.get('quick_links', [])
    if quick_links:
        ql_lines = []
        for ql in quick_links:
            headline = ql.get('headline', '')
            url = ql.get('source_url', '#')
            source = ql.get('source_name', '')
            ql_lines.append(f"→ [{headline}]({url}) *({source})*")
        sections.append(f"# ⚡ QUICK LINKS\n\n" + "\n\n".join(ql_lines))

    videos = [i for i in items if i.get('category') == 'watch_later']
    if videos:
        sections.append("# 📺 WATCH LATER\n\n" + "\n".join([format_video(i) for i in videos]))

    return "\n\n***\n\n".join(sections) + EMAIL_FOOTER


def send_via_buttondown(subject: str, content: str, draft: bool = False) -> Dict:
    """Envia email via Buttondown API"""

    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "subject": subject,
        "body": content,
        "status": "draft" if draft else "about_to_send"
    }

    print(f"📤 Enviando via Buttondown (draft={draft})...")

    response = requests.post(
        BUTTONDOWN_API_URL,
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Email {'salvo como rascunho' if draft else 'enviado'}!")
        print(f"   ID: {result.get('id', '?')}")
        return {"success": True, "data": result}
    else:
        print(f"❌ Erro: {response.status_code}")
        print(f"   {response.text}")
        raise RuntimeError(f"Buttondown API error: {response.status_code}")


def load_curated(path: str = "/tmp/digest_curated.json") -> Dict:
    """Carrega dados curados"""
    with open(path, 'r') as f:
        return json.load(f)


# ============================================
# MAIN
# ============================================

def send(preview: bool = False):
    """Pipeline de envio"""
    print("🔥 THE DAILY BYTE - Preparando envio...")

    # Load curated data
    curated = load_curated()

    if 'error' in curated:
        print(f"❌ Erro nos dados curados: {curated['error']}")
        raise RuntimeError(f"Dados curados contêm erro: {curated['error']}")

    # Generate subject
    today = datetime.now()
    weekdays_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    months_pt = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    # Dynamic subject with hook from curated data
    hook = curated.get('subject_hook', '')
    date_str = f"{weekdays_pt[today.weekday()]}, {today.day} de {months_pt[today.month]}"
    if hook:
        subject = f"{hook} | Daily Byte - {date_str}"
    else:
        subject = f"🔥 Daily Byte - {date_str}"

    # Generate content — HTML for sending, markdown for terminal preview
    html_content = generate_email_html(curated)
    md_content = generate_email_content(curated)

    if preview:
        print("\n" + "="*50)
        print("📧 PREVIEW DO EMAIL")
        print("="*50)
        print(f"Subject: {subject}")
        print("-"*50)
        print(md_content)
        print("="*50)

        # Save markdown preview
        preview_path = "/tmp/digest_preview.md"
        with open(preview_path, 'w') as f:
            f.write(f"# {subject}\n\n{md_content}")
        print(f"💾 Preview MD salvo em {preview_path}")

        # Save HTML preview
        html_preview_path = "/tmp/digest_preview.html"
        with open(html_preview_path, 'w') as f:
            f.write(html_content)
        print(f"💾 Preview HTML salvo em {html_preview_path}")

        return {"preview": True, "subject": subject, "content": md_content, "html": html_content}

    # Send HTML version
    result = send_via_buttondown(subject, html_content)

    # v2.3: Registra itens enviados no cache para dedup
    if result.get('success') and register_sent and load_cache and save_cache:
        try:
            cache = load_cache()
            cache = register_sent(curated, cache)
            save_cache(cache)
        except Exception as e:
            print(f"⚠️ Erro ao salvar cache de dedup: {e}")

    return result


if __name__ == "__main__":
    import sys

    preview_mode = "--preview" in sys.argv or "-p" in sys.argv

    send(preview=preview_mode)
