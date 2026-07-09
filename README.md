# Ronda Eletronica QR - MVP

Sistema profissional de ronda eletronica por QR Code para controle operacional de funcionarios usando um unico celular Android compartilhado por turno.

O documento completo do escopo esta em [ESPECIFICACAO_RONDA_ELETRONICA_QRCODE.md](ESPECIFICACAO_RONDA_ELETRONICA_QRCODE.md).

## O Que Este MVP Entrega

- Login com senha e token de sessao.
- Inicio e finalizacao de turno.
- Registro de ponto por selecao dos pontos cadastrados, com camera QR como apoio quando suportada.
- Foto obrigatoria apos cada leitura.
- Registro automatico de funcionario, ponto, data, horario do servidor e localizacao GPS.
- Validacao GPS por Haversine com latitude, longitude, precisao, distancia e raio permitido.
- Bloqueio de leitura duplicada no mesmo turno.
- Tempo minimo configuravel entre leituras.
- Observacao e ocorrencia opcionais.
- Relatorio HTML automatico ao finalizar turno ou logout.
- Envio automatico por e-mail via Resend quando configurado.
- Painel administrativo web para funcionarios, pontos QR, GPS, empresa, logo, e-mail e cor principal.
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
3. Toca em `Registrar ponto`.
4. Escolhe o ponto cadastrado ou usa a camera para selecionar pelo QR Code.
5. Tira a foto obrigatoria do local.
6. O navegador solicita a localizacao GPS do celular.
7. O sistema valida se o funcionario esta dentro do raio permitido do posto.
8. Adiciona observacao ou ocorrencia se precisar.
9. Salva a leitura.
10. Finaliza o turno ou faz logout.
11. O sistema gera o relatorio e tenta enviar o e-mail automaticamente.

## Administracao

No perfil administrador ou supervisor:

- Cadastrar funcionarios.
- Ativar/desativar funcionarios.
- Cadastrar pontos QR com latitude, longitude e raio permitido em metros.
- Capturar a localizacao atual do celular ao cadastrar ou editar o ponto.
- Ativar/desativar pontos QR.
- Visualizar QR Code SVG dos pontos.
- Configurar nome da empresa, logo, e-mail do supervisor, cor principal e raio GPS padrao.

## Validacao GPS

Cada ponto de ronda possui latitude, longitude e raio permitido em metros. Se o ponto nao tiver raio proprio, o sistema usa o raio padrao global, inicialmente 20 metros.

Ao registrar uma leitura, o frontend usa a Geolocation API do navegador para capturar latitude, longitude, precisao e data/hora da localizacao. O backend calcula a distancia ate o ponto pela formula de Haversine.

A leitura e aprovada somente quando:

- o GPS esta disponivel e autorizado;
- a precisao do GPS e de ate 30 metros;
- a distancia atual e menor ou igual ao raio permitido do ponto.

Se o funcionario estiver fora da area permitida, a leitura e bloqueada com a mensagem de distancia atual e raio permitido. Leituras aprovadas registram latitude, longitude, precisao, distancia e status GPS no banco e no relatorio.

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

## E-mail

O envio automatico do relatorio usa Resend via HTTPS. Configure no ambiente:

```text
RESEND_API_KEY=...
RESEND_FROM_EMAIL=Ronda QR <relatorios@seudominio.com.br>
```

Enquanto o Resend nao estiver configurado, o sistema ainda encerra o turno e gera o relatorio HTML em `reports/`, mas informa que o envio ficou aguardando configuracao.

## Testes

```bash
.venv\Scripts\python.exe -m pytest -q
```
