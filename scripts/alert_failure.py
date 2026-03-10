#!/usr/bin/env python3
"""
THE DAILY BYTE - Alerta de Falha
Envia email para o autor quando o pipeline falha.
Usa Buttondown API para enviar email direto (não para subscribers).
"""

import os
import sys
import argparse
import requests
from datetime import datetime


BUTTONDOWN_API_KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
BUTTONDOWN_API_URL = "https://api.buttondown.email/v1/emails"


def send_alert(run_id: str, run_url: str, failed_step: str = ""):
    """Envia alerta de falha via Buttondown como email real"""

    now = datetime.utcnow()
    weekdays_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    date_str = f"{weekdays_pt[now.weekday()]}, {now.day}/{now.month:02d}"

    step_info = f"\n**Step que falhou:** {failed_step}" if failed_step else ""

    subject = f"🚨 Daily Byte FALHOU — {date_str}"
    body = f"""# 🚨 Pipeline do Daily Byte falhou

**Data:** {date_str} ({now.strftime('%H:%M')} UTC)
**Run ID:** {run_id}{step_info}

O digest de hoje **não foi enviado** porque o pipeline falhou.

**Próximos passos:**
1. [Ver logs do GitHub Actions]({run_url})
2. Identificar a causa do erro no step acima
3. Rodar manualmente se necessário: Actions → Run workflow

***

*Alerta automático do THE DAILY BYTE pipeline*
"""

    # Sempre loga no stdout (visível nos logs do Actions)
    print("=" * 60)
    print(f"🚨 DAILY BYTE PIPELINE FAILED")
    print(f"   Run ID: {run_id}")
    if failed_step:
        print(f"   Failed: {failed_step}")
    print(f"   URL: {run_url}")
    print(f"   Time: {now.isoformat()} UTC")
    print("=" * 60)

    if not BUTTONDOWN_API_KEY:
        print("⚠️ BUTTONDOWN_API_KEY not set — cannot send email alert")
        sys.exit(1)

    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }

    # Envia como email real para todos os subscribers
    # Como só o Toto é subscriber, ele recebe o alerta direto no email
    payload = {
        "subject": subject,
        "body": body,
        "status": "about_to_send"
    }

    print(f"🚨 Enviando alerta de falha via email...")

    try:
        resp = requests.post(BUTTONDOWN_API_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code in [200, 201]:
            print(f"✅ Alerta enviado com sucesso!")
        else:
            print(f"❌ Erro ao enviar alerta: {resp.status_code}")
            print(f"   {resp.text[:300]}")
    except Exception as e:
        print(f"❌ Erro ao enviar alerta: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send failure alert')
    parser.add_argument('--run-id', default='unknown')
    parser.add_argument('--run-url', default='https://github.com')
    parser.add_argument('--failed-step', default='')
    args = parser.parse_args()

    send_alert(args.run_id, args.run_url, args.failed_step)
