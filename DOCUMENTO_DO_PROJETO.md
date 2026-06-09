# Documento do Projeto - Sistema de Supervisao de Zeladoria

Este documento centraliza os requisitos, decisoes e pontos de referencia do sistema. Sempre que houver duvida sobre escopo, funcionalidades ou evolucao, este deve ser o primeiro arquivo consultado.

## Objetivo

Criar um MVP funcional, profissional, organizado e escalavel para supervisao de equipes externas de limpeza, conservacao, zeladoria e facilities, com base para evoluir futuramente para um SaaS operacional.

## Tecnologias

- Backend: Python com FastAPI
- Banco inicial: SQLite
- Frontend mobile: Flutter
- Painel administrativo: Streamlit
- Comunicacao: API REST
- Arquitetura: separacao entre API, app mobile, dashboard, arquivos enviados e relatorios

## Estrutura do Projeto

```text
backend/    API REST FastAPI, models, schemas, rotas, seguranca, banco e servicos
mobile/     App Flutter para funcionarios em campo
dashboard/  Painel Streamlit para supervisores e administradores
uploads/    Fotos e arquivos enviados pela operacao
reports/    Relatorios gerados pelo sistema
tests/      Testes automatizados do MVP
```

## Perfis de Usuario

- Administrador: gerencia funcionarios, supervisores, locais, relatorios e indicadores.
- Supervisor: acompanha equipe, aprova servicos, consulta ocorrencias, fotos, faltas e produtividade.
- Funcionario: executa rotina de campo com check-in, check-out, checklist, ocorrencias, fotos e observacoes.

## Funcionalidades do App do Funcionario

- Login seguro com JWT.
- Check-in em local de trabalho com latitude/longitude quando disponivel.
- Check-out do atendimento em andamento.
- Registro de ronda por QR Code.
- Checklist de limpeza/conservacao.
- Registro de ocorrencias.
- Upload de fotos.
- Registro de observacoes.
- Historico de tarefas e atendimentos.
- Interface simples, moderna e adequada para usuarios operacionais.

## Funcionalidades do Supervisor

- Visualizar equipe.
- Aprovar ou reprovar servicos.
- Consultar fotos enviadas.
- Consultar ocorrencias.
- Acompanhar relatorios de produtividade.
- Controlar faltas.
- Consultar historico completo de execucao.
- Cadastrar locais/clientes reais antes da operacao.
- Desativar funcionarios e locais/clientes preservando historico operacional.
- Cadastrar pontos de ronda com QR Code e acompanhar leituras feitas pelos funcionarios.
- Visualizar presencas com coordenadas GPS e abrir no mapa pelo app.

## Funcionalidades do Dashboard

- Quantidade de servicos realizados.
- Funcionarios ativos.
- Ranking de produtividade.
- Ocorrencias por local.
- Relatorios em PDF.
- Indicadores operacionais.

## Backend

- API REST organizada por rotas.
- Models SQLAlchemy.
- Schemas Pydantic.
- Banco SQLite estruturado.
- Upload de imagens.
- Autenticacao JWT.
- Logs de aplicacao.
- Tratamento centralizado de erros.
- Servicos separados para armazenamento e relatorios.

## Banco de Dados

Tabelas principais:

- users: usuarios de acesso ao sistema.
- employees: funcionarios operacionais e supervisores vinculados.
- locations: locais ou clientes atendidos.
- attendance: check-in, check-out e faltas.
- checklists: servicos/checklists realizados.
- checklist_tasks: itens internos do checklist.
- occurrences: ocorrencias operacionais.
- photos: fotos enviadas pela equipe.
- reports: relatorios PDF gerados.

## Design

- Visual corporativo.
- Cores principais: azul escuro, branco e cinza.
- Usabilidade simples para funcionarios de campo.
- Dashboard objetivo para leitura rapida de indicadores.

## Preparacao Para Evolucao

O sistema deve deixar pontos claros para evoluir com:

- GPS no check-in.
- QR Code por local.
- IA para analise de fotos, ocorrencias e produtividade.
- Chatbot operacional.
- Notificacoes push.
- Reconhecimento facial.
- Multiempresa e planos SaaS.

## Entregaveis do MVP

- Estrutura completa do projeto.
- Backend FastAPI funcional.
- Modelos do banco.
- APIs principais.
- App Flutter funcional com area do funcionario e area do supervisor.
- Dashboard Streamlit opcional para computador.
- README profissional.
- Instrucoes de execucao.
- Comentarios pontuais explicando decisoes tecnicas relevantes.

## Diretriz Atual

O celular deve ser a interface principal do sistema. Funcionario, supervisor e administrador devem conseguir executar as rotinas centrais pelo app Flutter, deixando o dashboard web apenas como apoio complementar.
