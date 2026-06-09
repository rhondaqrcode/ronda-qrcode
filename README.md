# Ronda Eletronica QR - MVP

Sistema profissional de ronda eletronica por QR Code para controle operacional de funcionarios usando um unico celular Android compartilhado por turno.

O documento completo do escopo esta em [ESPECIFICACAO_RONDA_ELETRONICA_QRCODE.md](ESPECIFICACAO_RONDA_ELETRONICA_QRCODE.md).

## O Que Este MVP Entrega

- Login com senha e token de sessao.
- Inicio e finalizacao de turno.
- Leitura de QR Code por camera no navegador Android quando suportado.
- Campo manual para codigo QR como alternativa operacional.
- Foto obrigatoria apos cada leitura.
- Registro automatico de funcionario, ponto, data e horario do servidor.
- Bloqueio de leitura duplicada no mesmo turno.
- Tempo minimo configuravel entre leituras.
- Observacao e ocorrencia opcionais.
- Relatorio HTML automatico ao finalizar turno ou logout.
- Envio automatico por e-mail quando SMTP estiver configurado.
- Painel administrativo web para funcionarios, pontos QR, empresa, logo, SMTP e cor principal.
- QR Code SVG gerado para cada ponto.

## Tecnologia

- Backend: Python FastAPI
- Banco: PostgreSQL em producao
- Banco local opcional: SQLite para desenvolvimento rapido
- Frontend: web responsivo mobile-first
- Deploy futuro: VPS Linux com Docker Compose, PostgreSQL e Caddy

## Estrutura

```text
backend/      API FastAPI, modelos, rotas, seguranca, relatorios e e-mail
frontend/     Interface web mobile-first para funcionario e administrador
uploads/      Fotos de ronda e logos enviados
reports/      Relatorios HTML gerados automaticamente
tests/        Testes automatizados do backend
deploy/       Configuracao Caddy para VPS
```

## Executar Local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Acesse:

- Sistema: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/docs`

Usuario inicial:

```text
Email: admin@facilities.local
Senha: admin123
```

Para desenvolvimento sem PostgreSQL, deixe no `.env`:

```text
DATABASE_URL=sqlite:///./backend/facilities.db
```

Para usar PostgreSQL local:

```text
DATABASE_URL=postgresql+psycopg://ronda:ronda@localhost:5432/ronda_eletronica
```

## Fluxo Operacional

1. Funcionario faz login no celular compartilhado.
2. Toca em `Iniciar Turno`.
3. Toca em `Ler QR Code`.
4. Escaneia o QR Code ou informa o codigo.
5. Tira a foto obrigatoria do local.
6. Adiciona observacao ou ocorrencia se precisar.
7. Salva a leitura.
8. Finaliza o turno ou faz logout.
9. O sistema gera o relatorio e tenta enviar o e-mail automaticamente.

## Administracao

No perfil administrador ou supervisor:

- Cadastrar funcionarios.
- Ativar/desativar funcionarios.
- Cadastrar pontos QR.
- Ativar/desativar pontos QR.
- Visualizar QR Code SVG dos pontos.
- Configurar nome da empresa, logo, e-mail do supervisor e cor principal.
- Configurar SMTP.

## Principais Rotas

- `POST /auth/login`
- `GET /auth/me`
- `GET /ronda/public-config`
- `POST /ronda/turnos/iniciar`
- `GET /ronda/turnos/ativo`
- `POST /ronda/leituras`
- `POST /ronda/turnos/finalizar`
- `POST /ronda/logout`
- `GET /ronda/pontos`
- `POST /ronda/pontos`
- `GET /ronda/pontos/{id}/qr.svg`
- `GET /ronda/config`
- `PUT /ronda/config`
- `POST /ronda/config/logo`

## Deploy Em VPS Linux

1. Copie `.env.production.example` para `.env.production`.
2. Altere `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY`, `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD` e dominio.
3. Ajuste `deploy/Caddyfile` com seu dominio.
4. Suba os containers:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

O compose cria:

- API FastAPI
- PostgreSQL
- Caddy para HTTP/HTTPS
- volumes persistentes para banco, uploads e relatorios

## SMTP

O envio de e-mail fica configuravel pelo painel administrativo.

Enquanto o SMTP nao estiver configurado, o sistema ainda encerra o turno e gera o relatorio HTML em `reports/`, mas informa que o envio ficou aguardando configuracao.

## Testes

```bash
.venv\Scripts\python.exe -m pytest -q
```
