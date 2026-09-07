# Algoritmo, rastreabilidade e decisões

## Fluxo verificável

1. O importador acha um cabeçalho entre as primeiras 40 linhas, mas exige revisão.
   Nomes homônimos ganham sufixo estável; linha original permanece em `_source_row`.
   Linhas vazias, cabeçalhos repetidos e estatísticas explicitamente reconhecidas
   são excluídos com motivo. Valores brutos, ausências e extremos permanecem.
2. Fórmulas não são executadas. A inspeção compara workbook com e sem `data_only` e
   sinaliza cache ausente. Estatísticas usadas pela receita são recalculadas do bruto.
3. O motor separa tipos definidos pelo usuário. Para os numéricos, calcula escala
   robusta por IQR, ignora constantes na distância e escolhe deterministicamente o
   medoid observado. Pares sem sobreposição mínima não recebem distância. Não há
   imputação para fabricar um vetor completo.
4. Quantis lineares 10%/90% configuram a faixa local inicial. Restrições confirmadas
   recortam a faixa; conflito fica pendente. Target é do vetor observado e é limitado
   à faixa coerente. Precisão usa arredondamento half-up. Constantes não ganham
   tolerância inventada; categorias usam a moda; ausência usa somente regra confirmada.
5. Laboratório é avaliado por propriedade como conforme, não conforme ou inconclusivo.
   Ausência não aprova. Sem chave confirmada, não há join. O utilitário de vínculo
   impede expansão muitos-para-muitos e relata cobertura/ambiguidades.

O modo chama a referência de **condição recorrente**, não de estabilidade. Contagens
de registros e ordens são separadas. Faixas marginais não autorizam combinações
arbitrárias. Não existe percentual de confiança sem fundamento.

## Inspeção dos anexos

O `Claude.zip` continha os três nomes informados (aprox. 868 kB). A inspeção XML
confirmou `KSEA8BR45 WINDER` (`A1:AJ975`), Slitter vazia (`A1`),
`PARAMETROS DE PROCESSO ` (`A1:FF252`), `MÁSCARA` (`A1:FG657`) e `ABRIDORA`
(`A1:CM31`). A integração semântica real permanece um check manual neste ambiente;
os arquivos privados não são versionados.
O perfil inicial aceita nomes de abas com espaços finais e cabeçalhos deslocados, em
vez de codificar uma resposta para KSEA8BR45.

## Decisões pendentes (configuráveis)

- unidades, etapas, precisão, parâmetros ajustáveis e limites da máquina;
- categorias que separam condições e regra de blocos/lacuna temporal;
- versão de especificação aplicável ao histórico e aceite por lote;
- chave/janela válida para modo vinculado; `KSEA8BR45=KSEI8BR45` requer confirmação;
- revisão semântica das tabelas PDF e regras textuais propostas;
- critérios industriais de estabilidade, custo e produtividade (fora do MVP).
