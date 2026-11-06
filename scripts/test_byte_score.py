"""Testes standalone do pipeline (sem pytest). Rodar: python scripts/test_byte_score.py

Cobre Byte Score (v2.13/v2.14), sanitização de URL (v2.15.1) e o corte
estratificado + filtro BR + strip de emoji (v2.16).

Nota: este arquivo foi reescrito na v2.16. A versão anterior testava
`_byte_badge_html`/`_byte_badge_md`, funções que a v2.14 substituiu pelo LED VU
meter — o suite quebrava logo na primeira linha e ninguém percebeu, porque nada
no workflow o executa. Se você adicionar função nova ao sender/processor,
adicione o caso aqui.
"""
import sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))
import sender
import processor

def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        check.failed += 1
check.failed = 0


# ── Byte Score: faixas (score inteiro desde v2.14) ──
check("10 -> GIGABYTE", sender._byte_tier(10)[0] == "GIGABYTE")
check("9 -> GIGABYTE", sender._byte_tier(9)[0] == "GIGABYTE")
check("8 -> MEGABYTE", sender._byte_tier(8)[0] == "MEGABYTE")
check("7 -> MEGABYTE", sender._byte_tier(7)[0] == "MEGABYTE")
check("6 -> KILOBYTE", sender._byte_tier(6)[0] == "KILOBYTE")
check("5 -> KILOBYTE", sender._byte_tier(5)[0] == "KILOBYTE")
check("4 -> byte", sender._byte_tier(4)[0] == "byte")
check("0 -> byte", sender._byte_tier(0)[0] == "byte")

# ── Cores por tier ──
check("GIGA bg laranja", sender._byte_tier(9)[2] == "#FF6B35")
check("MEGA bg", sender._byte_tier(7)[2] == "#F7A072")
check("KILO bg", sender._byte_tier(5)[2] == "#6B7280")
check("byte bg", sender._byte_tier(2)[2] == "#E5E7EB")

# ── Entradas inválidas ──
check("None -> None", sender._byte_tier(None) is None)
check("texto -> None", sender._byte_tier("abc") is None)
check("negativo -> None", sender._byte_tier(-1) is None)
check("NaN -> None", sender._byte_tier(float('nan')) is None)
check("acima de 10 -> clamp GIGABYTE", sender._byte_tier(99)[0] == "GIGABYTE")
check("acima de 10 -> valor 10", sender._byte_tier(99)[4] == 10)

# ── LED VU meter (v2.14) ──
check("LED html vazio p/ None", sender._byte_led_html(None) == "")
check("LED md vazio p/ None", sender._byte_led_md(None) == "")
check("LED html vazio p/ negativo", sender._byte_led_html(-1) == "")
_led9 = sender._byte_led_html(9)
check("LED html 9 renderiza", len(_led9) > 0)
check("LED html 9 mostra o numero", "9" in _led9)
check("LED html alinha o piso", "vertical-align:2px" in _led9)
_led_md = sender._byte_led_md(7)
check("LED md 7 renderiza", len(_led_md) > 0 and "7" in _led_md)

# ── Sanitização de URL (v2.15.1) ──
check("url http ok", sender._safe_url("http://exemplo.com/a") == "http://exemplo.com/a")
check("url https ok", sender._safe_url("https://exemplo.com/a") == "https://exemplo.com/a")
check("javascript: bloqueado", sender._safe_url("javascript:alert(1)") == "#")
check("data: bloqueado", sender._safe_url("data:text/html,<script>") == "#")
check("vbscript: bloqueado", sender._safe_url("vbscript:msgbox") == "#")
check("url vazia -> #", sender._safe_url("") == "#")
check("url None -> #", sender._safe_url(None) == "#")
check("sem host -> #", sender._safe_url("https://") == "#")
check("aspas escapadas", '"' not in sender._safe_url('https://x.com/a"onmouseover="evil()'))

# ── Strip de emoji no subject (v2.16) ──
check("1 fogo removido", sender._strip_leading_fire("\U0001F525 Manchete") == "Manchete")
check("3 fogos removidos",
      sender._strip_leading_fire("\U0001F525 \U0001F525 \U0001F525 TSMC investe") == "TSMC investe")
check("sem fogo fica intacto", sender._strip_leading_fire("Alibaba sacode") == "Alibaba sacode")
check("fogo no meio preservado",
      sender._strip_leading_fire("Preco do \U0001F525 sobe") == "Preco do \U0001F525 sobe")
check("alerta removido", sender._strip_leading_fire("⚠️ Casa Branca") == "Casa Branca")
check("string vazia", sender._strip_leading_fire("") == "")
check("None -> vazio", sender._strip_leading_fire(None) == "")
check("so fogo -> vazio", sender._strip_leading_fire("\U0001F525") == "")

# ── Classificação de fonte (v2.16) ──
check("Bloomberg -> mainstream", processor._source_tier({"source_name": "Bloomberg"}) == "mainstream")
check("BBC -> mainstream", processor._source_tier({"source_name": "bbc_world"}) == "mainstream")
check("NeoFeed -> br", processor._source_tier({"source_name": "neofeed"}) == "br")
check("InfoMoney -> br", processor._source_tier({"source_name": "infomoney"}) == "br")
check("Simon Willison -> primaria",
      processor._source_tier({"source_name": "sub_simon_willison"}) == "primaria")
check("arXiv -> primaria", processor._source_tier({"source_name": "arxiv_ai"}) == "primaria")
check("HN -> primaria", processor._source_tier({"source_name": "hacker_news"}) == "primaria")

# ── Filtro de relevância BR (v2.16) ──
_rel = processor._br_item_relevante
check("BR generalista + tech = passa",
      _rel({"source_name": "infomoney", "title": "Nubank lanca plataforma de IA para PMEs"}))
check("BR generalista + esporte = corta",
      not _rel({"source_name": "infomoney", "title": "Fifa abre inquerito sobre briga na final"}))
check("BR generalista + variedades = corta",
      not _rel({"source_name": "valor_economico", "title": "Calor aumenta o risco de micoses pos-praia"}))
check("BR generalista + politica partidaria = corta",
      not _rel({"source_name": "poder360", "title": "Deputado chama colega de papel higienico"}))
check("BR especializada sempre passa",
      _rel({"source_name": "tecmundo", "title": "Chrome corrige tres falhas criticas"}))
check("placeholder de scraping = corta",
      not _rel({"source_name": "TechDrop", "title": "Home | TechDrops"}))
check("titulo vazio = corta", not _rel({"source_name": "neofeed", "title": ""}))

# ── Corte estratificado (v2.16) ──
def _mk(n, src, h=1):
    return [{"title": f"Noticia {src} numero {i} sobre tecnologia", "source_name": src,
             "hours_ago": h} for i in range(n)]

def _conta_tiers(cut):
    t = {}
    for it in cut:
        k = processor._source_tier(it)
        t[k] = t.get(k, 0) + 1
    return t

# Cenário 1 — há alternativa de sobra: o teto de mainstream DEVE valer.
_pool_rico = _mk(120, "Bloomberg") + _mk(40, "sub_simon_willison") + _mk(40, "neofeed")
_cut_rico = processor._stratified_cut(_pool_rico, total=80)
_t_rico = _conta_tiers(_cut_rico)
check("corte devolve o total pedido", len(_cut_rico) == 80)
check("com alternativa, mainstream respeita o teto", _t_rico.get("mainstream", 0) <= 24)
check("primaria atinge a quota minima", _t_rico.get("primaria", 0) >= 32)
check("br atinge a quota minima", _t_rico.get("br", 0) >= 12)

# Cenário 2 — sem alternativa: o teto CEDE para não entregar pool pequeno.
# (Um dia em que nenhuma fonte indie/BR publicou não pode reduzir o material
#  do curador de 80 para 24 itens.)
_cut_pobre = processor._stratified_cut(_mk(200, "Bloomberg"), total=80)
check("sem alternativa, o corte ainda preenche o total", len(_cut_pobre) == 80)
check("sem alternativa, o teto cede", _conta_tiers(_cut_pobre).get("mainstream", 0) == 80)

# Cenário 3 — pool pequeno volta inteiro, sem inventar item.
check("pool menor que o total volta inteiro",
      len(processor._stratified_cut(_mk(10, "Bloomberg"), total=80)) == 10)

# Cenário 4 — sem duplicatas no resultado.
_cut_dup = processor._stratified_cut(_pool_rico, total=80)
check("corte nao duplica itens", len({id(x) for x in _cut_dup}) == len(_cut_dup))


# ============================================================================
# v2.17c — guard de idempotencia (already_sent_today)
# ============================================================================
# O disparo agora tem duas origens: o cron da VPS (workflow_dispatch, 09:41
# UTC) e o schedule do GitHub as 10:40 UTC como rede de seguranca. Sem o guard,
# um dia em que os dois rodam manda dois emails para a lista.
# A API real nao e chamada aqui: injetamos a resposta em requests.get.

print("\n--- guard de idempotencia (v2.17c) ---")

class _FakeResp:
    def __init__(self, payload, boom=False):
        self._p, self._boom = payload, boom
    def raise_for_status(self):
        if self._boom:
            raise RuntimeError("500 Server Error")
    def json(self):
        return self._p

def _com_api(payload, boom=False):
    """Roda already_sent_today com a resposta do Buttondown injetada."""
    real_get, real_key = sender.requests.get, sender.BUTTONDOWN_API_KEY
    sender.requests.get = lambda *a, **k: _FakeResp(payload, boom)
    sender.BUTTONDOWN_API_KEY = "fake-key-para-teste"
    try:
        return sender.already_sent_today()
    finally:
        sender.requests.get, sender.BUTTONDOWN_API_KEY = real_get, real_key

_hoje = datetime.now(sender.BRT)
_ontem = _hoje - timedelta(days=1)

def _email(dt, status="sent", subject="Edicao"):
    return {"publish_date": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "status": status, "subject": subject}

check("detecta edicao ja enviada hoje",
      _com_api({"results": [_email(_hoje)]}) is True)
check("edicao de ontem nao bloqueia hoje",
      _com_api({"results": [_email(_ontem)]}) is False)
check("lista vazia libera o envio",
      _com_api({"results": []}) is False)
check("rascunho de hoje nao conta como enviado",
      _com_api({"results": [_email(_hoje, status="draft")]}) is False)
check("agendado de hoje conta como enviado",
      _com_api({"results": [_email(_hoje, status="scheduled")]}) is True)
check("acha o envio de hoje mesmo atras de outros",
      _com_api({"results": [_email(_ontem), _email(_ontem), _email(_hoje)]}) is True)
check("publish_date corrompido nao quebra o guard",
      _com_api({"results": [{"publish_date": "nao-e-data", "status": "sent"},
                            _email(_hoje)]}) is True)
check("item sem publish_date e ignorado",
      _com_api({"results": [{"status": "sent"}]}) is False)
check("API fora devolve None (fail-open, nao False)",
      _com_api({}, boom=True) is None)
check("resposta sem 'results' nao quebra",
      _com_api({"detail": "erro"}) is False)

# Sem chave nao da para verificar -> None, e send() trata como "pode enviar".
_k = sender.BUTTONDOWN_API_KEY
sender.BUTTONDOWN_API_KEY = ""
check("sem BUTTONDOWN_API_KEY devolve None", sender.already_sent_today() is None)
sender.BUTTONDOWN_API_KEY = _k

# O guard NAO pode agir no preview nem no envio manual: so o fallback o pede.
_chamou = {"n": 0}
_real = sender.already_sent_today
sender.already_sent_today = lambda *a, **k: _chamou.__setitem__("n", _chamou["n"] + 1) or True
try:
    sender.send(preview=True, skip_if_sent_today=True)
except Exception:
    pass  # sem /tmp/digest_curated.json o preview morre depois do ponto que importa
check("preview nunca consulta o guard", _chamou["n"] == 0)
sender.already_sent_today = _real


# ── v2.17d: pre-flight de credito ──────────────────────────────────────────
# A edicao de 2026-09-03 morreu por saldo zerado na conta Anthropic. O
# pipeline gastou 4 min coletando antes de descobrir, e o alerta culpou o
# processor. Estes casos travam as duas regras: o que bloqueia e o que
# falha aberto.
import preflight
import alert_failure

check("no_credit bloqueia", "no_credit" in preflight.BLOCKING)
check("auth bloqueia", "auth" in preflight.BLOCKING)
check("no_key bloqueia", "no_key" in preflight.BLOCKING)
check("model_missing bloqueia", "model_missing" in preflight.BLOCKING)
# Falha aberta: blip de rede ou rate limit no ping nao pode matar a edicao.
check("unknown NAO bloqueia", "unknown" not in preflight.BLOCKING)
check("rate_limit NAO bloqueia", "rate_limit" not in preflight.BLOCKING)
check("ok NAO bloqueia", "ok" not in preflight.BLOCKING)
check("todo codigo bloqueante tem diagnostico",
      all(preflight.DIAGNOSIS.get(c) for c in preflight.BLOCKING))

# A 400 de saldo tem de virar no_credit; qualquer outra 400 e "unknown"
# (falha aberta) — mensagem literal capturada no run 33740197964.
_real_msg = ("Your credit balance is too low to access the Anthropic API. "
             "Please go to Plans & Billing to upgrade or purchase credits.")
check("400 de saldo -> no_credit",
      preflight._classify_bad_request(_real_msg) == "no_credit")
check("no_credit e case-insensitive",
      preflight._classify_bad_request("YOUR CREDIT BALANCE IS TOO LOW") == "no_credit")
check("outra 400 -> unknown (falha aberta)",
      preflight._classify_bad_request("max_tokens: must be >= 1") == "unknown")
check("400 vazia -> unknown", preflight._classify_bad_request("") == "unknown")
check("400 None -> unknown", preflight._classify_bad_request(None) == "unknown")

# Chave ausente e detectada sem tocar a rede.
check("chave vazia -> no_key", preflight.check_anthropic(api_key="")[0] == "no_key")
check("chave em branco -> no_key", preflight.check_anthropic(api_key="   ")[0] == "no_key")

# O modelo sai do config.yaml, nao hardcoded.
check("modelo vem do config", preflight._configured_model() == "claude-sonnet-4-6")

# read_fail_state tolera ausencia/lixo — nunca levanta.
_orig = preflight.FAIL_STATE_PATH
preflight.FAIL_STATE_PATH = "/tmp/digest_preflight_nao_existe_xyz.json"
check("fail_state ausente -> {}", preflight.read_fail_state() == {})
preflight.FAIL_STATE_PATH = "/tmp/digest_preflight_lixo.json"
open(preflight.FAIL_STATE_PATH, "w").write("{isso nao e json")
check("fail_state corrompido -> {}", preflight.read_fail_state() == {})
os.remove(preflight.FAIL_STATE_PATH)
preflight.FAIL_STATE_PATH = _orig

# ── O alerta precisa NOMEAR billing, nao acusar o processor ──
_state = "/tmp/digest_preflight_test_state.json"
import json as _json
with open(_state, "w") as f:
    _json.dump({"code": "no_credit",
                "diagnosis": preflight.DIAGNOSIS["no_credit"],
                "detail": "Your credit balance is too low"}, f)
preflight.FAIL_STATE_PATH = _state

_t, _b, _pf = alert_failure.build_alert("42", "http://x", "🤖 Curadoria (processor.py)")
check("titulo aponta credito", "credito" in _t.lower())
check("titulo NAO culpa curadoria", "curadoria" not in _t.lower())
check("corpo diz que nao ha bug", "Nao ha bug de codigo" in _b)
check("corpo manda re-disparar", "Run workflow" in _b)
check("corpo cita o billing", "billing" in _b.lower())
check("build_alert devolve o state", _pf.get("code") == "no_credit")

# Sem pre-flight reprovado, o alerta volta a ser o generico de sempre.
os.remove(_state)
preflight.FAIL_STATE_PATH = "/tmp/digest_preflight_nao_existe_xyz.json"
_t2, _b2, _pf2 = alert_failure.build_alert("42", "http://x", "📰 Coleta (collector.py)")
check("sem pre-flight -> titulo generico", _t2.startswith("🚨 Pipeline falhou"))
check("sem pre-flight -> mostra o step", "Coleta (collector.py)" in _b2)
check("sem pre-flight -> state vazio", _pf2 == {})
preflight.FAIL_STATE_PATH = _orig


# ── v2.18: benchmark The Rundown AI ────────────────────────────────────────
print("\n--- v2.18: emoji do subject ---")
check("emoji simples aceito", sender._subject_emoji("\U0001F4C8") == "\U0001F4C8")
check("bandeira aceita", sender._subject_emoji("\U0001F1E7\U0001F1F7") == "\U0001F1E7\U0001F1F7")
check("emoji com variation selector", sender._subject_emoji("⚖️") == "⚖️")
check("emoji ZWJ aceito", sender._subject_emoji("\U0001F468‍\U0001F4BB") == "\U0001F468‍\U0001F4BB")
check("vazio -> fogo", sender._subject_emoji("") == "\U0001F525")
check("None -> fogo", sender._subject_emoji(None) == "\U0001F525")
check("texto -> fogo", sender._subject_emoji("alta") == "\U0001F525")
check("emoji + texto -> fogo", sender._subject_emoji("\U0001F4C8 alta") == "\U0001F525")
check("dois emojis -> fogo", sender._subject_emoji("\U0001F4C8\U0001F4C9") == "\U0001F525")
check("nao-string -> fogo", sender._subject_emoji(7) == "\U0001F525")

check("subject usa emoji do curador",
      sender._compose_subject({"subject_emoji": "\U0001F4C8", "subject_hook": "Anthropic dobra o ritmo"})
      == "\U0001F4C8 Anthropic dobra o ritmo")
check("subject sem emoji -> fogo",
      sender._compose_subject({"subject_hook": "Anthropic dobra o ritmo"}) == "\U0001F525 Anthropic dobra o ritmo")
check("hook ja com emoji nao empilha",
      sender._compose_subject({"subject_emoji": "\U0001F4C8", "subject_hook": "\U0001F4C8 \U0001F525 Anthropic dobra"})
      == "\U0001F4C8 Anthropic dobra")
check("emoji no meio do hook preservado",
      sender._compose_subject({"subject_emoji": "\U0001F4C8", "subject_hook": "Preco do \U0001F525 sobe"})
      == "\U0001F4C8 Preco do \U0001F525 sobe")
check("sem hook -> Daily Byte",
      sender._compose_subject({"subject_emoji": "\U0001F4C8"}) == "\U0001F4C8 Daily Byte")

print("\n--- v2.18: preheader 'MAIS:' ---")
def _it(h, score, cat="hoje_no_byte", big=False, **kw):
    d = {"headline": h, "byte_score": score, "category": cat, "big_story": big,
         "source_url": "https://ex.com/" + h.replace(" ", "-"), "why_it_matters": "Teste: x."}
    d.update(kw)
    return d

_cur = {
    "subject_hook": "Anthropic dobra o ritmo da pesquisa interna",
    "items": [
        _it("Anthropic dobra ritmo de pesquisa com IA propria", 9, big=True),
        _it("Google corta preco do video em 30%", 6),
        _it("OpenAI lanca modelo de imagem com GIFs", 8),
        _it("Video essencial", 0, cat="watch_later"),
    ],
}
_pre = sender._preheader(_cur)
check("preheader comeca com MAIS:", _pre.startswith("MAIS: "))
check("preheader pega o maior byte fora da big story", "OpenAI lanca modelo de imagem" in _pre)
check("preheader nunca usa watch_later", "Video essencial" not in _pre)

_cur2 = {"subject_hook": "OpenAI lanca modelo de imagem com GIFs",
         "items": [_it("OpenAI lanca modelo de imagem com GIFs no ChatGPT", 8),
                   _it("Google corta preco do video em 30%", 6)]}
check("preheader pula item que repete o subject", "Google corta preco" in sender._preheader(_cur2))

_cur3 = {"subject_hook": "x", "items": [], "number_of_day": {"value": "$600B", "context": "Meta de compute da OpenAI"}}
check("sem itens -> cai no numero do dia", sender._preheader(_cur3) == "MAIS: $600B — Meta de compute da OpenAI")
check("nada -> vazio", sender._preheader({}) == "")

_longo = {"subject_hook": "z", "items": [_it("palavra " * 40, 7)]}
_pl = sender._preheader(_longo)
check("preheader truncado <= 140", len(_pl) <= 140 and _pl.endswith("…"))

print("\n--- v2.18: abertura + sumario ---")
_cur_toc = {
    "items": [
        _it("Big story aqui", 9, big=True),
        _it("Segunda historia", 7),
        _it("Terceira historia", 6, cat="saas_enterprise"),
        _it("Quarta historia", 5),
        _it("Video", 0, cat="watch_later"),
    ],
    "tool_of_day": {"headline": "Granola — notas de reuniao"},
}
_toc = sender._toc_lines(_cur_toc)
check("sumario tem 4 linhas", len(_toc) == 4)
check("sumario abre pela big story", _toc[0] == "Big story aqui")
check("sumario fecha com a tool", _toc[-1] == "Tool do dia: Granola — notas de reuniao")
check("sumario sem watch_later", all("Video" != t for t in _toc))
check("sumario sem tool -> 3 historias", len(sender._toc_lines({"items": _cur_toc["items"]})) == 3)

_html = sender.generate_email_html(dict(_cur_toc, lede="Abertura <b>arma</b> a tensao."))
check("lede renderizado e escapado", "Abertura &lt;b&gt;arma&lt;/b&gt; a tensao." in _html)
check("bloco Nesta edicao presente", "NESTA EDI" in _html)
_html_sem = sender.generate_email_html({"items": [_it("So uma", 7)]})
check("sem lede e 1 historia -> sem bloco", "NESTA EDI" not in _html_sem)

print("\n--- v2.18: details nas historias principais ---")
_ih = sender._render_item_html(_it("Com detalhes", 7, details=["Preco cai de US$15 para US$6", "<script>x</script>"]))
check("details renderizados no item", "Preco cai de US$15 para US$6" in _ih)
check("details escapados", "<script>" not in _ih and "&lt;script&gt;" in _ih)
_ih4 = sender._render_item_html(_it("Muitos", 7, details=["a1", "a2", "a3", "a4"]))
check("details cortados em 3", "a3" in _ih4 and "a4" not in _ih4)
check("item sem details fica igual", "&bull;" not in sender._render_item_html(_it("Sem", 7)))
check("details nao-lista ignorado", "&bull;" not in sender._render_item_html(_it("Str", 7, details="texto solto")))

print("\n--- v2.18: ferramentas em alta ---")
_tt = [
    {"name": "Granola", "what_it_does": "Notas de reuniao com voz", "source_url": "https://granola.ai", "source_name": "Product Hunt"},
    {"name": "Malicioso", "what_it_does": "x", "source_url": "javascript:alert(1)"},
    {"name": "", "what_it_does": "sem nome", "source_url": "https://a.com"},
    {"name": "Dois", "what_it_does": "y", "source_url": "https://b.com"},
    {"name": "Tres", "what_it_does": "z", "source_url": "https://c.com"},
    {"name": "Quatro", "what_it_does": "w", "source_url": "https://d.com"},
]
_valid = sender._valid_trending_tools(_tt)
check("tools: descarta URL invalida", all(t["name"] != "Malicioso" for t in _valid))
check("tools: descarta sem nome", all(t["name"] for t in _valid))
check("tools: no maximo 3", len(_valid) == 3 and _valid[-1]["name"] == "Tres")
check("tools: lixo -> lista vazia", sender._valid_trending_tools("x") == [] and sender._valid_trending_tools(None) == [])
_h_tt = sender.generate_email_html({"items": [], "trending_tools": _tt})
check("tools: secao renderizada", "FERRAMENTAS EM ALTA" in _h_tt and "https://granola.ai" in _h_tt)
check("tools: javascript nao vaza", "javascript:" not in _h_tt)
check("tools: secao some sem ferramenta valida",
      "FERRAMENTAS EM ALTA" not in sender.generate_email_html({"items": [], "trending_tools": [_tt[1]]}))
check("tools: markdown preview", "Granola" in sender.generate_email_content({"items": [], "trending_tools": _tt}))

print("\n--- v2.18: dedup entre secoes com trending_tools ---")
_dd = processor.dedup_across_sections({
    "items": [], "world": [], "radar_brasil": [], "quick_links": [],
    "tool_of_day": {"headline": "Granola notas de reuniao com voz", "source_url": "https://granola.ai"},
    "trending_tools": [
        {"name": "Granola", "what_it_does": "Notas", "source_url": "https://granola.ai/"},
        {"name": "Cursor", "what_it_does": "Editor com agente", "source_url": "https://cursor.com"},
    ],
})
check("dedup: tool repetida sai do trending", [t["name"] for t in _dd["trending_tools"]] == ["Cursor"])
check("dedup: sem trending_tools nao quebra",
      "trending_tools" not in processor.dedup_across_sections({"items": [], "world": [], "quick_links": []})
      or processor.dedup_across_sections({"items": [], "world": [], "quick_links": []})["trending_tools"] == [])

print("\n--- v2.18: teto por secao imposto no codigo ---")
# Caso real de 06/11/2026: prompt pedia 3-4 no Hoje no Byte e o curador mandou 7 (+2 SaaS).
def _ci(h, score, cat="hoje_no_byte", big=False):
    return {"headline": h, "byte_score": score, "category": cat, "big_story": big,
            "source_url": f"https://ex.com/{h}"}
_capped = processor.enforce_section_caps({
    "items": [_ci("h1", 6), _ci("big", 9, big=True), _ci("h3", 7), _ci("h4", 7), _ci("h5", 5),
              _ci("h6", 6), _ci("h7", 4), _ci("s1", 5, "saas_enterprise"), _ci("s2", 6, "saas_enterprise"),
              _ci("v", None, "watch_later")],
    "quick_links": [{"headline": "q1", "byte_score": 6, "source_url": "https://q/1"},
                    {"headline": "q2", "byte_score": 3, "source_url": "https://q/2"},
                    {"headline": "q3", "byte_score": 4, "source_url": "https://q/3"},
                    {"headline": "q4", "byte_score": 2, "source_url": "https://q/4"},
                    {"headline": "q5", "byte_score": 1, "source_url": "https://q/5"}],
    "world": [_ci("w1", 5, "x"), _ci("w2", 5, "x"), _ci("w3", 5, "x"), _ci("w4", 5, "x")],
})
_hoje = [i["headline"] for i in _capped["items"] if i["category"] == "hoje_no_byte"]
_saas = [i["headline"] for i in _capped["items"] if i["category"] == "saas_enterprise"]
check("teto: hoje_no_byte = 3", len(_hoje) == 3)
check("teto: big story sempre fica", "big" in _hoje)
check("teto: fica o maior byte_score", set(_hoje) == {"big", "h3", "h4"})
check("teto: ordem do curador preservada", _hoje == ["big", "h3", "h4"])
check("teto: saas = 1 (o maior)", _saas == ["s2"])
check("teto: watch_later intocado", any(i["category"] == "watch_later" for i in _capped["items"]))
check("teto: world = 3", len(_capped["world"]) == 3)
_ql = [q["headline"] for q in _capped["quick_links"]]
check("teto: quick = 4", len(_ql) == 4)
check("teto: cortado de hoje disputa vaga de quick", "h1" in _ql or "h6" in _ql)
check("teto: quick por byte_score", _ql[0] in ("h1", "h6", "q1"))
check("teto: quick rebaixado sem why", all("why_it_matters" not in q for q in _capped["quick_links"]))
check("teto: dentro do limite nao mexe",
      len(processor.enforce_section_caps({"items": [_ci("a", 7), _ci("b", 6)]})["items"]) == 2)

print("\n--- v2.18: regressoes da revisao adversarial (Codex + Kimi, PR #31) ---")
# 1 (alta): byte_score textual nao pode derrubar o envio
try:
    _p = sender._preheader({"subject_hook": "x", "items": [
        {"headline": "Alfa beta gama", "byte_score": "7", "category": "hoje_no_byte"},
        {"headline": "Delta epsilon zeta", "byte_score": "9", "category": "hoje_no_byte"}]})
    check("rev1: preheader com byte_score str", _p == "MAIS: Delta epsilon zeta")
    check("rev1: big story com byte_score str",
          sender._big_story_of({"items": [{"headline": "B", "byte_score": "9", "big_story": True,
                                           "category": "hoje_no_byte"}]}) is not None)
except Exception as e:
    check(f"rev1: preheader com byte_score str ({e!r})", False)

# 2 (alta): trending_tools malformado nao pode derrubar o processor
for _lbl, _tt_bad in [("int", 7), ("str", "x"), ("url em lista", [{"name": "X", "source_url": ["https://a.com"]}]),
                      ("item nao-dict", [3, None])]:
    try:
        _o = processor.dedup_across_sections({"items": [], "world": [], "quick_links": [], "trending_tools": _tt_bad})
        check(f"rev2: trending_tools {_lbl} -> lista vazia", _o["trending_tools"] == [])
    except Exception as e:
        check(f"rev2: trending_tools {_lbl} ({e!r})", False)
try:
    processor.dedup_across_sections({"items": [{"headline": "h", "source_url": ["x"]}], "world": [], "quick_links": []})
    check("rev2: source_url nao-string em item nao quebra o dedup", True)
except Exception as e:
    check(f"rev2: source_url nao-string em item ({e!r})", False)

# 3 (media): so Big Story ELEGIVEL (>=8) e fixada; a mesma que o sender escolheria
_c3 = processor.enforce_section_caps({"items": [
    _ci("s7", 7, "saas_enterprise", big=True), _ci("s9", 9, "saas_enterprise", big=True)]})
check("rev3: big story 7 marcada nao derruba a 9", [i["headline"] for i in _c3["items"]] == ["s9"])
_c3b = processor.enforce_section_caps({"items": [
    {"headline": "semscore", "category": "hoje_no_byte", "big_story": True},
    _ci("n9", 9), _ci("n8", 8), _ci("n7", 7)]})
check("rev3: big story sem score nao e fixada", "semscore" not in [i["headline"] for i in _c3b["items"]])
_c3c = processor.enforce_section_caps({"items": [_ci("baixa", 8, big=True), _ci("a", 9), _ci("b", 9), _ci("c", 9)]})
check("rev3: big story valida fica mesmo sem o maior score", "baixa" in [i["headline"] for i in _c3c["items"]])

# 4 (media): ferramenta invalida nao consome URL nem vaga
_c4 = processor.dedup_across_sections({"items": [], "world": [],
    "trending_tools": [{"name": "", "source_url": "https://q.com/1"}],
    "quick_links": [{"headline": "Noticia boa", "source_url": "https://q.com/1"}]})
check("rev4: tool sem nome nao apaga quick link", len(_c4["quick_links"]) == 1)
_c4b = processor.dedup_across_sections({"items": [], "world": [], "quick_links": [], "trending_tools": [
    {"name": "A"}, {"name": "B", "source_url": "javascript:x"}, {"name": "", "source_url": "https://c.com"},
    {"name": "Valida", "source_url": "https://ok.com"}]})
check("rev4: invalidas nao ocupam o teto", [t["name"] for t in _c4b["trending_tools"]] == ["Valida"])

# 5 (media): watch_later tem teto 1
_c5 = processor.enforce_section_caps({"items": [_ci("v1", None, "watch_later"), _ci("v2", None, "watch_later")]})
check("rev5: watch_later = 1", [i["headline"] for i in _c5["items"]] == ["v1"])

# 6 (media): preheader so exclui a Big Story quando o subject E sobre ela
_c6 = {"subject_hook": "Google corta preco do video",
       "items": [_it("Anthropic dobra ritmo de pesquisa", 9, big=True),
                 _it("Google corta preco do video em 30%", 8), _it("Terceira historia aqui", 7)]}
check("rev6: subject sobre a 2a -> preheader e a big story", sender._preheader(_c6) == "MAIS: Anthropic dobra ritmo de pesquisa")
_c6b = {"subject_hook": "Mercado entra em panico total",
        "items": [_it("Anthropic dobra ritmo de pesquisa", 9, big=True), _it("Google corta preco do video", 8)]}
check("rev6: subject sem match -> assume big story", sender._preheader(_c6b) == "MAIS: Google corta preco do video")

# 7 (baixa): quick links mantem a ordem do curador (selecao por score, exibicao na ordem)
_c7 = processor.enforce_section_caps({"items": [], "quick_links": [
    {"headline": n, "byte_score": s, "source_url": f"https://q/{n}"}
    for n, s in [("baixa", 1), ("alta", 9), ("media", 5), ("sete", 7), ("seis", 6)]]})
check("rev7: quick na ordem do curador", [q["headline"] for q in _c7["quick_links"]] == ["alta", "media", "sete", "seis"])

# 8 (baixa): emoji
check("rev8: keycap aceito", sender._subject_emoji("1️⃣") == "1️⃣")
check("rev8: bloco grafico rejeitado", sender._subject_emoji("░") == "\U0001F525")
check("rev8: copyright rejeitado", sender._subject_emoji("©") == "\U0001F525")
check("rev8: ZWJ pendurado rejeitado", sender._subject_emoji("\U0001F4C8‍") == "\U0001F525")
check("rev8: indicador regional sozinho rejeitado", sender._subject_emoji("\U0001F1E7") == "\U0001F525")

# testes frouxos apontados pelo Codex: rebaixado com why nao leva o why para o quick
_c9 = processor.enforce_section_caps({"items": [dict(_ci(f"x{k}", k), why_it_matters="Teste: x.", details=["d"])
                                                for k in range(1, 6)]})
check("rev9: quick rebaixado nao herda why nem details",
      all("why_it_matters" not in q and "details" not in q for q in _c9["quick_links"]))

print("\n--- v2.18: template do curador formata sem KeyError ---")
try:
    _p = processor.CURATOR_USER_TEMPLATE.format(total=1, items="[]", feedback_section="")
    check("template formata", True)
    check("template pede subject_emoji", '"subject_emoji"' in _p)
    check("template pede lede", '"lede"' in _p)
    check("template pede trending_tools", '"trending_tools"' in _p)
except (KeyError, IndexError, ValueError) as e:
    check(f"template formata ({e!r})", False)


print()
if check.failed:
    print(f"{check.failed} teste(s) FALHARAM")
    sys.exit(1)
print("todos os testes passaram")
