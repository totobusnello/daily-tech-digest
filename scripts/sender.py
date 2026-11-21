#!/usr/bin/env python3
"""
THE DAILY BYTE - Sender
Envia o digest via Buttondown API
v2.4: Template HTML dedicado, mobile-first
"""

import copy
import os
import json
import math
import re
import unicodedata
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

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

# v2.17c: fuso editorial. O "dia" da edição é o dia no Brasil, não em UTC.
# O Brasil não tem horário de verão desde 2019, então o offset fixo -3 é
# correto o ano inteiro e não depende de tzdata estar presente no runner.
BRT = timezone(timedelta(hours=-3))

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


def _safe_url(url: str) -> str:
    """Sanitiza URL: aceita apenas http(s), escapa aspas/tags. Retorna '#' se invalida.
    Bloqueia javascript:, data:, vbscript:, e attribute breakouts."""
    if not url or not isinstance(url, str):
        return "#"
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return "#"
        if not parsed.netloc:
            return "#"
    except (ValueError, TypeError):
        return "#"
    return _esc(url)


# Emojis de fogo que o curador às vezes prefixa por conta própria no subject_hook.
# U+1F525 = 🔥 | U+2757/U+2755 = ❗❕ | U+26A0 = ⚠ (com ou sem variation selector)
_LEADING_FIRE_RE = re.compile(r'^(?:[\U0001F525❗❕⚠]️?[\s ]*)+')


def _strip_leading_fire(hook: str) -> str:
    """Remove emojis de destaque repetidos no início do subject_hook (v2.16).

    O sender prefixa 🔥 uma vez; quando o curador já devolvia o hook com fogo,
    os dois empilhavam ("🔥 🔥 🔥 TSMC investe US$265B"). Normaliza para que o
    prefixo do sender seja sempre o único.
    """
    if not hook or not isinstance(hook, str):
        return ""
    return _LEADING_FIRE_RE.sub('', hook).strip()


# ── v2.18: emoji temático no subject (benchmark The Rundown AI) ──
# 100 edições seguidas abriram com 🔥 (medido no Buttondown em 06/11/2026) — o
# sinal que se repete todo dia deixa de ser sinal. O Rundown troca o emoji pelo
# tema da edição (📈 🕵️ 🚀 ⚖️). O curador sugere; o código valida e cai no 🔥.
_FALLBACK_EMOJI = "\U0001F525"
_EMOJI_JOINERS = {"‍", "️", "︎", "⃣"}  # ZWJ, VS16, VS15, keycap


# Faixas de pictograma de emoji. Antes valia qualquer caractere da categoria
# Unicode 'So', o que deixava passar ░ e © (revisão Codex+Kimi do PR #31).
_EMOJI_RANGES = ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2300, 0x23FF),
                 (0x2B00, 0x2BFF), (0x3030, 0x3030), (0x303D, 0x303D),
                 (0x3297, 0x3297), (0x3299, 0x3299))
_KEYCAP_RE = re.compile(r'^[0-9#*]️?⃣$')


def _is_emoji_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _EMOJI_RANGES)


def _num(score) -> float:
    """byte_score como número. O curador às vezes manda "7" em vez de 7; o
    _byte_tier sempre tolerou, e o preheader derrubava o envio inteiro com
    TypeError (achado alto do Codex e do Kimi no PR #31)."""
    try:
        v = float(score)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(v) else v


def _subject_emoji(raw) -> str:
    """UM emoji vindo do curador, ou 🔥. Rejeita texto, espaço e mais de um emoji.

    Conta "bases": cada pictograma conta 1, exceto o que vem colado por ZWJ (👨‍💻)
    e pares de indicador regional (🇧🇷), que formam um emoji só. Keycap (1️⃣)
    tem regra própria porque começa por dígito. Limite conhecido: não valida
    contra a tabela oficial de sequências ZWJ — "📈‍📉" passa como 1 emoji.
    É cosmético (o cliente de email mostra 2 emojis), não bloqueia o envio.
    """
    if not isinstance(raw, str):
        return _FALLBACK_EMOJI
    s = raw.strip()
    if _KEYCAP_RE.match(s):
        return s
    if not s or len(s) > 8 or any(c.isspace() or c.isalnum() for c in s):
        return _FALLBACK_EMOJI
    if s.endswith("‍") or s.startswith("‍"):
        return _FALLBACK_EMOJI  # ZWJ pendurado
    bases, regional, prev_zwj = 0, 0, False
    for ch in s:
        if ch in _EMOJI_JOINERS:
            prev_zwj = ch == "‍"
            continue
        if not _is_emoji_char(ch):
            return _FALLBACK_EMOJI
        if 0x1F1E6 <= ord(ch) <= 0x1F1FF:
            regional += 1
        elif 0x1F3FB <= ord(ch) <= 0x1F3FF:
            pass  # modificador de tom de pele não é emoji novo
        elif not prev_zwj:
            bases += 1
        prev_zwj = False
    if regional % 2:
        return _FALLBACK_EMOJI  # indicador regional sem par não é bandeira
    bases += regional // 2
    return s if bases == 1 else _FALLBACK_EMOJI


def _strip_leading_emoji(hook) -> str:
    """Remove QUALQUER emoji/espaço no início do hook (generaliza o strip de fogo).

    Com o emoji agora variável, o curador pode repetir o próprio emoji no hook
    ("📈 📈 Anthropic..."); só o fogo sair não basta mais. Emoji no meio fica.
    """
    if not hook or not isinstance(hook, str):
        return ""
    i = 0
    while i < len(hook) and (hook[i].isspace() or hook[i] in _EMOJI_JOINERS
                             or _is_emoji_char(hook[i]) or hook[i] in "❗❕⚠"):
        i += 1
    return hook[i:].strip()


def _compose_subject(curated: Dict) -> str:
    emoji = _subject_emoji((curated or {}).get('subject_emoji'))
    hook = _strip_leading_emoji((curated or {}).get('subject_hook', ''))
    return f"{emoji} {hook or 'Daily Byte'}"


def _story_items(curated: Dict) -> list:
    """Itens noticiosos de items[] (sem watch_later/tool), na ordem do curador."""
    return [i for i in ((curated or {}).get('items') or [])
            if isinstance(i, dict) and i.get('category') in ('hoje_no_byte', 'saas_enterprise')]


def _big_story_of(curated: Dict):
    return next((i for i in _story_items(curated)
                 if i.get('big_story') is True and _num(i.get('byte_score')) >= 8), None)


_STOP_PT = {"para", "com", "sem", "pela", "pelo", "como", "mais", "uma", "seu", "sua",
            "dos", "das", "que", "nos", "nas", "por", "the", "and", "from"}


def _sig_words(text: str) -> set:
    norm = unicodedata.normalize('NFKD', str(text or '').lower())
    norm = ''.join(c for c in norm if not unicodedata.combining(c))
    return {w for w in re.findall(r'[a-z0-9$]+', norm) if len(w) > 3 and w not in _STOP_PT}


def _clip(text: str, limit: int) -> str:
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0].rstrip(' ,;:—-')
    return cut + "…"


def _preheader(curated: Dict, limit: int = 140) -> str:
    """Texto de preview "MAIS: <segunda história>" (v2.18, padrão "PLUS:" do Rundown).

    Derivado no código, não pedido ao curador: é só escolher, entre o que ele já
    escreveu, a história de maior byte_score que NÃO é a do subject — o preview
    que repete o subject desperdiça a segunda linha da caixa de entrada.
    Vai no campo `description` do Buttondown, que é quem define o preheader
    (docs.buttondown.com/glossary-developers). Sem isso o Gmail mostrava o
    cabeçalho que o próprio Buttondown injeta ("THE DAILY BYTE · 06/11/2026...").
    """
    curated = curated or {}
    hook_words = _sig_words(curated.get('subject_hook', ''))
    stories = [i for i in _story_items(curated) if i.get('headline')]
    # Qual história é a do subject? A de maior sobreposição de palavras com o
    # hook (mínimo de 2 palavras, ou metade do hook). Sem nenhuma que passe,
    # assume-se a Big Story — o curador pede o hook sobre a notícia principal.
    # Antes a Big Story era excluída sempre, e quando o hook era sobre a 2ª
    # história o preview pulava a Big Story (achado do Kimi no PR #31).
    def _overlap(i):
        return len(_sig_words(i['headline']) & hook_words)
    need = max(2, len(hook_words) // 2)
    matched = [i for i in stories if hook_words and _overlap(i) >= need]
    subject_story = (max(matched, key=_overlap) if matched else _big_story_of(curated))
    cands = [i for i in stories if i is not subject_story]
    cands.sort(key=lambda i: -_num(i.get('byte_score')))  # sort estável: empate mantém a ordem
    for item in cands:
        if hook_words and _overlap(item) >= need:
            continue  # outra cobertura da mesma história do subject
        return _clip("MAIS: " + item['headline'], limit)
    n = curated.get('number_of_day') or {}
    if n.get('value') and n.get('context'):
        return _clip(f"MAIS: {n['value']} — {n['context']}", limit)
    return ""


def _valid_trending_tools(tools) -> list:
    """Até 3 ferramentas com nome e URL http(s) válida (v2.18).

    Sem URL a ferramenta NÃO entra: mesma regra do source_url dos itens. É a
    trava contra o curador inventar ou inflar ferramenta que não veio da coleta.
    """
    if not isinstance(tools, list):
        return []
    out = []
    for t in tools:
        if not isinstance(t, dict) or not str(t.get('name') or '').strip():
            continue
        if _safe_url(t.get('source_url', '')) == '#':
            continue
        out.append(t)
        if len(out) == 3:
            break
    return out


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

# VU meter — alturas e cores por posição (verde → laranja) — v2.14.1 mais discreto
_VU_HEIGHTS = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
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
        off = '' if i < filled else ' class="vu-off"'
        cells.append(
            f'<span{off} style="display:inline-block;width:4px;height:{_VU_HEIGHTS[i]}px;'
            f'background-color:{color};margin-right:1px;border-radius:1px;'
            f'vertical-align:bottom;"></span>'
        )
    peak_color = _VU_COLORS[filled - 1] if filled > 0 else '#9ca3af'
    return (
        '<span style="display:inline-block;white-space:nowrap;line-height:12px;height:12px;vertical-align:2px;">'
        + "".join(cells)
        + f'<span style="font-size:12px;font-weight:700;color:{peak_color};margin-left:4px;vertical-align:bottom;">{s}</span>'
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


# ── Camada de apresentação v2.20 ────────────────────────────────────────────
# Redesenho a partir da análise de layout de 21/11/2026 (regra 91). Em resumo:
# - UM card por seção (rótulo + conteúdo na mesma célula). Antes eram 3 <tr>
#   com 3 sombras, círculo numerado e pílula com emoji: ~90px de moldura por seção.
# - Metadados = "Fonte ↗ · há Nh · LED". Saíram ⏰, "N min" e o botão-pílula
#   "Ver original"; o link vai na própria manchete. O LED fica em todos os
#   itens (decisão do Toto), mas num grupo nowrap junto do "·" — antes ele
#   quebrava sozinho numa linha no celular, com um "·" pendurado.
# - Um só estilo de botão (laranja, bulletproof), só na Big Story e na Tool.
# - Dark mode por CLASSE em todo texto (.text-dark/.text-muted/.tint-bg):
#   antes nenhum texto tinha classe e o Apple Mail escuro punha #2d2d2d sobre
#   #2d2d2d. Botão tem .btn para o `a{color}` do dark não pintá-lo de azul.
# - Nada abaixo de 12px.

_SANS = "'Helvetica Neue',Arial,sans-serif"
_SERIF = "Georgia,'Times New Roman',serif"

# Cor do RÓTULO de seção: versão escura de cada acento. Âmbar/laranja/azul-céu
# puros sobre branco ficam abaixo de 3:1 em texto de 12px.
_LABEL = {
    "byte": "#c2410c", "saas": "#047857", "world": "#0369a1", "brasil": "#15803d",
    "number": "#6d28d9", "analysis": "#6d28d9", "deep_dive": "#1e40af",
    "tool": "#b45309", "quick": "#475569", "video": "#b91c1c",
}

_TBL = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'


def _spacer(height: int = 14) -> str:
    return f'<tr><td style="padding:0;height:{height}px;line-height:{height}px;font-size:1px;">&nbsp;</td></tr>'


def _label_html(title: str, key: str, pad_top: int = 0) -> str:
    """Rótulo de seção/sub-seção: texto caixa-alta, 12px, sem pílula nem emoji."""
    return (f'<div style="font-family:{_SANS};font-size:12px;font-weight:800;color:{_LABEL[key]};'
            f'letter-spacing:1px;text-transform:uppercase;padding:{pad_top}px 0 10px 0;">{_esc(title)}</div>')


def _section(title: str, key: str, inner: str) -> str:
    """Um card por seção (v2.20)."""
    return f'''<tr>
  <td class="card-bg card-border" style="background-color:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px 4px 20px;">
    {_label_html(title, key)}
    {inner}
  </td>
</tr>'''


def _stack(blocks: list, gap: int = 14) -> str:
    """Empilha blocos com divisória ENTRE eles — nunca depois do último (v2.20).

    Antes cada item levava border-bottom + margin próprios, e o último deixava
    uma linha e ~40px vazios antes do fim do card.
    """
    n = len(blocks)
    rows = []
    for i, b in enumerate(blocks):
        top = 0 if i == 0 else gap
        sep = 'border-bottom:1px solid #eeeeee;' if i < n - 1 else ''
        rows.append(f'<tr><td class="sep" style="padding:{top}px 0 {gap}px 0;{sep}">{b}</td></tr>')
    return _TBL + ''.join(rows) + '</table>'


def _tag_html(tag) -> str:
    if not tag:
        return ''
    return (f'<span class="tag" style="display:inline-block;border:1px solid #d1d5db;color:#6b7280;'
            f'font-family:{_SANS};font-size:11px;font-weight:700;padding:1px 6px;border-radius:4px;'
            f'margin-right:6px;vertical-align:2px;letter-spacing:0.5px;text-transform:uppercase;">{_esc(tag)}</span>')


def _headline_html(item: Dict, size: int = 17, prefix: str = '', tag: str = '') -> str:
    """Manchete É o link (v2.20) — substitui o botão "Ver original"."""
    hl = _esc(item.get('headline', '') or 'Sem título')
    url = _safe_url(item.get('source_url', ''))
    if url != '#':
        hl = f'<a href="{url}" class="text-dark" style="color:#1a1a2e;text-decoration:none;">{hl}</a>'
    return (f'<div class="text-dark" style="font-family:{_SANS};font-size:{size}px;font-weight:700;'
            f'color:#1a1a2e;line-height:1.35;padding-bottom:6px;">{_tag_html(tag)}{prefix}{hl}</div>')


def _body_html(text: str, size: int = 15, pad: int = 8) -> str:
    if not text:
        return ''
    return (f'<div class="text-dark" style="font-family:{_SERIF};font-size:{size}px;color:#2d2d2d;'
            f'line-height:1.55;padding-bottom:{pad}px;">{text}</div>')


def _meta_html(item: Dict, link_source: bool = True) -> str:
    """"Fonte ↗ · há Nh · LED" em 12px. Cada parte em nowrap; o LED vai num grupo
    nowrap JUNTO do seu "·" — assim, se a linha quebrar, quebra inteira."""
    source = _esc(item.get('source_name', '') or 'Fonte')
    url = _safe_url(item.get('source_url', ''))
    if link_source and url != '#':
        source = (f'<a href="{url}" style="color:{COLORS["link"]};text-decoration:none;font-weight:600;">'
                  f'{source}&nbsp;&#x2197;</a>')
    parts = [source]
    h = item.get('hours_ago')
    if h not in (None, '', '?'):
        parts.append(f'h&aacute;&nbsp;{_esc(str(h))}h')
    meta = ' &middot; '.join(f'<span style="white-space:nowrap;">{p}</span>' for p in parts)
    led = _byte_led_html(item.get('byte_score'))
    if led:
        meta += f' <span style="white-space:nowrap;">&middot;&nbsp;{led}</span>'
    return (f'<div class="text-muted" style="font-family:{_SANS};font-size:12px;color:#6b7280;'
            f'line-height:1.7;">{meta}</div>')


def _button_html(url: str, label: str) -> str:
    """Botão bulletproof (cor no <td>, área clicável preservada no Outlook). Um só estilo."""
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td bgcolor="{COLORS["brand"]}" style="background-color:{COLORS["brand"]};border-radius:20px;">'
            f'<a class="btn" href="{_safe_url(url)}" style="display:inline-block;padding:9px 18px;'
            f'font-family:{_SANS};font-size:13px;font-weight:700;color:#ffffff;text-decoration:none;white-space:nowrap;">'
            f'{label}</a></td></tr></table>')


def _details_html(item: Dict, font_size: int = 14) -> str:
    """Até 3 bullets de dado duro. '' sem details[] válido.

    v2.17 criou para a Big Story; v2.18 estende às 2-3 histórias principais
    (molde "The details" do Rundown). O leitor consome a notícia DENTRO do email
    — o número tem de estar aqui, não no link. v2.20: traço neutro, mínimo 14px.
    """
    detalhes = item.get('details') if isinstance(item, dict) else None
    if not isinstance(detalhes, list):
        return ''
    detalhes = [str(d).strip() for d in detalhes if str(d or '').strip()][:3]
    if not detalhes:
        return ''
    linhas = ''.join(
        f'<tr><td class="text-dark det" style="padding:0 0 5px 0;font-family:{_SANS};'
        f'font-size:{max(14, font_size)}px;color:#3d3d3d;line-height:1.45;">'
        f'<span class="text-muted" style="color:#9ca3af;">&ndash;</span>&nbsp; {_esc(d)}'
        f'</td></tr>'
        for d in detalhes
    )
    return f'<div style="padding-bottom:8px;">{_TBL}{linhas}</table></div>'


def _render_big_story_html(item: Dict) -> str:
    """Card de destaque no topo — é a abertura do email desde a v2.19 (regra 89)."""
    return f'''<tr>
  <td class="tint-bg" style="background-color:#fff8f2;border:2px solid {COLORS["brand"]};border-radius:12px;padding:20px 22px;">
    <div style="padding-bottom:10px;"><span style="display:inline-block;background-color:{COLORS["brand"]};color:#ffffff;font-family:{_SANS};font-size:11px;font-weight:800;padding:3px 10px;border-radius:20px;letter-spacing:1px;text-transform:uppercase;">&#x2605; Big Story</span></div>
    {_headline_html(item, size=22)}
    {_body_html(_esc(item.get('why_it_matters', '')), size=16, pad=10)}
    {_details_html(item, font_size=14)}
    <div style="padding-bottom:12px;">{_meta_html(item, link_source=False)}</div>
    {_button_html(item.get('source_url', ''), 'Ler agora &#x2197;')}
  </td>
</tr>'''


def _render_item_html(item: Dict) -> str:
    """Item de Hoje no Byte / SaaS: manchete-link, why, details, metadados."""
    return (_headline_html(item, size=17, tag=item.get('tag', ''))
            + _body_html(_esc(item.get('why_it_matters', '')))
            + _details_html(item, font_size=14)
            + _meta_html(item))


def _render_compact_html(item: Dict, text_key: str) -> str:
    """Item de Mundo Real / Radar Brasil: mesma anatomia, sem tag e sem details."""
    return (_headline_html(item, size=16)
            + _body_html(_esc(item.get(text_key, '')), pad=6)
            + _meta_html(item))


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
        if isinstance(item.get('details'), list):  # v2.18: details agora em várias histórias
            text_parts.extend(str(d) for d in item['details'][:3])

    for t in _valid_trending_tools(curated.get('trending_tools')):
        text_parts.append(f"{t.get('name', '')} {t.get('what_it_does', '')}")

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


def generate_email_html(curated: Dict) -> str:
    """Gera o HTML do email — layout v2.20 (um card por seção, ordem por prioridade de leitura)."""
    body_rows = []

    # ── HEADER (uma célula; antes eram 2 gradientes com emenda) ──
    today = datetime.now()
    weekdays = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    months = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    date_str = f"{weekdays[today.weekday()]}, {today.day} de {months[today.month]} de {today.year}"
    read_min = _estimate_reading_time(curated)
    body_rows.append(f'''<tr>
  <td class="dark-header" style="background-color:{COLORS["dark"]};background:linear-gradient(135deg, #1a1a2e 0%, #2d1b69 100%);padding:18px 20px 14px 20px;text-align:center;border-radius:12px;">
    <div style="font-family:{_SANS};font-size:20px;font-weight:800;color:#ffffff;letter-spacing:-0.3px;padding-bottom:4px;">THE DAILY BYTE</div>
    <div style="font-family:{_SANS};font-size:12px;color:#94a3b8;">{date_str} &middot; {read_min} min de leitura</div>
  </td>
</tr>''')
    body_rows.append(_spacer())

    # Sem bloco de abertura desde a v2.19 (regra 89): a Big Story abre o email.

    # ── BIG STORY (v2.14) ───────────────────────
    # Regras defensivas (v2.15): só boolean True; só hoje_no_byte/saas_enterprise;
    # byte_score >= 8; filtra por IDENTIDADE; não muta curated (dedup + preview).
    items_all = curated.get('items', []) or []

    def _is_valid_big_story(i):
        return (
            i.get('big_story') is True
            and i.get('category') in ('hoje_no_byte', 'saas_enterprise')
            and _num(i.get('byte_score')) >= 8  # v2.18: "9" (str) dava TypeError aqui
        )

    big_story = next((i for i in items_all if _is_valid_big_story(i)), None)
    if big_story:
        body_rows.append(_render_big_story_html(big_story))
        body_rows.append(_spacer())
    items = [i for i in items_all if i is not big_story] if big_story else items_all

    # ORDEM v2.20 (regra 91): o miolo do produto e a análise vêm antes do que é
    # contexto (mundo) e do que é ferramenta. Quem para no meio da leitura de
    # manhã já leu as notícias principais e a análise.

    # ── HOJE NO BYTE ────────────────────────────
    hoje = [i for i in items if i.get('category') == 'hoje_no_byte']
    if not hoje:
        hoje = [i for i in items if i.get('category') in ('breaking', 'ai_models', 'big_tech')]
    if hoje:
        body_rows.append(_section('Hoje no Byte', 'byte', _stack([_render_item_html(i) for i in hoje])))
        body_rows.append(_spacer())

    # ── SaaS & ENTERPRISE ───────────────────────
    saas = [i for i in items if i.get('category') == 'saas_enterprise']
    if saas:
        body_rows.append(_section('SaaS & Enterprise', 'saas', _stack([_render_item_html(i) for i in saas])))
        body_rows.append(_spacer())

    # ── MUNDO REAL + RADAR BRASIL (um card) ─────
    world_items = curated.get('world', []) or []
    radar_brasil = curated.get('radar_brasil', []) or []
    if world_items or radar_brasil:
        world_html = _stack([_render_compact_html(w, 'context') for w in world_items]) if world_items else ''
        radar_html = _stack([_render_compact_html(r, 'why_it_matters') for r in radar_brasil]) if radar_brasil else ''
        if world_items and radar_brasil:
            inner = (world_html
                     + f'<div class="sep" style="border-top:1px solid #eeeeee;">{_label_html("Radar Brasil", "brasil", pad_top=14)}</div>'
                     + radar_html)
            body_rows.append(_section('Mundo Real', 'world', inner))
        elif world_items:
            body_rows.append(_section('Mundo Real', 'world', world_html))
        else:
            body_rows.append(_section('Radar Brasil', 'brasil', radar_html))
        body_rows.append(_spacer())

    # ── NÚMERO DO DIA (faixa, sem card) ─────────
    number = curated.get('number_of_day', {}) or {}
    if number.get('value'):
        body_rows.append(f'''<tr>
  <td style="padding:2px 4px;">
    {_TBL}<tr><td style="border-left:4px solid {COLORS["number"]};padding:2px 0 2px 14px;">
      {_label_html("Número do dia", "number")}
      <div style="font-family:{_SANS};font-size:30px;font-weight:800;color:{COLORS["number"]};line-height:1.15;padding-bottom:4px;">{_esc(str(number.get('value', '')))}</div>
      {_body_html(_esc(number.get('context', '')), size=15, pad=0)}
    </td></tr></table>
  </td>
</tr>''')
        body_rows.append(_spacer(18))

    # ── ANÁLISE DO DIA ──────────────────────────
    analysis = curated.get('daily_analysis', '')
    if analysis:
        blocks = []
        if isinstance(analysis, list):
            for a_item in analysis:
                a_item = re.sub(r'^#{1,6}\s*', '', str(a_item).strip())
                a_item = re.sub(r'^(?:[•\-]|\*(?!\*))\s*', '', a_item.strip())  # v2.19: nunca come o 1º * de **Título**
                bold_match = re.match(r'\*\*(.+?)\*\*\s*[—–\-]\s*(.*)', a_item)
                if bold_match:
                    txt = f'<strong>{_esc(bold_match.group(1))}</strong> &#x2014; {_esc(bold_match.group(2))}'
                else:
                    txt = _esc(a_item)
                blocks.append(f'<div class="text-dark" style="font-family:{_SANS};font-size:15px;line-height:1.55;color:#2d2d2d;padding-bottom:12px;">'
                              f'<span style="color:{COLORS["analysis"]};">&#x25CF;</span>&nbsp; {txt}</div>')
        else:
            blocks.append(_body_html(_esc(str(analysis)), pad=12))
        body_rows.append(_section('Análise do Dia', 'analysis', ''.join(blocks)))
        body_rows.append(_spacer())

    # ── DEEP DIVE (sextas) ──────────────────────
    deep_dive = curated.get('deep_dive', {}) or {}
    if deep_dive.get('title') and deep_dive.get('body'):
        paras = [p.strip() for p in str(deep_dive.get('body', '')).split('\n\n') if p.strip()]
        inner = (f'<div class="text-dark" style="font-family:{_SANS};font-size:18px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:10px;">{_esc(deep_dive.get("title", ""))}</div>'
                 + ''.join(_body_html(_esc(p), pad=12) for p in paras))
        body_rows.append(_section('Deep Dive', 'deep_dive', inner))
        body_rows.append(_spacer())

    # ── PARA USAR HOJE: Tool + Como usar + Prompt + Ferramentas em alta ──
    # Eram 3 cards seguidos de "use ferramenta" (v2.17/v2.18); para um C-level é
    # o bloco de menor urgência, então vem depois da análise e num card só.
    tool = curated.get('tool_of_day', {}) or {}
    if not tool:
        tool_items = [i for i in items if i.get('category') == 'tool_of_day']
        if tool_items:
            tool = tool_items[0]
    parts = []
    if tool and tool.get('headline'):
        parts.append(_headline_html(tool, size=18))
        parts.append(_body_html(_esc(tool.get('why_it_matters', '')), pad=10))
        src = _esc(tool.get('source_name', '') or '')
        parts.append(f'{_TBL}<tr><td style="padding-bottom:12px;width:1%;white-space:nowrap;">'
                     f'{_button_html(tool.get("source_url", ""), "Experimentar &#x2197;")}</td>'
                     f'<td class="text-muted" style="padding:0 0 12px 10px;font-family:{_SANS};font-size:12px;color:#6b7280;">{src}</td></tr></table>')
        how_to = _esc(tool.get('how_to_use', '') or '')
        if how_to:
            parts.append(f'<div class="sep" style="border-top:1px solid #eeeeee;">{_label_html("Como usar hoje", "tool", pad_top=12)}</div>')
            parts.append(_body_html(how_to, pad=12))
    # PROMPT DO DIA (v2.17): continua com caixa própria — é o elemento mais copiado
    _prompt = tool.get('prompt_of_day', '') if tool else ''
    if _prompt:
        parts.append(f'<div class="sep" style="border-top:1px solid #eeeeee;">{_label_html("Prompt do dia", "tool", pad_top=12)}</div>')
        parts.append(f'<div class="text-muted" style="font-family:{_SANS};font-size:12px;color:#6b7280;padding-bottom:8px;">Copie e cole no ChatGPT, Claude ou Gemini &#x2014; funciona como est&aacute;.</div>')
        parts.append(f'<div style="padding-bottom:14px;">{_TBL}<tr><td class="tint-bg text-dark" style="background-color:#f8f4ff;border-left:4px solid {COLORS["analysis"]};padding:12px 14px;font-family:\'Courier New\',Courier,monospace;font-size:14px;color:#1a1a2e;line-height:1.55;">{_esc(_prompt)}</td></tr></table></div>')
    # FERRAMENTAS EM ALTA (v2.18): só com URL válida vinda da coleta
    _tools = _valid_trending_tools(curated.get('trending_tools'))
    if _tools:
        parts.append(f'<div class="sep" style="border-top:1px solid #eeeeee;">{_label_html("Ferramentas em alta", "tool", pad_top=12)}</div>')
        for t in _tools:
            _src = _esc(str(t.get('source_name') or ''))
            _src_html = f' <span class="text-muted" style="color:#6b7280;font-size:12px;">&middot; {_src}</span>' if _src else ''
            parts.append(f'<div class="text-dark" style="font-family:{_SANS};font-size:15px;line-height:1.45;color:#2d2d2d;padding-bottom:10px;">'
                         f'<a href="{_safe_url(t.get("source_url", ""))}" style="color:{COLORS["link"]};text-decoration:none;font-weight:700;">'
                         f'{_esc(str(t.get("name")).strip())}</a> &#x2014; {_esc(str(t.get("what_it_does") or "").strip())}{_src_html}</div>')
    if parts:
        title = 'Tool do Dia' if (tool and tool.get('headline')) else 'Para usar hoje'
        body_rows.append(_section(title, 'tool', ''.join(parts)))
        body_rows.append(_spacer())

    # ── WORKFLOW DA SEMANA (sextas) ─────────────
    workflow = curated.get('weekly_workflow', {}) or {}
    wf_steps = workflow.get('steps', []) or []
    if workflow.get('title') and wf_steps:
        inner = (f'<div class="text-dark" style="font-family:{_SANS};font-size:17px;font-weight:700;color:#1a1a2e;line-height:1.35;padding-bottom:10px;">{_esc(workflow.get("title", ""))}</div>'
                 + ''.join(f'<div class="text-dark" style="font-family:{_SERIF};font-size:15px;color:#2d2d2d;line-height:1.55;padding:0 0 8px 10px;border-left:3px solid {COLORS["tool"]};margin-bottom:6px;">{_esc(str(s))}</div>' for s in wf_steps))
        body_rows.append(_section('Workflow da Semana', 'tool', inner))
        body_rows.append(_spacer())

    # ── QUICK LINKS (1 coluna sempre: 2 colunas dependiam de @media, que o app do Gmail ignora) ──
    quick_links = curated.get('quick_links', []) or []
    if quick_links:
        blocks = [_headline_html(q, size=15) + _meta_html(q, link_source=False) for q in quick_links]
        body_rows.append(_section('Quick Links', 'quick', _stack(blocks, gap=10)))
        body_rows.append(_spacer())

    # ── WATCH LATER ─────────────────────────────
    videos = [i for i in items if i.get('category') == 'watch_later']
    if videos:
        blocks = [_headline_html(v, size=16, prefix='&#x25B6; ')
                  + f'<div class="text-muted" style="font-family:{_SANS};font-size:12px;color:#6b7280;">{_esc(v.get("source_name", "") or "Canal")}</div>'
                  for v in videos]
        body_rows.append(_section('Watch Later', 'video', _stack(blocks)))
        body_rows.append(_spacer())

    # ── RODAPÉ ÚNICO: enquete (sextas) + feedback + indicação + assinatura ──
    _lnk = f'color:{COLORS["link"]};text-decoration:none;font-weight:600;'
    poll = ''
    if datetime.utcnow().weekday() == 4:  # v2.7: enquete semanal às sextas
        _opts = [('tema-ai-tools', 'AI Tools'), ('tema-estrategia', 'Estrat&eacute;gia'),
                 ('tema-brasil', 'Brasil'), ('tema-deep-dive', 'Deep Dive')]
        poll = (f'<div class="text-dark" style="font-family:{_SANS};font-size:14px;color:#2d2d2d;padding-bottom:12px;">'
                f'<strong>Enquete da semana:</strong> qual tema voc&ecirc; quer ver mais?<br/>'
                + ' &middot; '.join(f'<a href="https://buttondown.com/totobusnello?tag={t}" style="{_lnk}">{n}</a>' for t, n in _opts)
                + '</div>')
    body_rows.append(f'''<tr>
  <td style="padding:6px 12px 8px 12px;text-align:center;">
    {poll}
    <div class="text-dark" style="font-family:{_SANS};font-size:14px;color:#2d2d2d;padding-bottom:6px;">Esta edi&ccedil;&atilde;o foi &uacute;til?
      <a href="https://buttondown.com/totobusnello?tag=feedback-positivo" style="font-size:22px;text-decoration:none;padding:0 6px;">&#x1F44D;</a>
      <a href="https://buttondown.com/totobusnello?tag=feedback-neutro" style="font-size:22px;text-decoration:none;padding:0 6px;">&#x1F44B;</a>
      <a href="https://buttondown.com/totobusnello?tag=feedback-negativo" style="font-size:22px;text-decoration:none;padding:0 6px;">&#x1F44E;</a>
    </div>
    <div style="font-family:{_SANS};font-size:14px;padding-bottom:14px;"><a href="https://buttondown.com/totobusnello" style="{_lnk}">Encaminhe esta edi&ccedil;&atilde;o &#x2197;</a></div>
    <div class="text-muted" style="font-family:{_SANS};font-size:12px;color:#6b7280;">Curated by Tot&oacute; Busnello AI &middot; <a href="https://www.linkedin.com/in/luiz-antonio-busnello/" style="color:#6b7280;text-decoration:none;">LinkedIn &#x2197;</a></div>
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
  body, .email-bg {{ background-color: #161616 !important; }}
  .card-bg {{ background-color: #242424 !important; }}
  .card-border {{ border-color: #3a3a3a !important; }}
  .tint-bg {{ background-color: #2b2420 !important; }}
  .dark-header {{ background-color: #111111 !important; }}
  .text-dark {{ color: #f0f0f0 !important; }}
  .text-muted {{ color: #a3a3a3 !important; }}
  .sep {{ border-color: #3a3a3a !important; }}
  .tag {{ color: #a3a3a3 !important; border-color: #555555 !important; }}
  a {{ color: #6cb6ff !important; }}
  a.text-dark {{ color: #f0f0f0 !important; }}
  a.btn {{ color: #ffffff !important; }}
  .vu-off {{ background-color: #444444 !important; }}
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
    _det = item.get('details')
    det_md = ''
    if isinstance(_det, list):
        _det = [str(d).strip() for d in _det if str(d or '').strip()][:3]
        det_md = ''.join(f"- {d}\n" for d in _det) + ("\n" if _det else '')

    return f"""{tag_str}**{headline}**

{why}

{det_md}🔗 [Ver original]({url}) | 📍 {source} | ⏰ Há {hours}h{led_suffix}

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
            wi_hours = wi.get('hours_ago')
            wi_hours_str = f" | ⏰ {wi_hours}h" if wi_hours is not None else ""
            wi_led_md = _byte_led_md(wi.get('byte_score'))
            suffix = f"\n  {wi_led_md}" if wi_led_md else ""
            world_lines.append(f"→ **{headline}** — {context} ([{source}]({url})){wi_hours_str}{suffix}")
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
            rb_hours = rb.get('hours_ago')
            rb_hours_str = f" | ⏰ {rb_hours}h" if rb_hours is not None else ""
            rb_led = _byte_led_md(rb.get('byte_score'))
            rb_suffix = f"\n  {rb_led}" if rb_led else ""
            rb_lines.append(f"→ **{headline}** — {why} ([{source}]({url})){rb_hours_str}{rb_suffix}")
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

    _tools = _valid_trending_tools(curated.get('trending_tools'))
    if _tools:
        sections.append("# 🧰 FERRAMENTAS EM ALTA\n\n" + "\n".join(
            f"→ [{t.get('name')}]({t.get('source_url')}) — {t.get('what_it_does', '')}" for t in _tools))

    analysis = curated.get('daily_analysis', '')
    if analysis:
        if isinstance(analysis, list):
            sanitized = []
            for a_item in analysis:
                a_item = re.sub(r'^#{1,6}\s*', '', a_item.strip())
                a_item = re.sub(r'^(?:[•\-]|\*(?!\*))\s*', '', a_item.strip())  # v2.19: nunca come o 1º * de **Título**
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
            ql_hours = ql.get('hours_ago')
            ql_hours_str = f" | ⏰ {ql_hours}h" if ql_hours is not None else ""
            ql_led = _byte_led_md(ql.get('byte_score'))
            ql_suffix = f"\n  {ql_led}" if ql_led else ""
            ql_lines.append(f"→ [{headline}]({url}) *({source})*{ql_hours_str}{ql_suffix}")
        sections.append(f"# ⚡ QUICK LINKS\n\n" + "\n\n".join(ql_lines))

    videos = [i for i in items if i.get('category') == 'watch_later']
    if videos:
        sections.append("# 📺 WATCH LATER\n\n" + "\n".join([format_video(i) for i in videos]))

    return "\n\n***\n\n".join(sections) + EMAIL_FOOTER


def send_via_buttondown(subject: str, content: str, draft: bool = False,
                        description: str = "") -> Dict:
    """Envia email via Buttondown API.

    v2.18: `description` é o preheader (texto de preview na caixa de entrada).
    Sem ele o Buttondown gera o preview das primeiras linhas, que hoje são o
    cabeçalho injetado por ele mesmo ("THE DAILY BYTE · 06/11/2026 Recebeu
    isso de alguém?...") — medido no snippet do Gmail em 06/11/2026.
    """

    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "subject": subject,
        "body": content,
        "status": "draft" if draft else "about_to_send"
    }
    if description:
        payload["description"] = description

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


# ============================================
# v2.17c: GUARD DE IDEMPOTÊNCIA
# ============================================

def already_sent_today(now: Optional[datetime] = None) -> Optional[bool]:
    """Já saiu edição hoje?

    Existe porque o disparo passou a ter DUAS origens: o cron da VPS
    (`workflow_dispatch` às 09:41 UTC, caminho principal) e o `schedule` do
    próprio GitHub às 10:40 UTC, que é só rede de segurança para o caso de a
    VPS estar fora do ar. Sem este guard, um dia em que ambos rodam manda dois
    emails para a lista.

    A fonte da verdade é o Buttondown, não um arquivo de estado: é lá que o
    email de fato existe, e a resposta continua correta mesmo se o cache do
    Actions for perdido ou se alguém disparar manualmente.

    Retorna True/False, ou None quando não deu para saber (sem chave, API
    fora, resposta inesperada). Quem chama decide o que fazer com o None —
    `send()` trata como "pode enviar", ver a nota lá.
    """
    if not BUTTONDOWN_API_KEY:
        print("⚠️ Guard: BUTTONDOWN_API_KEY ausente, não dá para verificar")
        return None

    hoje = (now or datetime.now(BRT)).astimezone(BRT).date()

    try:
        resp = requests.get(
            BUTTONDOWN_API_URL,
            headers={"Authorization": f"Token {BUTTONDOWN_API_KEY}"},
            params={"ordering": "-publish_date"},
            timeout=20,
        )
        resp.raise_for_status()
        results = (resp.json() or {}).get("results") or []
    except Exception as e:
        print(f"⚠️ Guard: falha ao consultar o Buttondown ({e})")
        return None

    for email in results[:10]:
        if (email.get("status") or "").lower() not in ("sent", "scheduled"):
            continue
        raw = email.get("publish_date")
        if not raw:
            continue
        try:
            # publish_date vem em UTC com sufixo Z, que o fromisoformat do
            # 3.10 não aceita — normalizamos antes de converter para BRT.
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.astimezone(BRT).date() == hoje:
            print(f"🛑 Guard: já saiu edição hoje ({dt.astimezone(BRT):%d/%m %H:%M} BRT) "
                  f"— \"{(email.get('subject') or '')[:60]}\"")
            return True

    print(f"✅ Guard: nenhuma edição publicada hoje ({hoje:%d/%m}), envio liberado")
    return False


def load_curated(path: str = "/tmp/digest_curated.json") -> Dict:
    """Carrega dados curados"""
    with open(path, 'r') as f:
        return json.load(f)


# ============================================
# MAIN
# ============================================

def send(preview: bool = False, skip_if_sent_today: bool = False):
    """Pipeline de envio"""
    print("🔥 THE DAILY BYTE - Preparando envio...")

    # v2.17c: só o disparo de rede de segurança pede o guard. O caminho
    # principal (dispatch da VPS) e o envio manual passam direto — quem
    # dispara à mão normalmente QUER reenviar.
    if skip_if_sent_today and not preview:
        if already_sent_today() is True:
            print("↩️  Nada a fazer: a edição de hoje já foi entregue pelo disparo principal.")
            return {"skipped": True, "reason": "already_sent_today"}
        # None (API fora / sem chave) cai aqui de propósito: preferimos correr
        # o risco de um email repetido a engolir a edição do dia em silêncio.
        # Se o Buttondown estiver fora, o próprio envio abaixo falha e alerta.

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
    # v2.16: o curador às vezes já devolve o hook prefixado com 🔥, e o prefixo
    # fixo daqui empilhava em cima — saíram subjects como "🔥 🔥 🔥 TSMC investe".
    # v2.18: o emoji passou a ser temático (subject_emoji, validado, 🔥 de
    # reserva) e o strip remove qualquer emoji inicial, não só o fogo.
    subject = _compose_subject(curated)
    preheader = _preheader(curated)

    # Generate content — HTML for sending, markdown for terminal preview
    html_content = generate_email_html(curated)
    md_content = generate_email_content(curated)

    if preview:
        print("\n" + "="*50)
        print("📧 PREVIEW DO EMAIL")
        print("="*50)
        print(f"Subject: {subject}")
        print(f"Preview: {preheader or '(vazio — Buttondown gera das primeiras linhas)'}")
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
    result = send_via_buttondown(subject, html_content, description=preheader)

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
    # Passado pelo workflow quando o gatilho é o `schedule` (rede de segurança).
    skip_if_sent = "--skip-if-sent-today" in sys.argv

    result = send(preview=preview_mode, skip_if_sent_today=skip_if_sent)

    # Sai 0 no skip: não é falha, é o fallback constatando que não precisa agir.
    if isinstance(result, dict) and result.get("skipped"):
        sys.exit(0)
