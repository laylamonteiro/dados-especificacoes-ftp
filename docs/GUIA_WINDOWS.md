# Guia curto — Windows 10/11 x64

1. Extraia todo o ZIP para qualquer pasta local gravável. Não execute dentro do ZIP.
2. Selecione arquivos OneDrive como **Sempre manter neste dispositivo**.
3. Abra `ReceitaLocal.exe`. O navegador abrirá em `127.0.0.1`; nenhuma internet é usada.
4. Importe os três arquivos, revise cabeçalho/mapeamento, confirme regras e gere a proposta.
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
