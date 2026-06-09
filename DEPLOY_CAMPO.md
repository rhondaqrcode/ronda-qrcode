# Deploy para uso real em campo

Este guia publica a API na internet com HTTPS para o app Flutter acessar fora do cabo USB.

## 1. O que voce precisa

- Um servidor Linux Ubuntu com IP publico.
- Um dominio ou subdominio apontando para o IP do servidor, por exemplo `api.suaempresa.com.br`.
- Docker e Docker Compose instalados no servidor.
- Portas `80` e `443` liberadas no firewall do servidor.

## 2. Preparar variaveis de producao

No servidor, dentro da pasta do projeto:

```bash
cp .env.production.example .env.production
```

Edite `.env.production`:

```text
SECRET_KEY=uma-chave-grande-e-secreta
DEFAULT_ADMIN_EMAIL=seu-email-admin
DEFAULT_ADMIN_PASSWORD=uma-senha-forte
API_DOMAIN=api.suaempresa.com.br
```

## 3. Subir a API com HTTPS

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Teste no navegador:

```text
https://api.suaempresa.com.br/health
https://api.suaempresa.com.br/docs
```

## 4. Gerar o app apontando para a internet

No computador de desenvolvimento:

```bash
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=https://api.suaempresa.com.br
```

O APK final fica em:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

## 5. Dados persistentes

No deploy Docker, banco, uploads e relatorios ficam no volume `facilities_data`.
Nao remova esse volume sem backup.

## 6. Backups

Faca backup periodico destes arquivos dentro do volume:

- `/data/facilities.db`
- `/data/uploads`
- `/data/reports`

## 7. Observacoes importantes

- Troque a senha do admin no primeiro acesso.
- Para operacao real com muitos usuarios, o proximo passo tecnico e migrar SQLite para PostgreSQL.
- Para publicar em loja ou distribuir profissionalmente, gere APK/AAB assinado com chave propria.
