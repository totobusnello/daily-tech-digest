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

print()
if check.failed:
    print(f"{check.failed} teste(s) FALHARAM")
    sys.exit(1)
print("todos os testes passaram")
