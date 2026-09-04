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


def build_alert(run_id: str, run_url: str, failed_step: str = "") -> tuple:
    """Monta (title, body, preflight_state) da issue. Puro — nao chama gh."""

    now = datetime.utcnow()
    weekdays_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    date_str = f"{weekdays_pt[now.weekday()]}, {now.day}/{now.month:02d}"

    step_info = f"**Step que falhou:** {failed_step}\n" if failed_step else ""

    # v2.17d: se o pre-flight reprovou, ele sabe MAIS que o `steps.*.outcome`.
    # Sem isso, saldo zerado virava issue "Curadoria (processor.py) falhou" —
    # diagnostico que manda cacar bug em codigo quando o problema e billing.
    pf = {}
    try:
        from preflight import read_fail_state
        pf = read_fail_state() or {}
    except Exception:
        pf = {}

    if pf.get("code"):
        titles = {
            "no_credit": "💳 Sem credito na API Anthropic",
            "auth": "🔑 Credencial da API Anthropic invalida",
            "no_key": "🔑 ANTHROPIC_API_KEY ausente",
            "model_missing": "🤖 Modelo do curador indisponivel",
        }
        label = titles.get(pf["code"], f"Pre-flight reprovou ({pf['code']})")
        title = f"🚨 {label} — {date_str}"
        step_info = (
            f"**Reprovado no pre-flight:** `{pf['code']}`\n"
            f"**O que e:** {pf.get('diagnosis', '')}\n"
        )
        if pf.get("detail"):
            step_info += f"**Resposta da API:** `{pf['detail'][:200]}`\n"
        step_info += (
            "\n> Nada foi coletado nem curado — o pipeline abortou antes de gastar "
            "trabalho. **Nao ha bug de codigo a procurar.**\n"
        )
    else:
        title = f"🚨 Pipeline falhou — {date_str}"

    if pf.get("code"):
        next_steps = (
            "1. Resolver o item acima (billing/credencial — fora do repo)\n"
            "2. Re-disparar: Actions → Run workflow (a coleta usa o cache, "
            "a edicao sai em ~1 min)\n"
            f"3. Logs, se precisar: [run #{run_id}]({run_url})"
        )
    else:
        next_steps = (
            f"1. [Ver logs do GitHub Actions]({run_url})\n"
            "2. Identificar a causa do erro no step acima\n"
            "3. Rodar manualmente se necessario: Actions → Run workflow"
        )

    body = f"""## 🚨 Pipeline do Daily Byte falhou

**Data:** {date_str} ({now.strftime('%H:%M')} UTC)
**Run ID:** {run_id}
{step_info}
O digest de hoje **não foi enviado** porque o pipeline falhou.

### Próximos passos
{next_steps}

---
*Alerta automático do THE DAILY BYTE pipeline*"""

    return title, body, pf


def send_alert(run_id: str, run_url: str, failed_step: str = ""):
    """Cria GitHub Issue com detalhes da falha"""
    from datetime import datetime as _dt
    now = _dt.utcnow()
    title, body, pf = build_alert(run_id, run_url, failed_step)

    # Sempre loga no stdout (visível nos logs do Actions)
    print("=" * 60)
    print("🚨 DAILY BYTE PIPELINE FAILED")
    print(f"   Run ID: {run_id}")
    if pf.get("code"):
        print(f"   Pre-flight: {pf['code']} — {pf.get('diagnosis', '')}")
    elif failed_step:
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
