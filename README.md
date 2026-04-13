# Daily Byte — Newsletter Automatizada de IA e Tecnologia

Newsletter automatizada "Daily Byte" sobre inteligência artificial e tecnologia. O sistema coleta conteúdo de múltiplas fontes, realiza curadoria inteligente com IA e distribui edições diárias de forma completamente autônoma via GitHub Actions. A versão 2.7 introduz workflow de sexta-feira com formato especial, enquetes para engajamento da audiência e suporte a múltiplas fontes de conteúdo simultaneamente.

## Stack

- **Python** — scripts de coleta, processamento e curadoria
- **GitHub Actions** — CI/CD para agendamento e execução diária
- **YAML** — configuração de fontes, filtros e parâmetros de distribuição
- **Prompts de IA** — curadoria e geração de conteúdo editorial

## Funcionalidades

- Coleta automatizada de conteúdo de IA e tecnologia de múltiplas fontes
- Curadoria inteligente via prompts especializados (`prompts/curator.md`)
- Distribuição diária agendada via `daily-digest.yml`
- Workflow especial para edições de sexta-feira
- Suporte a enquetes para engajamento da audiência
- Configuração flexível de fontes via `config.yaml`

## Estrutura

```
daily-tech-digest/
├── collector.py              # Coleta de conteúdo das fontes
├── processor.py              # Processamento e filtragem
├── newsletter_collector.py   # Orquestração da newsletter
├── config.yaml               # Configuração de fontes e parâmetros
├── prompts/
│   └── curator.md            # Prompt de curadoria editorial
└── .github/
    └── workflows/
        └── daily-digest.yml  # Workflow de automação diária
```

## Como Funciona

1. O GitHub Actions dispara o workflow no horário configurado
2. `collector.py` busca conteúdo das fontes definidas em `config.yaml`
3. `processor.py` filtra e prioriza os itens coletados
4. `newsletter_collector.py` orquestra a curadoria final via IA
5. A newsletter é gerada e distribuída automaticamente

---

Desenvolvido por [totobusnello](https://github.com/totobusnello)
