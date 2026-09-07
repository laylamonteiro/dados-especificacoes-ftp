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
   ser administrador. O navegador abre em `127.0.0.1`; nenhuma internet é usada.
4. Em **Nova análise**, importe os três arquivos. Em **Revisão da importação**, confirme
   aba e cabeçalho do arquivo de processo **e** do de laboratório. Em **Regras e hipóteses**,
   escolha os parâmetros, as colunas que separam condições e confira os requisitos lidos do
   PDF. Em **Diagnóstico dos dados**, ligue cada requisito à coluna do laboratório e avalie a
   qualidade. Em **Receita proposta**, gere a proposta.
5. Baixe Excel/PDF. Use **Encerrar aplicativo** na lateral; fechar a aba não encerra.

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

Na aba **Actions**, abra a execução mais recente e baixe o artefato
`ReceitaLocal-Windows-x64`. Actions entrega apenas o instalável: depois de extraído,
o programa roda no computador e abre `http://127.0.0.1:<porta>` automaticamente.
Não envie arquivos de produção ao GitHub; eles são selecionados somente na interface
local do aplicativo.
