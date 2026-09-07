# Guia curto — Windows 10/11 x64

## Antes de abrir pela primeira vez: desbloquear o ZIP

Todo arquivo baixado da internet chega com uma marca de origem. Por causa dela o
Windows mostra um aviso na primeira execução. Desbloquear o ZIP **antes de
extrair** remove a marca de todos os arquivos de uma vez e o aviso não aparece:

1. Clique com o botão direito no **arquivo ZIP baixado** (não na pasta extraída).
2. **Propriedades**.
3. Na parte de baixo da aba **Geral**, marque **Desbloquear** e clique em **OK**.
   Se essa opção não aparecer, o arquivo já está desbloqueado.
4. Só então extraia o ZIP.

Isso é o procedimento normal do Windows, não um contorno de política.

## Se mesmo assim aparecer "O Windows protegeu o computador"

Essa tela azul é o **SmartScreen**, um aviso de reputação: o programa é novo e
ainda não é conhecido pela Microsoft. Não é um bloqueio da empresa.

1. Clique em **Mais informações**.
2. Clique em **Executar assim mesmo**.

A presença desse botão significa que a política da empresa permite a execução.
**Se em vez disso aparecer uma mensagem dizendo que o aplicativo foi bloqueado
pelo administrador do sistema, pare por aí**: aí sim é uma política corporativa
(AppLocker/WDAC) e o caminho é falar com a TI. Não tente contornar.

Se o antivírus remover o arquivo, também fale com a TI: é um falso positivo
conhecido de aplicativos empacotados com PyInstaller, e eles conseguem liberar.

## Usar

1. Extraia todo o ZIP para qualquer pasta local gravável. Não execute dentro do ZIP.
2. Selecione arquivos OneDrive como **Sempre manter neste dispositivo**.
3. Abra `ReceitaLocal.exe`. Não é preciso instalar, ter Python, usar terminal nem
   ser administrador. **O navegador abre sozinho**, normalmente em
   **`http://127.0.0.1:8531`** — pode guardar esse endereço nos favoritos.
   Nenhuma internet é usada.
4. Em **Nova análise**, importe os três arquivos. Em **Revisão da importação**, confirme
   aba e cabeçalho do arquivo de processo **e** do de laboratório. Em **Regras e hipóteses**,
   escolha os parâmetros, as colunas que separam condições e confira os requisitos lidos do
   PDF. Em **Diagnóstico dos dados**, ligue cada requisito à coluna do laboratório e avalie a
   qualidade. Em **Receita proposta**, gere a proposta.
5. Baixe Excel/PDF. Use **Encerrar aplicativo** na lateral; fechar a aba não encerra.

## Se o navegador abrir e der "connection refused" ou "não é possível acessar esse site"

Antes de mais nada, **confira as outras abas do navegador**. Se ele estiver
configurado para restaurar a sessão anterior, a aba com erro pode ser de outro
site aberto antes, e a aba da aplicação estar ao lado.

O endereço normal é **`http://127.0.0.1:8531`**. Se essa porta já estiver ocupada
por outro programa, o aplicativo escolhe outra automaticamente. Para descobrir
qual está em uso:

1. Com o `ReceitaLocal.exe` aberto, cole isto na barra de endereços do Explorador
   de Arquivos e tecle Enter:

       %LOCALAPPDATA%\ReceitasProcesso

2. Abra o arquivo **`ENDERECO_DO_APLICATIVO.txt`**. A primeira linha é o endereço,
   algo como `http://127.0.0.1:52341`.
3. Copie essa linha e cole no navegador.

Esse arquivo só existe enquanto o aplicativo está aberto. Se ele não aparecer, o
programa não chegou a subir: veja `logs\launcher.log` na mesma pasta.

Endereços como `localhost:3000` ou `localhost:8501` **não** são desta aplicação.

### Se o endereço certo também falhar: proxy da empresa

Em rede corporativa o navegador às vezes é configurado para mandar **todo**
endereço ao proxy da empresa, inclusive os locais. Nesse caso a aplicação está no
ar, mas o navegador pergunta ao proxy em vez de perguntar ao próprio computador,
e a resposta vem como erro ou 404.

O aplicativo detecta essa configuração sozinho: se for o caso, o
`ENDERECO_DO_APLICATIVO.txt` traz um aviso no fim explicando isso.

A correção é da TI e é simples de pedir: **incluir `127.0.0.1`, `localhost` e
`<-loopback>` na lista de exceções do proxy**. É a configuração padrão
recomendada pela própria Microsoft para aplicações locais, e não abre exceção
nenhuma na navegação da empresa.

## Atualizar para uma versão nova

Baixe o ZIP novo, desbloqueie, extraia por cima ou em outra pasta e abra o
`ReceitaLocal.exe`. **Seu histórico não se perde**: análises, receitas e cópias de
trabalho ficam em `%LOCALAPPDATA%\ReceitasProcesso`, fora da pasta do programa.

Para saber em que versão você está, olhe o rodapé do cabeçalho da aplicação.

## Observações

Dados, banco e logs locais ficam em `%LOCALAPPDATA%\ReceitasProcesso`. O aplicativo
não altera os arquivos originais. Para remover dados, use a exclusão confirmada no
Histórico; cópias compartilhadas por outras análises permanecem. Uma proposta
revisada pelo usuário **não** equivale a validação em produção.

## Obter o ZIP pelo GitHub

Use sempre este link, que aponta para a versão mais recente e não expira:
<https://github.com/laylamonteiro/dados-especificacoes-ftp/releases/latest>

Durante o desenvolvimento também é possível baixar da aba **Actions**, na
execução mais recente, o artefato `ReceitaLocal-Windows-x64`. Actions entrega apenas o instalável: depois de extraído,
o programa roda no computador e abre `http://127.0.0.1:<porta>` automaticamente.
Não envie arquivos de produção ao GitHub; eles são selecionados somente na interface
local do aplicativo.
