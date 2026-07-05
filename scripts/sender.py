#!/usr/bin/env python3
"""
THE DAILY BYTE - Sender
Envia o digest via Buttondown API
v2.4: Template HTML dedicado, mobile-first
"""

import os
import json
import math
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
#   Light bg:      #faf8f5
#   Body text:     #2d2d2d
#   Muted text:    #6b7280
#   Link blue:     #2563eb
#   Section colors per category

COLORS = {
    "brand": "#FF6B35",
    "dark": "#1a1a2e",
    "card": "#ffffff",
    "bg": "#faf8f5",
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
    "brasil": "#16a34a",      # green for radar brasil
    "deep_dive": "#1e40af",   # deep blue for deep dive
}


def _esc(text: str) -> str:
    """Escape HTML entities"""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── Byte Score (v2.13) — classificador de impacto estratégico ──
# (limite_inferior, label, emoji, cor_fundo, cor_texto)
BYTE_TIERS = [
    (9, "GIGABYTE", "📦", "#FF6B35", "#ffffff"),
    (7, "MEGABYTE", "💿", "#F7A072", "#1a1a2e"),
    (5, "KILOBYTE", "💾", "#6B7280", "#ffffff"),
    (0, "byte",     "📄", "#E5E7EB", "#6B7280"),
]

def _byte_tier(score):
    """Deriva (label, emoji, bg, fg, s_norm) de um Byte Score inteiro 0-10. None se ausente/inválido.

    Normaliza ANTES de derivar o tier: arredonda + clamp a [0, 10].
    O valor normalizado s_norm (índice 4) é inteiro e usado para exibição.
    """
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if math.isnan(s) or s < 0:
        return None
    s = max(0, min(10, int(round(s))))
    for lower, label, emoji, bg, fg in BYTE_TIERS:
        if s >= lower:
            return (label, emoji, bg, fg, s)
    return (*BYTE_TIERS[-1][1:], s)

# VU meter — alturas e cores por posição (verde → laranja)
_VU_HEIGHTS = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
_VU_COLORS = [
    '#10b981', '#10b981', '#10b981', '#10b981',  # verde (1-4)
    '#84cc16', '#eab308',                         # verde-limão + amarelo (5-6)
    '#f59e0b', '#f97316',                         # âmbar + laranja (7-8)
    '#FF6B35', '#FF6B35',                         # laranja brand (9-10)
]
_VU_EMPTY = '#e5e7eb'

def _byte_led_html(score):
    """LED bar HTML: 10 barras verticais crescendo em altura (VU meter). '' se ausente."""
    tier = _byte_tier(score)
    if tier is None:
        return ""
    _, _, _, _, s = tier
    filled = int(round(s))
    cells = []
    for i in range(10):
        color = _VU_COLORS[i] if i < filled else _VU_EMPTY
        cells.append(
            f'<span style="display:inline-block;width:6px;height:{_VU_HEIGHTS[i]}px;'
            f'background-color:{color};margin-right:2px;border-radius:1px;'
            f'vertical-align:bottom;"></span>'
        )
    peak_color = _VU_COLORS[filled - 1] if filled > 0 else '#9ca3af'
    return (
        '<span style="display:inline-block;white-space:nowrap;line-height:24px;height:24px;vertical-align:middle;">'
        + "".join(cells)
        + f'<span style="font-size:11px;font-weight:700;color:{peak_color};margin-left:6px;vertical-align:bottom;">{s}</span>'
        + '</span>'
    )

def _byte_led_md(score):
    """LED bar markdown: barra VU meter '▂▂▃▃▄▄▅▆▇█ 9.2'. '' se ausente."""
    tier = _byte_tier(score)
    if tier is None:
        return ""
    _, _, _, _, s = tier
    filled = int(round(s))
    heights = ['▂', '▂', '▃', '▃', '▄', '▄', '▅', '▆', '▇', '█']
    bar = "".join(heights[i] if i < filled else '░' for i in range(10))
    return f"{bar} {s}"


_section_counter = 0

def _section_header(emoji: str, title: str, color: str, numbered: bool = True) -> str:
    """Generates a section header row — v2.12 pill badge + numbered circle"""
    global _section_counter
    num_html = ""
    if numbered:
        _section_counter += 1
        num_html = f'<span style="display:inline-block;width:22px;height:22px;background-color:#ffffff;color:{color};border-radius:50%;font-size:11px;font-weight:800;text-align:center;line-height:22px;margin-right:8px;border:2px solid {color};">{_section_counter}</span>'
    return f'''<tr>
  <td style="padding:0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td class="card-bg card-border" style="background-color:#ffffff;padding:16px 20px 10px 20px;border:1px solid #e5e7eb;border-bottom:none;border-radius:12px 12px 0 0;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
          {num_html}<span style="display:inline-block;background-color:{color};color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;font-weight:700;padding:5px 14px;border-radius:20px;letter-spacing:0.5px;text-transform:uppercase;vertical-align:middle;">{emoji}&nbsp; {_esc(title)}</span>
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _render_big_story_html(item: Dict) -> str:
    """Renderiza item de destaque no topo — card grande com borda laranja."""
    headline = _esc(item.get('headline', ''))
    why = _esc(item.get('why_it_matters', ''))
    url = item.get('source_url', '#')
    source = _esc(item.get('source_name', ''))
    hours = item.get('hours_ago', '?')
    led = _byte_led_html(item.get('byte_score'))
    led_footer = f'<div style="padding-top:10px;">{led}</div>' if led else ''
    return f'''<tr>
  <td style="background-color:#fff8f2;border:2px solid {COLORS["brand"]};border-radius:12px;padding:20px 22px;box-shadow:0 4px 12px rgba(255,107,53,0.15);">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="padding-bottom:8px;">
          <span style="display:inline-block;background-color:{COLORS["brand"]};color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;font-size:10px;font-weight:800;padding:4px 12px;border-radius:20px;letter-spacing:1px;text-transform:uppercase;">&#x2605; BIG STORY</span>
        </td>
      </tr>
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:22px;font-weight:800;color:#1a1a2e;line-height:1.25;padding-bottom:10px;">
          {headline}
        </td>
      </tr>
      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:16px;color:#2d2d2d;line-height:1.55;padding-bottom:12px;">
          {why}
        </td>
      </tr>
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#6b7280;">
          <a href="{url}" style="display:inline-block;color:#ffffff;background-color:{COLORS["brand"]};text-decoration:none;font-weight:700;padding:8px 18px;border-radius:20px;font-size:13px;">Ler agora &#x2197;</a>
          &nbsp;&middot;&nbsp; {source} &nbsp;&middot;&nbsp; &#x23F0; {hours}h
          {led_footer}
        </td>
      </tr>
    </table>
  </td>
</tr>'''


def _estimate_reading_time(curated: Dict) -> int:
    """Estima tempo de leitura em minutos baseado no total de palavras do digest.
    Usa 220 wpm (leitura casual em mobile). Mínimo 2 minutos."""
    text_parts = []

    n = curated.get('number_of_day', {}) or {}
    text_parts.append(str(n.get('context', '')))

    for wi in curated.get('world', []) or []:
        text_parts.append(str(wi.get('headline', '')))
        text_parts.append(str(wi.get('context', '')))

    for item in curated.get('items', []) or []:
        text_parts.append(str(item.get('headline', '')))
        text_parts.append(str(item.get('why_it_matters', '')))

    for rb in curated.get('radar_brasil', []) or []:
        text_parts.append(str(rb.get('headline', '')))
        text_parts.append(str(rb.get('why_it_matters', '')))

    tool = curated.get('tool_of_day', {}) or {}
    text_parts.append(str(tool.get('headline', '')))
    text_parts.append(str(tool.get('why_it_matters', '')))
    text_parts.append(str(tool.get('how_to_use', '')))
    text_parts.append(str(tool.get('prompt_of_day', '')))

    analysis = curated.get('daily_analysis', '')
    if isinstance(analysis, list):
        text_parts.extend(str(a) for a in analysis)
    else:
        text_parts.append(str(analysis))

    dd = curated.get('deep_dive', {}) or {}
    text_parts.append(str(dd.get('title', '')))
    text_parts.append(str(dd.get('body', '')))

    workflow = curated.get('weekly_workflow', {}) or {}
    text_parts.append(str(workflow.get('title', '')))
    text_parts.extend(str(s) for s in workflow.get('steps', []) or [])

    for ql in curated.get('quick_links', []) or []:
        text_parts.append(str(ql.get('headline', '')))

    total_words = sum(len(t.split()) for t in text_parts if t)
    minutes = max(2, round(total_words / 220))
    return minutes


def _card_start() -> str:
    return '''<tr>
  <td class="card-bg card-border" style="background-color:#ffffff;padding:16px 20px;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'''


def _card_end() -> str:
    return '''  </td>
</tr>'''


def _card_bottom() -> str:
    return '''<tr>
  <td class="card-bg card-border" style="background-color:#ffffff;padding:0 20px 12px 20px;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;border-radius:0 0 12px 12px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
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
    led_html = _byte_led_html(item.get('byte_score'))
    led_footer = f'<div style="padding-top:8px;">{led_html}</div>' if led_html else ''

    tag_html = f'<span style="display:inline-block;background-color:#FF6B35;color:#ffffff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:6px;vertical-align:middle;text-transform:uppercase;">{_esc(tag)}</span>' if tag else ''

    return f'''<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;border-bottom:1px solid #f0f0f0;padding-bottom:14px;">
  <tr>
    <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:17px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:6px;">
      {tag_html}{headline}
    </td>
  </tr>
  <tr>
    <td style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.55;padding-bottom:8px;">
      {why}
    </td>
  </tr>
  <tr>
    <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:#6b7280;line-height:1.4;">
      <a href="{url}" style="display:inline-block;color:#2563eb;text-decoration:none;font-weight:600;border:1px solid #2563eb;padding:4px 12px;border-radius:16px;font-size:12px;">Ver original &#x2197;</a>
      &nbsp;&middot;&nbsp; {source} &nbsp;&middot;&nbsp; &#x23F0; {hours}h
      {led_footer}
    </td>
  </tr>
</table>'''


def generate_email_html(curated: Dict) -> str:
    """Gera o conteúdo HTML do email — Template v2.12 mobile-first"""
    global _section_counter
    _section_counter = 0

    body_rows = []

    # ── HEADER ──────────────────────────────────
    body_rows.append(f'''<tr>
  <td class="dark-header" style="background-color:{COLORS["dark"]};background:linear-gradient(135deg, #1a1a2e 0%, #2d1b69 100%);padding:18px 20px;text-align:center;border-radius:12px 12px 0 0;">
    <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:20px;font-weight:800;color:#ffffff;letter-spacing:-0.3px;">THE DAILY BYTE</span>
  </td>
</tr>''')

    # Date subheader
    today = datetime.now()
    weekdays = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    months = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    date_str = f"{weekdays[today.weekday()]}, {today.day} de {months[today.month]} de {today.year}"
    read_min = _estimate_reading_time(curated)

    body_rows.append(f'''<tr>
  <td class="dark-header" style="background-color:{COLORS["dark"]};background:linear-gradient(135deg, #1a1a2e 0%, #2d1b69 100%);padding:0 20px 14px 20px;text-align:center;border-radius:0 0 12px 12px;">
    <span class="text-muted" style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;color:#94a3b8;">{date_str}</span>
    <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;color:#64748b;padding-left:8px;">&#x23F1; Leitura: {read_min} min</span>
  </td>
</tr>''')

    body_rows.append(_spacer(16))

    # ── BIG STORY (v2.14) ───────────────────────
    # Extrai o item marcado como big_story dos items[] e renderiza destacado no topo.
    # Remove de items[] para não aparecer duas vezes.
    items_all = curated.get('items', []) or []
    big_story = next((i for i in items_all if i.get('big_story')), None)
    if big_story:
        body_rows.append(_render_big_story_html(big_story))
        body_rows.append(_spacer())
        # Filtra big_story do array para renderização normal abaixo não duplicar
        curated['items'] = [i for i in items_all if not i.get('big_story')]

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
            wi_led_html = _byte_led_html(wi.get('byte_score'))
            wi_led_footer = f'<div style="padding-top:6px;">{wi_led_html}</div>' if wi_led_html else ''
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
          {wi_led_footer}
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
        body_rows.append(_section_header('&#x1F4B0;', 'SaaS & ENTERPRISE', COLORS["saas"]))
        body_rows.append(_card_start())
        for item in saas:
            body_rows.append(_render_item_html(item))
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 3b. RADAR BRASIL ───────────────────────
    radar_brasil = curated.get('radar_brasil', [])
    if radar_brasil:
        body_rows.append(_section_header('&#x1F1E7;&#x1F1F7;', 'RADAR BRASIL', COLORS["brasil"]))
        body_rows.append(_card_start())
        for i, rb in enumerate(radar_brasil):
            headline = _esc(rb.get('headline', ''))
            why = _esc(rb.get('why_it_matters', ''))
            url = rb.get('source_url', '#')
            source = _esc(rb.get('source_name', ''))
            rb_led_html = _byte_led_html(rb.get('byte_score'))
            rb_led_footer = f'<div style="padding-top:6px;">{rb_led_html}</div>' if rb_led_html else ''
            border = 'border-bottom:1px solid #f0f0f0;margin-bottom:12px;padding-bottom:12px;' if i < len(radar_brasil) - 1 else ''
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="{border}">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:4px;">
          &#x2192; {headline}
        </td>
      </tr>
      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:14px;color:#2d2d2d;line-height:1.5;padding-bottom:4px;">
          {why}
        </td>
      </tr>
      <tr>
        <td style="font-size:12px;color:#6b7280;">
          <a href="{url}" style="color:#2563eb;text-decoration:none;">{source} &#x2197;</a>
          {rb_led_footer}
        </td>
      </tr>
    </table>''')
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
          <a href="{tool_url}" style="display:inline-block;background-color:{COLORS["tool"]};color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;padding:14px 32px;border-radius:24px;text-decoration:none;box-shadow:0 2px 8px rgba(245,158,11,0.35);">&#x1F680; Experimentar</a>
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

    # ── 4b. WORKFLOW DA SEMANA (sextas) ────────
    workflow = curated.get('weekly_workflow', {})
    if workflow and workflow.get('title'):
        wf_title = _esc(workflow.get('title', ''))
        wf_steps = workflow.get('steps', [])
        if wf_steps:
            body_rows.append(_section_header('&#x1F4CB;', 'WORKFLOW DA SEMANA', COLORS["tool"]))
            body_rows.append(_card_start())
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:17px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:12px;">
          {wf_title}
        </td>
      </tr>''')
            for step in wf_steps:
                body_rows.append(f'''      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.55;padding-bottom:8px;padding-left:8px;border-left:3px solid {COLORS["tool"]};">
          {_esc(str(step))}
        </td>
      </tr>''')
            body_rows.append('''    </table>''')
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

    # ── 5b. DEEP DIVE SEMANAL (sextas) ─────────
    deep_dive = curated.get('deep_dive', {})
    if deep_dive and deep_dive.get('title') and deep_dive.get('body'):
        dd_title = _esc(deep_dive.get('title', ''))
        dd_body = deep_dive.get('body', '')
        dd_paragraphs = [p.strip() for p in dd_body.split('\n\n') if p.strip()]
        body_rows.append(_section_header('&#x1F52C;', 'DEEP DIVE', COLORS["deep_dive"]))
        body_rows.append(_card_start())
        body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:18px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:12px;">
          {dd_title}
        </td>
      </tr>''')
        for para in dd_paragraphs:
            body_rows.append(f'''      <tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;line-height:1.6;padding-bottom:12px;">
          {_esc(para)}
        </td>
      </tr>''')
        body_rows.append('''    </table>''')
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── 6. QUICK LINKS ──────────────────────────
    quick_links = curated.get('quick_links', [])
    if quick_links:
        body_rows.append(_section_header('&#x26A1;', 'QUICK LINKS', COLORS["quick"]))
        body_rows.append(_card_start())
        # 2-column grid layout (single column on mobile via width:100% class)
        pairs = []
        for i in range(0, len(quick_links), 2):
            pairs.append(quick_links[i:i+2])
        for pair in pairs:
            cols = []
            for ql in pair:
                headline = _esc(ql.get('headline', ''))
                url = ql.get('source_url', '#')
                source = _esc(ql.get('source_name', ''))
                ql_led = _byte_led_html(ql.get('byte_score'))
                ql_led_row = f'<br/><span style="color:#6b7280;font-size:11px;">{source}</span><br/>{ql_led}' if ql_led else f'<br/><span style="color:#6b7280;font-size:11px;">{source}</span>'
                cols.append(f'''<td class="ql-col" style="width:50%;vertical-align:top;padding:6px 8px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-left:3px solid {COLORS["quick"]};padding-left:10px;">
              <tr>
                <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;line-height:1.4;">
                  <a href="{url}" style="color:#2563eb;text-decoration:none;font-weight:600;">{headline}</a>
                  {ql_led_row}
                </td>
              </tr>
            </table>
          </td>''')
            if len(cols) == 1:
                cols.append(f'<td class="ql-col" style="width:50%;"></td>')
            body_rows.append(f'''    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:8px;">
      <tr>
          {cols[0]}
          {cols[1]}
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
          <a href="{url}" style="display:inline-block;background-color:{COLORS["video"]};color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;padding:14px 32px;border-radius:24px;text-decoration:none;box-shadow:0 2px 8px rgba(239,68,68,0.35);">&#x25B6;&#xFE0F; Assistir</a>
        </td>
      </tr>
    </table>''')
        body_rows.append(_card_end())
        body_rows.append(_card_bottom())
        body_rows.append(_spacer())

    # ── v2.7: ENQUETE SEMANAL (sextas) ──────────
    if datetime.utcnow().weekday() == 4:  # Friday
        body_rows.append(f'''<tr>
  <td style="background-color:#fffbeb;padding:20px;text-align:center;border:1px solid {COLORS["tool"]};border-radius:12px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="text-align:center;padding-bottom:10px;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;color:#1a1a2e;">&#x1F4CA; Enquete da Semana</span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;padding-bottom:12px;">
          <span style="font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#2d2d2d;">Qual tema voc&ecirc; quer ver mais no Daily Byte?</span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;">
          <a href="https://buttondown.com/totobusnello?tag=tema-ai-tools" style="display:inline-block;font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;background-color:{COLORS["tool"]};color:#ffffff;padding:10px 18px;border-radius:24px;text-decoration:none;margin:4px;box-shadow:0 2px 6px rgba(0,0,0,0.15);">AI Tools</a>
          <a href="https://buttondown.com/totobusnello?tag=tema-estrategia" style="display:inline-block;font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;background-color:{COLORS["analysis"]};color:#ffffff;padding:10px 18px;border-radius:24px;text-decoration:none;margin:4px;box-shadow:0 2px 6px rgba(0,0,0,0.15);">Estrat&eacute;gia</a>
          <a href="https://buttondown.com/totobusnello?tag=tema-brasil" style="display:inline-block;font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;background-color:{COLORS["saas"]};color:#ffffff;padding:10px 18px;border-radius:24px;text-decoration:none;margin:4px;box-shadow:0 2px 6px rgba(0,0,0,0.15);">Brasil</a>
          <a href="https://buttondown.com/totobusnello?tag=tema-deep-dive" style="display:inline-block;font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;background-color:{COLORS["world"]};color:#ffffff;padding:10px 18px;border-radius:24px;text-decoration:none;margin:4px;box-shadow:0 2px 6px rgba(0,0,0,0.15);">Deep Dive</a>
        </td>
      </tr>
    </table>
  </td>
</tr>''')
        body_rows.append(_spacer(12))

    # ── v2.6: 1-CLICK FEEDBACK ─────────────────
    body_rows.append(f'''<tr>
  <td style="background-color:#ffffff;padding:20px;text-align:center;border:1px solid #e5e7eb;border-radius:12px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="text-align:center;padding-bottom:10px;">
          <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;color:#1a1a2e;">Esta edi&ccedil;&atilde;o foi &uacute;til?</span>
        </td>
      </tr>
      <tr>
        <td style="text-align:center;">
          <a href="https://buttondown.com/totobusnello?tag=feedback-positivo" style="display:inline-block;font-size:28px;text-decoration:none;padding:8px 16px;">&#x1F44D;</a>
          <a href="https://buttondown.com/totobusnello?tag=feedback-neutro" style="display:inline-block;font-size:28px;text-decoration:none;padding:8px 16px;">&#x1F44B;</a>
          <a href="https://buttondown.com/totobusnello?tag=feedback-negativo" style="display:inline-block;font-size:28px;text-decoration:none;padding:8px 16px;">&#x1F44E;</a>
        </td>
      </tr>
    </table>
  </td>
</tr>''')

    body_rows.append(_spacer(12))

    # ── v2.6: REFERRAL CTA ─────────────────────
    body_rows.append(f'''<tr>
  <td style="background-color:#f8f4ff;padding:16px 20px;text-align:center;border:1px dashed {COLORS["analysis"]};border-radius:12px;">
    <span style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;color:#2d2d2d;">
      &#x1F4E8; Conhece algu&eacute;m que precisa saber disso?
    </span>
    <br/>
    <a href="https://buttondown.com/totobusnello" style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;font-weight:700;color:{COLORS["analysis"]};text-decoration:none;">Encaminhe esta edi&ccedil;&atilde;o &#x2197;</a>
  </td>
</tr>''')

    body_rows.append(_spacer(12))

    # ── FOOTER ──────────────────────────────────
    body_rows.append(f'''<tr>
  <td class="dark-header" style="background-color:{COLORS["dark"]};background:linear-gradient(135deg, #1a1a2e 0%, #2d1b69 100%);padding:20px;text-align:center;border-radius:12px;">
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
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>The Daily Byte</title>
<!--[if mso]>
<style>table,td {{font-family:Arial,sans-serif !important;}}</style>
<![endif]-->
<style type="text/css">
:root {{
  color-scheme: light dark;
  supported-color-schemes: light dark;
}}
@media only screen and (max-width: 620px) {{
  .email-container {{
    width: 100% !important;
    max-width: 100% !important;
  }}
  .mobile-padding {{
    padding-left: 12px !important;
    padding-right: 12px !important;
  }}
  .ql-col {{
    display: block !important;
    width: 100% !important;
    padding-bottom: 8px !important;
  }}
}}
@media (prefers-color-scheme: dark) {{
  body, .email-bg {{
    background-color: #1a1a1a !important;
  }}
  .card-bg, .card-border {{
    background-color: #2d2d2d !important;
    border-color: #404040 !important;
  }}
  .dark-header {{
    background-color: #111111 !important;
  }}
  .text-dark {{
    color: #f5f5f5 !important;
  }}
  .text-muted {{
    color: #a0a0a0 !important;
  }}
  a {{
    color: #4da6ff !important;
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

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{COLORS["bg"]};" class="email-bg">
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

    tag_str = f"[{tag}] " if tag else ""
    led_md = _byte_led_md(item.get('byte_score'))
    led_suffix = f"\n{led_md}" if led_md else ""

    return f"""{tag_str}**{headline}**

{why}

🔗 [Ver original]({url}) | 📍 {source} | ⏰ Há {hours}h{led_suffix}

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
            wi_led_md = _byte_led_md(wi.get('byte_score'))
            suffix = f"\n  {wi_led_md}" if wi_led_md else ""
            world_lines.append(f"→ **{headline}** — {context} ([{source}]({url})){suffix}")
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

    radar_brasil = curated.get('radar_brasil', [])
    if radar_brasil:
        rb_lines = []
        for rb in radar_brasil:
            headline = rb.get('headline', '')
            why = rb.get('why_it_matters', '')
            url = rb.get('source_url', '#')
            source = rb.get('source_name', '')
            rb_led = _byte_led_md(rb.get('byte_score'))
            rb_suffix = f"\n  {rb_led}" if rb_led else ""
            rb_lines.append(f"→ **{headline}** — {why} ([{source}]({url})){rb_suffix}")
        sections.append("# 🇧🇷 RADAR BRASIL\n\n" + "\n\n".join(rb_lines))

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

    deep_dive = curated.get('deep_dive', {})
    if deep_dive and deep_dive.get('title') and deep_dive.get('body'):
        dd_title = deep_dive.get('title', '')
        dd_body = deep_dive.get('body', '')
        sections.append(f"# 🔬 DEEP DIVE\n\n**{dd_title}**\n\n{dd_body}")

    quick_links = curated.get('quick_links', [])
    if quick_links:
        ql_lines = []
        for ql in quick_links:
            headline = ql.get('headline', '')
            url = ql.get('source_url', '#')
            source = ql.get('source_name', '')
            ql_led = _byte_led_md(ql.get('byte_score'))
            ql_suffix = f"\n  {ql_led}" if ql_led else ""
            ql_lines.append(f"→ [{headline}]({url}) *({source})*{ql_suffix}")
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
    if hook:
        subject = f"\U0001F525 {hook}"
    else:
        subject = f"\U0001F525 Daily Byte"

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
