#!/usr/bin/env python3
"""
THE DAILY BYTE - Pre-flight
Falha cedo e com o diagnostico certo, antes de gastar a coleta.

Motivo (2026-09-03): a edicao do dia morreu porque o saldo de credito da conta
Anthropic zerou (HTTP 400, "Your credit balance is too low"). O pipeline so
descobriu no Step 3, depois de gastar ~4 min coletando 840 itens, e o alerta
apontou "Curadoria (processor.py)" — que manda o leitor cacar bug em codigo
quando o problema era billing. Mesmo pecado da regra 62: colapsar modos de
falha distintos numa mensagem so.

Este modulo faz um ping minimo (max_tokens=1) antes da coleta e CLASSIFICA a
resposta. Custo por run: ~US$ 0,00002.

⚠️ Falha ABERTA (mesma logica do guard da regra 80): erro de rede, timeout ou
resposta estranha NAO bloqueiam o pipeline. So bloqueia o que e comprovadamente
fatal e que nenhuma etapa seguinte contorna — saldo zerado, chave invalida,
chave ausente, modelo inexistente. Melhor arriscar rodar e falhar adiante que
engolir a edicao do dia por um blip de rede.
"""

import os
import sys
import json

FAIL_STATE_PATH = "/tmp/digest_preflight_fail.json"

# Codigos que abortam o pipeline. O resto e informativo.
BLOCKING = {"no_key", "no_credit", "auth", "model_missing"}

# Mensagem por codigo: o que aconteceu + onde se resolve.
DIAGNOSIS = {
    "no_key": (
        "ANTHROPIC_API_KEY nao esta no ambiente. "
        "No Actions: Settings > Secrets and variables > Actions. "
        "Local: `source .env`."
    ),
    "no_credit": (
        "Saldo de credito da conta Anthropic esgotado — a API recusa qualquer "
        "chamada. NAO e bug de codigo. Recarregue em "
        "console.anthropic.com/settings/billing (ative auto-reload para nao "
        "repetir). A conta da API e um bolso separado da subscription do "
        "Claude Code."
    ),
    "auth": (
        "ANTHROPIC_API_KEY invalida ou revogada. Gere outra em "
        "console.anthropic.com/settings/keys e atualize o secret."
    ),
    "model_missing": (
        "O modelo configurado nao existe ou a conta nao tem acesso a ele. "
        "Confira `curator.model` no config.yaml."
    ),
    "rate_limit": (
        "Rate limit no ping. Nao bloqueia: o processor tem retry com backoff."
    ),
    "unknown": "Resposta inesperada no ping. Nao bloqueia — segue o pipeline.",
    "ok": "Credito e credencial OK.",
}


def _classify_bad_request(msg: str) -> str:
    """Separa a 400 de saldo das outras 400.

    A unica 400 que muda o rumo do diagnostico e a de credito — ela significa
    "recarregue a conta", enquanto qualquer outra significa "o ping esta
    malformado", que nao e problema do pipeline. Mensagem real observada em
    2026-09-03: "Your credit balance is too low to access the Anthropic API.
    Please go to Plans & Billing to upgrade or purchase credits."
    """
    return "no_credit" if "credit balance" in (msg or "").lower() else "unknown"


def _configured_model(default: str = "claude-sonnet-4-6") -> str:
    """Le curator.model do config.yaml. Cai no default se nao der."""
    try:
        import yaml
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        return (cfg.get("curator") or {}).get("model") or default
    except Exception:
        return default


def check_anthropic(api_key: str = None, model: str = None) -> tuple:
    """Ping minimo na API. Devolve (code, detail).

    code: ok | no_key | no_credit | auth | model_missing | rate_limit | unknown
    """
    api_key = api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key.strip():
        return ("no_key", "")

    model = model or _configured_model()

    try:
        import anthropic
    except ImportError:
        # Sem SDK o processor tambem nao roda, mas isso e erro de setup do
        # runner (requirements.txt), nao de credito — deixa o pipeline seguir
        # para falhar no lugar que descreve o problema de verdade.
        return ("unknown", "SDK anthropic nao instalado")

    try:
        client = anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=20.0)
        client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return ("ok", "")
    except anthropic.BadRequestError as e:
        return (_classify_bad_request(str(getattr(e, "message", "") or e)),
                str(getattr(e, "message", "") or e))
    except anthropic.AuthenticationError as e:
        return ("auth", str(getattr(e, "message", "") or e))
    except anthropic.PermissionDeniedError as e:
        return ("auth", str(getattr(e, "message", "") or e))
    except anthropic.NotFoundError as e:
        return ("model_missing", f"{model}: {getattr(e, 'message', '') or e}")
    except anthropic.RateLimitError as e:
        return ("rate_limit", str(getattr(e, "message", "") or e))
    except Exception as e:
        # Rede, TLS, timeout, 5xx: falha aberta.
        return ("unknown", f"{type(e).__name__}: {e}")


def _write_fail_state(code: str, detail: str):
    """Deixa o motivo em disco para o alert_failure.py titular a issue certo."""
    from datetime import datetime, timezone
    try:
        with open(FAIL_STATE_PATH, "w") as f:
            json.dump({
                "code": code,
                "diagnosis": DIAGNOSIS.get(code, ""),
                "detail": detail[:500],
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # o exit code e o log ja cumprem o essencial


def _clear_fail_state():
    try:
        if os.path.exists(FAIL_STATE_PATH):
            os.remove(FAIL_STATE_PATH)
    except Exception:
        pass


def read_fail_state() -> dict:
    """Usado pelo alert_failure.py. {} se nao houver pre-flight reprovado."""
    try:
        with open(FAIL_STATE_PATH) as f:
            return json.load(f) or {}
    except Exception:
        return {}


def run(verbose: bool = True) -> bool:
    """Roda o pre-flight. True = pode seguir. False = aborta."""
    code, detail = check_anthropic()
    blocking = code in BLOCKING

    if verbose:
        icon = "✅" if code == "ok" else ("❌" if blocking else "⚠️")
        print(f"{icon} Pre-flight [{code}] {DIAGNOSIS.get(code, '')}")
        if detail and code != "ok":
            print(f"   detalhe: {detail[:300]}")

    if blocking:
        _write_fail_state(code, detail)
    else:
        _clear_fail_state()

    return not blocking


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
