#!/usr/bin/env python3
"""
THE DAILY BYTE - Coletor de Fontes
Coleta notícias de X, YouTube, LinkedIn e RSS feeds
"""

import os
import json
import time
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import newsletter collector
try:
    from newsletter_collector import collect_all_newsletters
except ImportError:
    collect_all_newsletters = None

# ============================================
# CONFIGURAÇÃO
# ============================================

# Tier 1 - Primeira Mão (handles do X)
# ── v2.16: lista reduzida de 66 → 16 handles ──
# Motivo 1 (custo): o coletor faz 2 chamadas por handle (resolve user_id + busca
#   tweets). 66 handles = 132 requests/dia, muito acima do free tier atual da API
#   do X (~100 reads/mês). Com cache de user_id (ver _X_USER_ID_CACHE) e 16 handles,
#   o custo cai para ~16 requests/dia em regime.
# Motivo 2 (higiene): a lista antiga continha dezenas de handles inexistentes —
#   "swaborak", "ziaborak", "emaborak", "jackclarkaborak", "polyaborak", "maborak",
#   "daborak", "caborian", "demaboris", "xaborai", "ababorak", "alexaborak",
#   "manfraborak", "oaborak" — provavelmente alucinados numa expansão anterior e
#   nunca validados, porque a falha de auth era engolida em silêncio.
# ⚠️ Estes 16 são nomes públicos notórios, mas NÃO foram validados contra a API
#   (token estava com 401 na revisão). Rodar collector.py com token novo e conferir
#   o log "handle inexistente" antes de considerar a lista limpa.
TIER1_HANDLES = [
    # Labs / fundadores
    "sama",               # Sam Altman — OpenAI
    "AnthropicAI",        # Anthropic (conta oficial)
    "satyanadella",       # Satya Nadella — Microsoft
    "sundarpichai",       # Sundar Pichai — Google
    "demishassabis",      # Demis Hassabis — DeepMind
    "aravind_srinivas",   # Aravind Srinivas — Perplexity
    # Researchers
    "karpathy",           # Andrej Karpathy
    "ylecun",             # Yann LeCun — Meta
    "AndrewYNg",          # Andrew Ng — DeepLearning.AI
    "drfeifei",           # Fei-Fei Li — Stanford HAI
    "hardmaru",           # David Ha — Sakana AI
    # Practitioners / indie
    "simonw",             # Simon Willison — LLM na prática
    "levelsio",           # Pieter Levels — indie hacker
    "GergelyOrosz",       # Gergely Orosz — Pragmatic Engineer
    # Estratégia / negócio
    "benedictevans",      # Benedict Evans — análise de tech
    "ethanmollick",       # Ethan Mollick — AI aplicada a trabalho
]

# RSS Feeds — Tech & AI
RSS_FEEDS = {
    # ── Originais v2.2 ──
    "hacker_news": "https://hnrss.org/frontpage?points=100",
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/index",
    "wired": "https://www.wired.com/feed/rss",
    "the_verge": "https://www.theverge.com/rss/index.xml",
    # v2.16 removido: reuters_tech — HTTP 401 (RSS público descontinuado).
    "techcrunch_ai": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "mit_tech_review": "https://www.technologyreview.com/feed/",
    "arxiv_ai": "http://export.arxiv.org/rss/cs.AI",
    "the_decoder": "https://the-decoder.com/feed/",
    # ── v2.3 Expansion: AI & Enterprise Tech ──
    "venturebeat": "https://feeds.feedburner.com/venturebeat/SZYF",
    "ai_business": "https://aibusiness.com/rss.xml",
    # v2.16 removido: enterprise_ai — virou "AIwire" em hpcwire.com e devolve 403
    #   (Cloudflare) mesmo com UA de browser.
    "aithority": "https://aithority.com/feed/",
    "ai_news": "https://www.artificialintelligence-news.com/feed/",
    "zdnet": "https://www.zdnet.com/news/rss.xml",
    "engadget": "https://www.engadget.com/rss.xml",
    "siliconangle": "https://siliconangle.com/feed/",
    "geekwire": "https://www.geekwire.com/feed/",
    "fast_company": "https://www.fastcompany.com/latest/rss",
    "inc": "https://www.inc.com/rss",
    # ── v2.3 Expansion: Crypto / Web3 ──
    "coindesk": "https://feeds.feedburner.com/CoinDesk",
    "decrypt": "https://decrypt.co/feed",
    # ── v2.3 Expansion: SaaS / Enterprise ──
    # v2.16 removidos: saas_mag (ConnectionError, domínio fora do ar) e
    #   saastock_blog (HTTP 404 — blog descontinuado).
    "crunchbase_news": "https://news.crunchbase.com/feed/",
    # ── v2.5 Expansion: Official AI Labs Blogs + Breaking ──
    "huggingface_blog": "https://huggingface.co/blog/feed.xml",
    "google_ai_blog": "https://blog.google/technology/ai/rss/",
    "openai_blog": "https://openai.com/blog/rss.xml",
    # v2.16: Anthropic não publica RSS oficial (/feed.xml → 404). Este é um mirror
    #   comunitário do /news. Se sumir, remover — não há substituto oficial.
    "anthropic_news": "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml",
    # v2.16 removido: the_information — HTTP 403 mesmo com UA de browser, e o
    #   conteúdo é paywall (só teaser). Não sustenta why_it_matters.
    # ── v2.9 Expansion: Primary AI Lab Blogs (primeira mão) ──
    "deepmind_blog": "https://deepmind.google/blog/rss.xml",
    # v2.16: ai.meta.com/blog não expõe RSS (400/404 em todas as variações).
    #   engineering.fb.com é mais amplo que AI, mas cobre a maior parte do relevante.
    "meta_ai_blog": "https://engineering.fb.com/feed/",
    "nvidia_blog_ai": "https://blogs.nvidia.com/feed/",
    "microsoft_research": "https://www.microsoft.com/en-us/research/feed/",
    # v2.16 removidos: stability_ai (sem RSS em nenhuma rota; último post ~mai/2026)
    #   e cohere_blog (blog ativo mas sem feed — zero ocorrências de "rss" no HTML).
    "mistral_blog": "https://mistral.ai/rss.xml",
    # ── v2.9: Developer / Builder (ponto de vista prático) ──
    "changelog": "https://changelog.com/feed",
    "infoq_ai": "https://feed.infoq.com/ai-ml-data-eng/",
    "hacker_news_show": "https://hnrss.org/show?points=50",
    "producthunt": "https://www.producthunt.com/feed",
    # ── v2.9: Community-Driven (antes da mídia cobrir) ──
    "reddit_machinelearning": "https://www.reddit.com/r/MachineLearning/hot/.rss?limit=15",
    # v2.16 removido: reddit_localllama — HTTP 429. O Reddit apertou o rate limit
    #   de RSS anônimo em 2026; o fix documentado exige token de conta logada
    #   (reddit.com/prefs/feeds/), sem rota anônima viável. r/MachineLearning
    #   segue funcionando e cobre parte do sinal.
    "lobsters_ai": "https://lobste.rs/t/ai.rss",
    # ── v2.16b: expansão da camada PRIMÁRIA (blogs de eng, changelogs, mídia técnica) ──
    # A auditoria mostrou que mainstream domina por CADÊNCIA, não por privilégio:
    # 21 dos 24 feeds mainstream publicam diariamente, contra 15 de 72 na camada
    # primária. Estas foram escolhidas por publicarem com frequência real
    # (posts/30d medidos em 2026-07-20), não só por serem "boas fontes".
    "cloudflare_blog": "https://blog.cloudflare.com/rss/",          # 18/30d — infra, bot/agentic
    "supabase_blog": "https://supabase.com/rss.xml",                # agentic coding na prática
    "sourcegraph_blog": "https://sourcegraph.com/blog/rss.xml",     # AI agents em codebase enterprise
    "together_ai": "https://together.ai/blog/rss.xml",              # infra open-source, GPU
    "ramp_eng": "https://engineering.ramp.com/rss.xml",             # AI agents em produção fintech
    "weaviate_blog": "https://weaviate.io/blog/rss.xml",            # vector DB / memória agentic
    # Changelogs — sinal de adoção real, primeira mão
    "github_changelog": "https://github.blog/changelog/feed/",      # 10/30d
    "github_ai": "https://github.blog/ai-and-ml/feed/",             # 5/30d, Copilot em primeira mão
    # ⚠️ vercel_changelog publica ~104 itens/30d (release notes granulares). O cap
    #    de 5/fonte no processor segura o volume, mas se virar ruído na edição,
    #    esta é a primeira candidata a sair.
    "vercel_changelog": "https://vercel.com/changelog/rss.xml",
    # Mídia técnica especializada (da planilha Master Sources, testadas ao vivo)
    "ieee_spectrum": "https://spectrum.ieee.org/rss/",              # 27/30d
    "next_platform": "https://www.nextplatform.com/feed/",          # 19/30d — infra/HPC/AI datacenter
    "datacenter_dynamics": "https://www.datacenterdynamics.com/rss/",  # 20/30d — CapEx de datacenter
    "tech_eu": "https://tech.eu/feed/",                             # 20/30d — ângulo europeu
    "robot_report": "https://www.therobotreport.com/feed/",         # 15/30d — robótica
    "fintech_futures": "https://www.fintechfutures.com/rss.xml",    # 50/30d — fintech global
    "mit_sloan_ai": "https://sloanreview.mit.edu/feed/",            # 12/30d — gestão + AI para executivos
    # Community técnica
    "alignment_forum": "https://www.alignmentforum.org/feed.xml",   # AI safety/governance
    "lesswrong": "https://www.lesswrong.com/feed.xml",              # 10/30d
    "console_dev": "https://console.dev/rss.xml",                   # devtools obscuros → Tool do Dia

    # ── v2.16b: verticais de negócio (alimentam SaaS & Enterprise) ──
    # Garimpadas na planilha Master Sources. Seleção deliberadamente enxuta: a
    # varredura achou 6 feeds de segurança e 4 de health tech UK, mas empilhar
    # verticais redundantes só dilui o pool. Uma fonte forte por vertical.
    "schneier": "https://www.schneier.com/feed/",                   # segurança com lente estratégica
    "helpnet_security": "https://www.helpnetsecurity.com/feed/",    # 10/30d — segurança enterprise
    "martech": "https://martech.org/feed/",                         # 10/30d — ângulo CMO
    "practical_ecommerce": "https://www.practicalecommerce.com/feed/",  # 27/30d
    "supply_chain_review": "https://www.scmr.com/feed/",            # 37/30d — supply chain (tarifas/China)
    "finance_magnates": "https://www.financemagnates.com/feed/",    # 20/30d — fintech/mercados

    # ── v2.11: Brasil AI ──
    "ia_brasil_noticias": "https://iabrasilnoticias.com.br/feed/",
    # v2.16 removido: the_shift_br — o feed responde 200 com XML válido, mas ZERO
    #   <item>. Entrou na v2.15 sem teste de conteúdo. Revalidar no futuro.
}

# RSS Feeds - Mundo Real (governos, empresas, geopolítica, finanças)
WORLD_FEEDS = {
    # ── Originais v2.2 ──
    # v2.16 removidos: reuters_world e reuters_business — HTTP 401. A Reuters
    #   descontinuou RSS público; não há rota gratuita equivalente.
    "forbes_business": "https://www.forbes.com/business/feed/",
    "forbes_innovation": "https://www.forbes.com/innovation/feed/",
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    # ── v2.3 Expansion: Business / Finance / Macro ──
    "cnbc_top_news": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "cnbc_markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    # v2.16 removidos: cnbc_economy (feed devolve 0 itens) e wsj_markets (responde
    #   200 mas o item mais recente é de 539 dias atrás — família feeds.a.dj.com
    #   parece abandonada pela Dow Jones).
    "nyt_dealbook": "https://rss.nytimes.com/services/xml/rss/nyt/DealBook.xml",
    "axios": "https://api.axios.com/feed/",
    "fortune": "https://fortune.com/feed/",
    "business_insider": "https://www.businessinsider.com/rss",
    "quartz": "https://qz.com/feed",
    # v2.16 removido: nikkei_asia — a URL antiga dá 404 e a nova (/rss/feed/nar)
    #   responde 200 mas SEM pubDate em nenhum item. Como o coletor usa utcnow()
    #   quando falta data, os 20 itens entrariam como "recém-publicados" todo dia.
    "politico_eu_tech": "https://www.politico.eu/section/technology/feed/",
    # ── v2.3 Expansion: Fintech / Payments ──
    "pymnts": "https://www.pymnts.com/feed/",
    "finextra": "https://www.finextra.com/rss/headlines.aspx",
    # ── v2.3 Expansion: Paywalled (may fail gracefully) ──
    "bloomberg_tech": "https://feeds.bloomberg.com/technology/news.rss",
    "ft_technology": "https://www.ft.com/technology?format=rss",
    # v2.16: ft_startups (/start-ups?format=rss) dá 404 — substituído pelo feed
    #   principal do FT, que está ativo.
    "ft_home": "https://www.ft.com/rss/home",
    "economist_finance": "https://www.economist.com/finance-and-economics/rss.xml",
    "economist_business": "https://www.economist.com/business/rss.xml",
    # ── v2.5 Expansion: Wire Services + Brasil ──
    # v2.16 removidos: ap_news_tech e ap_news_business — HTTP 404, sem feed
    #   público equivalente.
    "poder360": "https://www.poder360.com.br/feed/",
    "infomoney": "https://www.infomoney.com.br/feed/",
    "startups_br": "https://startups.com.br/feed/",
    # v2.16: /rss/ dava 404. A rota correta da Globo é /rss/<editoria>/.
    "valor_economico": "https://valor.globo.com/rss/valor/",
    # ── v2.9 Expansion: Brasil tech/negócios (ineditismo BR) ──
    "neofeed": "https://neofeed.com.br/feed/",
    # v2.16 removidos: startse (feed devolve 0 itens) e pipeline_valor (HTTP 400
    #   em todas as rotas testadas, inclusive pox.globo.com).
    # v2.16: exame.com/tecnologia/feed/ dá 404 — o feed geral está ativo e traz
    #   itens de Tecnologia entre as editorias.
    "exame": "https://exame.com/feed/",
    "brazil_journal": "https://braziljournal.com/feed/",
    # v2.16: tecmundo.com.br/rss devolvia 0 itens; o feed vive em rss.tecmundo.
    "tecmundo": "https://rss.tecmundo.com.br/feed",
    "canaltech": "https://canaltech.com.br/rss/",

    # ── v2.16b: expansão BR (9 → 20 fontes) ──
    # A base brasileira tinha 9 feeds para uma quota de 12 no corte estratificado —
    # não havia de onde tirar. Todas abaixo testadas ao vivo em 2026-07-20 com
    # cadência medida (posts/30d) e conteúdo nativamente tech/negócios.
    # Nota: a planilha Master Sources (2.165 linhas) NÃO tinha nenhum domínio .br;
    # estas vieram de pesquisa dirigida.
    "olhar_digital": "https://olhardigital.com.br/feed/",           # tech/IA, alto volume
    "tecnoblog": "https://tecnoblog.net/feed/",                     # 50 posts/30d
    "it_forum": "https://itforum.com.br/feed/",                     # enterprise IT, 32/30d
    "ti_inside": "https://tiinside.com.br/feed/",                   # enterprise IT/telecom, 30/30d
    "teletime": "https://teletime.com.br/feed/",                    # telecom/infra B2B, 30/30d
    "convergencia_digital": "https://www.convergenciadigital.com.br/rss/",  # TI/telecom/IA enterprise
    "mobile_time": "https://www.mobiletime.com.br/feed/",           # mobile + fintech + IA aplicada
    "startupi": "https://startupi.com.br/feed/",                    # startups/VC Brasil
    "finsiders_br": "https://finsidersbrasil.com.br/feed/",         # fintech/finanças digitais
    # Cadência semanal, mas são as duas únicas vozes de engenharia/dev BR ainda
    # vivas — os blogs de iFood, QuintoAndar, Loft, Stone, PicPay e Mercado Livre
    # estão todos parados no Medium desde 2021-2023.
    "nubank_eng": "https://building.nubank.com/feed/",
    "hipsters_tech": "https://hipsters.tech/category/podcast/feed/",
    # Recuperado da planilha Master Sources: /feed/ devolve 0 itens, mas
    # /feed.xml está ativo com 30 posts/30d e pauta de gestão ("43% dos CEOs
    # usam IA para fundamentar decisões") — exatamente o público do digest.
    "startse": "https://startse.com/feed.xml",
}

# YouTube Channels (via RSS)
# v2.16: 5 dos 11 channel_id estavam errados (HTTP 404 no feed do YouTube) —
# corrigidos e validados um a um, conferindo o <title> do canal na resposta.
YOUTUBE_CHANNELS = {
    "fireship": "UCsBjURrPoezykLs9EqgamOA",
    "two_minute_papers": "UCbfYPyITQ-7l4upoX8nvctg",
    "ai_explained": "UCNJ1Ymd5yFuUPtn21xtRbbw",        # v2.16 corrigido
    "matt_wolfe": "UChpleBmo18P08aKCIgti38g",          # v2.16 corrigido
    "lex_fridman": "UCSHZKyawb77ixDdsGog4iWA",
    # ⚠️ v2.16b — o ID anterior (UCWN3xxRkmTPmbKwht9FuE5A) NÃO era do Karpathy:
    # devolvia o canal do Siraj Raval, e ele chegou a aparecer como fonte na
    # edição 182 ("YouTube / Siraj Raval"). ID correto confirmado via oEmbed
    # oficial do YouTube. O canal está parado há ~508 dias — mantido porque custa
    # uma request/dia e, se ele voltar a publicar, cada vídeo é evento.
    "andrej_karpathy": "UCXUPKJO5MZQN11PqgIvyuvQ",
    "ai_daily_brief": "UCKelCK4ZaO6HeEI1KQjqzWA",      # v2.16 corrigido
    # Sem vídeo novo há ~234 dias; mantido por ser a única voz BR do bloco —
    # se voltar a publicar, entra sozinho.
    "filipe_deschamps": "UCU5JicSrEM5A63jkJ2QvGYw",
    # ── v2.6 ──
    "the_ai_grid": "UCbY9xX3_jW5c2fjlZVBI4cg",
    # ── v2.7 ──
    "sabrina_ramonov": "UCiGWNa6QK6CiKPvv5-YPv8g",     # v2.16 corrigido
    # ── v2.11 ──
    "nate_herk": "UC2ojq-nuP8ceeHqiroeKhBA",           # v2.16 corrigido
}

# Substack Feeds — v2.3 (curated newsletters via RSS)
SUBSTACK_FEEDS = {
    # ── Business / Strategy ──
    "sub_capital_wars": "https://capitalwars.substack.com/feed",
    # v2.16 removido: sub_cfo_dynamics — HTTP 404.
    "sub_doomberg": "https://doomberg.substack.com/feed",
    "sub_beautiful_mess": "https://cutlefish.substack.com/feed",
    "sub_contrarian_hr": "https://thecontrarianhr.substack.com/feed",
    # ── AI / Tech ──
    # v2.16: bloco podado de 10 → 1. Removidos por HTTP 404 (sub_ai_chat,
    #   sub_ai_explored, sub_how_i_ai, sub_conversations_ai) e por abandono
    #   (sub_ai_at_work 1200d, sub_ai_marketing 1257d, sub_everyday_ai 912d,
    #   sub_authentic_ai 471d, sub_ai_today 383d).
    "sub_ai_for_humans": "https://aiforhumans.substack.com/feed",
    # ── Fintech ──
    "sub_fintech_biz_weekly": "https://fintechbusinessweekly.substack.com/feed",
    # v2.16 removidos: sub_fintech_hunting e sub_fintech_newscast (HTTP 404),
    #   sub_fintech_confidential (2067d sem post) e sub_connecting_dots_fintech (1433d).
    # ── Biotech / Pharma ──
    # v2.16 removidos: sub_ai_pharma e sub_biotech_strategy (HTTP 404),
    #   sub_biotech_bytes (806d sem post).
    "sub_biotech_blueprint": "https://biotechblueprint.substack.com/feed",
    "sub_health_tech": "https://longyearhealth.substack.com/feed",
    # ── E-commerce / EdTech / Sustainability ──
    # v2.16 removido: sub_ecommerce_playbook — HTTP 404.
    "sub_edtech_partnerships": "https://edtechpartnerships.substack.com/feed",
    "sub_sustainability_numbers": "https://hannahritchie.substack.com/feed",
    # ── Education / AI in Edu ──
    "sub_toms_ai_edu": "https://tomstakesaitools.substack.com/feed",
    # ── v2.6 Expansion: AI Engineering + Macro Strategy ──
    "sub_latent_space": "https://www.latent.space/feed",
    "sub_state_of_ai": "https://nathanbenaich.substack.com/feed",
    # ── v2.9 Expansion: Indie Voices / Builders / Practitioners ──
    "sub_simon_willison": "https://simonwillison.net/atom/everything/",
    "sub_lilian_weng": "https://lilianweng.github.io/index.xml",
    # v2.16 removido: sub_chip_huyen — sem post há 550d no blog e o Substack dela
    #   tem só um "coming soon" de jan/2025.
    "sub_one_useful_thing": "https://www.oneusefulthing.org/feed",
    "sub_ai_snake_oil": "https://www.aisnakeoil.com/feed",
    # v2.16: migraram de volta para o Substack; o domínio próprio parou em out/2025.
    "sub_semianalysis": "https://newsletter.semianalysis.com/feed",
    "sub_interconnects": "https://www.interconnects.ai/feed",
    "sub_ben_thompson": "https://stratechery.com/feed/",
    "sub_pragmatic_engineer": "https://newsletter.pragmaticengineer.com/feed",
    "sub_lennys_newsletter": "https://www.lennysnewsletter.com/feed",
    # ── v2.11 ──
    # v2.16 removido: sub_neatprompts — HTTP 404.
    # ── v2.14: alta qualidade (swyx daily + Karpathy raro-mas-evento) ──
    # v2.16: as duas entradas da v2.14 já nasceram mortas e nunca foram testadas.
    #   O AI News migrou do Buttondown para plataforma própria (news.smol.ai) —
    #   URL corrigida, feed ativo com 678 entradas.
    "sub_ai_news_swyx": "https://news.smol.ai/rss.xml",
    # v2.16 removido: sub_karpathy — o Substack dele está parado há 1199 dias
    #   (~3,3 anos). O canal ativo dele é o YouTube, que já coletamos.
    # ── v2.15: strategy essays (Packy McCormick) + rationalist AI (Scott Alexander) ──
    "sub_not_boring": "https://www.notboring.co/feed",
    "sub_astral_codex_ten": "https://www.astralcodexten.com/feed",
    # ── v2.16b: vozes de análise com cadência alta ──
    # Zvi faz roundup quase diário e reage a cada release; os demais trazem
    # ângulo de negócio/policy que o resto do catálogo não cobre.
    "sub_zvi": "https://thezvi.substack.com/feed",                        # 20/30d
    "sub_big_technology": "https://www.bigtechnology.com/feed",           # 9/30d — scoops de negócio
    "sub_ai_supremacy": "https://www.ai-supremacy.com/feed",              # 7/30d — estratégia da indústria
    "sub_understanding_ai": "https://www.understandingai.org/feed",       # AI policy independente
    "sub_ed_zitron": "https://www.wheresyoured.at/feed",                  # 7/30d — crítica contrarian à bolha
    "sub_strange_loop": "https://www.strangeloopcanon.com/feed",          # ensaios sobre agentes/benchmarks
    # Ben's Bites (166k) é a única newsletter concorrente que entra — é comentário
    # autoral de practitioner, não digest puro. TLDR AI e The Rundown ficaram DE FORA
    # por decisão editorial: republicar a curadoria deles contradiz a premissa do
    # produto ("trazer o que C-levels não encontram sozinhos") e quem assina os dois
    # percebe a repetição.
    "sub_bens_bites": "https://bensbites.com/feed",                       # 8/30d

    # ── v2.16: fontes novas verificadas ao vivo (RSS 200 + post recente) ──
    # Geopolítica de AI (China × EUA × Europa) — gap identificado na revisão.
    "sub_geopolitechs": "https://www.geopolitechs.org/feed",
    # ROI/adoção enterprise com métrica ("AI Metric of the Week") — outro gap.
    "sub_ai_to_roi": "https://ai2roi.substack.com/feed",
    # PT-BR: AI + enterprise pela lente do Distrito (distinto do Inside VC).
    "sub_ai_factory_br": "https://insideinnovation.substack.com/feed",
    # Agentic coding na prática (orquestração de subagents, padrões de loop).
    "sub_ai_engineer": "https://newsletter.aiengineer.co/feed",
}

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class RawItem:
    """Item bruto coletado das fontes"""
    title: str
    content: str
    url: str
    source_name: str
    source_type: str  # tweet, article, video, paper
    author: str
    published_at: datetime
    engagement: Dict  # likes, retweets, views, etc
    raw_data: Dict

    def hours_ago(self) -> float:
        return (datetime.utcnow() - self.published_at).total_seconds() / 3600

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['published_at'] = self.published_at.isoformat()
        d['hours_ago'] = round(self.hours_ago(), 1)
        d.pop('raw_data', None)  # v2.6: removido para economizar I/O
        return d


# ============================================
# COLETORES
# ============================================

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_feed(feed_url: str, max_retries: int = 3):
    """Fetch RSS feed with retry + exponential backoff.
    v2.5: Retry com backoff (2s, 4s, 8s) antes de desistir.
    Strategy: requests com browser UA primeiro (Substack bloqueia bots),
    feedparser direto como fallback.
    """
    feed = None
    for attempt in range(max_retries):
        # Primary: requests com browser headers (evita bloqueio Substack)
        try:
            resp = requests.get(
                feed_url, timeout=15,
                headers=_BROWSER_HEADERS,
                allow_redirects=True
            )
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                if feed.entries:
                    return feed
        except Exception:
            pass

        # Fallback: feedparser direto (funciona para feeds que nao bloqueiam)
        feed = feedparser.parse(feed_url)
        if feed.entries:
            return feed

        # Backoff before next retry (skip on last attempt)
        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)  # 2s, 4s
            print(f"  ⏳ Retry {attempt + 1}/{max_retries} for {feed_url[:60]}... waiting {wait}s")
            time.sleep(wait)

    return feed or feedparser.parse('')  # return empty feed if all failed


def _fetch_single_feed(source_name: str, feed_url: str, cutoff, source_type_fn=None, max_per_feed: int = 20) -> List[RawItem]:
    """Coleta itens de um único RSS feed (para uso em paralelo)"""
    items = []
    try:
        feed = _fetch_feed(feed_url)
        for entry in feed.entries[:max_per_feed]:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            else:
                published = datetime.utcnow()

            if published < cutoff:
                continue

            if source_type_fn:
                stype = source_type_fn(source_name)
            else:
                stype = 'article' if 'arxiv' not in source_name else 'paper'

            items.append(RawItem(
                title=entry.get('title', ''),
                content=entry.get('summary', ''),
                url=entry.get('link', ''),
                source_name=source_name,
                source_type=stype,
                author=entry.get('author', source_name),
                published_at=published,
                engagement={},
                raw_data={}
            ))
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
    return items


def _parse_feed_items(feeds: dict, cutoff, source_type_fn=None, max_per_feed: int = 20) -> List[RawItem]:
    """Coleta itens de um dicionário de RSS feeds — v2.6: paralelo com ThreadPool"""
    items = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(_fetch_single_feed, name, url, cutoff, source_type_fn, max_per_feed)
            for name, url in feeds.items()
        ]
        for future in as_completed(futures):
            items.extend(future.result())
    return items


def collect_rss_feeds() -> List[RawItem]:
    """Coleta itens de RSS feeds de tech"""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return _parse_feed_items(RSS_FEEDS, cutoff)


def collect_world_feeds() -> List[RawItem]:
    """Coleta notícias do mundo real (governos, empresas, geopolítica)"""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return _parse_feed_items(
        WORLD_FEEDS, cutoff,
        source_type_fn=lambda _: 'world',
        max_per_feed=10
    )


def collect_youtube_feeds() -> List[RawItem]:
    """Coleta vídeos recentes via YouTube RSS — v2.6: paralelo"""
    cutoff = datetime.utcnow() - timedelta(hours=48)
    yt_feeds = {
        name: f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
        for name, cid in YOUTUBE_CHANNELS.items()
    }
    return _parse_feed_items(yt_feeds, cutoff, source_type_fn=lambda _: 'video', max_per_feed=5)


def collect_substack_feeds() -> List[RawItem]:
    """Coleta posts recentes de Substacks curados via RSS (janela de 36h)"""
    cutoff = datetime.utcnow() - timedelta(hours=36)  # 36h window like newsletters
    return _parse_feed_items(
        SUBSTACK_FEEDS, cutoff,
        source_type_fn=lambda _: 'newsletter',
        max_per_feed=5  # Max 5 per Substack to avoid noise
    )


# v2.16: cache de user_id em disco. Resolver username→id é metade das chamadas
# à API e o id nunca muda, então basta resolver uma vez por handle.
_X_USER_ID_CACHE = "/tmp/digest_x_user_ids.json"


def _load_x_user_ids() -> Dict:
    try:
        with open(_X_USER_ID_CACHE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return {}


def _save_x_user_ids(cache: Dict) -> None:
    try:
        with open(_X_USER_ID_CACHE, 'w') as f:
            json.dump(cache, f)
    except IOError as e:
        print(f"   ⚠️ Não consegui salvar cache de user_id do X: {e}")


def collect_x_posts(bearer_token: str) -> List[RawItem]:
    """
    Coleta posts recentes do X via API
    Requer X API Bearer Token

    v2.16: erros de HTTP agora são LOGADOS. Antes, `if status != 200: continue`
    engolia 401/429 em silêncio — o token esteve revogado por meses e o pipeline
    só reportava "→ 0 tweets", sem sinal de que havia algo quebrado.
    """
    items = []

    if not bearer_token:
        print("X_BEARER_TOKEN not set, skipping X collection")
        return items

    headers = {"Authorization": f"Bearer {bearer_token}"}
    cutoff = datetime.utcnow() - timedelta(hours=24)

    user_ids = _load_x_user_ids()
    ids_changed = False
    erros = {}

    for handle in TIER1_HANDLES:
        try:
            # Get user ID (cacheado — o id de um handle não muda)
            user_id = user_ids.get(handle)
            if not user_id:
                user_url = f"https://api.twitter.com/2/users/by/username/{handle}"
                user_resp = requests.get(user_url, headers=headers, timeout=15)
                if user_resp.status_code != 200:
                    erros[user_resp.status_code] = erros.get(user_resp.status_code, 0) + 1
                    if user_resp.status_code == 404:
                        print(f"   ⚠️ X: handle inexistente @{handle} — remover da lista")
                    elif user_resp.status_code in (401, 403):
                        print(f"   🔑 X: auth falhou ({user_resp.status_code}) em @{handle} — token inválido/revogado")
                    elif user_resp.status_code == 429:
                        print(f"   ⏳ X: rate limit em @{handle} — interrompendo coleta")
                        break
                    else:
                        # Qualquer outro código também nomeia o handle. Enumerar só os
                        # status previstos recriava a cegueira que motivou este log:
                        # um HTTP 400 apareceu no agregado sem dizer de quem era.
                        print(f"   ⚠️ X: HTTP {user_resp.status_code} ao resolver @{handle}")
                    continue
                user_id = user_resp.json().get('data', {}).get('id')
                if not user_id:
                    continue
                user_ids[handle] = user_id
                ids_changed = True

            # Get recent tweets
            tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
            params = {
                "max_results": 10,
                "tweet.fields": "created_at,public_metrics,entities",
                "expansions": "author_id"
            }
            tweets_resp = requests.get(tweets_url, headers=headers, params=params, timeout=15)
            if tweets_resp.status_code != 200:
                erros[tweets_resp.status_code] = erros.get(tweets_resp.status_code, 0) + 1
                if tweets_resp.status_code == 429:
                    print(f"   ⏳ X: rate limit ao buscar tweets de @{handle} — interrompendo coleta")
                    break
                print(f"   ⚠️ X: HTTP {tweets_resp.status_code} ao buscar tweets de @{handle}")
                continue

            tweets = tweets_resp.json().get('data', [])
            for tweet in tweets:
                created_at = datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')).replace(tzinfo=None)

                if created_at < cutoff:
                    continue

                metrics = tweet.get('public_metrics', {})
                items.append(RawItem(
                    title=tweet['text'][:100],
                    content=tweet['text'],
                    url=f"https://x.com/{handle}/status/{tweet['id']}",
                    source_name=f"@{handle}",
                    source_type='tweet',
                    author=handle,
                    published_at=created_at,
                    engagement={
                        'likes': metrics.get('like_count', 0),
                        'retweets': metrics.get('retweet_count', 0),
                        'replies': metrics.get('reply_count', 0)
                    },
                    raw_data={}
                ))
        except Exception as e:
            print(f"Error fetching X @{handle}: {e}")

    if ids_changed:
        _save_x_user_ids(user_ids)

    # v2.16: resumo de erros — se a coleta veio vazia, o motivo fica explícito no log
    if erros:
        resumo = ", ".join(f"HTTP {c}: {n}×" for c, n in sorted(erros.items()))
        print(f"   ⚠️ X: coleta com falhas ({resumo})")
        if not items and (401 in erros or 403 in erros):
            print("   🔑 X: NENHUM item coletado e auth falhou — renove X_BEARER_TOKEN "
                  "em developer.x.com e atualize o secret do repositório.")

    return items


# ============================================
# MAIN
# ============================================

def collect_all() -> Dict:
    """Coleta de todas as fontes"""
    print("🔥 THE DAILY BYTE - Iniciando coleta...")

    all_items = []

    # RSS Feeds (tech)
    print("📰 Coletando RSS feeds...")
    rss_items = collect_rss_feeds()
    all_items.extend(rss_items)
    print(f"   → {len(rss_items)} itens de RSS")

    # World Feeds (Reuters, Forbes, BBC)
    print("🌍 Coletando mundo real...")
    world_items = collect_world_feeds()
    all_items.extend(world_items)
    print(f"   → {len(world_items)} itens do mundo real")

    # YouTube
    print("📺 Coletando YouTube...")
    youtube_items = collect_youtube_feeds()
    all_items.extend(youtube_items)
    print(f"   → {len(youtube_items)} vídeos")

    # Substacks (v2.3 — 29 curated Substacks via RSS)
    print("📝 Coletando Substacks...")
    substack_items = collect_substack_feeds()
    all_items.extend(substack_items)
    print(f"   → {len(substack_items)} itens de Substacks")

    # X/Twitter
    print("🐦 Coletando X...")
    x_bearer = os.environ.get('X_BEARER_TOKEN', '').strip()
    x_items = collect_x_posts(x_bearer)
    all_items.extend(x_items)
    print(f"   → {len(x_items)} tweets")

    # Newsletters (9 fontes: AiDrop, Evolving AI, Update Diário, TechDrop, AlphaSignal, TAAFT, Turing Post, Import AI, Distrito News)
    newsletter_items_raw = []
    if collect_all_newsletters:
        print("📰 Coletando newsletters...")
        newsletter_items_raw = collect_all_newsletters()
        print(f"   → {len(newsletter_items_raw)} itens de newsletters")
    else:
        print("⚠️ Newsletter collector não disponível")

    # Sort by recency (RawItem objects)
    all_items.sort(key=lambda x: x.published_at, reverse=True)

    # Merge: convert RawItems to dicts + add newsletter items (already dicts)
    all_items_dicts = [item.to_dict() for item in all_items]
    all_items_dicts.extend(newsletter_items_raw)

    result = {
        "collected_at": datetime.utcnow().isoformat(),
        "total_items": len(all_items_dicts),
        "breakdown": {
            "rss": len(rss_items),
            "world": len(world_items),
            "substacks": len(substack_items),
            "youtube": len(youtube_items),
            "x": len(x_items),
            "newsletters": len(newsletter_items_raw)
        },
        "items": all_items_dicts
    }

    print(f"\n✅ Total coletado: {len(all_items_dicts)} itens")
    return result


if __name__ == "__main__":
    data = collect_all()

    # Save to file
    output_path = "/tmp/digest_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Salvo em {output_path}")
