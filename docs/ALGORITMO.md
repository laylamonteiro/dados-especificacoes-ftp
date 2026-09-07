# Algoritmo, rastreabilidade e decisões

## Fluxo verificável

1. **Importação.** O importador procura o cabeçalho nas primeiras 40 linhas e sempre
   exige revisão. Nomes homônimos ganham sufixo estável (`Observações__2`); a linha
   original permanece em `_source_row`. São excluídos com motivo explícito: linhas
   vazias, cabeçalhos repetidos, rótulos de estatística conhecidos e **linhas sem data
   válida na coluna temporal** — é este último critério que separa registros de
   produção do rodapé de agregados (`+3sigma`, `Limite superior`, `Campo Real`).
   Valores brutos, ausências e extremos permanecem intactos.
2. **Fórmulas.** Não são executadas. A inspeção compara o workbook com e sem
   `data_only` e sinaliza fórmula sem valor em cache. As estatísticas usadas pela
   receita são recalculadas a partir dos registros brutos aceitos.
3. **Especificação.** Os requisitos são lidos do texto do PDF, não de heurística de
   tabela. O parser distingue **requisito do cliente** de **controle interno** pela
   seção do documento, registra a etapa declarada no nome (Winder, Slitter, após
   bobinamento) e preserva limites unilaterais como ausentes — `-` nunca vira zero.
   Requisitos qualitativos (Aparência) ficam fora do cálculo numérico. Tudo entra
   como proposta editável; se nada for reconhecido, a interface pede cadastro manual.
4. **Separação de condições.** Antes de qualquer referência, os registros são
   particionados pelas colunas categóricas que o usuário confirmou (receita, ordem,
   máquina). A receita usa a condição com mais registros e declara as demais como
   não combinadas. Em seguida os registros são ordenados no tempo e os blocos de
   produção são contados por lacuna configurável; lacunas longas não são atravessadas.
5. **Referência.** Escala robusta por IQR, colunas constantes ignoradas na distância,
   medoid observado escolhido deterministicamente (empate resolvido pela primeira
   posição). Pares sem sobreposição mínima não recebem distância. Não há imputação
   para fabricar um vetor completo: se o parâmetro está ausente na condição de
   referência, o item fica **pendente** em vez de receber a mediana.
6. **Faixas.** Quantis lineares configuráveis (padrão 10%/90%) sobre o subconjunto
   selecionado. Restrições confirmadas recortam a faixa; conflito fica pendente e não
   é resolvido em silêncio. O target vem do vetor observado e é limitado à faixa
   coerente. Precisão usa arredondamento half-up. Parâmetro constante mostra o valor
   observado e declara ausência de evidência para tolerância; categórico usa a moda;
   sem dados, apenas regra técnica confirmada.
7. **Qualidade.** Avaliada por propriedade como conforme, não conforme ou
   inconclusivo, com contagem de leituras fora do limite e seções envolvidas. O
   vínculo entre requisito e coluna do laboratório é **confirmado pelo usuário**;
   sem mapeamento o resultado é inconclusivo. Ausência de teste nunca é aprovação e
   o aplicativo não emite aprovação de lote. O utilitário de vínculo impede expansão
   muitos-para-muitos e relata cobertura e ambiguidades.

O modo chama a referência de **condição recorrente**, não de estabilidade. Contagens
de registros e de ordens são separadas. Faixas marginais não autorizam combinações
arbitrárias. Não existe percentual de confiança sem fundamento.

## Verificado com os arquivos do estudo de caso

| Verificação | Resultado |
|---|---|
| `PARAMETROS DE PROCESSO ` (espaço final) | 219 registros aceitos; 15 linhas excluídas com motivo |
| `KSEA8BR45 WINDER` | 966 registros aceitos; 8 linhas excluídas com motivo |
| `KSEA8BR45 SLITTER` (vazia) | mensagem acionável, sem stack trace |
| Requisitos do PDF | 19 extraídos: 6 do cliente, 13 de controle interno, 11 unilaterais |
| Ordens de fabricação | 144135, 144138 e 146748 separadas antes da referência |
| Motor sobre 219 × 116 parâmetros | 0,11 s, resultado idêntico entre execuções |

Os arquivos de produção não são versionados; a verificação acima é reprodutível
apontando o aplicativo para eles localmente.

## Decisões pendentes (configuráveis)

- unidades, etapas, precisão, parâmetros ajustáveis e limites técnicos da máquina;
- quais colunas separam condições e qual lacuna delimita blocos de produção;
- versão de especificação aplicável ao histórico e regra de aceite por lote;
- chave e janela válidas para o modo vinculado; `KSEA8BR45=KSEI8BR45` exige confirmação;
- revisão semântica dos requisitos extraídos e das regras textuais propostas;
- cabeçalhos enganosos da FTP (`Turno` contém a receita, `Responsável Teste` contém a
  ordem de fabricação): hoje o usuário renomeia no mapeamento, sem renomeação automática;
- critérios industriais de estabilidade, custo e produtividade (fora do MVP).
