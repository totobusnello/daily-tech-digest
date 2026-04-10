#!/usr/bin/env python3
"""
THE DAILY BYTE - Feedback Loop (v2.4)
Puxa métricas de engajamento do Buttondown API para informar curadoria.

Funcionalidades:
- Puxa opens/clicks dos últimos 7 dias
- Calcula open rate, click rate, growth semanal
- Gera resumo dos top 3 assuntos mais engajados
- Salva métricas em /tmp/digest_feedback.json para o curador usar
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================
# CONFIGURAÇÃO
# ============================================

BUTTONDOWN_API_KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
BUTTONDOWN_API_BASE = "https://api.buttondown.email/v1"

FEEDBACK_OUTPUT = "/tmp/digest_feedback.json"


def _get_headers() -> Dict:
    return {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }


# ============================================
# API CALLS
# ============================================

def fetch_recent_emails(days: int = 7, max_emails: int = 10) -> List[Dict]:
    """Busca emails enviados nos últimos N dias via Buttondown API"""
    if not BUTTONDOWN_API_KEY:
        print("⚠️ BUTTONDOWN_API_KEY não configurada — pulando feedback")
        return []

    try:
        resp = requests.get(
            f"{BUTTONDOWN_API_BASE}/emails",
            headers=_get_headers(),
            params={"ordering": "-publish_date", "page_size": max_emails},
            timeout=15
        )

        if resp.status_code != 200:
            print(f"⚠️ Buttondown API erro: {resp.status_code}")
            return []

        data = resp.json()
        emails = data.get('results', data) if isinstance(data, dict) else data

        # Filtrar por data
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = []
        for email in emails:
            pub_date = email.get('publish_date', '')
            if pub_date:
                try:
                    dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).replace(tzinfo=None)
                    if dt >= cutoff:
                        recent.append(email)
                except (ValueError, TypeError):
                    recent.append(email)  # inclui se não conseguir parsear data

        return recent

    except Exception as e:
        print(f"⚠️ Erro buscando emails: {e}")
        return []


def fetch_email_analytics(email_id: str) -> Dict:
    """Busca analytics de um email específico"""
    try:
        resp = requests.get(
            f"{BUTTONDOWN_API_BASE}/emails/{email_id}/analytics",
            headers=_get_headers(),
            timeout=15
        )

        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  ⚠️ Analytics erro para {email_id}: {resp.status_code}")
            return {}

    except Exception as e:
        print(f"  ⚠️ Erro analytics {email_id}: {e}")
        return {}


def fetch_subscriber_count() -> int:
    """Busca contagem de assinantes ativos"""
    try:
        resp = requests.get(
            f"{BUTTONDOWN_API_BASE}/subscribers",
            headers=_get_headers(),
            params={"page_size": 1, "type": "regular"},
            timeout=15
        )

        if resp.status_code == 200:
            data = resp.json()
            return data.get('count', 0)

    except Exception as e:
        print(f"⚠️ Erro contando subscribers: {e}")

    return 0


# ============================================
# ANÁLISE
# ============================================

def analyze_feedback(days: int = 7) -> Dict:
    """Analisa métricas da última semana e gera feedback para o curador"""
    print(f"📊 Analisando feedback dos últimos {days} dias...")

    emails = fetch_recent_emails(days=days)
    if not emails:
        print("  → Nenhum email encontrado no período")
        return {"status": "no_data", "emails_analyzed": 0}

    total_opens = 0
    total_clicks = 0
    total_recipients = 0
    total_unsubs = 0
    email_metrics = []

    for email in emails:
        email_id = email.get('id', '')
        subject = email.get('subject', 'Sem assunto')

        analytics = fetch_email_analytics(email_id)

        if analytics:
            opens = analytics.get('opens', 0)
            clicks = analytics.get('clicks', 0)
            recipients = analytics.get('recipients', 0)
            unsubs = analytics.get('unsubscriptions', 0)

            total_opens += opens
            total_clicks += clicks
            total_recipients += recipients
            total_unsubs += unsubs

            email_metrics.append({
                "subject": subject,
                "date": email.get('publish_date', ''),
                "opens": opens,
                "clicks": clicks,
                "recipients": recipients,
                "open_rate": round(opens / recipients * 100, 1) if recipients > 0 else 0,
                "click_rate": round(clicks / recipients * 100, 1) if recipients > 0 else 0,
            })

            print(f"  📧 {subject[:50]}... → {opens} opens, {clicks} clicks")
        else:
            print(f"  📧 {subject[:50]}... → sem analytics")

    # Métricas agregadas
    avg_open_rate = round(total_opens / total_recipients * 100, 1) if total_recipients > 0 else 0
    avg_click_rate = round(total_clicks / total_recipients * 100, 1) if total_recipients > 0 else 0

    # Top 3 assuntos mais engajados (por clicks)
    top_by_clicks = sorted(email_metrics, key=lambda x: x.get('clicks', 0), reverse=True)[:3]

    # Subscriber count
    subscriber_count = fetch_subscriber_count()

    # Extrair temas dos subjects mais clicados
    top_themes = []
    for em in top_by_clicks:
        subject = em.get('subject', '')
        # Extrair hook (antes do "|")
        hook = subject.split('|')[0].strip() if '|' in subject else subject[:50]
        top_themes.append({
            "hook": hook,
            "clicks": em.get('clicks', 0),
            "open_rate": em.get('open_rate', 0),
        })

    # Extrair hooks recentes (últimos 5 dias) para evitar repetição de subject lines
    recent_hooks = []
    for em in email_metrics:
        subject = em.get('subject', '')
        hook = subject.split('|')[0].strip() if '|' in subject else subject[:50]
        if hook:
            recent_hooks.append({
                "hook": hook,
                "date": em.get('date', '')[:10],
            })

    feedback = {
        "status": "ok",
        "period_days": days,
        "emails_analyzed": len(email_metrics),
        "generated_at": datetime.utcnow().isoformat(),
        "aggregate": {
            "avg_open_rate": avg_open_rate,
            "avg_click_rate": avg_click_rate,
            "total_opens": total_opens,
            "total_clicks": total_clicks,
            "total_unsubs": total_unsubs,
            "subscriber_count": subscriber_count,
        },
        "top_themes": top_themes,
        "recent_hooks": recent_hooks,
        "curator_hint": _generate_curator_hint(top_themes, avg_open_rate, avg_click_rate),
        "email_details": email_metrics,
    }

    return feedback


def _generate_curator_hint(top_themes: List[Dict], open_rate: float, click_rate: float) -> str:
    """Gera dica textual para o curador baseada nos dados de engajamento"""
    if not top_themes:
        return "Sem dados de engajamento suficientes para gerar recomendações."

    hints = []

    # Top temas
    theme_names = [t['hook'] for t in top_themes if t.get('hook')]
    if theme_names:
        hints.append(f"Temas com mais engajamento esta semana: {', '.join(theme_names)}.")

    # Open rate benchmark
    if open_rate > 50:
        hints.append(f"Open rate excelente ({open_rate}%). Subject lines estão funcionando bem.")
    elif open_rate > 35:
        hints.append(f"Open rate bom ({open_rate}%). Continuar com hooks curtos e específicos.")
    elif open_rate > 20:
        hints.append(f"Open rate médio ({open_rate}%). Testar subject lines mais provocativas.")
    else:
        hints.append(f"Open rate baixo ({open_rate}%). Revisar horário de envio e subject lines.")

    # Click rate
    if click_rate > 5:
        hints.append(f"Click rate alto ({click_rate}%). Curadoria está acertando.")
    elif click_rate > 2:
        hints.append(f"Click rate ok ({click_rate}%). Priorizar temas que geraram mais cliques.")
    else:
        hints.append(f"Click rate baixo ({click_rate}%). Considerar CTAs mais diretos e headlines mais fortes.")

    return " ".join(hints)


# ============================================
# SAVE / LOAD
# ============================================

def save_feedback(feedback: Dict, path: str = FEEDBACK_OUTPUT):
    """Salva feedback para uso pelo curador"""
    with open(path, 'w') as f:
        json.dump(feedback, f, indent=2, ensure_ascii=False)
    print(f"💾 Feedback salvo em {path}")


def load_feedback(path: str = FEEDBACK_OUTPUT) -> Optional[Dict]:
    """Carrega feedback salvo (se existir)"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ============================================
# MAIN
# ============================================

def collect_feedback() -> Dict:
    """Pipeline completo: coleta + análise + save"""
    feedback = analyze_feedback(days=7)
    if feedback.get('status') == 'ok':
        save_feedback(feedback)
    return feedback


if __name__ == "__main__":
    feedback = collect_feedback()

    print(f"\n📊 Resumo:")
    print(f"   Emails analisados: {feedback.get('emails_analyzed', 0)}")

    agg = feedback.get('aggregate', {})
    print(f"   Open rate médio: {agg.get('avg_open_rate', 0)}%")
    print(f"   Click rate médio: {agg.get('avg_click_rate', 0)}%")
    print(f"   Subscribers: {agg.get('subscriber_count', 0)}")

    print(f"\n💡 Dica pro curador:")
    print(f"   {feedback.get('curator_hint', 'N/A')}")
