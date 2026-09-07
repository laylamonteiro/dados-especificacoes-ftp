# Prompt para continuar o projeto em outro chat

Copie o texto abaixo para um novo chat. Anexe ou disponibilize o repositório nesse
chat; somente o prompt não transfere os arquivos nem o histórico de commits.

```text
Quero continuar o desenvolvimento do projeto “Receita Local”. Trabalhe diretamente
no repositório que estou fornecendo: primeiro leia o README.md, todos os AGENTS.md
aplicáveis, docs/ALGORITMO.md, docs/GUIA_WINDOWS.md, o workflow
.github/workflows/build-windows.yml e inspecione o git log/status. Não recomece o
projeto do zero e não presuma que descrições de conversas anteriores estão corretas:
confirme tudo no código e nos testes.

Contexto essencial:
- É um MVP local e offline para Windows 10/11 x64.
- A interface é Streamlit, aberta pelo executável no navegador padrão em
  http://127.0.0.1:<porta>; não existe e não deve existir uma URL pública.
- O GitHub Actions apenas testa, cria o pacote PyInstaller onedir para Windows e
  publica o ZIP como artifact. Arquivos industriais nunca devem ir ao GitHub.
- A aplicação importa PDF de especificação, Excel laboratorial e Excel de processo,
  permite revisar importação/regras, gera receita exploratória rastreável, exporta
  Excel/PDF e persiste o histórico localmente.
- Nunca invente dados, faça joins artificiais ou trate a proposta como receita ideal
  ou validação industrial.
- KSEA8BR45 e KSEI8BR45 só podem ser equivalentes por alias explícito registrado.
- Dados persistentes ficam em %LOCALAPPDATA%\ReceitasProcesso; originais não podem
  ser alterados; processamento, logs e arquivos permanecem locais.

Antes de alterar código:
1. Mostre resumidamente o estado real encontrado no repositório.
2. Execute os testes existentes e inspecione a execução mais recente do workflow,
   se tiver acesso ao GitHub.
3. Identifique lacunas entre o que está implementado e o fluxo funcional descrito
   no README, priorizando falhas que impeçam uma pessoa não técnica de baixar, abrir
   e testar o aplicativo.

Depois, implemente uma melhoria completa e verificável, não apenas um plano. Preserve
a separação entre domain, importers, analysis, storage, exports, ui e launcher. O
motor de análise não pode depender do Streamlit. Não adicione serviços cloud,
telemetria, APIs externas, CDNs ou execução de expressões arbitrárias. Use fixtures
sintéticas nos testes e não versione documentos reais, bancos, logs ou artefatos de
produção.

Ao concluir:
- execute testes e verificações relevantes;
- se a interface mudar perceptivelmente, execute-a e registre uma captura de tela;
- atualize a documentação afetada;
- faça commit das alterações na branch atual;
- crie o pull request quando a ferramenta estiver disponível;
- relate com precisão o que foi validado localmente, o que foi validado no Actions e
  o que ainda depende de teste em um Windows corporativo.

Minha próxima prioridade específica é: [ESCREVA AQUI O QUE VOCÊ QUER MELHORAR OU O
ERRO QUE DESEJA CORRIGIR].
```
