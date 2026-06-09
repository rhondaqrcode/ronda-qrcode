# Manual de uso do Sistema de Ronda Eletronica por QR Code

Este manual explica, de forma simples, como usar o sistema de ronda eletronica por QR Code.

O sistema foi criado para ajudar empresas a controlar rondas de funcionarios, porteiros, vigilantes, zeladores ou equipes operacionais.

## 1. O que o sistema faz

O sistema registra as rondas feitas durante um turno de trabalho.

O funcionario entra no sistema, inicia o turno, passa pelos pontos da empresa, le o QR Code de cada local, tira uma foto obrigatoria e salva a leitura.

No final do turno, o sistema encerra a ronda, gera um relatorio e envia por e-mail para o supervisor configurado.

O sistema registra:

- funcionario responsavel;
- ponto visitado;
- data e horario;
- foto do local;
- observacao, se houver;
- ocorrencia, se houver;
- pontos realizados;
- pontos pendentes;
- status final da ronda.

## 2. Perfis de acesso

O sistema possui dois tipos principais de acesso.

### Administrador

O administrador pode:

- cadastrar funcionarios;
- editar dados de funcionarios;
- remover funcionarios da lista operacional;
- cadastrar pontos de ronda;
- editar pontos de ronda;
- configurar meta de passagens por ponto;
- configurar tempo de carencia entre leituras;
- gerar e imprimir QR Codes;
- configurar dados da empresa;
- configurar envio de e-mail SMTP.

### Funcionario

O funcionario pode:

- fazer login;
- iniciar turno;
- ler QR Codes;
- tirar foto obrigatoria do local;
- informar observacao;
- informar ocorrencia;
- acompanhar pontos pendentes e realizados;
- finalizar o turno.

## 3. Como o administrador deve usar

### 3.1 Entrar no sistema

1. Abra o sistema no navegador ou pelo icone instalado no celular.
2. Digite o e-mail do administrador.
3. Digite a senha.
4. Clique em Entrar.

Depois do login, o administrador vera duas abas:

- Operacao;
- Admin.

A aba Admin e onde ficam os cadastros e configuracoes.

## 4. Cadastro de funcionarios

Na aba Admin, localize a area Funcionarios.

Para cadastrar um funcionario:

1. Informe o nome.
2. Informe o e-mail.
3. Informe a senha inicial.
4. Informe o telefone, se desejar.
5. Informe o cargo.
6. Escolha o perfil.
7. Clique em Cadastrar.

O funcionario cadastrado podera fazer login usando o e-mail e a senha informados.

Ao clicar em um funcionario cadastrado, o sistema mostra as informacoes dele.

Para remover um funcionario da lista operacional, clique em Remover.

## 5. Cadastro de pontos QR

Na aba Admin, localize a area Pontos QR.

Cada ponto representa um local da empresa que precisa ser visitado durante a ronda.

Exemplos:

- Portao Principal;
- Garagem;
- Corredor Operacional;
- Patio;
- Recepcao;
- Sala de Maquinas.

Para cadastrar um ponto:

1. Informe o nome do ponto.
2. Informe o codigo QR, se quiser definir manualmente.
3. Informe a ordem na lista.
4. Informe a meta de passagens por turno.
5. Informe a carencia entre leituras em minutos.
6. Informe uma descricao, se desejar.
7. Clique em Cadastrar ponto.

Se o codigo QR ficar em branco, o sistema pode gerar um codigo automaticamente.

## 6. O que significa cada campo do ponto

### Nome do ponto

E o nome do local onde o QR Code sera instalado.

Exemplo: Portao Principal.

### Codigo QR

E o codigo interno daquele ponto.

Exemplo: PONTO_PORTAO_01.

Esse codigo fica dentro do QR Code.

### Ordem na ronda

E apenas a posicao do ponto na lista.

Exemplo:

- ordem 1: Portao Principal;
- ordem 2: Garagem;
- ordem 3: Corredor.

Importante: a ordem nao obriga o funcionario a seguir uma sequencia fixa. Ela serve apenas para organizar a lista na tela.

### Meta de passagens por turno

E a quantidade de vezes que o funcionario precisa passar naquele ponto durante o turno.

Exemplo: se a meta for 4, o funcionario precisa registrar aquele ponto 4 vezes no mesmo turno.

### Carencia entre leituras em minutos

E o tempo minimo que o funcionario precisa aguardar para registrar o mesmo ponto novamente.

Exemplo:

Se a carencia for 45 minutos e o funcionario registrar o ponto as 22:00, a proxima leitura do mesmo ponto so sera liberada as 22:45.

Isso evita que o funcionario leia o mesmo QR Code varias vezes seguidas.

### Descricao

Campo opcional para explicar melhor onde fica o ponto.

Exemplo: QR Code instalado ao lado da porta da garagem.

## 7. Como imprimir QR Codes

Na aba Admin, na area Pontos QR, existem opcoes de impressao.

### Imprimir um ponto

1. Localize o ponto desejado.
2. Clique em Imprimir QR.
3. O sistema mostra a pre-visualizacao.
4. Clique em Imprimir agora.

Se a impressao direta nao abrir, clique em Baixar folha HTML.

Depois abra o arquivo baixado no Chrome ou Edge e imprima usando Ctrl + P.

### Imprimir todos os pontos

1. Clique em Imprimir todos.
2. O sistema mostra uma folha com todos os QR Codes.
3. Clique em Imprimir agora ou Baixar folha HTML.
4. Imprima a folha.
5. Recorte e fixe cada QR Code no local correto.

## 8. Como o funcionario deve usar

### 8.1 Fazer login

1. Abra o sistema no celular.
2. Digite o e-mail.
3. Digite a senha.
4. Clique em Entrar.

Se o celular for compartilhado por turno, cada funcionario deve fazer login com o proprio usuario.

## 9. Iniciar turno

Depois do login, o funcionario deve clicar em Iniciar turno.

A partir desse momento, o sistema passa a registrar as leituras daquele funcionario.

O sistema mostra:

- nome do funcionario;
- turno atual;
- progresso da ronda;
- total de passagens esperadas;
- passagens realizadas;
- passagens pendentes;
- lista dos pontos.

## 10. Registrar uma leitura

Para registrar uma ronda:

1. Clique em Ler QR Code.
2. Aponte a camera para o QR Code do ponto.
3. Tire ou selecione a foto obrigatoria do local.
4. Se necessario, escreva uma observacao.
5. Se houver problema, escreva uma ocorrencia.
6. Clique em Salvar leitura.

O sistema registra automaticamente o horario usando o horario do servidor.

## 11. Foto obrigatoria

A foto e obrigatoria para aumentar a seguranca da ronda.

Ela ajuda o supervisor a confirmar que o funcionario esteve no local correto.

Sem foto, o sistema nao salva a leitura.

## 12. Observacao e ocorrencia

### Observacao

Use para informar algo simples.

Exemplo: Local conferido, tudo normal.

### Ocorrencia

Use quando houver algum problema.

Exemplos:

- luz queimada;
- porta aberta;
- vazamento;
- portao com defeito;
- movimentacao suspeita.

## 13. Regra de carencia

Depois que um ponto e registrado, ele pode ficar bloqueado por alguns minutos.

Esse tempo e definido pelo administrador.

Exemplo:

- ponto: Portao Principal;
- carencia: 45 minutos;
- leitura feita as 22:00;
- proxima leitura liberada as 22:45.

Se o funcionario tentar registrar antes do tempo, o sistema mostra uma mensagem amigavel:

Ponto verificado recentemente. Proxima leitura liberada as 22:45.

Essa mensagem nao e erro do sistema. Ela apenas informa que o ponto ainda esta dentro do tempo de carencia.

## 14. Meta de passagens

Cada ponto pode ter uma meta de passagens por turno.

Exemplo:

Se o ponto Garagem tiver meta 4, ele precisa ser registrado 4 vezes durante o turno.

O funcionario pode fazer as leituras em horarios diferentes, sem horario fixo.

Isso ajuda a evitar uma rotina previsivel.

## 15. Finalizar turno

No final do trabalho, o funcionario deve clicar em Finalizar turno.

Ao finalizar, o sistema:

1. encerra o turno;
2. calcula os pontos realizados;
3. calcula os pontos pendentes;
4. gera o relatorio;
5. envia o relatorio por e-mail ao supervisor.

Se o funcionario fizer logout com turno aberto, o sistema tambem pode encerrar o turno automaticamente.

## 16. Relatorio enviado por e-mail

O relatorio mostra:

- nome da empresa;
- nome do funcionario;
- data do turno;
- horario de inicio;
- horario de fim;
- duracao;
- quantidade total esperada;
- quantidade realizada;
- quantidade pendente;
- lista dos pontos;
- horarios das leituras;
- fotos registradas;
- observacoes;
- ocorrencias;
- status final da ronda.

## 17. Status da ronda

O relatorio pode indicar:

- ronda concluida com sucesso;
- ronda concluida com pendencias;
- turno encerrado parcialmente.

## 18. Cuidados importantes

Para usar corretamente:

- cada funcionario deve usar o proprio login;
- nao compartilhe senha;
- sempre tire foto do local;
- confira se o QR Code esta no local correto;
- finalize o turno ao terminar o trabalho;
- mantenha o e-mail do supervisor atualizado;
- teste o envio de e-mail antes de usar em producao.

## 19. Problemas comuns

### O ponto aparece bloqueado

Isso significa que ele foi verificado recentemente.

Aguarde o horario indicado pelo sistema.

### A camera nao abriu

Verifique se o navegador tem permissao para usar a camera.

Se necessario, digite o codigo do QR manualmente.

### A foto nao salva

Confira se uma foto foi escolhida ou tirada antes de salvar.

### O relatorio nao chegou no e-mail

Confira as configuracoes SMTP no painel Admin.

No Gmail, normalmente e necessario usar senha de aplicativo.

### O botao imprimir nao abriu a impressao

Use a opcao Baixar folha HTML.

Depois abra o arquivo baixado no Chrome ou Edge e imprima.

## 20. Resumo rapido para funcionario

1. Entrar com e-mail e senha.
2. Clicar em Iniciar turno.
3. Ir ate o ponto de ronda.
4. Ler o QR Code.
5. Tirar foto obrigatoria.
6. Salvar leitura.
7. Repetir nos outros pontos.
8. Respeitar o horario de liberacao quando o ponto estiver em carencia.
9. Finalizar turno ao terminar.

## 21. Resumo rapido para administrador

1. Entrar como administrador.
2. Cadastrar funcionarios.
3. Cadastrar pontos QR.
4. Definir meta de passagens.
5. Definir carencia entre leituras.
6. Imprimir QR Codes.
7. Fixar QR Codes nos locais corretos.
8. Configurar e-mail do supervisor.
9. Acompanhar os relatorios enviados ao final dos turnos.

