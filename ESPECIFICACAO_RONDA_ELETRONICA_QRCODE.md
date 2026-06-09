# Especificacao do MVP - Sistema de Ronda Eletronica por QR Code

## Objetivo do Sistema

Criar um sistema profissional de ronda eletronica por QR Code para controle operacional de funcionarios utilizando um unico celular Android compartilhado por turno.

O sistema sera utilizado por empresas para controle de rondas operacionais.

O funcionario fara login no celular compartilhado, iniciara o turno, realizara leituras dos QR Codes espalhados pelos pontos da empresa, registrara fotos obrigatorias e, ao finalizar o turno ou fazer logout, o sistema devera gerar automaticamente um relatorio completo e enviar por e-mail ao supervisor responsavel.

O sistema deve ser:

- simples
- rapido
- moderno
- profissional
- facil para funcionarios operacionais

## Tecnologias

### Backend

- Python FastAPI

### Banco de Dados

- PostgreSQL

### Frontend

Opcao recomendada para o MVP:

- Web responsivo mobile-first

Motivo: e a opcao mais simples, estavel e profissional para um MVP com um unico celular Android compartilhado, pois evita instalacao de app, facilita manutencao, deploy e atualizacoes.

### Hospedagem Futura

- VPS Linux

### Outros Recursos

- Leitura de QR Code
- Upload de imagens
- SMTP para envio de e-mail
- Upload de logo da empresa

## Funcionamento Geral

Fluxo principal do sistema:

1. Funcionario faz login.
2. Funcionario inicia turno.
3. Funcionario escaneia QR Codes.
4. Sistema registra automaticamente:
   - funcionario
   - ponto
   - data
   - horario
5. Apos cada leitura:
   - abrir camera automaticamente
   - exigir foto obrigatoria do local
6. Funcionario pode registrar:
   - observacao
   - ocorrencia
7. Funcionario finaliza turno ou faz logout.
8. Sistema:
   - encerra turno
   - gera relatorio completo
   - envia automaticamente por e-mail ao supervisor

## Funcionalidades do Funcionario

### Tela de Login

- usuario
- senha

### Apos Login

- mostrar nome do funcionario
- mostrar botao "Iniciar Turno"

### Durante o Turno

- botao "Ler QR Code"
- lista de pontos:
  - realizados
  - pendentes
- mostrar progresso da ronda

### Apos Leitura do QR Code

- abrir camera automaticamente
- exigir foto obrigatoria
- salvar:
  - foto
  - horario
  - ponto
  - funcionario

### Registros Permitidos

- observacao opcional
- ocorrencia opcional

### Finalizacao

- botao "Finalizar Turno"
- botao "Logout"

### Ao Finalizar

- encerrar turno automaticamente
- gerar relatorio automatico
- enviar e-mail automatico

## Funcionalidades Administrativas

Criar painel administrativo simples contendo:

### 1. Funcionarios

- cadastrar
- editar
- ativar/desativar
- resetar senha

### 2. Pontos QR

- cadastrar
- editar
- ativar/desativar
- gerar QR Code

### 3. Configuracoes da Empresa

- nome da empresa
- upload de logo
- e-mail do supervisor
- cor principal do sistema

### 4. Configuracoes SMTP

- e-mail remetente
- senha SMTP
- host SMTP
- porta SMTP

## Personalizacao da Empresa

O sistema deve permitir personalizacao visual da empresa.

Mostrar:

- logo da empresa
- nome da empresa

Locais:

- tela de login
- cabecalho do sistema
- relatorios e e-mails

## QR Code

Cada ponto tera:

- nome do ponto
- codigo QR unico
- descricao
- status ativo/inativo

Exemplos:

- `PONTO_PORTAO_01`
- `PONTO_GARAGEM_02`
- `PONTO_CORREDOR_03`

O sistema deve:

- impedir leitura duplicada no mesmo turno
- registrar horario automaticamente
- identificar ponto escaneado
- exigir foto obrigatoria apos leitura

## Mecanismos Antifraude

Implementar:

1. Foto obrigatoria apos leitura QR.
2. Registro automatico com horario do servidor.
3. Registro do funcionario responsavel.
4. Impedir leitura duplicada no mesmo turno.
5. Tempo minimo configuravel entre leituras.
6. Observacao opcional.
7. Ocorrencia opcional.

Objetivo:

Evitar falsa ronda e leituras sem verificacao real do local.

## Relatorio Automatico por E-mail

Ao final de cada turno ou logout do funcionario, o sistema deve obrigatoriamente:

1. Encerrar turno automaticamente.
2. Gerar relatorio completo.
3. Enviar automaticamente por e-mail para:
   - supervisor
   - ou e-mail configurado no sistema

O envio deve ocorrer automaticamente sem intervencao manual.

## Conteudo do Relatorio

O relatorio deve conter:

- logo da empresa
- nome da empresa
- nome do funcionario
- data do turno
- horario de inicio
- horario de fim
- duracao do turno

### Resumo

- quantidade de pontos
- pontos realizados
- pontos pendentes

### Lista Completa

- nome do ponto
- status:
  - realizado
  - pendente
- horario da leitura
- foto registrada

### Tambem Incluir

- observacoes
- ocorrencias
- status final da ronda

Exemplos de status:

- Ronda concluida com sucesso
- Ronda concluida com pendencias
- Turno encerrado parcialmente

## Formato do E-mail

### Assunto

```text
Relatorio de Turno - [Funcionario] - [Data]
```

### Formato

- HTML profissional
- layout corporativo
- tabela organizada
- imagens/fotos anexadas ou exibidas

## Banco de Dados

Criar tabelas:

### 1. usuarios

- id
- nome
- email
- senha_hash
- tipo_usuario
- ativo

### 2. funcionarios

- id
- usuario_id
- nome
- cargo
- ativo

### 3. pontos_qr

- id
- nome_ponto
- codigo_qr
- descricao
- ordem
- ativo

### 4. turnos

- id
- funcionario_id
- data_inicio
- data_fim
- status
- observacao_final

### 5. leituras_qr

- id
- turno_id
- ponto_qr_id
- funcionario_id
- data_hora
- observacao
- ocorrencia
- foto
- status

### 6. configuracoes

- id
- nome_empresa
- logo_empresa
- email_supervisor
- cor_primaria

## Regras Importantes

- Sistema totalmente dinamico.
- Nao limitar funcionarios.
- Nao limitar pontos QR.
- Nao limitar turnos.
- Nao limitar rondas.

Administrador deve cadastrar, editar e ativar/desativar funcionarios e pontos QR livremente.

O sistema deve:

- funcionar com um unico celular compartilhado
- permitir logout e troca de usuario
- registrar funcionario responsavel
- registrar horario do servidor
- considerar automaticamente todos os pontos ativos nos relatorios

## Design

### Visual

- moderno
- clean
- corporativo
- simples
- rapido

### Layout

- responsivo
- otimizado para celular Android

### Cor

- configuravel pelo administrador

## Seguranca

Implementar:

- autenticacao com login e senha
- hash de senha
- validacao de sessao
- protecao basica da API

## Entregaveis

Gerar:

- estrutura completa do projeto
- backend FastAPI funcional
- frontend responsivo
- APIs organizadas
- banco PostgreSQL
- leitura QR
- upload de fotos
- envio automatico de e-mail
- upload de logo da empresa
- painel administrativo
- README completo
- instrucoes de instalacao
- instrucoes de deploy em VPS Linux
- arquivo `.env` de exemplo
- comentarios importantes no codigo

## Dados de Exemplo

Criar:

- funcionarios ficticios
- pontos QR ficticios
- empresa exemplo
- supervisor exemplo

## Fora do Escopo Neste MVP

Nao implementar agora:

- IA
- reconhecimento facial
- GPS avancado
- WhatsApp
- mapa em tempo real
- modo offline avancado

## Prioridades do MVP

Priorizar:

- simplicidade
- estabilidade
- baixo custo operacional
- manutencao facil

O MVP deve focar em:

- login
- turno
- QR Code
- foto obrigatoria
- registro de horarios
- antifraude
- relatorio automatico por e-mail
- administracao simples
