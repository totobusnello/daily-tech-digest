# 🔥 THE DAILY BYTE - Setup Completo

## Passo a Passo para Deploy

---

## PASSO 1: Criar Repositório no GitHub

```bash
# No seu terminal, vá para onde quer criar o projeto
cd ~/projetos  # ou onde preferir

# Crie a pasta
mkdir daily-tech-digest
cd daily-tech-digest

# Inicialize git
git init
```

---

## PASSO 2: Copiar os Arquivos

Copie toda a estrutura de `daily-tech-digest/` para sua pasta local.

A estrutura final deve ser:
```
daily-tech-digest/
├── .github/
│   └── workflows/
│       └── daily-digest.yml
├── scripts/
│   ├── collector.py
│   ├── processor.py
│   ├── sender.py
│   └── run.py
├── prompts/
│   └── curator.md
├── templates/
│   └── email.html
├── config.yaml
├── requirements.txt
├── SKILL.md
└── SETUP.md
```

---

## PASSO 3: Criar Repositório no GitHub

1. Vá em https://github.com/new
2. Nome: `daily-tech-digest`
3. Privado (recomendado)
4. NÃO inicialize com README
5. Clique "Create repository"

---

## PASSO 4: Push Inicial

```bash
# Adicione todos os arquivos
git add .

# Commit inicial
git commit -m "🔥 Initial commit - THE DAILY BYTE"

# Conecte ao GitHub (substitua SEU_USUARIO)
git remote add origin https://github.com/SEU_USUARIO/daily-tech-digest.git

# Push
git branch -M main
git push -u origin main
```

---

## PASSO 5: Configurar Secrets no GitHub

1. Vá em: `https://github.com/SEU_USUARIO/daily-tech-digest/settings/secrets/actions`

2. Clique **"New repository secret"** e adicione:

### Secret 1: ANTHROPIC_API_KEY
- Name: `ANTHROPIC_API_KEY`
- Secret: `sk-ant-api03-...` (sua chave da Anthropic)
- Clique "Add secret"

### Secret 2: BUTTONDOWN_API_KEY
- Name: `BUTTONDOWN_API_KEY`
- Secret: `1efd990d-1ad0-4fb2-99cf-f000df7269bc`
- Clique "Add secret"

### Secret 3 (Opcional): X_BEARER_TOKEN
- Name: `X_BEARER_TOKEN`
- Secret: Seu Bearer Token do X/Twitter API
- Clique "Add secret"

---

## PASSO 6: Testar Manualmente

1. Vá em: `https://github.com/SEU_USUARIO/daily-tech-digest/actions`

2. Clique em "🔥 THE DAILY BYTE - Daily Digest"

3. Clique "Run workflow" (botão à direita)

4. Opções:
   - **preview_only = true**: Gera mas NÃO envia (para testar)
   - **preview_only = false**: Gera E envia para subscribers

5. Clique "Run workflow"

6. Acompanhe os logs clicando no run

---

## PASSO 7: Verificar Execução Automática

O workflow está configurado para rodar:
- **Todos os dias às 08:00 BRT** (11:00 UTC)

Para verificar:
1. Vá em Actions
2. Veja o histórico de execuções
3. Clique em qualquer run para ver logs

---

## 🔧 Comandos Úteis

### Rodar localmente (para debug):
```bash
cd scripts

# Só coletar
python collector.py

# Só processar (precisa ter coletado antes)
python processor.py

# Só enviar (precisa ter processado antes)
python sender.py --preview  # preview
python sender.py            # envia de verdade

# Pipeline completo
python run.py --preview     # tudo, mas só preview
python run.py               # tudo, e envia
```

### Ver logs no GitHub:
```
https://github.com/SEU_USUARIO/daily-tech-digest/actions
```

### Editar horário de execução:
Edite `.github/workflows/daily-digest.yml`:
```yaml
schedule:
  - cron: '0 11 * * *'  # 11 UTC = 08 BRT
```

Formato cron: `minuto hora dia mês dia-da-semana`
- `0 11 * * *` = 11:00 UTC todos os dias
- `0 12 * * 1-5` = 12:00 UTC seg-sex
- `30 10 * * *` = 10:30 UTC todos os dias

---

## 📊 Onde Ver os Resultados

1. **Email**: Chega no email dos subscribers
2. **Artifacts**: No GitHub Actions, cada run tem os JSONs gerados
3. **Buttondown Dashboard**: https://buttondown.email/emails

---

## ❓ Troubleshooting

### Erro: "ANTHROPIC_API_KEY not set"
→ Verifique se o secret está configurado corretamente

### Erro: "0 items collected"
→ Normal se X_BEARER_TOKEN não estiver configurado
→ RSS feeds podem estar temporariamente indisponíveis

### Erro no envio Buttondown
→ Verifique se a API key está correta
→ Verifique se há subscribers na lista

---

*Setup criado em 02/02/2026*
