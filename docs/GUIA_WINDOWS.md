# Guia curto — Windows 10/11 x64

1. Extraia todo o ZIP para qualquer pasta local gravável. Não execute dentro do ZIP.
2. Selecione arquivos OneDrive como **Sempre manter neste dispositivo**.
3. Abra `ReceitaLocal.exe`. O navegador abrirá em `127.0.0.1`; nenhuma internet é usada.
4. Em **Nova análise**, importe os três arquivos. Em **Revisão da importação**, confirme
   aba e cabeçalho do arquivo de processo **e** do de laboratório. Em **Regras e hipóteses**,
   escolha os parâmetros, as colunas que separam condições e confira os requisitos lidos do
   PDF. Em **Diagnóstico dos dados**, ligue cada requisito à coluna do laboratório e avalie a
   qualidade. Em **Receita proposta**, gere a proposta.
5. Baixe Excel/PDF. Use **Encerrar aplicativo** na lateral; fechar a aba não encerra.

Dados, banco e logs locais ficam em `%LOCALAPPDATA%\ReceitasProcesso`. O aplicativo
não altera originais. Para remover dados, use a exclusão confirmada no Histórico;
cópias compartilhadas por outras análises permanecem. Uma proposta revisada pelo
usuário **não** equivale a validação em produção.

Se a política corporativa bloquear o executável, contate TI. Não tente contornar a
política. O programa não requer administrador, Python, terminal ou conta.

## Obter o ZIP pelo GitHub

Na aba **Actions**, execute **Validar e empacotar para Windows** e baixe o artefato
`ReceitaLocal-Windows-x64`. Actions entrega apenas o instalável: depois de extraído,
o programa roda no computador e abre `http://127.0.0.1:<porta>` automaticamente.
Não envie arquivos de produção ao GitHub; eles são selecionados somente na interface
local do aplicativo.
