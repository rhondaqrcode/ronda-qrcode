# Deploy no PythonAnywhere Gratuito - Ronda Eletronica QR

Este guia e para subir o sistema em uma conta gratuita do PythonAnywhere para teste, demonstracao e MVP inicial.

## Limitacoes importantes

No plano gratuito, use isto apenas para teste:

- limite baixo de armazenamento
- apenas 1 web app
- recursos limitados
- ASGI/FastAPI no PythonAnywhere ainda e recurso experimental
- PostgreSQL no PythonAnywhere e recurso pago
- em conta gratuita nova, use SQLite para teste

Para cliente real, o recomendado continua sendo VPS Linux com PostgreSQL.

## 1. Criar conta

Crie uma conta em:

```text
https://www.pythonanywhere.com/
```

O endereco gratuito ficara parecido com:

```text
https://SEUUSUARIO.pythonanywhere.com
```

## 2. Preparar o pacote no Windows

No computador onde esta o projeto, clique duas vezes em:

```text
preparar_pythonanywhere.bat
```

Ele cria este arquivo:

```text
dist_pythonanywhere/ronda-pythonanywhere.zip
```

Esse pacote ja ignora ambiente virtual, cache, banco local, logs, fotos enviadas e relatorios gerados.

## 3. Enviar o projeto

Opcoes:

### Opcao A - GitHub

No console Bash do PythonAnywhere:

```bash
cd ~
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git magnum
cd magnum
```

### Opcao B - Upload manual com o ZIP preparado

1. Envie `dist_pythonanywhere/ronda-pythonanywhere.zip` pelo painel `Files`.
2. Extraia para:

```text
/home/SEUUSUARIO/magnum
```

Exemplo pelo console Bash do PythonAnywhere, se o ZIP estiver em `/home/SEUUSUARIO`:

```bash
cd ~
mkdir -p magnum
unzip -o ronda-pythonanywhere.zip -d magnum
cd magnum
```

Nao envie manualmente:

- `.venv`
- `venv`
- `__pycache__`
- arquivos grandes de teste

## 4. Criar ambiente virtual

No console Bash:

```bash
cd ~/magnum
mkvirtualenv ronda --python=python3.10
pip install --upgrade pip
pip install -r requirements.txt
```

Se `python3.10` nao estiver disponivel na sua conta, use a versao mais nova disponivel no PythonAnywhere, por exemplo `python3.11`.

## 5. Criar arquivo .env

Copie o modelo preparado:

```bash
cd ~/magnum
cp .env.pythonanywhere.example .env
nano .env
```

Troque todas as ocorrencias de `SEUUSUARIO` pelo seu usuario do PythonAnywhere.

Conteudo esperado:

```text
APP_NAME=Ronda Eletronica QR API
ENVIRONMENT=production
DATABASE_URL=sqlite:////home/SEUUSUARIO/magnum/backend/facilities.db
SECRET_KEY=troque-por-uma-chave-grande-e-secreta
ACCESS_TOKEN_EXPIRE_MINUTES=480
UPLOADS_DIR=/home/SEUUSUARIO/magnum/uploads
REPORTS_DIR=/home/SEUUSUARIO/magnum/reports
DEFAULT_ADMIN_EMAIL=admin@suaempresa.com.br
DEFAULT_ADMIN_PASSWORD=troque-esta-senha
CORS_ORIGINS=["*"]
```

Tambem troque `SECRET_KEY`, `DEFAULT_ADMIN_EMAIL` e `DEFAULT_ADMIN_PASSWORD`.

## 6. Criar pastas de arquivos

```bash
mkdir -p ~/magnum/uploads
mkdir -p ~/magnum/reports
```

## 7. Testar importacao

```bash
cd ~/magnum
python -c "from pythonanywhere_asgi import app; print('ok')"
```

Se aparecer `ok`, continue.

## 8. Preparar ASGI no PythonAnywhere

No console Bash:

```bash
pip install --upgrade pythonanywhere
```

No painel da conta PythonAnywhere:

1. Va em `Account`.
2. Gere um `API token`.

Depois, no Bash:

```bash
pa website create --domain SEUUSUARIO.pythonanywhere.com --command '/bin/bash -lc "cd /home/SEUUSUARIO/magnum && /home/SEUUSUARIO/.virtualenvs/ronda/bin/uvicorn pythonanywhere_asgi:app --uds ${DOMAIN_SOCKET}"'
```

Troque `SEUUSUARIO`.

## 9. Acessar

Abra:

```text
https://SEUUSUARIO.pythonanywhere.com
```

Login inicial:

```text
admin@suaempresa.com.br
troque-esta-senha
```

## 10. Configurar SMTP Gmail

No painel admin do sistema:

```text
Host SMTP: smtp.gmail.com
Porta SMTP: 587
E-mail remetente: seuemail@gmail.com
Senha SMTP: senha de app do Gmail
Usar TLS: marcado
```

Use senha de app do Gmail, nao a senha normal.

## 11. Instalar na tela inicial do Android

No celular:

1. Abra o Chrome.
2. Acesse `https://SEUUSUARIO.pythonanywhere.com`.
3. Toque nos tres pontos.
4. Escolha `Adicionar a tela inicial` ou `Instalar app`.

## 12. Quando atualizar o sistema

Se usou GitHub:

```bash
cd ~/magnum
git pull
pip install -r requirements.txt
pa website reload --domain SEUUSUARIO.pythonanywhere.com
```

Se usou upload manual:

1. Rode `preparar_pythonanywhere.bat` novamente no Windows.
2. Envie o novo `dist_pythonanywhere/ronda-pythonanywhere.zip`.
3. Extraia por cima da pasta `~/magnum`.
4. Rode:

```bash
cd ~/magnum
pip install -r requirements.txt
pa website reload --domain SEUUSUARIO.pythonanywhere.com
```

Se o comando `reload` nao estiver disponivel na sua conta ASGI, use o painel/API do PythonAnywhere ou recrie o site ASGI.

## 13. Agendar aviso de cobranca por e-mail

Configure no `.env`:

```text
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=seuemail@gmail.com
EMAIL_PASSWORD=senha-de-app-do-gmail
BILLING_CLIENT_EMAIL=cliente@empresa.com.br
BILLING_CLIENT_NAME=Nome do Cliente
BILLING_DUE_DATE=2026-06-30
```

O aviso sera enviado somente quando faltarem exatamente 10 dias para `BILLING_DUE_DATE`.

No PythonAnywhere:

1. Va em `Tasks`.
2. Em `Scheduled tasks`, crie uma tarefa diaria.
3. Use um horario fixo, por exemplo `09:00`.
4. Comando:

```bash
cd /home/SEUUSUARIO/magnum && /home/SEUUSUARIO/.virtualenvs/ronda/bin/python -m backend.app.scripts.send_billing_notice
```

Troque `SEUUSUARIO`.

## Recomendacao

Use PythonAnywhere gratuito para:

- demonstracao
- teste interno
- validar com primeiro cliente

Para uso real com cliente pagando:

- VPS Linux
- PostgreSQL
- dominio proprio
- HTTPS
- backup diario
