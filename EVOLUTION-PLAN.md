# THE DAILY BYTE — Plano de Evolução v2.0

**Data:** 06/02/2026
**Autor:** Claude (para aprovação do Totó)

---

## 1. Diagnóstico do Estado Atual

### O que já funciona bem

O pipeline atual é sólido: collector.py coleta de RSS, YouTube e X/Twitter, o processor.py usa Claude Sonnet para curadoria com Heat Score, e o sender.py entrega via Buttondown. Roda automaticamente via GitHub Actions às 06:45 BRT.

O sistema de Heat Score (Freshness 40pts + Fonte 30pts + Impacto 30pts) é criterioso. A filosofia de curadoria é excelente — "zero mesmice", priorizar primeira mão, ser impiedoso na seleção.

### Gaps identificados

**Gap 1 — Fontes 100% anglófonas e genéricas.** Todas as fontes RSS são internacionais (Reuters, TechCrunch, The Verge, HN, BBC). Nenhuma newsletter brasileira ou curada em português entra no pipeline. Isso significa que o digest está perdendo o "ângulo BR" e os insights que curadores humanos brasileiros já filtram.

**Gap 2 — Sem capacidade de ingerir newsletters.** O collector.py só sabe ler RSS feeds, YouTube RSS e X API. Não existe módulo para coletar conteúdo de newsletters no Beehiiv/Substack. As 4 newsletters desejadas não têm RSS público habilitado (testei /feed, /feed.xml, /api/v1/posts/feed — todas 404).

**Gap 3 — Categorias limitadas.** Hoje: breaking, ai_models, big_tech, watch_later, world. Falta uma categoria SaaS/Enterprise (que o TechDrop cobre muito bem) e uma visão Brasil-específica (que o Update Diário traz).

**Gap 4 — Seção "Mundo Real" sem perspectiva brasileira.** A seção world puxa de Reuters, BBC e Forbes — tudo em inglês, sem Folha, Valor, InfoMoney ou visão de mercado BR.

**Gap 5 — Análise superficial.** A "Análise do Dia" hoje são 3 bullets curtos. Newsletters como AiDrop e TechDrop trazem análises profundas que conectam pontos — o digest poderia incorporar esses insights para enriquecer a análise.

---

## 2. Análise das 4 Novas Fontes

### 2.1 AiDrop (aidrop.news)

- **Idioma:** PT-BR
- **Foco:** Ecossistema AI — plugins, modelos, plataformas
- **Estilo:** Análise profunda com contexto estratégico
- **Frequência:** ~Diária
- **Valor para o Digest:** Traz o "por que importa" que RSS puro não traz. Excelente para enriquecer a seção AI & Models com contexto brasileiro.

### 2.2 Evolving AI (evolvingai.io)

- **Idioma:** Inglês
- **Foco:** Lançamentos de modelos, benchmarks, guerra entre labs
- **Estilo:** Competitivo, foco em comparação entre modelos
- **Frequência:** ~Diária
- **Valor para o Digest:** Complementa os handles do X com análise mais estruturada sobre modelos. Bom para validar e enriquecer notícias de AI.

### 2.3 Update Diário (updatediario.beehiiv.com)

- **Idioma:** PT-BR
- **Foco:** Notícias gerais — economia, política, varejo, tech (amplo)
- **Estilo:** Headlines curtos e diretos, tom conversacional ("Itaú vai bem obrigado")
- **Frequência:** Diária
- **Valor para o Digest:** Perfeito para turbinar a seção "Mundo Real" com perspectiva brasileira. Cobre Itaú, shoppings, tratados — exatamente o que falta.

### 2.4 TechDrop (techdrop.news)

- **Idioma:** PT-BR
- **Foco:** SaaS, enterprise tech, CapEx das big techs
- **Estilo:** Dramático e envolvente ("SaaSpocalipse", "banho de sangue")
- **Frequência:** ~Diária
- **Valor para o Digest:** Traz a visão financeira/business de tech que falta. CapEx, M&A de SaaS, valuations — muito relevante para quem é CEO/CFO/CMO/CPO.

---

## 3. Plano de Implementação

### FASE 1 — Novo Módulo: Newsletter Collector

**O que:** Criar `newsletter_collector.py` — um scraper para coletar os posts mais recentes das 4 newsletters.

**Como funciona:** Como os RSS feeds não estão habilitados, o módulo vai acessar as páginas de arquivo de cada newsletter (ex: `aidrop.news`, `techdrop.news`) e fazer parsing do HTML para extrair os posts mais recentes (título, URL, data, resumo).

**Estrutura técnica:**
```python
NEWSLETTER_SOURCES = {
    "aidrop": {
        "name": "AiDrop",
        "base_url": "https://www.aidrop.news",
        "language": "pt-br",
        "category_hint": "ai_models",
        "tier": "newsletter_br"
    },
    "evolving_ai": {
        "name": "Evolving AI",
        "base_url": "https://evolvingai.io",
        "language": "en",
        "category_hint": "ai_models",
        "tier": "newsletter_en"
    },
    "update_diario": {
        "name": "Update Diário",
        "base_url": "https://updatediario.beehiiv.com",
        "language": "pt-br",
        "category_hint": "brasil",
        "tier": "newsletter_br"
    },
    "techdrop": {
        "name": "TechDrop",
        "base_url": "https://www.techdrop.news",
        "language": "pt-br",
        "category_hint": "saas_enterprise",
        "tier": "newsletter_br"
    }
}
```

**Dependências novas:** `beautifulsoup4`, `lxml` (adicionar ao requirements.txt).

**Integração:** O `collect_all()` ganha uma etapa `collect_newsletters()` que roda junto com RSS, YouTube e X.

---

### FASE 2 — Novas Categorias no Digest

**Adicionar ao config.yaml e ao curator prompt:**

```yaml
distribution:
  world: 3          # mantém
  brasil: 2         # NOVO — notícias BR relevantes
  breaking: 4       # mantém
  ai_models: 3      # mantém
  saas_enterprise: 2 # NOVO — SaaS, valuations, CapEx
  big_tech: 3       # mantém
  watch_later: 2    # mantém
```

**Nova seção no email: 🇧🇷 BRASIL**
Inspirada no Update Diário — headlines curtos sobre economia, política e mercado brasileiro que impactam quem trabalha com tech.

**Nova seção no email: 💰 SaaS & ENTERPRISE**
Inspirada no TechDrop — movimentos de SaaS, CapEx das big techs, valuations, "quem está morrendo e quem está crescendo".

---

### FASE 3 — Evolução do Curator Prompt

**3.1 Novo sistema de Heat Score para newsletters:**

```
NEWSLETTER CONTENT (bônus):
├── Insight exclusivo da newsletter: +15 pts (boost)
├── Cross-validação (newsletter confirma RSS): +10 pts
├── Apenas repost do que já veio por RSS: 0 pts
└── Newsletter atrasada (>24h do fato): -10 pts
```

**3.2 Instruções de cross-referência:**

Adicionar ao prompt do curator:
> "Quando o mesmo fato aparecer tanto em um RSS feed quanto em uma newsletter, prefira a versão da newsletter se ela trouxer análise ou contexto adicional. Se a newsletter apenas repetir o que o RSS já trouxe, descarte a duplicata da newsletter."

**3.3 Tom de voz aprimorado:**

Inspirado no estilo dos 4 newsletters:
- Do AiDrop: análise com contexto estratégico (não só "o que", mas "por que importa para seu negócio")
- Do Evolving AI: comparação direta entre modelos/empresas (sem ser genérico)
- Do Update Diário: headlines curtíssimos e diretos (max 8 palavras na seção Brasil)
- Do TechDrop: pitada de drama ("SaaSpocalipse") quando o conteúdo justificar

---

### FASE 4 — Template de Email Atualizado

**Nova estrutura do digest:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE DAILY BYTE
News, insights & trends
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌍 MUNDO REAL (3 notícias fora da bolha)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🇧🇷 BRASIL (2 notícias do mercado BR)     ← NOVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 BREAKING (2-4 notícias bombásticas)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 AI & MODELS (2-3 updates de modelos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 SaaS & ENTERPRISE (2 movimentos)       ← NOVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💼 BIG TECH MOVES (2-3 movimentos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔮 ANÁLISE DO DIA (1 parágrafo conectando tudo)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📺 WATCH LATER (1-2 vídeos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📰 DESTAQUES DAS NEWSLETTERS              ← NOVO
   Melhores insights de AiDrop,
   TechDrop, Evolving AI e Update Diário
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Nova seção "Destaques das Newsletters":**
Uma mini-seção no final com 2-3 links diretos para os melhores posts das newsletters do dia — serve como "crédito" e direciona o leitor para as fontes completas.

---

### FASE 5 — Atualizações de Configuração

**config.yaml — novas fontes:**
```yaml
sources:
  # ... (manter existentes)

  # Newsletter Sources (NOVO)
  newsletters:
    - name: "AiDrop"
      url: "https://www.aidrop.news"
      language: "pt-br"
      focus: "ai"
    - name: "Evolving AI"
      url: "https://evolvingai.io"
      language: "en"
      focus: "ai"
    - name: "Update Diário"
      url: "https://updatediario.beehiiv.com"
      language: "pt-br"
      focus: "general"
    - name: "TechDrop"
      url: "https://www.techdrop.news"
      language: "pt-br"
      focus: "saas"
```

**requirements.txt — novas deps:**
```
beautifulsoup4>=4.12.0
lxml>=4.9.0
```

**Temas prioritários — expandir:**
```yaml
themes:
  priority:
    - "agentic engineering"
    - "agent swarms"
    - "foundation models"
    - "AI safety"
    - "enterprise AI"
    - "Claude"
    - "GPT"
    - "LLM"
    - "SaaS"              # NOVO
    - "CapEx"             # NOVO
    - "valuations"        # NOVO
    - "Brasil"            # NOVO
    - "regulação AI"      # NOVO
```

---

## 4. Arquivos a Criar/Modificar

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `scripts/newsletter_collector.py` | CRIAR | Novo módulo scraper para as 4 newsletters |
| `scripts/collector.py` | MODIFICAR | Integrar `collect_newsletters()` no pipeline |
| `scripts/processor.py` | MODIFICAR | Atualizar curator prompt com novas categorias e regras de newsletter |
| `scripts/sender.py` | MODIFICAR | Adicionar seções Brasil, SaaS e Destaques das Newsletters |
| `templates/email.html` | MODIFICAR | Adicionar HTML para as novas seções |
| `config.yaml` | MODIFICAR | Adicionar newsletter sources e novas categorias |
| `prompts/curator.md` | MODIFICAR | Atualizar prompt com regras de cross-referência |
| `requirements.txt` | MODIFICAR | Adicionar beautifulsoup4 e lxml |
| `SKILL.md` | MODIFICAR | Documentar novas fontes e categorias |

---

## 5. Riscos e Mitigações

**Risco 1: Scraping pode quebrar se o Beehiiv mudar o layout.**
Mitigação: Usar seletores CSS resilientes e fallback para meta tags (og:title, og:description). Adicionar log de warning se o scraper não encontrar posts.

**Risco 2: Newsletters podem publicar tarde (após 06:45 BRT).**
Mitigação: Aumentar janela de coleta para newsletters para 36h (em vez de 24h dos RSS). Newsletters do dia anterior ainda são relevantes se trouxerem análise.

**Risco 3: Duplicação de conteúdo entre RSS e newsletters.**
Mitigação: Instrução explícita no curator prompt para cross-referenciar e deduplicar. Newsletter entra como "enriquecimento", não como fonte primária de fatos.

**Risco 4: Digest fica grande demais com mais categorias.**
Mitigação: Manter limite de 15-18 itens total. As novas categorias competem pelo mesmo espaço — a curadoria decide o que é mais relevante no dia.

---

## 6. Ordem de Execução Sugerida

1. **Criar `newsletter_collector.py`** com scraper para as 4 fontes
2. **Atualizar `collector.py`** para integrar a coleta de newsletters
3. **Atualizar `config.yaml`** com novas fontes e categorias
4. **Atualizar `processor.py`** e `prompts/curator.md` com novas regras
5. **Atualizar `sender.py`** e `templates/email.html` com novas seções
6. **Atualizar `requirements.txt`** com novas dependências
7. **Atualizar `SKILL.md`** com documentação
8. **Testar localmente** com `python run.py --preview`
9. **Push e testar no GitHub Actions**

---

## Decisão Necessária

Antes de implementar, preciso de sua aprovação em 3 pontos:

**A) Seção "DESTAQUES DAS NEWSLETTERS" — incluir ou não?**
É uma mini-seção que credita as newsletters e linka os posts completos. Pode ser vista como "publicidade" para as fontes, mas também é transparência.

**B) Limite total de itens — manter 15 ou aumentar para 18?**
Com 2 novas categorias (Brasil + SaaS), pode ficar apertado em 15. Sugestão: 18 no máximo.

**C) Seção Brasil — separada ou dentro de "Mundo Real"?**
Opção 1: Seção própria 🇧🇷 BRASIL (mais visível, mais identidade)
Opção 2: Incluir itens BR dentro de 🌍 MUNDO REAL (mais enxuto)

---

*Aguardando aprovação para iniciar implementação.*
