#!/usr/bin/env python3
"""
THE DAILY BYTE - Sender
Envia o digest via Buttondown API
"""

import os
import json
import re
import requests
from datetime import datetime
from typing import Dict, Optional

# ============================================
# CONFIGURAÇÃO
# ============================================

BUTTONDOWN_API_KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
BUTTONDOWN_API_URL = "https://api.buttondown.email/v1/emails"

# ============================================
# TEMPLATES
# ============================================

EMAIL_FOOTER = """
---

*Curated by Totó Busnello AI*

✍️ **Quer ir mais fundo?** Leia meus artigos sobre tech, AI e negócios no [LinkedIn](https://www.linkedin.com/in/luiz-antonio-busnello/)

*[Gerenciar assinatura]({{ unsubscribe_url }})*
"""


def format_item(item: Dict) -> str:
    """Formata um item para o email"""
    headline = item.get('headline', 'Sem título')
    why = item.get('why_it_matters', '')
    url = item.get('source_url', '#')
    source = item.get('source_name', 'Fonte')
    hours = item.get('hours_ago', '?')
    heat = item.get('heat_score', 0)

    heat_emoji = "🔥🔥🔥" if heat >= 80 else "🔥🔥" if heat >= 70 else "🔥"

    return f"""**{headline}** {heat_emoji}

{why}

🔗 [Ver original]({url}) | 📍 {source} | ⏰ Há {hours}h

"""


def format_video(item: Dict) -> str:
    """Formata um vídeo para o email"""
    title = item.get('headline', 'Vídeo')
    url = item.get('source_url', '#')
    source = item.get('source_name', 'Canal')

    return f"""🎬 **{title}**
*{source}*
▶️ [Assistir]({url})

"""


def generate_email_content(curated: Dict) -> str:
    """Gera o conteúdo do email a partir dos dados curados"""

    sections = []

    # Mundo Real (sempre presente)
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

    # Categorize items
    items = curated.get('items', [])
    breaking = [i for i in items if i.get('category') == 'breaking']
    ai_models = [i for i in items if i.get('category') == 'ai_models']
    saas_enterprise = [i for i in items if i.get('category') == 'saas_enterprise']
    big_tech = [i for i in items if i.get('category') == 'big_tech']
    videos = [i for i in items if i.get('category') == 'watch_later']

    # Só adiciona seções que têm conteúdo
    if breaking:
        sections.append("# 🔥 BREAKING\n\n" + "\n".join([format_item(i) for i in breaking]))

    if ai_models:
        sections.append("# 🤖 AI & MODELS\n\n" + "\n".join([format_item(i) for i in ai_models]))

    if saas_enterprise:
        sections.append("# 💰 SaaS & ENTERPRISE\n\n" + "\n".join([format_item(i) for i in saas_enterprise]))

    if big_tech:
        sections.append("# 💼 BIG TECH MOVES\n\n" + "\n".join([format_item(i) for i in big_tech]))

    # Análise do dia
    analysis = curated.get('daily_analysis', '')
    if analysis:
        if isinstance(analysis, list):
            sanitized = []
            for item in analysis:
                # Strip heading markers (###, ##, #)
                item = re.sub(r'^#{1,6}\s*', '', item.strip())
                # Strip leading bullet markers (•, -, *)
                item = re.sub(r'^[•\-\*]\s*', '', item.strip())
                sanitized.append(f"• {item}")
            analysis_text = "\n\n".join(sanitized)
        else:
            analysis_text = analysis
        sections.append(f"# 🔮 ANÁLISE DO DIA\n\n{analysis_text}")

    if videos:
        sections.append("# 📺 WATCH LATER\n\n" + "\n".join([format_video(i) for i in videos]))

    return "\n\n---\n\n".join(sections) + EMAIL_FOOTER


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
        return

    # Generate subject
    today = datetime.now()
    weekdays_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    months_pt = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    subject = f"🔥 Daily Byte - {weekdays_pt[today.weekday()]}, {today.day} de {months_pt[today.month]}"

    # Generate content
    content = generate_email_content(curated)

    if preview:
        print("\n" + "="*50)
        print("📧 PREVIEW DO EMAIL")
        print("="*50)
        print(f"Subject: {subject}")
        print("-"*50)
        print(content)
        print("="*50)

        # Save preview
        preview_path = "/tmp/digest_preview.md"
        with open(preview_path, 'w') as f:
            f.write(f"# {subject}\n\n{content}")
        print(f"💾 Preview salvo em {preview_path}")

        return {"preview": True, "subject": subject, "content": content}

    # Send
    return send_via_buttondown(subject, content)


if __name__ == "__main__":
    import sys

    preview_mode = "--preview" in sys.argv or "-p" in sys.argv

    send(preview=preview_mode)
