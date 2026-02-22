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

***

*Curated by Totó Busnello AI*

✍️ **Quer ir mais fundo?** Leia meus artigos sobre tech, AI e negócios no [LinkedIn](https://www.linkedin.com/in/luiz-antonio-busnello/)

*[Gerenciar assinatura]({{ unsubscribe_url }})*
"""


def format_item(item: Dict) -> str:
    """Formata um item principal com tag para o email"""
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
    """Formata um vídeo para o email"""
    title = item.get('headline', 'Vídeo')
    url = item.get('source_url', '#')
    source = item.get('source_name', 'Canal')

    return f"""🎬 **{title}**
*{source}*
▶️ [Assistir]({url})

"""


def generate_email_content(curated: Dict) -> str:
    """Gera o conteúdo do email — Layout consolidado v2.2"""

    sections = []

    # 0. Número do Dia (data point impactante)
    number = curated.get('number_of_day', {})
    if number and number.get('value'):
        sections.append(f"# 📊 NÚMERO DO DIA\n\n**{number.get('value', '')}** — {number.get('context', '')}")

    # 1. Mundo Real (3 itens — mundo + Brasil)
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

    # 2. Hoje no Byte (seção principal consolidada — breaking + ai + big tech)
    items = curated.get('items', [])
    hoje = [i for i in items if i.get('category') == 'hoje_no_byte']
    # Fallback: suporta formato antigo (breaking/ai_models/big_tech separados)
    if not hoje:
        hoje = [i for i in items if i.get('category') in ('breaking', 'ai_models', 'big_tech')]
    if hoje:
        sections.append("# 🔥 HOJE NO BYTE\n\n" + "\n".join([format_item(i) for i in hoje]))

    # 3. SaaS & Enterprise
    saas = [i for i in items if i.get('category') == 'saas_enterprise']
    if saas:
        sections.append("# 💰 SaaS & ENTERPRISE\n\n" + "\n".join([format_item(i) for i in saas]))

    # 4. Tool do Dia + Como Usar Hoje
    tool = curated.get('tool_of_day', {})
    # Fallback: tool pode estar no array items (formato antigo)
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

    # 5. Análise do dia
    analysis = curated.get('daily_analysis', '')
    if analysis:
        if isinstance(analysis, list):
            sanitized = []
            for a_item in analysis:
                # Strip heading markers (###, ##, #)
                a_item = re.sub(r'^#{1,6}\s*', '', a_item.strip())
                # Strip leading bullet markers (•, -, *)
                a_item = re.sub(r'^[•\-\*]\s*', '', a_item.strip())
                sanitized.append(f"• {a_item}")
            analysis_text = "\n\n".join(sanitized)
        else:
            analysis_text = analysis
        sections.append(f"# 🔮 ANÁLISE DO DIA\n\n{analysis_text}")

    # 6. Quick Links (headlines rápidos sem análise)
    quick_links = curated.get('quick_links', [])
    if quick_links:
        ql_lines = []
        for ql in quick_links:
            headline = ql.get('headline', '')
            url = ql.get('source_url', '#')
            source = ql.get('source_name', '')
            ql_lines.append(f"→ [{headline}]({url}) *({source})*")
        sections.append(f"# ⚡ QUICK LINKS\n\n" + "\n\n".join(ql_lines))

    # Watch Later (1 vídeo no final)
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
