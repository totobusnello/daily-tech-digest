#!/usr/bin/env python3
"""
THE DAILY BYTE - Alerta de Falha
Cria GitHub Issue quando o pipeline falha.
Notificação chega por email via GitHub Notifications (só para o owner).
Não usa Buttondown (evita spam para subscribers).
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime


def send_alert(run_id: str, run_url: str, failed_step: str = ""):
    """Cria GitHub Issue com detalhes da falha"""

    now = datetime.utcnow()
    weekdays_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    date_str = f"{weekdays_pt[now.weekday()]}, {now.day}/{now.month:02d}"

    step_info = f"**Step que falhou:** {failed_step}\n" if failed_step else ""

    title = f"🚨 Pipeline falhou — {date_str}"
    body = f"""## 🚨 Pipeline do Daily Byte falhou

**Data:** {date_str} ({now.strftime('%H:%M')} UTC)
**Run ID:** {run_id}
{step_info}
O digest de hoje **não foi enviado** porque o pipeline falhou.

### Próximos passos
1. [Ver logs do GitHub Actions]({run_url})
2. Identificar a causa do erro no step acima
3. Rodar manualmente se necessário: Actions → Run workflow

---
*Alerta automático do THE DAILY BYTE pipeline*"""

    # Sempre loga no stdout (visível nos logs do Actions)
    print("=" * 60)
    print("🚨 DAILY BYTE PIPELINE FAILED")
    print(f"   Run ID: {run_id}")
    if failed_step:
        print(f"   Failed: {failed_step}")
    print(f"   URL: {run_url}")
    print(f"   Time: {now.isoformat()} UTC")
    print("=" * 60)

    # Cria GitHub Issue via gh CLI (disponível no GitHub Actions runner)
    try:
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--title", title,
                "--body", body,
                "--label", "pipeline-failure",
            ],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"✅ Issue criada: {result.stdout.strip()}")
        else:
            # Label pode não existir, tenta sem label
            result = subprocess.run(
                [
                    "gh", "issue", "create",
                    "--title", title,
                    "--body", body,
                ],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"✅ Issue criada: {result.stdout.strip()}")
            else:
                print(f"❌ Erro ao criar issue: {result.stderr}")
                sys.exit(1)
    except FileNotFoundError:
        print("❌ gh CLI não encontrado — rodando fora do GitHub Actions?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao criar issue: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send failure alert')
    parser.add_argument('--run-id', default='unknown')
    parser.add_argument('--run-url', default='https://github.com')
    parser.add_argument('--failed-step', default='')
    args = parser.parse_args()

    send_alert(args.run_id, args.run_url, args.failed_step)
