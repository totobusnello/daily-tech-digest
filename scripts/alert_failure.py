#!/usr/bin/env python3
"""
THE DAILY BYTE - Alerta de Falha
Envia email para o autor quando o pipeline falha.
Usa Buttondown API (mesmo canal do digest) com envio direto para lab@nuvini.com.br
"""

import os
import sys
import argparse
import requests
from datetime import datetime


BUTTONDOWN_API_KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
BUTTONDOWN_API_URL = "https://api.buttondown.email/v1/emails"
ALERT_RECIPIENT = "lab@nuvini.com.br"


def send_alert(run_id: str, run_url: str):
    """Envia alerta de falha via Buttondown como draft (visível na inbox do Buttondown)"""

    if not BUTTONDOWN_API_KEY:
        # Fallback: print to stdout (aparece nos logs do GitHub Actions)
        print("=" * 60)
        print("🚨 DAILY BYTE PIPELINE FAILED")
        print(f"   Run ID: {run_id}")
        print(f"   URL: {run_url}")
        print(f"   Time: {datetime.utcnow().isoformat()} UTC")
        print("=" * 60)
        print("⚠️ BUTTONDOWN_API_KEY not set — cannot send email alert")
        sys.exit(1)

    now = datetime.utcnow()
    weekdays_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    date_str = f"{weekdays_pt[now.weekday()]}, {now.day}/{now.month:02d}"

    subject = f"🚨 Daily Byte FALHOU — {date_str}"
    body = f"""# 🚨 Pipeline do Daily Byte falhou

**Data:** {date_str} ({now.strftime('%H:%M')} UTC)
**Run ID:** {run_id}

O digest de hoje **não foi enviado** porque o pipeline falhou.

**Próximos passos:**
1. [Ver logs do GitHub Actions]({run_url})
2. Identificar qual step falhou (coleta, curadoria, ou envio)
3. Rodar manualmente se necessário: Actions → Run workflow

***

*Alerta automático do THE DAILY BYTE pipeline*
"""

    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }

    # Envia como DRAFT — aparece apenas no painel do Buttondown para revisão
    # NÃO envia para subscribers (alertas de falha são internos)
    payload = {
        "subject": subject,
        "body": body,
        "status": "draft"
    }

    print(f"🚨 Enviando alerta de falha...")

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
    args = parser.parse_args()

    send_alert(args.run_id, args.run_url)
