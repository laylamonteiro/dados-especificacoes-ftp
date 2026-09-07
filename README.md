# Receita Local

Aplicação local para Windows 10/11 x64 que lê uma especificação em PDF,
resultados laboratoriais em Excel e um histórico de parâmetros de processo para
gerar uma **proposta exploratória e rastreável de receita**. A proposta não é uma
garantia de receita ideal nem uma validação industrial.

> **Importante sobre a URL:** o GitHub Actions gera o aplicativo para download;
> ele não hospeda a aplicação. Depois de executar `ReceitaLocal.exe` no Windows,
> o navegador abre uma URL como `http://127.0.0.1:8501`. Essa URL funciona somente
> naquele computador e apenas enquanto o executável estiver aberto. Isso mantém os
> arquivos industriais fora da internet.

## Caminho mais simples: baixar pela Releases

**Link permanente, sempre a versão mais recente:**
<https://github.com/laylamonteiro/dados-especificacoes-ftp/releases/latest>

Esse link não expira e não muda a cada versão — pode ser guardado nos favoritos.
Cada envio para `main` publica uma release nova automaticamente.

Existe também uma [prévia visual da interface](https://laylamonteiro.github.io/dados-especificacoes-ftp/),
com capturas reais da aplicação usando dados sintéticos, para ver as telas sem
instalar nada. As imagens ficam em `docs/` e são publicadas pelo GitHub Pages a
partir do branch; para atualizá-las depois de mexer na interface, rode:

```bash
python tools/gerar_previa.py --destino docs --versao "$(git rev-parse --short HEAD)"
```

### 1. Gerar o ZIP no GitHub (alternativa, durante o desenvolvimento)

1. Envie este repositório para o GitHub e confirme que o arquivo
   `.github/workflows/build-windows.yml` está na branch padrão (normalmente `main`).
2. No repositório do GitHub, clique na aba **Actions**.
3. Na coluna da esquerda, selecione **Validar e empacotar para Windows**.
4. Clique em **Run workflow**, escolha a branch que contém o código e confirme em
   **Run workflow**.
5. Abra a execução que apareceu e aguarde os jobs **Testes Python** e
   **Aplicativo Windows x64** ficarem verdes. O processo costuma levar alguns
   minutos.
6. No fim da página da execução, em **Artifacts**, clique em
   **ReceitaLocal-Windows-x64** para baixar o artefato.

Se o botão **Run workflow** não aparecer, verifique se você está autenticada, se
tem permissão de escrita no repositório, se Actions está habilitado em
**Settings > Actions > General** e se o workflow já existe na branch padrão.

### 2. Abrir a aplicação

1. Localize o ZIP baixado, `ReceitaLocal-Windows-x64.zip`.
2. **Antes de extrair**, clique com o botão direito no ZIP → **Propriedades** →
   marque **Desbloquear** → **OK**. Isso remove a marca de "arquivo baixado da
   internet" de todo o conteúdo de uma vez e evita o aviso do SmartScreen.
3. Extraia **todo** o conteúdo para uma pasta local gravável. Não execute o
   programa diretamente dentro do ZIP.
4. Entre na pasta `ReceitaLocal` extraída e dê dois cliques em
   `ReceitaLocal.exe`. Não é necessário instalar nada: o aplicativo é portátil e
   não precisa de Python, terminal nem permissão de administrador.
5. Aguarde o navegador padrão abrir sozinho, normalmente em
   `http://127.0.0.1:8531`. Se essa porta estiver ocupada, o aplicativo escolhe
   outra e grava o endereço em
   `%LOCALAPPDATA%\ReceitasProcesso\ENDERECO_DO_APLICATIVO.txt`.
6. Para encerrar corretamente, use **Encerrar aplicativo** na barra lateral.
   Fechar apenas a aba do navegador não encerra o servidor local.

### Diferença entre aviso e bloqueio

- **"O Windows protegeu o computador"** é o SmartScreen, um *aviso* de reputação
  para programas novos. Há **Mais informações → Executar assim mesmo**, e a
  existência desse botão indica que a política da empresa permite executar.
  Desbloquear o ZIP no passo 2 normalmente evita que esse aviso apareça.
- **"Bloqueado pelo administrador do sistema"** é uma *política corporativa*
  (AppLocker/WDAC). Nesse caso encaminhe o ZIP à TI. Não tente contornar
  SmartScreen, antivírus ou políticas da empresa.
- **Antivírus removeu o arquivo**: falso positivo conhecido de executáveis
  empacotados com PyInstaller. A TI consegue liberar pelo hash; a solução
  definitiva é assinatura de código.

### 3. Fazer um teste rápido sem dados da empresa

1. Vá em **Nova análise** e clique em **Carregar demonstração sintética**.
2. Gere a análise usando os dados sintéticos identificados como demonstração.
3. Vá em **Receita proposta**, gere a análise e confira a configuração de
   referência, os parâmetros, as evidências e as pendências apresentadas.
4. Exporte a receita em Excel e PDF e abra os dois arquivos.
5. Feche corretamente o aplicativo, abra `ReceitaLocal.exe` de novo e confirme
   que a análise continua no Histórico.

### 4. Testar com os três arquivos reais

1. Se os arquivos estiverem no OneDrive, escolha **Sempre manter neste
   dispositivo** e espere o download terminar.
2. Crie uma nova análise e selecione:
   - o PDF de especificação;
   - o Excel de resultados laboratoriais;
   - o Excel de parâmetros de processo.
3. Na revisão da importação, confira aba, linha de cabeçalho, registros
   excluídos e o motivo de cada exclusão — **para o arquivo de processo e para o
   de laboratório**, nas duas abas da tela.
4. Em regras e hipóteses, escolha os parâmetros, as colunas que separam condições
   incompatíveis e confira os requisitos lidos do PDF, corrigindo o que for
   necessário. Confirme o alias `KSEA8BR45` / `KSEI8BR45` somente para este
   estudo de caso.
5. Em diagnóstico dos dados, ligue cada requisito à coluna correspondente do
   laboratório e avalie a qualidade. Sem esse vínculo confirmado o resultado é
   inconclusivo, nunca aprovado.
6. Gere a receita exploratória, confira pendências e evidências e exporte Excel e
   PDF.

Não faça upload dos arquivos de produção no GitHub ou no Actions. Eles devem ser
selecionados somente na aplicação executada localmente.

## O que verificar no primeiro teste

- A página abre em `127.0.0.1`, e não em um endereço público.
- Os arquivos originais permanecem inalterados.
- Ausências aparecem como pendências, não como zeros ou valores inventados.
- A receita distingue faixas observadas, restrições técnicas e limites da
  especificação.
- Excel, PDF e tela apresentam a mesma versão da receita.
- O histórico permanece disponível após reiniciar o aplicativo.

## Status de verificação

Verificado automaticamente a cada execução do workflow (24 testes):

- importação com cabeçalho deslocado, cabeçalho repetido, rodapé de estatísticas,
  colunas homônimas, aba vazia e caminho com acentos e espaços;
- limites nunca inventados para parâmetros constantes ou sem dados;
- separação de condições incompatíveis antes da escolha da referência;
- requisitos do PDF com limite unilateral, etapa e critério preservados;
- qualidade inconclusiva sem mapeamento confirmado;
- repetibilidade com as mesmas entradas, persistência entre reinicializações e
  exportações Excel/PDF consistentes com a tela;
- as sete telas renderizam sem stack trace;
- **verificação em navegador real**, no Linux contra a aplicação e no Windows
  contra o `.exe` empacotado: a interface carrega, as sete telas existem, o modo
  demonstração roda, a receita é gerada com os rótulos em português e o histórico
  oferece as exportações. Uma resposta HTTP 200 não prova nada disso;
- no runner Windows: build `onedir`, execução do `.exe` com porta fixa e com porta
  dinâmica, e a página inicial servida com 200.

Verificado manualmente contra os três arquivos do estudo de caso (não versionados):
219 registros de processo, 966 de laboratório, 19 requisitos do PDF e 3 ordens de
fabricação separadas.

Ainda depende de validação no Windows corporativo de destino: comportamento do
SmartScreen/antivírus sobre o executável não assinado, políticas de execução da
empresa e leitura de pastas do OneDrive nesse ambiente.

Dados persistentes, cópias de trabalho e logs ficam em
`%LOCALAPPDATA%\ReceitasProcesso`, nunca junto do executável. Consulte também o
[guia curto para Windows](docs/GUIA_WINDOWS.md), a
[documentação do algoritmo](docs/ALGORITMO.md) e o
[prompt para continuar o projeto em outro chat](docs/PROMPT_CONTINUACAO.md).

## Desenvolvimento local

Requer Python 3.12. Em Linux/macOS:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/streamlit run src/receita_local/ui/app.py --server.address 127.0.0.1
.venv/bin/python -m pytest -q
```

No PowerShell do Windows, troque `.venv/bin/` por `.venv\Scripts\`.

## Build manual no Windows

Como alternativa ao Actions, execute `build_windows.bat` em Windows 10/11 x64.
O build PyInstaller em modo `onedir` inclui Python e as dependências. O ambiente
Linux de desenvolvimento não produz nem valida o executável Windows; a validação
final deve ocorrer em Windows e, para uso corporativo, sob as políticas da empresa.

## Privacidade e limitações

- O processamento é local; não há APIs externas, telemetria, IA remota ou CDN.
- O servidor escuta exclusivamente em `127.0.0.1`.
- Actions recebe somente o código usado no build, nunca os arquivos que o usuário
  selecionar posteriormente no aplicativo.
- Uma URL pública exigiria hospedar o sistema e transmitir os arquivos pela rede,
  contrariando o requisito de processamento exclusivamente local.
- Os anexos reais não fazem parte da distribuição. Fixtures sintéticas estão em
  `fixtures/demo/` e são identificadas como demonstração.
