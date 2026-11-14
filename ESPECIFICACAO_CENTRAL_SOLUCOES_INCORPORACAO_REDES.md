# Central de Soluções de Incorporação de Redes
## Especificação Funcional e Técnica para implementação em Django

> **Nome do sistema:** Central de Soluções de Incorporação de Redes
> **Sigla interna / nome do projeto Django:** `csir`
>
> **Documento de engenharia.** Escrito para ser aberto no VSCode e executado passo a passo.
> Gerado a partir da engenharia reversa de:
> - `Gestão de Incorporação RD - Corporativo.pbix` (modelo semântico, DAX, Power Query, relatório)
> - `Orçamento NOME_DO_EMPREENDIMENTO_PEP 7.1.2.xlsx` (modelo de orçamento RDU)
> - `POP.00813.EQTL - 00 - Anexo II - Checklist documentos - Incorporação de Redes 4.xlsx` (checklist documental)
> - `ESPEC_painel_tratativa_notas_incorporacao.md` (painel de tratativas a ser portado para dentro do sistema)
>
> Versão do documento: 2.0 — 14/11/2026
>
> **ESCOPO ATUAL (v2.0): sistema próprio de gestão das notas de incorporação** — Visão geral, Análise, Prazos,
> Notas (lista + ficha com acompanhamento) e Documentos modelo, sobre uma base única sincronizada do Snowflake.
> O Dashboard-réplica do BI e as Tratativas foram removidos. Ver [§23.0](#23-estado-atual-da-implementação).
> **Este arquivo é a referência viva do sistema**: toda mudança implementada deve ser registrada aqui
> (ver [§23 Estado atual da implementação](#23-estado-atual-da-implementação)).
>
> Histórico: 1.0 especificação inicial · 1.1 tratativas e consolidação · **1.2** nova identidade visual
> (login e paleta), padrão de envio/validação/concorrência, estado da implementação · **1.3** fonte Snowflake
> `TB_NOTAS_IR_CORPORATIVO` mapeada (`docs/MAPEAMENTO_SNOWFLAKE.md`) · **1.4** sistema reduzido a 3 módulos;
> Dashboard réplica do BI (engenharia reversa do `.pbix`), sincronização com o Snowflake, Tratativas completas (F8).

---

## Índice

1. [Objetivo e escopo](#1-objetivo-e-escopo)
2. [Diagnóstico do BI atual (engenharia reversa)](#2-diagnóstico-do-bi-atual-engenharia-reversa)
3. [Diagnóstico das planilhas modelo](#3-diagnóstico-das-planilhas-modelo)
4. [Arquitetura da solução](#4-arquitetura-da-solução)
5. [Perfis de acesso e matriz de permissões](#5-perfis-de-acesso-e-matriz-de-permissões)
6. [Modelo de dados completo (código Django)](#6-modelo-de-dados-completo-código-django)
7. [Módulo 1 — Painel / BI](#módulo-1--painel--bi)
8. [Módulo 2 — Carteira de Notas (Incorporações)](#módulo-2--carteira-de-notas-incorporações)
9. [Módulo 3 — Documentos Modelo (central de downloads)](#módulo-3--documentos-modelo-central-de-downloads)
10. [Módulo 4 — Orçamento RDU](#módulo-4--orçamento-rdu)
11. [Módulo 5 — Checklist documental](#módulo-5--checklist-documental)
12. [Módulo 6 — Esteira de medidas e gerências](#módulo-6--esteira-de-medidas-e-gerências)
13. [Módulo 7 — Administração e Desenvolvedor](#módulo-7--administração-e-desenvolvedor)
14. [Módulo 8 — Acompanhamento de Tratativas](#módulo-8--acompanhamento-de-tratativas)
15. [Identidade visual, login e navegação](#identidade-visual-login-e-navegação)
16. [Consolidação dos sistemas das 7 distribuidoras](#consolidação-dos-sistemas-das-7-distribuidoras)
17. [Integração Snowflake (ETL)](#integração-snowflake-etl)
18. [API REST](#api-rest)
19. [Regras de negócio consolidadas](#regras-de-negócio-consolidadas)
20. [Setup no VSCode — passo a passo](#setup-no-vscode--passo-a-passo)
21. [Roadmap por sprints](#roadmap-por-sprints)
22. [Decisões pendentes / divergências encontradas](#decisões-pendentes--divergências-encontradas)
23. [Estado atual da implementação](#23-estado-atual-da-implementação)
24. [Padrões de envio, validação e concorrência](#24-padrões-de-envio-validação-e-concorrência)

---

## 1. Objetivo e escopo

### 1.1 Problema atual

O processo de **Incorporação de Redes (nota tipo IR)** existe nas **7 distribuidoras do grupo Equatorial**, mas hoje está espalhado em:

| Onde está | O que é | Dor |
|---|---|---|
| Power BI `Gestão de Incorporação RD - Corporativo` | Visão gerencial da carteira de notas IR | Só leitura. Não permite tratar a nota, só olhar. |
| Planilha `Orçamento ... PEP 7.1.2.xlsx` | Modelo de orçamento com ~117 mil linhas de catálogo de serviços | Arquivo circula por e-mail, cada um tem uma versão, preço desatualizado. |
| Planilha `POP.00813 Anexo II Checklist` | Checklist dos 16 itens documentais | Preenchida à mão, pendência digitada em texto livre. |
| Pastas de rede / e-mail | Termos, POPs, modelos de ofício | Ninguém sabe qual é a versão vigente. |

### 1.2 O que o sistema vai ser

Hoje cada distribuidora do grupo resolveu o problema do seu jeito: algumas têm painéis próprios, planilhas compartilhadas, bases paralelas. A **Central de Soluções de Incorporação de Redes** é o destino único desses sistemas — cada solução local vira um módulo aqui dentro, com a mesma base, as mesmas regras e os mesmos perfis de acesso (ver [§16](#consolidação-dos-sistemas-das-7-distribuidoras)).

**Central de Soluções de Incorporação de Redes** = plataforma Django que centraliza, para as 7 distribuidoras, as **soluções do processo de incorporação de rede**:

1. **Painel** — reproduz e amplia o BI atual (KPIs por etapa, gerência, regional, prazo, distribuidora).
2. **Carteira de notas** — lista operável das notas IR, com tratamento por perfil.
3. **Documentos Modelo** — repositório versionado dos arquivos modelo, **com download direto pelo usuário**.
4. **Orçamento RDU** — motor de cálculo que substitui a planilha (catálogo de preços por distribuidora/regional, ERD, participação financeira, restituição) e **exporta o .xlsx no layout oficial**.
5. **Checklist documental** — os 16 itens do POP.00813 como formulário, com upload de anexos e geração automática do texto de pendência.
6. **Esteira de medidas** — histórico de passagem da nota por cada gerência, com SLA.
7. **Administração** — DE-PARA de medidas/gerências, parâmetros, usuários, auditoria.
8. **Acompanhamento de Tratativas** — base diária importada, comparação entre duas datas, movimentação por regional/gerência/carteira, caminho da nota entre gerências e validação nota a nota (porte do painel "Tratativa das notas de incorporação").

### 1.3 Fora de escopo (versão 1)

- Escrita de volta no SAP/CCS (o sistema **lê** do Snowflake, não grava no SAP).
- Assinatura digital de termos (prever integração futura).
- App mobile nativo (o front será responsivo).

---

## 2. Diagnóstico do BI atual (engenharia reversa)

### 2.1 Fontes de dados reais

O `.pbix` se conecta a **Snowflake** (não a arquivos):

```
Servidor : CFGKDTB-ISB76799.snowflakecomputing.com
Warehouse: WH_EQTLINFO
```

| Tabela no modelo | Origem | Tipo |
|---|---|---|
| `BaseIncorporacao` | `EQTLINFO_RAW` → `SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO` | **Fato principal** — 1 linha por nota IR |
| `HistoricoGerencias` | SQL nativo sobre `EQTLINFO_PRD.EQTL_PA.MEDIDAS_NOTAS_SERVICOS` + `NOTAS_SERVICOS` + `TAB_GRPCODES_MEDIDAS` + `SB_ATENDIMENTO.EQTL_PA.TAB_CENTRO_TRABALHO_GERENCIA` | **Fato de esteira** — 1 linha por medida da nota |
| `Tabela_medidas_gerencia` | Tabela estática embutida (53 linhas) | DE-PARA medida × centro de trabalho → gerência / etapa |
| `Tabela_status_fisc` | Tabela estática embutida (7 linhas) | DE-PARA status SISCO → status macro / detalhado / ordem |
| `Tabela_regional` | Tabela estática embutida (49 linhas, só PA) | DE-PARA município → regional |
| `d_Calendario` / `Calendario Gerencial` | Calendários gerados | Dimensão de tempo |
| `Data_Atualizacao` | `DateTime.LocalNow()` | Timestamp do refresh |
| `_Medidas` | Tabela vazia | Hospeda as 48 medidas DAX |

> ⚠️ **Achado importante:** `BaseIncorporacao` já é corporativa (`TB_NOTAS_IR_CORPORATIVO`, e tem coluna `ESTADO` com visual *"Incorporações por Distribuidora"*), mas `HistoricoGerencias` está **hardcoded em `EQTL_PA`** (Pará) e `Tabela_regional` só tem os 49 municípios do Pará. **A esteira de medidas hoje só funciona para o Pará.** O sistema Django precisa parametrizar o schema por distribuidora.

Tratamentos aplicados no Power Query que viram **regras de ingestão** no Django:

```
GERENCIA: Trim + Clean, e substituições:
  "RELACIONAMENTO COM O CLIENTE" → "RELACIONAMENTO"
  "RELACIONAMENTO ¿ APOIO"       → "RELACIONAMENTO"
  "EXPANSÃO DE REDE"             → "EXPANSÃO"
  "OPERAÇÃO SISTEMA"             → "OPERAÇÃO"
  null                           → "Não Mapeado"
STATUS_FISCALIZACAO: null → "Fora SISCO"
STATUS_SGO:          null → "Sem Nota Proj"
STATUS_SAP:          null → "Projeto Não Elaborado"
CLIENTE_LIGADO:      null → "NOTA NÃO MAPEADA"
Deduplicação: Table.Distinct por NOTA
HistoricoGerencias: STATUS_CCS null → "ATIV"; descarta STATUS_CCS = "RECE"
Filtro geral: TIPO_NOTA = 'IR'
```

### 2.2 Relacionamentos do modelo

Só existem **dois** relacionamentos reais (ambos M:1, filtro único, ativos):

```
BaseIncorporacao[STATUS_FISCALIZACAO] ──M:1──► Tabela_status_fisc[STATUS_SISCO]
BaseIncorporacao[CHAVE_MAPEAMENTO]    ──M:1──► Tabela_medidas_gerencia[CHAVE_MAPEAMENTO]
```

Onde `CHAVE_MAPEAMENTO = TRIM(MEDIDA_ATUAL) & "|" & TRIM(CENTRO_TRABALHO)`.

> ⚠️ `HistoricoGerencias`, `Tabela_regional` e `d_Calendario` **não estão relacionadas** ao fato. São usadas isoladamente. No Django isso vira FK de verdade.

### 2.3 Colunas da tabela fato (`BaseIncorporacao`)

109 colunas. Agrupadas por domínio:

**Identificação**
`NOTA`, `TIPO_NOTA`, `NOTA_PROJ`, `PEP`, `PEP_I`, `INSTALACAO`, `CONTA_CONTRATO`, `NOTA_OC_VINCULADA`, `NOTAS_VINCULADAS`

**Localização**
`ESTADO`, `REGIONAL`, `AREA_ESTRUT_REGIONAL`, `MUNICIPIO`, `BAIRRO`, `PERIMETRO`, `ENDERECO`, `LATITUDE`, `LONGITUDE`, `Localização Mapa`

**Cliente / obra**
`NOME`, `CARTEIRA_CLIENTE`, `SLI_SOLICITANTE`, `SLI_DESC_OBRA`, `TEXTO_BREVE`, `NOME_SOLICITANTE_DEMANDA_INTERNA`, `DESCRICAO_SOLICITACAO_DEMANDA_INTERNA`

**Esteira / medida**
`MEDIDA_ATUAL`, `CODIGO_MEDIDA_ATUAL`, `TEXTO_MEDIDA_ATUAL`, `MEDIDA_ANTERIOR`, `CODIGO_MEDIDA_ANTERIOR`, `TEXTO_MEDIDA_ANTERIOR`, `TEXTO_OBSERVACAO_MEDIDA_ANTERIOR`, `GRUPO_CODES`, `CODIFICACAO`, `TEXTO_BREVE_GRUPO_CODIGO`, `CENTRO_TRABALHO`, `GERENCIA`, `ETAPA`, `CHAVE_MAPEAMENTO`

**Status**
`STATUS_CCS`, `STATUS_CCS_NOTA_OC`, `STATUS_FISCALIZACAO`, `STATUS_FISCALIZACAO_FORMATADA`, `STATUS_FISCALIZACAO_FORMAT`, `STATUS_SGO`, `STATUS_SAP`, `STATUS_PROJ`, `STATUS_DEMANDA_INTERNA`, `status_demanda`, `status_demanda_ordem`, `status_rtp`, `status_documentacao`, `CLASSIFICACAO_DEMANDA`, `Flag_compulsoria`

**Datas** (21 campos)
`DATA_CRIACAO`, `DATA_ALTERACAO`, `DATA_ABERTURA_DEMANDA_INTERNA`, `INICIO_DESEJADO`, `FIM_DESEJADO`, `INICIO_AVARIA`, `INICIO_AVARIA_NOTA_VINCULADA`, `DATA_ENCERRAMENTO_NOTA`, `DATA_CRIACAO_MEDIDA`, `DATA_CONCLUSAO_MEDIDA`, `INICIO_PROGRAMADO_MEDIDA`, `FIM_PROGRAMADO_MEDIDA`, `DATA_AGENDAMENTO`, `DATA_ATRIBUICAO_FISCAL`, `DATA_DA_FISCALIZACAO`, `DATA_PREVISAO_ENTREGA`, `DATA_SOLICITACAO`, `DATA_DEVOLUCAO`, `DATA_CONCLUSAO`, `DATA_ENTREGA_RELATORIO_CAMPO`, `DATA_LIGACAO`, `DATA_PRIMEIRA_ENERGIZACAO`, `DATA_ULTIMA_ENERGIZACAO`, `DATA_ENERGIZACAO_NOTA_IR`, `DATA_ULTIMA_NOTA_VINCULADA`

**Prazo / SLA (calculadas)**
`Data_Prazo`, `Dias_prazo`, `Status_Prazo`, `Prazo_nota_vinculada`, `Dias_prazo_nota_vinculada`, `Status_Prazo_nota_vinculada`, `status_prazo_nota_vinculada_ordem`, `Prazo_medida`, `Dias_prazo_medida`, `Status_Prazo_medida`, `status_prazo_medida_ordem`, `Prazo_nota_IR`, `Dias_prazo_NOTA_IR`, `Status_Prazo_NOTA_IR`, `PRAZO_ANEXOIV`, `DURACAO_DIAS`, `MULTA`

**Financeiro**
`VL_MATERIAL_TOTAL`, `VL_MO_TOTAL`, `VL_TOTAL_ORCAMENTO`

**Notas vinculadas / ligação de cliente**
`QTD_NOTAS_VINCULADAS`, `TIPOS_NOTAS_VINCULADAS`, `QTD_NOTAS_VINCULADAS_LIGADAS`, `QTD_NOTAS_VINCULADAS_NAO_LIGADAS`, `NOTAS_VINCULADAS_LIGADAS`, `TEM_VINCULADA_LIGADA`, `CLIENTE_LIGADO`, `CLIENTE_LIGADO_NOTA_IR`, `QTD_CLIENTES_LIGADOS`, `CONCLUIDO_POR`

### 2.4 Colunas calculadas DAX → regras de negócio

As 31 colunas calculadas são **a inteligência do BI**. Vão migrar para `properties` Python e campos materializados.

```dax
-- ETAPA (incompleta no BI: só 4 medidas)
SWITCH(MEDIDA_ATUAL,
  "VERDOCIN","DOCUMENTAÇÃO", "CATEBDGD","BDGD",
  "VISTOBRA","VISTORIA",     "VISLEMAT","VISTORIA")

-- SLA da nota (90 dias da criação)
Data_Prazo   = DATA_CRIACAO + 90
Dias_prazo   = DATEDIFF(TODAY(), Data_Prazo, DAY)
Status_Prazo = <0 "Fora prazo" | =0 "Vence Hoje" | <=5 "Prestes a Vencer" | "No Prazo"

-- SLA da nota vinculada (30 dias do início da avaria)
Prazo_nota_vinculada = COALESCE(INICIO_AVARIA_NOTA_VINCULADA, INICIO_AVARIA) + 30
(mesma escala de status + coluna de ordem 1..4)

-- SLA da medida (usa o fim programado SAP)
Prazo_medida       = FIM_PROGRAMADO_MEDIDA
Dias_prazo_medida  = Prazo_medida - COALESCE(DATA_CONCLUSAO_MEDIDA, TODAY())
Status_Prazo_medida:
  concluída & dias<0 → "Medida concluída fora do prazo"  (ordem 5)
  concluída          → "Medida Concluída no prazo"       (ordem 6)
  dias<0             → "Medida Fora prazo"               (ordem 1)
  dias=0             → "Medida Vence Hoje"               (ordem 2)
  dias<=5            → "Medida Prestes a Vencer"         (ordem 3)
  senão              → "Medida No Prazo"                 (ordem 4)

-- SLA da nota IR
Prazo_nota_IR = FIM_DESEJADO  (mesma escala de 4 status)

-- Classificações
status_demanda         = STATUS_CCS: FINL→FINALIZADA(2) | CANC→CANCELADA(3) | else ATIVA(1)
status_rtp             = DATA_CRIACAO > 2023-12-01 → "RTP26" | "RTP_Anterior"
CLASSIFICACAO_DEMANDA  = DATA_CRIACAO > 2026-01-01 → "GIRO" | "PASSIVO"
Flag_compulsoria       = DATA_CRIACAO <= EDATE(TODAY(),-60) → "Mais de 5 anos" | "Até 5 anos"
status_documentacao    = TEXTO_MEDIDA_ANTERIOR contém "Documentação Aprovada"/"Documentação Reprovada"
CHAVE_MAPEAMENTO       = TRIM(MEDIDA_ATUAL) & "|" & TRIM(CENTRO_TRABALHO)
Localização Mapa       = MUNICIPIO & ", Pará, Brasil"   ⚠️ hardcoded "Pará"
STATUS_FISCALIZACAO_FORMAT = RELATED(Tabela_status_fisc[STATUS_MACRO])
```

### 2.5 Medidas DAX → KPIs do sistema

48 medidas. As que importam:

| Medida | Expressão | KPI no sistema |
|---|---|---|
| `Total_notas` | `DISTINCTCOUNT(NOTA)` | Total de Notas |
| `notas_com_projeto` | `DISTINCTCOUNT(NOTA_PROJ)` | Notas com projeto |
| `notas_sem_projeto` | `Total - com_projeto` | Notas sem projeto |
| `notas_em_campo` | filtro `STATUS_FISCALIZACAO ∈ {Contestação Parceira, Devolvido de Campo, Roteirizado}` | Em campo |
| `Total_orcamento` | `SUM(VL_TOTAL_ORCAMENTO)` | Orçamento estimado |
| `Total_multas` | `SUM(MULTA)` | Multas |
| `Total_clientes_ligados` | `SUM(QTD_CLIENTES_LIGADOS)` | Clientes ligados |
| `pend_tatico` | `ETAPA = "TÁTICO"` | Pendência Tático |
| `pend_relac` | `ETAPA = "RELACIONAMENTO"` | Pendência Relacionamento |
| `pend_ATV` | `ETAPA = "ATIVOS"` | Pendência Ativos |
| `pend_cadastro` | `ETAPA = "CADASTRO"` | Pendência Cadastro |
| `pend_financ` | `ETAPA = "FINANCEIRO"` | Pendência Financeiro |
| `pend_orcamento` | `ETAPA = "ORÇAMENTO"` | Pendência Orçamento |
| `pend_doc` | `ETAPA = "DOCUMENTAÇÃO"` | Pendência Documentação |
| `pend_PEP` | `ETAPA = "PEP"` | Pendência Criação de PEP |
| `pend_vistoria` | `ETAPA = "VISTORIA"` | Pendência Vistoria |
| `total_etapa_BDGD` | `ETAPA = "BDGD"` | Etapa BDGD |
| `total_etapa_capitalizacao` | `ETAPA = "CAPITALIZAÇÃO"` | Capitalização |
| `% Gerencia`, `% MEDIDAS`, `% status_fisc`, `% Ano`, `% Notas por Etapa` | `DIVIDE` com `ALL`/`REMOVEFILTERS` | % de participação nos gráficos |
| `Rotulo *` | `"n (x%)"` | Rótulo dos gráficos |
| `Max Eixo *` | `MAXX(ALLSELECTED(...)) * fator` | Escala dos eixos (não migra: o front cuida) |

### 2.6 Páginas do relatório atual

**Página "Home"** (2420×1080, 35 visuais)

- **Filtros (slicers):** `REGIONAL`, `GERENCIA` (da tabela DE-PARA), `status_demanda`, `STATUS_FISCALIZACAO_FORMAT`, `Flag_compulsoria`, `status_rtp`, `ESTADO`
- **Busca livre:** caixas de texto para `NOTA` e `NOTA_PROJ`
- **12 cards:** Total de Notas, Documentação, Vistoria, Orçamento, Criação de PEP, Etapa Cadastro, Pend. Ativos, Pend. Relac., Pend. Financeiro, Pend. Tático, Orçamento Estimado
- **Gráficos:** Incorporações por Gerência (coluna) · Incorporações por Medidas (barra) · Incorporações por Regional (waterfall) · Tipo Demanda (treemap) · Prazo da Nota IR (coluna) · Entrantes × Mês × Ano (coluna agrupada) · Incorporações por Distribuidora (coluna)
- **Tabela detalhe (49 colunas):** `NOTA`, `NOTA_PROJ`, `PEP_I`, `TIPO_NOTA`, `STATUS_CCS`, `STATUS_CCS_NOTA_OC`, `STATUS_FISCALIZACAO`, `STATUS_FISCALIZACAO_FORMAT`, `STATUS_SGO`, `STATUS_DEMANDA_INTERNA`, `MEDIDA_ATUAL`, `MEDIDA_ANTERIOR`, `TEXTO_MEDIDA_ANTERIOR`, `TEXTO_OBSERVACAO_MEDIDA_ANTERIOR`, `TEXTO_BREVE_GRUPO_CODIGO`, `GERENCIA`, `CENTRO_TRABALHO`, `ETAPA`, `REGIONAL`, `AREA_ESTRUT_REGIONAL`, `MUNICIPIO`, `BAIRRO`, `ENDERECO`, `NOME`, `CARTEIRA_CLIENTE`, `SLI_DESC_OBRA`, `CLASSIFICACAO_DEMANDA`, `status_rtp`, `status_documentacao`, `CLIENTE_LIGADO`, `NOTAS_VINCULADAS_LIGADAS`, `QTD_CLIENTES_LIGADOS`, `Status_Prazo_medida`, `Status_Prazo_nota_vinculada`, datas e somas de `VL_TOTAL_ORCAMENTO` / `QTD_NOTAS_VINCULADAS*`

**Página "Desempenho"** (2420×920)

- Mesmos 11 cards + filtro `status_demanda`
- 3 matrizes (pivot): `GERENCIA × Total_notas`, `ETAPA × Total_notas`, `TEXTO_BREVE_GRUPO_CODIGO × Total_notas`

**Página 1** — rascunho (tabela `MEDIDA_ATUAL × TEXTO_BREVE_GRUPO_CODIGO`). Descartar.

### 2.7 DE-PARA medida → gerência → etapa (`Tabela_medidas_gerencia`, 53 linhas)

Esta é a **tabela mais importante do sistema** — define quem é responsável pela nota a cada momento.

| Medida | Descrição | Gerência | Etapa | Centro trabalho | Gerência SAP |
|---|---|---|---|---|---|
| VISLEMAT | Vistoria para levantamento de materiais | TÁTICO | VISTORIA | EXPRBOSU, EXPRBOND, EXPRBONO, EXPRBOOE | EXPANSÃO |
| VISTOBRA | Vistoria de Qualidade da Obra | TÁTICO | VISTORIA | EXPRBOND, EXPRBONO, EXPRBOCT, EXPRBOOE, EXPRBOSU | EXPANSÃO |
| ORCAFMTS | Orçamento final de materiais e serviços | TÁTICO | ORÇAMENTO | EXPCPJCO, EXPRBOCT, EXPRBOND, *(vazio)* | EXPANSÃO |
| ORCAFIMS | Orçamento final de materiais e serviços | TÁTICO | ORÇAMENTO | EXPCPJCO, EXPRBOSU | EXPANSÃO |
| VERDOCIN | Verificar documentação para incorporação | TÁTICO | DOCUMENTAÇÃO | EXPCPJCO, *(vazio)* | EXPANSÃO |
| CRIPEPIR | Criação de PEP de incorporação de rede | TÁTICO | PEP | EXPCPJCO, EXPRBOND, *(vazio)* | EXPANSÃO |
| PENNAOIF | Pendências não relatadas anteriormente | TÁTICO | TÁTICO | EXPCPJCO | EXPANSÃO |
| AGREPENC | Aguardando Regularização Pendência | TÁTICO | TÁTICO | EXPRBOND | EXPANSÃO |
| AGREPENC | Aguardando Regularização Pendência | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| COMPORCA | Comparação de orçamento | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| VERIUNIV | Verificar universalização | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| COPENDIN | Comunicar Pendências de Incorporação | RELACIONAMENTO | RELACIONAMENTO | RELAARCO, *(vazio)* | RELACIONAMENTO |
| AGANOUNI | Aguardando o ano da universalização | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| ENCOPENT | Entrega de comunicação de pendências | RELACIONAMENTO | RELACIONAMENTO | RELAACCO | RELACIONAMENTO |
| CONVPECL | Comunicar pendências de notas | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| CORECOPN | Confirmação entrega de pendência da nota | RELACIONAMENTO | RELACIONAMENTO | RELAACCO | RELACIONAMENTO |
| AGURECTM | Devolução do termo | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| AGURECTI | Aguardar devolução do Termo de Incorporação/Doação | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| ENTEINPN | Entrega do termo de incorporação | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| ENTEINCD | Envio termo incorporação ao Cliente/Doação | RELACIONAMENTO | RELACIONAMENTO | RELAARCO, RELAACCO | RELACIONAMENTO |
| AGREPENO | Aguardando Regularização Pendência | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| AGREGNVP | Aguardar regularização pendências de Nota | RELACIONAMENTO | RELACIONAMENTO | RELAARCO | RELACIONAMENTO |
| CONRECTM | Confirmação do recebimento do termo | RELACIONAMENTO | RELACIONAMENTO | ESTCACOC | RELACIONAMENTO |
| ASSDOANF | Assinatura Termo Doação (notas incompletas) | RELACIONAMENTO | RELACIONAMENTO | RELAACCO, RELAARCO | RELACIONAMENTO |
| ARQUPROC | Arquivamento do processo | RELACIONAMENTO | RELACIONAMENTO | RELAARCO, RELAACCO | RELACIONAMENTO |
| ARQUPROC | Arquivamento do processo | ATIVOS | ATIVOS | CONTGTAC | CONTROLADORIA |
| ARQUPROC | Arquivamento do processo | FINANCEIRO | FINANCEIRO | ARFNCIFC | ARRECADAÇÃO E FINANÇAS |
| CATEBDGD | Cadastro Técnico (BDGD) | CADASTRO | CADASTRO | OPSECGCO | OPERAÇÃO |
| CONTUNIT / CONTUNIO | Contabilização e Unitização da obra | ATIVOS | ATIVOS | CONTGTAC | CONTROLADORIA |
| APRONOFI | Aprovação de notas fiscais | ATIVOS | ATIVOS | CONTGTAC | CONTROLADORIA |
| REVARESS | Registro do valor do ressarcimento | ATIVOS | ATIVOS | CONTGTAC | CONTROLADORIA |
| ANREVLPN | Análise restituição de valores – cliente | ATIVOS | ATIVOS | CONTGTAC | CONTROLADORIA |
| ELAORDPG | Elaboração de ordem de pagamento | ATIVOS | ATIVOS | CONTGTAC | CONTROLADORIA |
| CORESSPN | Ciência do ressarcimento do cliente | FINANCEIRO | FINANCEIRO | ARFNCIFC | ARRECADAÇÃO E FINANÇAS |

**Observações críticas:**
- A chave é **composta** (`MEDIDA|CENTRO_TRABALHO`) — a *mesma* medida pode pertencer a gerências diferentes (ex.: `ARQUPROC` é de Relacionamento, Ativos **ou** Financeiro dependendo do centro).
- Existem 5 linhas com centro de trabalho **vazio** → chave `MEDIDA|` → "Não Mapeado". São fallback.
- A classificação do SQL do `HistoricoGerencias` **divergem** desta tabela — ver [§19](#19-decisões-pendentes--divergências-encontradas).

### 2.8 DE-PARA status de fiscalização (`Tabela_status_fisc`)

| Ordem | Status SISCO | Status macro | Status detalhado |
|---|---|---|---|
| 1 | Fora SISCO | PENDENTE DE CRIAÇÃO DE DEMANDA | Obra não cadastrada no SISCO |
| 2 | Em Roteirização | AGUARDANDO ATRIBUIÇÃO A CAMPO | Em roteirização |
| 3 | Roteirizado | EM FISCALIZAÇÃO | Equipe em campo |
| 4 | Contestação Parceira | ENTREGUE COM RESSALVAS | Contestada pela parceira |
| 5 | Capitalização | ENTREGUE | Fiscalizada – em capitalização |
| 6 | Histórico | ENTREGUE/LEGADO | Fiscalizada – legado PROGEO |
| 7 | Retirado da Fiscalização por processo Manual a pedido do cliente | CANCELADA / RETIRADA | Retirada a pedido do cliente |

### 2.9 Esteira de gerências (`HistoricoGerencias`) — lógica SQL

O SQL reconstrói a **passagem da nota por gerência** com funções de janela:

```sql
-- 1) classifica cada GRUPO_MEDIDA em gerência responsável
-- 2) LAG/LEAD por NOTA ordenado por DATA_CRIACAO_MEDIDA, MEDIDA:
--      GERENCIA_ANTERIOR, DATA_SAIDA_MEDIDA, PROXIMA_MEDIDA, PROXIMA_GERENCIA
-- 3) CICLO_GERENCIA = soma cumulativa de trocas de gerência
--      (permite a nota voltar para a mesma gerência e contar como ciclo novo)
-- 4) DATA_ENTRADA_GERENCIA = MIN(DATA_CRIACAO_MEDIDA) por (NOTA, CICLO_GERENCIA)
-- 5) flags derivadas:
--      MEDIDA_ATUAL        = DATA_SAIDA_MEDIDA IS NULL
--      ENTROU_NA_GERENCIA  = gerência anterior nula ou diferente
--      SAIU_DA_GERENCIA    = saiu e a próxima gerência é outra
--      DATA_TRATAMENTO_GERENCIA = data de saída quando saiu de fato
--      DIAS_NA_MEDIDA = DATEDIFF(entrada, COALESCE(saída, now))
-- Filtros: TIPO_NOTA = 'IR'; STATUS_CCS <> 'RECE'
```

Classificação de `GRUPO_MEDIDA` → gerência **no SQL**:

```
TÁTICO         : VISLEMAT, VISTOBRA, ORCAFMTS, ORCAFIMS, VERDOCIN, CRIPEPIR, PENNAOIF
RELACIONAMENTO : ARQUPROC, AGREPENO, VERIUNIV, ENCOPENT, CONRECTM, AGURECTM, ENTEINCD,
                 ENTEINPN, COPENDIN, COMPORCA, AGANOUNI, AGREPENC, CONVPECL, AGREGNVP,
                 CORECOPN, AGURECTI
CADASTRO       : CATEBDGD
ATIVOS         : REVARESS, ANREVLPN, CONTUNIT, APRONOFI, CONTUNIO, ANEAPRPG,
                 CORESSPN, ASSDOANF, AGENPAGA, ATUAMONE, ELAORDPG, CONFPAGA
senão          : NÃO MAPEADA
```

> 💡 Note que os perfis que você pediu (**Tático, Relacionamento, Ativos, Cadastro**) são exatamente as 4 gerências desta classificação. O perfil **Desenvolvedor** é o admin. **Financeiro** aparece no DE-PARA mas não tem perfil → ver §19.

---
## 3. Diagnóstico das planilhas modelo

### 3.1 `Orçamento NOME_DO_EMPREENDIMENTO_PEP 7.1.2.xlsx`

**4 abas:**

| Aba | Visível | Linhas | Função |
|---|---|---|---|
| `Orcamento RDU` | sim | 113 | Formulário do orçamento |
| `Serviços` | sim | **117.478** | Catálogo de preços de mão de obra por distribuidora + regional |
| `Distribuidoras` | oculta | 777 | DE-PARA município → regional + sigla, e listas por distribuidora |
| `Colar Serviços PROJ` | oculta | 108 | Área de colagem do extrato do projeto (SGO/PROJ) + tabela dinâmica |

**Catálogo `Serviços`** — colunas: `DISTRIBUIDORA`, `REGIONAL`, `JUNTAR` (=`DISTRIBUIDORA&REGIONAL&Nº SERVIÇO`), `TIPO`, `Nº SERVIÇO`, `TEXTO BREVE`, `QUANT`, `UN`, `PREÇO BRUTO`

Volumetria por distribuidora:

| Distribuidora | Serviços | Regionais no catálogo | Municípios |
|---|---|---|---|
| PARÁ | 51.142 | CENTRO, NORDESTE, NORTE, OESTE, SUL | 145 |
| PIAUÍ | 26.199 | FLORIANO, METROPOLITANA, PARNAIBA, PICOS | 224 |
| ALAGOAS | 21.160 | LESTE, OESTE | 102 |
| RIO.GRANDE.DO.SUL | 9.322 | NORTE, SUL | 72 |
| AMAPA | 8.487 | METROPOLITANA | 16 |
| MARANHÃO | 1.167 | CENTRO, LESTE, NOROESTE, NORTE, SUL | 217 |
| **GOIÁS** | **ausente** | — | — |

> ⚠️ A planilha cobre **6 das 7 distribuidoras**. **Equatorial Goiás não está no catálogo.** O sistema deve ser modelado para 7 e permitir carga posterior de Goiás.

Unidades usadas: `UN` (84.353), `M`, `M2`, `CDA`, `KM`, `VAO`, `UA`, `CJ`, `M3`, `H`, `DIA`.

**Estrutura e fórmulas da aba `Orcamento RDU`:**

| Célula | Conteúdo | Tipo |
|---|---|---|
| `C1` | Distribuidora | **entrada** (lista) |
| `C5` / `E5` | Obra / PEP | entrada |
| `C7` / `E7` | Cliente / Dt Energização | entrada |
| `C9` | Município | **entrada** (lista dinâmica `=INDIRECT($C$1)`) |
| `F9` | Regional | `=IFERROR(VLOOKUP(C1&C9, Distribuidoras!C:D, 2, 0),"")` |
| `B14:I68` | **1 – Materiais** | entrada manual; `G = ROUND(F*E,2)` |
| `G70` | Total Materiais | `=SUBTOTAL(9,G14:G68)` |
| `I70` | Total NF Materiais | `=SUBTOTAL(9,I14:I69)` |
| `B74:B83` | **2 – Mão de obra**: código do serviço | entrada |
| `C74` | Descrição | `=INDEX(Serviços!F:F, MATCH(B74, Serviços!E:E, 0))` |
| `D74` | Unidade | `=INDEX(Serviços!H:H, MATCH(B74, Serviços!E:E, 0))` |
| `F74` | Preço unitário | `=IF($C$1="ALAGOAS", VLOOKUP($C$1&$B74, Serviços!$C:$I, 7, 0), VLOOKUP($C$1&$F$9&$B74, Serviços!$C:$I, 7, 0))` |
| `G84` | Total Mão de obra | `=SUM(G74:G83)` |
| `B88` | **3 – Transporte** | entrada; `G88 = ROUND(F88*E88,2)` |
| `G90` | Total Transporte | `=SUM(G88:G88)` |
| `G92` | **4 – Total Obra** | `=G70+G84+G90` |
| `G94` | **5 – ERC** | entrada (default 0) |
| `G96` | **6 – Total Obra Proporcionalizado** | `=G92-G94` |
| `M90` | Demanda (kW) | **entrada** |
| `M92` | Constante K | **entrada** |
| `M94` | ERD | `=$M$90*$M$92` |
| `G98` | **7 – ERD** | `=M94` |
| `G100` | **8 – Participação Financeira Cliente** | `=IF(G96-G98<=0, 0, G96-G98)` |
| `M96` | Custo comprovado pelo cliente | `=$I$70+$I$84` |
| `M98` | Orçamento da obra distribuidora | `=$G$92` |
| `M100` | ERD+ERC | `=IF(M94>=M98, M94, M94+G94)` |
| `G102` | **9 – A restituir** | `=IF(M90="",0, IF($M90<50, MIN(M96,M98), MIN(M96,M98,M100)))` |

**As 9 regras de cálculo, formalizadas:**

```
(1) total_materiais      = Σ round(qtd_i × preco_i, 2)
(2) total_mao_obra       = Σ round(qtd_j × preco_catalogo_j, 2)
    preco_catalogo_j     = Serviços.PRECO_BRUTO onde
                             chave = distribuidora + regional + nº_serviço
                             (exceção ALAGOAS: distribuidora + nº_serviço)
(3) total_transporte     = Σ round(qtd_k × preco_k, 2)
(4) total_obra           = (1) + (2) + (3)
(5) erc                  = informado
(6) total_proporcional   = (4) − (5)
(7) erd                  = demanda_kw × constante_k
(8) participacao_cliente = max(0, (6) − (7))
(9) a_restituir          = 0                                      se demanda_kw vazia
                         = min(custo_comprovado, orcamento_distr)  se demanda_kw < 50
                         = min(custo_comprovado, orcamento_distr, erd_mais_erc)  caso contrário
    onde custo_comprovado = total_nf_materiais + total_nf_servicos
          orcamento_distr = total_obra
          erd_mais_erc    = erd            se erd ≥ orcamento_distr
                          = erd + erc      caso contrário
```

### 3.2 `POP.00813 Anexo II — Checklist de documentos`

Revisão: **Rev. 00 — 16/01/2024**. 3 abas (`NOVO CHECK-LIST`, `Planilha2`, `Planilha1`).

**Domínio de resposta** (`Planilha1`): `SIM` · `NÃO` · `NÃO SE APLICA`

**Os 16 itens** (coluna D = documento exigido; coluna B = texto da pendência gerada quando resposta = NÃO):

| # | Documento exigido | Texto de pendência (se NÃO) | Observação / obrigatoriedade |
|---|---|---|---|
| 1 | TERMO DE INCORPORAÇÃO DE REDES | Falta solicitação de incorporação | Apresentar após a fiscalização de campo |
| 2 | PROJETO APROVADO PELA EQTL – cópia e arquivo magnético (CAD georreferenciado) | Encaminhar DWG | Necessário — Res. 1000/21, responsabilidade da distribuidora |
| 3 | ART – projeto e execução | Projeto sem ART de execução | Necessário |
| 4 | NOTA FISCAL DE MATERIAL aplicado na execução | Falta Nota fiscal (material ou serviço) | Necessário |
| 5 | NOTA FISCAL DE SERVIÇOS (com detalhamento do serviço executado) | Falta Nota fiscal (material ou serviço) | Necessário — comprovante de pagamento válido, ideal NF |
| 6 | LAUDO DE ENSAIO DOS EQUIPAMENTOS (trafo, regulador, religador…) | Falta laudo de equipamentos | Necessário |
| 7 | Cópia RG+CPF (PF) ou CPF/CNPJ + contrato social (PJ) | Sem documentos (CPF, RG ou CNPJ) | PF ou PJ |
| 8 | DADOS BANCÁRIOS em nome do cliente (dono da RD/UC) | Falta dados bancários | Quando houver restituição |
| 9 | Procuração reconhecida em cartório (reclamante ≠ dono) | Falta cópia de procuração | Quando não for o próprio interessado; em PJ quando não for o representante legal |
| 10 | DOCUMENTO DE PROPRIEDADE DO TERRENO ou autorização de obra | Falta de documento da propriedade | Necessário — informar se é propriedade ou arrendamento |
| 11 | Contrato com a CEF quando projeto MCMV | Falta contrato assinado MINHA CASA MINHA VIDA | Verificar data de corte da necessidade de restituição |
| 12 | LICENÇAS AMBIENTAIS – LI e LO | Projeto sem licenças ambientais | **Obrigatórias e impeditivas para ligação** — Res. 1000/21 |
| 13 | FICHA CADASTRAL DE FORNECEDOR preenchida e assinada | Falta ficha de cadastro de fornecedor | Quando houver restituição |
| 14 | CONTRATO ASSINADO ENTRE EQTL E CLIENTE com opção por execução da obra | Falta contrato assinado para execução | Quando houver restituição |
| 15 | RELAÇÃO DE MATERIAIS APLICADOS na rede a incorporar | Falta relação de materiais aplicados | Necessário |
| 16 | VIABILIDADE TÉCNICA | Falta viabilidade técnica | Necessário |

**Consolidação de pendências** (`D20`): concatena as 16 colunas `C` separadas por `;` → é a string que hoje é copiada para o campo de observação da medida no SAP. **O sistema gera isso automaticamente.**

**Agrupamento em 12 grupos de documentos** (`R24/R25`) — é o resumo gerencial:

| Grupo de documento | Alimentado pelo item |
|---|---|
| Projeto/As Built em CAD | 2 |
| ART de Execução | 3 |
| Notas Fiscais de Materiais | 4 |
| Notas Fiscais de Serviços | 5 |
| Laudo de Ensaios de Equipamentos | 6 |
| Documentos Cliente (RG/CPF/CNPJ) | 7 |
| Documento Terreno | 10 |
| Viabilidade técnica | 16 |
| Contrato de Obras | 14 |
| TERMO DE DOAÇÃO | 1 |
| Dados Bancários / Comprovante | 8 |
| Licença Ambiental | 12 |

Status derivado: `SIM → ok` · `NÃO → Falta` · `NÃO SE APLICA → N/A`

**Catálogo de pendências codificadas** (`Planilha2`) — 16 códigos `IT1..IT16` com códigos hierárquicos `1.1 … 6.2`:

| Código | Cód. hier. | Pendência |
|---|---|---|
| IT1 | 1.1 | Encaminhar DWG |
| IT2 | 1.2 | Falta Nota fiscal (material ou serviço) |
| IT3 | 1.3 | Falta solicitação de incorporação |
| IT4 | 1.4 | Projeto sem ART de execução |
| IT5 | 1.5 | Falta laudo de equipamentos |
| IT6 | 1.6 | Sem documentos (CPF, RG ou CNPJ) |
| IT7 | 2.1 | Falta dados bancários |
| IT8 | 3.1 | Falta cópia de procuração |
| IT9 | 3.2 | Falta de documento da propriedade |
| IT10 | 3.3 | Projeto sem licenças ambientais |
| IT11 | 3.4 | Falta relação de materiais aplicados |
| IT12 | 4.1 | Falta viabilidade técnica |
| IT13 | 4.2 | Documentação anexada não corresponde ao processo |
| IT14 | 5.1 | Nota sem anexos |
| IT15 | 6.1 | Falta contrato assinado MINHA CASA MINHA VIDA |
| IT16 | 6.2 | Falta contrato assinado para execução |

> ⚠️ `IT13` ("Documentação anexada não corresponde ao processo") e `IT14` ("Nota sem anexos") estão no catálogo mas **não têm item correspondente no checklist**. Devem entrar como itens 17 e 18 ou como pendências avulsas.

**Prazo regulatório registrado na planilha:** `RESTITUIÇÃO TEMOS 90 DIAS PARA DEVOLUÇÃO DO DINHEIRO` → vira SLA no sistema.

---

## 4. Arquitetura da solução

### 4.1 Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| Backend | **Django 5.1** + Python 3.12 | Admin pronto, permissões nativas, ORM maduro |
| API | **Django REST Framework** | Front rico + integrações |
| Banco | **PostgreSQL 16** | JSONB, particionamento, window functions |
| Fila | **Celery + Redis** | ETL noturno do Snowflake, geração de XLSX/PDF |
| Front | **Django Templates + HTMX + Alpine.js + Tailwind** | Entrega rápida, sem SPA separada |
| Gráficos | **ECharts** (via CDN) | Cobre todos os visuais do BI (waterfall, treemap, colunas) |
| Arquivos | **django-storages** → S3/Azure Blob (fallback: `FileField` local) | Documentos modelo e anexos |
| Planilhas | **openpyxl** | Exportar orçamento no layout oficial |
| PDF | **WeasyPrint** | Termo de incorporação, checklist assinado |
| Fonte de dados | **snowflake-connector-python** | Replicação das tabelas do BI |
| Auth | Django auth + **django-axes** + SSO Azure AD (`django-auth-adfs`) | Padrão corporativo Equatorial |
| Auditoria | **django-simple-history** | Trilha de alteração em todos os modelos sensíveis |

### 4.2 Estrutura de pastas

```
csir/                      # Central de Soluções de Incorporação de Redes
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── celery.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── core/              # Distribuidora, Regional, Município, Usuário, Perfil, login, Sistema legado
│   ├── incorporacao/      # Nota IR, medidas, esteira, SLA
│   ├── documentos/        # ⭐ Documentos Modelo (download) + anexos da nota
│   ├── orcamento/         # Catálogo de serviços + motor de cálculo + export XLSX
│   ├── checklist/         # POP.00813: templates, itens, respostas, pendências
│   ├── tratativas/        # Base diária, comparação entre datas, movimentação, drill-down
│   ├── painel/            # KPIs, gráficos, filtros (substitui o BI)
│   ├── integracao/        # ETL Snowflake, jobs Celery, DE-PARA
│   └── api/               # Routers DRF
├── static/
│   ├── css/
│   │   ├── tokens.css     # design tokens (ver §15)
│   │   └── app.css
│   ├── js/
│   └── img/
│       ├── logo-equatorial-branco.svg
│       └── grafismo-flor.svg
├── templates/
│   ├── base.html
│   ├── partials/
│   ├── core/
│   │   ├── login.html             # tela de login (ver §15.V2)
│   │   └── selecionar_distribuidora.html
│   ├── painel/
│   ├── incorporacao/
│   ├── documentos/
│   ├── orcamento/
│   ├── checklist/
│   └── tratativas/
├── media/                 # dev apenas
│   ├── documentos_modelo/
│   └── anexos_nota/
└── docs/
    └── ESPECIFICACAO.md   # este arquivo
```

### 4.3 Multi-distribuidora (multi-tenant leve)

Não é multi-tenant por banco. É **tenant por coluna**, com filtro obrigatório:

1. Toda tabela de negócio tem FK `distribuidora`.
2. `UsuarioPerfil.distribuidoras` = M2M das distribuidoras que o usuário pode ver.
3. Um **middleware** grava a distribuidora ativa na request (`request.distribuidora`).
4. Todos os managers de negócio herdam de `DistribuidoraQuerySet.for_user(user)`.
5. Perfil **Desenvolvedor** enxerga todas.

**As 7 distribuidoras:**

| Sigla | Razão/Nome | UF | No catálogo de orçamento? |
|---|---|---|---|
| EQTL-PA | Equatorial Pará | PA | ✅ 51.142 serviços |
| EQTL-MA | Equatorial Maranhão | MA | ✅ 1.167 serviços |
| EQTL-PI | Equatorial Piauí | PI | ✅ 26.199 serviços |
| EQTL-AL | Equatorial Alagoas | AL | ✅ 21.160 serviços |
| EQTL-AP | Equatorial Amapá (CEA) | AP | ✅ 8.487 serviços |
| EQTL-RS | Equatorial Rio Grande do Sul (CEEE) | RS | ✅ 9.322 serviços |
| EQTL-GO | Equatorial Goiás | GO | ❌ **pendente de carga** |

---

## 5. Perfis de acesso e matriz de permissões

### 5.1 Os 5 perfis

| Perfil | Código | Gerência correspondente | Papel no processo |
|---|---|---|---|
| **Tático** | `TATICO` | TÁTICO (Expansão) | Vistoria, orçamento, verificação documental, criação de PEP |
| **Relacionamento** | `RELACIONAMENTO` | RELACIONAMENTO | Comunicação de pendência ao cliente, termo de incorporação/doação, universalização |
| **Ativos** | `ATIVOS` | ATIVOS (Controladoria) | Contabilização/unitização, aprovação de NF, ressarcimento, ordem de pagamento |
| **Cadastro** | `CADASTRO` | CADASTRO (Operação) | Cadastro técnico BDGD |
| **Desenvolvedor** | `DEV` | — | Administração total, DE-PARA, ETL, usuários, logs |

### 5.2 Matriz de permissões

Legenda: **V** = visualizar · **E** = editar · **C** = criar · **D** = excluir · **—** = sem acesso

| Funcionalidade | Tático | Relacion. | Ativos | Cadastro | Dev |
|---|---|---|---|---|---|
| **Painel / BI** | | | | | |
| Painel corporativo (todas as etapas) | V | V | V | V | V |
| Painel da própria gerência | V | V | V | V | V |
| Filtrar por outra distribuidora | só as suas | só as suas | só as suas | só as suas | todas |
| Exportar painel (XLSX/PDF) | V | V | V | V | V |
| **Carteira de notas** | | | | | |
| Listar / consultar nota | V | V | V | V | V |
| Editar nota em etapa da própria gerência | E | E | E | E | E |
| Editar nota de outra gerência | — | — | — | — | E |
| Reatribuir nota / forçar etapa | — | — | — | — | E |
| Registrar tratativa / comentário | C | C | C | C | C |
| **Documentos Modelo** | | | | | |
| Listar e **baixar** documentos modelo | V | V | V | V | V |
| Publicar nova versão | — | — | — | — | C/E |
| Criar/editar categoria | — | — | — | — | C/E/D |
| Arquivar documento | — | — | — | — | E |
| Ver log de downloads | — | — | — | — | V |
| **Orçamento RDU** | | | | | |
| Criar/editar orçamento | **C/E** | V | V | — | C/E |
| Aprovar orçamento | — | — | **E** | — | E |
| Exportar XLSX oficial | V | V | V | — | V |
| Importar catálogo de serviços | — | — | — | — | C |
| Editar preço do catálogo | — | — | — | — | E |
| **Checklist documental** | | | | | |
| Preencher checklist (análise) | **C/E** | V | V | — | C/E |
| Comunicar pendência ao cliente | V | **C/E** | — | — | C/E |
| Anexar documento do cliente | C | **C** | C | — | C |
| Aprovar/reprovar documentação | **E** | — | — | — | E |
| **Tratativas (base diária)** | | | | | |
| Ver painel de tratativas / comparar datas | V | V | V | V | V |
| Importar ou reimportar base do dia | **C** | — | — | — | **C** |
| Excluir uma base importada | — | — | — | — | **D** |
| Marcar nota como tratada | E | **E** | E | — | E |
| **Esteira de medidas** | | | | | |
| Ver histórico/SLA da nota | V | V | V | V | V |
| Ver ranking de SLA por gerência | V | V | V | V | V |
| **Administração** | | | | | |
| DE-PARA medida→gerência→etapa | V | V | V | V | **C/E/D** |
| Parâmetros de SLA | V | V | V | V | **E** |
| Usuários e perfis | — | — | — | — | **C/E/D** |
| Disparar/monitorar ETL | — | — | — | — | **E** |
| Django Admin | — | — | — | — | **V/E** |
| Trilha de auditoria | — | — | — | — | **V** |

### 5.3 Implementação das permissões

Três camadas combinadas:

1. **Groups + Permissions nativos** — um `Group` por perfil, criado por data migration.
2. **Mixins de view** — `PerfilRequiredMixin`, `DistribuidoraQuerysetMixin`.
3. **Regra de objeto** — `pode_editar_nota(user, nota)`: `True` se `nota.etapa.gerencia == user.perfil.gerencia` ou perfil `DEV`.

```python
# apps/core/permissions.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin

PERFIL_GERENCIA = {
    "TATICO": "TÁTICO",
    "RELACIONAMENTO": "RELACIONAMENTO",
    "ATIVOS": "ATIVOS",
    "CADASTRO": "CADASTRO",
}

def is_dev(user) -> bool:
    return user.is_superuser or getattr(user.perfil, "tipo", None) == "DEV"

def gerencia_do_usuario(user):
    return PERFIL_GERENCIA.get(getattr(user.perfil, "tipo", None))

def pode_editar_nota(user, nota) -> bool:
    if is_dev(user):
        return True
    ger = gerencia_do_usuario(user)
    return bool(ger) and nota.gerencia_responsavel == ger

def pode_ver_distribuidora(user, distribuidora) -> bool:
    if is_dev(user):
        return True
    return user.perfil.distribuidoras.filter(pk=distribuidora.pk).exists()


class PerfilRequiredMixin(LoginRequiredMixin):
    """Use: perfis_permitidos = ["TATICO", "DEV"]"""
    perfis_permitidos: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)
        return resp

    def get(self, request, *args, **kwargs):
        self._checar_perfil(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._checar_perfil(request)
        return super().post(request, *args, **kwargs)

    def _checar_perfil(self, request):
        if is_dev(request.user):
            return
        if self.perfis_permitidos and request.user.perfil.tipo not in self.perfis_permitidos:
            raise PermissionDenied("Seu perfil não tem acesso a esta funcionalidade.")


class DistribuidoraQuerysetMixin:
    """Restringe o queryset às distribuidoras do usuário."""
    def get_queryset(self):
        qs = super().get_queryset()
        if is_dev(self.request.user):
            return qs
        return qs.filter(distribuidora__in=self.request.user.perfil.distribuidoras.all())
```

---
## 6. Modelo de dados completo (código Django)

### 6.1 `apps/core/models.py`

```python
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class TimeStamped(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        abstract = True


class Distribuidora(TimeStamped):
    """As 7 distribuidoras do grupo Equatorial."""
    sigla = models.CharField(max_length=10, unique=True)          # EQTL-PA
    nome = models.CharField(max_length=120)                        # Equatorial Pará
    nome_catalogo = models.CharField(
        max_length=60, unique=True,
        help_text="Nome como aparece na planilha de orçamento: PARÁ, RIO.GRANDE.DO.SUL…",
    )
    uf = models.CharField(max_length=2)
    schema_snowflake = models.CharField(
        max_length=80, blank=True,
        help_text="Ex.: EQTLINFO_PRD.EQTL_PA — usado pelo ETL da esteira de medidas.",
    )
    ativa = models.BooleanField(default=True)
    catalogo_carregado = models.BooleanField(
        default=False, help_text="Se o catálogo de serviços já foi importado."
    )

    class Meta:
        verbose_name = "Distribuidora"
        verbose_name_plural = "Distribuidoras"
        ordering = ["sigla"]

    def __str__(self):
        return f"{self.sigla} — {self.nome}"


class Regional(TimeStamped):
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="regionais")
    nome = models.CharField(max_length=60)       # NORTE, SUL, CENTRO, NORDESTE, OESTE, METROPOLITANA…

    class Meta:
        unique_together = [("distribuidora", "nome")]
        ordering = ["distribuidora", "nome"]

    def __str__(self):
        return f"{self.distribuidora.sigla}/{self.nome}"


class Municipio(TimeStamped):
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="municipios")
    regional = models.ForeignKey(Regional, on_delete=models.PROTECT, related_name="municipios")
    nome = models.CharField(max_length=120)
    sigla = models.CharField(max_length=5, blank=True)   # ABA, AIG, ACA…

    class Meta:
        unique_together = [("distribuidora", "nome")]
        indexes = [models.Index(fields=["distribuidora", "nome"])]
        ordering = ["distribuidora", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.regional.nome})"


class CentroTrabalho(TimeStamped):
    """EXPRBOSU, RELAARCO, CONTGTAC, OPSECGCO, ARFNCIFC, ESTCACOC…"""
    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.CharField(max_length=160, blank=True)
    gerencia_sap = models.CharField(max_length=60, blank=True)   # EXPANSÃO, CONTROLADORIA…
    distribuidora = models.ForeignKey(
        Distribuidora, null=True, blank=True, on_delete=models.SET_NULL, related_name="centros_trabalho"
    )

    def __str__(self):
        return self.codigo


class Gerencia(models.TextChoices):
    TATICO = "TÁTICO", "Tático"
    RELACIONAMENTO = "RELACIONAMENTO", "Relacionamento"
    ATIVOS = "ATIVOS", "Ativos"
    CADASTRO = "CADASTRO", "Cadastro"
    FINANCEIRO = "FINANCEIRO", "Financeiro"
    NAO_MAPEADA = "NÃO MAPEADA", "Não mapeada"


class Etapa(models.TextChoices):
    VISTORIA = "VISTORIA", "Vistoria"
    ORCAMENTO = "ORÇAMENTO", "Orçamento"
    DOCUMENTACAO = "DOCUMENTAÇÃO", "Documentação"
    PEP = "PEP", "Criação de PEP"
    TATICO = "TÁTICO", "Tático"
    RELACIONAMENTO = "RELACIONAMENTO", "Relacionamento"
    CADASTRO = "CADASTRO", "Cadastro"
    BDGD = "BDGD", "BDGD"
    ATIVOS = "ATIVOS", "Ativos"
    FINANCEIRO = "FINANCEIRO", "Financeiro"
    CAPITALIZACAO = "CAPITALIZAÇÃO", "Capitalização"


class Usuario(AbstractUser):
    """Mantém username/email do AD."""
    matricula = models.CharField(max_length=20, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.get_full_name() or self.username


class Perfil(TimeStamped):
    class Tipo(models.TextChoices):
        TATICO = "TATICO", "Tático"
        RELACIONAMENTO = "RELACIONAMENTO", "Relacionamento"
        ATIVOS = "ATIVOS", "Ativos"
        CADASTRO = "CADASTRO", "Cadastro"
        DEV = "DEV", "Desenvolvedor (Admin)"

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    distribuidoras = models.ManyToManyField(Distribuidora, related_name="usuarios", blank=True)
    regionais = models.ManyToManyField(
        Regional, blank=True, related_name="usuarios",
        help_text="Opcional: restringe ainda mais a visão dentro da distribuidora.",
    )
    distribuidora_padrao = models.ForeignKey(
        Distribuidora, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Perfil de acesso"
        verbose_name_plural = "Perfis de acesso"

    @property
    def gerencia(self) -> str | None:
        from apps.core.permissions import PERFIL_GERENCIA
        return PERFIL_GERENCIA.get(self.tipo)

    def __str__(self):
        return f"{self.usuario} — {self.get_tipo_display()}"


class ParametroSistema(TimeStamped):
    """Parâmetros editáveis só pelo Desenvolvedor (nada hardcoded)."""
    chave = models.CharField(max_length=60, unique=True)
    valor = models.CharField(max_length=200)
    descricao = models.CharField(max_length=240, blank=True)
    tipo_dado = models.CharField(
        max_length=10,
        choices=[("int", "Inteiro"), ("dec", "Decimal"), ("str", "Texto"), ("date", "Data"), ("bool", "Booleano")],
        default="str",
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.chave} = {self.valor}"
```

**Parâmetros a semear** (data migration), todos extraídos do DAX/planilhas:

| Chave | Valor | Origem |
|---|---|---|
| `SLA_NOTA_DIAS` | `90` | `Data_Prazo = DATA_CRIACAO + 90` |
| `SLA_NOTA_VINCULADA_DIAS` | `30` | `Prazo_nota_vinculada = INICIO_AVARIA + 30` |
| `SLA_ALERTA_DIAS` | `5` | faixa "Prestes a Vencer" |
| `SLA_RESTITUICAO_DIAS` | `90` | nota do checklist |
| `ANOS_COMPULSORIA` | `5` | `Flag_compulsoria` (EDATE −60 meses) |
| `DATA_CORTE_GIRO` | `2026-01-01` | `CLASSIFICACAO_DEMANDA` |
| `DATA_CORTE_RTP26` | `2023-12-01` | `status_rtp` |
| `DEMANDA_LIMITE_RESTITUICAO_KW` | `50` | fórmula `G102` |
| `ORCAMENTO_LINHAS_MATERIAL` | `55` | faixa `G14:G68` |
| `ORCAMENTO_LINHAS_MAO_OBRA` | `10` | faixa `G74:G83` |

### 6.2 `apps/integracao/models.py` — DE-PARA (fonte única da verdade)

```python
from django.db import models
from apps.core.models import CentroTrabalho, Distribuidora, Etapa, Gerencia, TimeStamped
from simple_history.models import HistoricalRecords


class Medida(TimeStamped):
    """Grupo de código / medida SAP: VISLEMAT, ORCAFMTS, VERDOCIN…"""
    codigo = models.CharField(max_length=20, unique=True)        # VISLEMAT
    texto_breve = models.CharField(max_length=160)               # "Vistoria para levantamento de materiais"
    catalogo = models.CharField(max_length=5, default="2")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.texto_breve}"


class MapeamentoMedidaGerencia(TimeStamped):
    """
    Substitui 'Tabela_medidas_gerencia' do PBIX.
    Chave de negócio: MEDIDA | CENTRO_TRABALHO  (centro vazio = fallback).
    Editável SOMENTE pelo perfil Desenvolvedor.
    """
    medida = models.ForeignKey(Medida, on_delete=models.CASCADE, related_name="mapeamentos")
    centro_trabalho = models.ForeignKey(
        CentroTrabalho, null=True, blank=True, on_delete=models.CASCADE, related_name="mapeamentos",
        help_text="Vazio = regra de fallback para a medida.",
    )
    gerencia = models.CharField(max_length=20, choices=Gerencia.choices)
    etapa = models.CharField(max_length=20, choices=Etapa.choices)
    gerencia_sap = models.CharField(max_length=60, blank=True)
    distribuidora = models.ForeignKey(
        Distribuidora, null=True, blank=True, on_delete=models.CASCADE,
        help_text="Vazio = vale para todas as distribuidoras.",
    )
    history = HistoricalRecords()

    class Meta:
        unique_together = [("medida", "centro_trabalho", "distribuidora")]
        verbose_name = "DE-PARA medida → gerência"
        verbose_name_plural = "DE-PARA medida → gerência"

    @property
    def chave(self) -> str:
        return f"{self.medida.codigo}|{self.centro_trabalho.codigo if self.centro_trabalho else ''}"

    def __str__(self):
        return f"{self.chave} → {self.gerencia} / {self.etapa}"


class StatusFiscalizacao(TimeStamped):
    """Substitui 'Tabela_status_fisc'."""
    status_sisco = models.CharField(max_length=160, unique=True)
    status_macro = models.CharField(max_length=60)
    status_detalhado = models.CharField(max_length=120)
    ordem = models.PositiveSmallIntegerField()
    considera_em_campo = models.BooleanField(
        default=False,
        help_text="Marque para 'Contestação Parceira', 'Devolvido de Campo' e 'Roteirizado' (medida notas_em_campo).",
    )

    class Meta:
        ordering = ["ordem"]
        verbose_name = "Status de fiscalização"
        verbose_name_plural = "Status de fiscalização"

    def __str__(self):
        return f"{self.ordem}. {self.status_sisco} → {self.status_macro}"


class ExecucaoETL(models.Model):
    """Log de cada rodada de carga do Snowflake."""
    class Status(models.TextChoices):
        EXECUTANDO = "EXEC", "Executando"
        SUCESSO = "OK", "Sucesso"
        ERRO = "ERR", "Erro"

    job = models.CharField(max_length=60)                 # notas_ir, historico_medidas, catalogo_servicos
    distribuidora = models.ForeignKey(Distribuidora, null=True, blank=True, on_delete=models.SET_NULL)
    iniciado_em = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=5, choices=Status.choices, default=Status.EXECUTANDO)
    registros_lidos = models.IntegerField(default=0)
    registros_inseridos = models.IntegerField(default=0)
    registros_atualizados = models.IntegerField(default=0)
    mensagem = models.TextField(blank=True)

    class Meta:
        ordering = ["-iniciado_em"]
        verbose_name = "Execução de ETL"
        verbose_name_plural = "Execuções de ETL"
```

### 6.3 `apps/incorporacao/models.py` — a nota IR

```python
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import (CentroTrabalho, Distribuidora, Etapa, Gerencia,
                              Municipio, Regional, TimeStamped)
from apps.integracao.models import Medida, StatusFiscalizacao


class NotaQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.core.permissions import is_dev
        if is_dev(user):
            return self
        qs = self.filter(distribuidora__in=user.perfil.distribuidoras.all())
        regionais = user.perfil.regionais.all()
        if regionais.exists():
            qs = qs.filter(regional__in=regionais)
        return qs

    def ativas(self):
        return self.exclude(status_ccs__in=["FINL", "CANC"])

    def da_gerencia(self, gerencia: str):
        return self.filter(gerencia_responsavel=gerencia)

    def em_campo(self):
        return self.filter(status_fiscalizacao__considera_em_campo=True)


class Nota(TimeStamped):
    """
    Nota de Incorporação de Rede (TIPO_NOTA = 'IR').
    Espelha BaseIncorporacao do PBIX. Campos vindos do Snowflake são read-only
    na interface; campos de tratativa são editáveis pelo perfil responsável.
    """

    # ---------- chave e tenant ----------
    nota = models.CharField(max_length=20, db_index=True)
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.PROTECT, related_name="notas")
    tipo_nota = models.CharField(max_length=5, default="IR")

    # ---------- identificação ----------
    nota_proj = models.CharField("Nota PROJ", max_length=20, blank=True, db_index=True)
    pep = models.CharField("PEP", max_length=40, blank=True)
    pep_i = models.CharField("PEP (I)", max_length=40, blank=True)
    instalacao = models.CharField(max_length=30, blank=True)
    conta_contrato = models.CharField(max_length=30, blank=True)
    texto_breve = models.CharField(max_length=240, blank=True)
    nota_oc_vinculada = models.CharField(max_length=20, blank=True)

    # ---------- localização ----------
    estado = models.CharField(max_length=40, blank=True)
    regional = models.ForeignKey(Regional, null=True, blank=True, on_delete=models.SET_NULL, related_name="notas")
    area_estrut_regional = models.CharField(max_length=80, blank=True)
    municipio = models.ForeignKey(Municipio, null=True, blank=True, on_delete=models.SET_NULL, related_name="notas")
    municipio_txt = models.CharField(max_length=120, blank=True, help_text="Valor bruto do SAP (antes do De-Para).")
    bairro = models.CharField(max_length=120, blank=True)
    perimetro = models.CharField(max_length=40, blank=True)
    endereco = models.CharField(max_length=240, blank=True)
    latitude = models.CharField(max_length=30, blank=True)
    longitude = models.CharField(max_length=30, blank=True)

    # ---------- cliente / obra ----------
    nome_cliente = models.CharField("Cliente", max_length=180, blank=True)
    carteira_cliente = models.CharField(max_length=80, blank=True)
    sli_solicitante = models.CharField(max_length=120, blank=True)
    sli_desc_obra = models.TextField(blank=True)
    nome_solicitante_demanda_interna = models.CharField(max_length=180, blank=True)
    descricao_solicitacao_demanda_interna = models.TextField(blank=True)

    # ---------- esteira ----------
    medida_atual = models.ForeignKey(
        Medida, null=True, blank=True, on_delete=models.SET_NULL, related_name="notas_atuais"
    )
    codigo_medida_atual = models.CharField(max_length=20, blank=True)
    texto_medida_atual = models.CharField(max_length=240, blank=True)
    medida_anterior = models.CharField(max_length=20, blank=True)
    codigo_medida_anterior = models.CharField(max_length=20, blank=True)
    texto_medida_anterior = models.TextField(blank=True)
    texto_observacao_medida_anterior = models.TextField(blank=True)
    grupo_codes = models.CharField(max_length=20, blank=True)
    codificacao = models.CharField(max_length=40, blank=True)
    texto_breve_grupo_codigo = models.CharField(max_length=160, blank=True)
    centro_trabalho = models.ForeignKey(
        CentroTrabalho, null=True, blank=True, on_delete=models.SET_NULL, related_name="notas"
    )
    gerencia_sap = models.CharField(max_length=60, blank=True)

    # materializados pelo De-Para (ver recalcular_derivados)
    gerencia_responsavel = models.CharField(
        max_length=20, choices=Gerencia.choices, default=Gerencia.NAO_MAPEADA, db_index=True
    )
    etapa = models.CharField(max_length=20, choices=Etapa.choices, blank=True, db_index=True)
    chave_mapeamento = models.CharField(max_length=45, blank=True, db_index=True)

    # ---------- status ----------
    status_ccs = models.CharField(max_length=10, blank=True, db_index=True)   # ATIV, FINL, CANC, RECE
    status_ccs_nota_oc = models.CharField(max_length=10, blank=True)
    status_fiscalizacao = models.ForeignKey(
        StatusFiscalizacao, null=True, blank=True, on_delete=models.SET_NULL, related_name="notas"
    )
    status_sgo = models.CharField(max_length=60, blank=True, default="Sem Nota Proj")
    status_sap = models.CharField(max_length=60, blank=True, default="Projeto Não Elaborado")
    status_proj = models.CharField(max_length=60, blank=True)
    status_demanda_interna = models.CharField(max_length=60, blank=True)

    # ---------- datas ----------
    data_criacao = models.DateField(null=True, blank=True, db_index=True)
    data_alteracao = models.DateField(null=True, blank=True)
    data_abertura_demanda_interna = models.DateField(null=True, blank=True)
    inicio_desejado = models.DateField(null=True, blank=True)
    fim_desejado = models.DateField(null=True, blank=True)
    inicio_avaria = models.DateField(null=True, blank=True)
    inicio_avaria_nota_vinculada = models.DateField(null=True, blank=True)
    data_encerramento_nota = models.DateField(null=True, blank=True)
    data_criacao_medida = models.DateField(null=True, blank=True)
    data_conclusao_medida = models.DateField(null=True, blank=True)
    inicio_programado_medida = models.DateField(null=True, blank=True)
    fim_programado_medida = models.DateField(null=True, blank=True)
    data_agendamento = models.DateField(null=True, blank=True)
    data_atribuicao_fiscal = models.DateField(null=True, blank=True)
    data_da_fiscalizacao = models.DateField(null=True, blank=True)
    data_previsao_entrega = models.DateField(null=True, blank=True)
    data_solicitacao = models.DateField(null=True, blank=True)
    data_devolucao = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)
    data_entrega_relatorio_campo = models.DateField(null=True, blank=True)
    data_ligacao = models.DateField(null=True, blank=True)
    data_primeira_energizacao = models.DateField(null=True, blank=True)
    data_ultima_energizacao = models.DateField(null=True, blank=True)
    data_energizacao_nota_ir = models.DateField(null=True, blank=True)
    data_ultima_nota_vinculada = models.DateField(null=True, blank=True)
    concluido_por = models.CharField(max_length=120, blank=True)
    duracao_dias = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prazo_anexo_iv = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    multa = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # ---------- financeiro (vindo do SAP) ----------
    vl_material_total = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    vl_mo_total = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    vl_total_orcamento = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)

    # ---------- notas vinculadas / ligação ----------
    qtd_notas_vinculadas = models.IntegerField(default=0)
    tipos_notas_vinculadas = models.CharField(max_length=240, blank=True)
    notas_vinculadas = models.TextField(blank=True)
    qtd_notas_vinculadas_ligadas = models.IntegerField(default=0)
    qtd_notas_vinculadas_nao_ligadas = models.IntegerField(default=0)
    notas_vinculadas_ligadas = models.TextField(blank=True)
    tem_vinculada_ligada = models.CharField(max_length=10, blank=True)
    cliente_ligado = models.CharField(max_length=40, blank=True, default="NOTA NÃO MAPEADA")
    cliente_ligado_nota_ir = models.CharField(max_length=40, blank=True)
    qtd_clientes_ligados = models.IntegerField(default=0)

    # ---------- controle ----------
    sincronizado_em = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords(excluded_fields=["sincronizado_em", "atualizado_em"])

    objects = NotaQuerySet.as_manager()

    class Meta:
        verbose_name = "Nota de incorporação"
        verbose_name_plural = "Notas de incorporação"
        constraints = [models.UniqueConstraint(fields=["distribuidora", "nota"], name="uniq_nota_distribuidora")]
        indexes = [
            models.Index(fields=["distribuidora", "gerencia_responsavel"]),
            models.Index(fields=["distribuidora", "etapa"]),
            models.Index(fields=["distribuidora", "status_ccs"]),
            models.Index(fields=["data_criacao"]),
        ]

    def __str__(self):
        return f"Nota {self.nota} ({self.distribuidora.sigla})"

    # ===================== REGRAS DAX MIGRADAS =====================

    @staticmethod
    def _param(chave, default):
        from apps.core.models import ParametroSistema
        try:
            return ParametroSistema.objects.get(chave=chave).valor
        except ParametroSistema.DoesNotExist:
            return default

    @staticmethod
    def _faixa_prazo(dias: int | None) -> str | None:
        """Escala usada em Status_Prazo, Status_Prazo_nota_vinculada e Status_Prazo_NOTA_IR."""
        if dias is None:
            return None
        alerta = int(Nota._param("SLA_ALERTA_DIAS", 5))
        if dias < 0:
            return "Fora prazo"
        if dias == 0:
            return "Vence Hoje"
        if dias <= alerta:
            return "Prestes a Vencer"
        return "No Prazo"

    # --- SLA da nota (DATA_CRIACAO + 90) ---
    @property
    def data_prazo(self) -> date | None:
        if not self.data_criacao:
            return None
        return self.data_criacao + timedelta(days=int(self._param("SLA_NOTA_DIAS", 90)))

    @property
    def dias_prazo(self) -> int | None:
        return (self.data_prazo - date.today()).days if self.data_prazo else None

    @property
    def status_prazo(self) -> str | None:
        return self._faixa_prazo(self.dias_prazo)

    # --- SLA da nota vinculada (INICIO_AVARIA + 30) ---
    @property
    def prazo_nota_vinculada(self) -> date | None:
        base = self.inicio_avaria_nota_vinculada or self.inicio_avaria
        if not base:
            return None
        return base + timedelta(days=int(self._param("SLA_NOTA_VINCULADA_DIAS", 30)))

    @property
    def dias_prazo_nota_vinculada(self) -> int | None:
        p = self.prazo_nota_vinculada
        return (p - date.today()).days if p else None

    @property
    def status_prazo_nota_vinculada(self) -> str | None:
        return self._faixa_prazo(self.dias_prazo_nota_vinculada)

    @property
    def ordem_status_prazo_nota_vinculada(self) -> int | None:
        return {"Fora prazo": 1, "Vence Hoje": 2, "Prestes a Vencer": 3,
                "No Prazo": 4}.get(self.status_prazo_nota_vinculada)

    # --- SLA da medida (FIM_PROGRAMADO_MEDIDA) ---
    @property
    def dias_prazo_medida(self) -> int | None:
        if not self.fim_programado_medida:
            return None
        ref = self.data_conclusao_medida or date.today()
        return (self.fim_programado_medida - ref).days

    @property
    def status_prazo_medida(self) -> str | None:
        dias = self.dias_prazo_medida
        if dias is None:
            return None
        concluida = self.data_conclusao_medida is not None
        if concluida and dias < 0:
            return "Medida concluída fora do prazo"
        if concluida:
            return "Medida concluída no prazo"
        alerta = int(self._param("SLA_ALERTA_DIAS", 5))
        if dias < 0:
            return "Medida fora prazo"
        if dias == 0:
            return "Medida vence hoje"
        if dias <= alerta:
            return "Medida prestes a vencer"
        return "Medida no prazo"

    @property
    def ordem_status_prazo_medida(self) -> int | None:
        return {
            "Medida fora prazo": 1, "Medida vence hoje": 2, "Medida prestes a vencer": 3,
            "Medida no prazo": 4, "Medida concluída fora do prazo": 5, "Medida concluída no prazo": 6,
        }.get(self.status_prazo_medida)

    # --- SLA da nota IR (FIM_DESEJADO) ---
    @property
    def dias_prazo_nota_ir(self) -> int | None:
        return (self.fim_desejado - date.today()).days if self.fim_desejado else None

    @property
    def status_prazo_nota_ir(self) -> str | None:
        return self._faixa_prazo(self.dias_prazo_nota_ir)

    # --- Classificações ---
    @property
    def status_demanda(self) -> str:
        return {"FINL": "DEMANDA FINALIZADA", "CANC": "DEMANDA CANCELADA"}.get(
            self.status_ccs, "DEMANDA ATIVA"
        )

    @property
    def ordem_status_demanda(self) -> int:
        return {"FINL": 2, "CANC": 3}.get(self.status_ccs, 1)

    @property
    def status_rtp(self) -> str:
        corte = date.fromisoformat(self._param("DATA_CORTE_RTP26", "2023-12-01"))
        if not self.data_criacao:
            return ""
        return "RTP26" if self.data_criacao > corte else "RTP_Anterior"

    @property
    def classificacao_demanda(self) -> str:
        corte = date.fromisoformat(self._param("DATA_CORTE_GIRO", "2026-01-01"))
        if not self.data_criacao:
            return ""
        return "GIRO" if self.data_criacao > corte else "PASSIVO"

    @property
    def flag_compulsoria(self) -> str:
        if not self.data_criacao:
            return "Sem data"
        anos = int(self._param("ANOS_COMPULSORIA", 5))
        limite = date.today() - relativedelta(years=anos)
        return "Mais de 5 anos" if self.data_criacao <= limite else "Até 5 anos"

    @property
    def status_documentacao(self) -> str:
        txt = (self.texto_medida_anterior or "").lower()
        if "documentação aprovada" in txt:
            return "Documentação Aprovada"
        if "documentação reprovada" in txt:
            return "Documentação Reprovada"
        return ""

    @property
    def localizacao_mapa(self) -> str:
        """Corrige o hardcode 'Pará' do BI."""
        nome = self.municipio.nome if self.municipio else self.municipio_txt
        if not nome:
            return ""
        return f"{nome}, {self.distribuidora.uf}, Brasil"

    @property
    def status_fiscalizacao_formatada(self) -> str:
        if not self.status_fiscalizacao and not self.nota_proj:
            return "Sem Nota Proj"
        return self.status_fiscalizacao.status_sisco if self.status_fiscalizacao else ""

    @property
    def status_fiscalizacao_macro(self) -> str:
        return self.status_fiscalizacao.status_macro if self.status_fiscalizacao else ""

    # ===================== DERIVAÇÃO =====================

    def recalcular_derivados(self, salvar=True):
        """
        Recalcula chave_mapeamento + gerencia/etapa via De-Para.
        Chamado no ETL e no save().
        """
        from apps.integracao.models import MapeamentoMedidaGerencia

        cod_medida = (self.codigo_medida_atual or (self.medida_atual.codigo if self.medida_atual else "")).strip()
        cod_centro = (self.centro_trabalho.codigo if self.centro_trabalho else "").strip()
        self.chave_mapeamento = f"{cod_medida}|{cod_centro}"

        mapa = (
            MapeamentoMedidaGerencia.objects
            .filter(medida__codigo=cod_medida)
            .filter(models.Q(distribuidora=self.distribuidora) | models.Q(distribuidora__isnull=True))
            .order_by("-distribuidora_id", "-centro_trabalho_id")
        )
        escolhido = mapa.filter(centro_trabalho__codigo=cod_centro).first() or \
                    mapa.filter(centro_trabalho__isnull=True).first()

        if escolhido:
            self.gerencia_responsavel = escolhido.gerencia
            self.etapa = escolhido.etapa
            self.gerencia_sap = escolhido.gerencia_sap or self.gerencia_sap
        else:
            self.gerencia_responsavel = Gerencia.NAO_MAPEADA
            self.etapa = ""

        if salvar:
            self.save(update_fields=["chave_mapeamento", "gerencia_responsavel", "etapa", "gerencia_sap"])


class HistoricoMedida(models.Model):
    """
    Espelha HistoricoGerencias: 1 linha por medida da nota, com janelas calculadas.
    Base do SLA por gerência.
    """
    nota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name="historico")
    medida = models.CharField(max_length=40)
    grupo_medida = models.CharField(max_length=20, db_index=True)
    codigo_medida = models.CharField(max_length=20, blank=True)
    texto_breve_grupo_codigo = models.CharField(max_length=160, blank=True)

    gerencia_responsavel = models.CharField(max_length=20, choices=Gerencia.choices)
    gerencia_anterior = models.CharField(max_length=20, blank=True)
    proxima_medida = models.CharField(max_length=20, blank=True)
    proxima_gerencia = models.CharField(max_length=20, blank=True)
    gerencia_centro_trabalho = models.CharField(max_length=60, blank=True)

    data_entrada_medida = models.DateField(null=True, blank=True)
    data_saida_medida = models.DateField(null=True, blank=True)
    data_entrada_gerencia = models.DateField(null=True, blank=True)
    data_tratamento_gerencia = models.DateField(null=True, blank=True)
    data_atualizacao_registro = models.DateField(null=True, blank=True)

    ciclo_gerencia = models.PositiveIntegerField(default=1)
    is_medida_atual = models.BooleanField(default=False, db_index=True)
    entrou_na_gerencia = models.BooleanField(default=False)
    saiu_da_gerencia = models.BooleanField(default=False)
    dias_na_medida = models.IntegerField(null=True, blank=True)
    medida_nao_mapeada = models.CharField(max_length=40, blank=True)
    grupo_nao_mapeado = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Histórico de medida"
        verbose_name_plural = "Histórico de medidas"
        ordering = ["nota", "data_entrada_medida", "medida"]
        indexes = [
            models.Index(fields=["nota", "is_medida_atual"]),
            models.Index(fields=["gerencia_responsavel", "data_entrada_gerencia"]),
        ]

    def __str__(self):
        return f"{self.nota.nota} · {self.grupo_medida} · {self.gerencia_responsavel}"


class Tratativa(TimeStamped):
    """Registro manual do analista na nota — o que o BI não permite hoje."""
    class Tipo(models.TextChoices):
        COMENTARIO = "COM", "Comentário"
        CONTATO_CLIENTE = "CTT", "Contato com cliente"
        PENDENCIA = "PEN", "Pendência registrada"
        RESOLUCAO = "RES", "Pendência resolvida"
        ENCAMINHAMENTO = "ENC", "Encaminhamento a outra gerência"

    nota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name="tratativas")
    tipo = models.CharField(max_length=3, choices=Tipo.choices, default=Tipo.COMENTARIO)
    gerencia = models.CharField(max_length=20, choices=Gerencia.choices)
    texto = models.TextField()
    data_prevista_retorno = models.DateField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.nota.nota}"
```

---
### 6.4 `apps/documentos/models.py` — ⭐ Documentos Modelo

```python
import hashlib
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords

from apps.core.models import Distribuidora, Etapa, Gerencia, TimeStamped

EXTENSOES_PERMITIDAS = {
    ".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".pdf",
    ".pptx", ".dwg", ".dxf", ".zip", ".csv", ".txt",
}
TAMANHO_MAX_MB = 100


def valida_arquivo_modelo(arquivo):
    ext = os.path.splitext(arquivo.name)[1].lower()
    if ext not in EXTENSOES_PERMITIDAS:
        raise ValidationError(f"Extensão {ext} não permitida.")
    if arquivo.size > TAMANHO_MAX_MB * 1024 * 1024:
        raise ValidationError(f"Arquivo maior que {TAMANHO_MAX_MB} MB.")


def caminho_versao(instance, filename):
    doc = instance.documento
    return f"documentos_modelo/{doc.categoria.slug}/{doc.slug}/v{instance.numero}/{filename}"


class CategoriaDocumento(TimeStamped):
    """Agrupador da aba de Documentos Modelo."""
    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    descricao = models.CharField(max_length=240, blank=True)
    icone = models.CharField(max_length=40, blank=True, help_text="Nome do ícone (ex.: 'file-spreadsheet').")
    ordem = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "Categoria de documento"
        verbose_name_plural = "Categorias de documento"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class DocumentoModelo(TimeStamped):
    """
    Um documento modelo do processo (planilha de orçamento, checklist, termo,
    POP, ofício…). O ARQUIVO fica em VersaoDocumento — aqui mora a identidade.
    """
    class Status(models.TextChoices):
        VIGENTE = "VIG", "Vigente"
        EM_REVISAO = "REV", "Em revisão"
        ARQUIVADO = "ARQ", "Arquivado"

    categoria = models.ForeignKey(CategoriaDocumento, on_delete=models.PROTECT, related_name="documentos")
    nome = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, blank=True)
    codigo_pop = models.CharField(
        "Código do POP / norma", max_length=60, blank=True,
        help_text="Ex.: POP.00813.EQTL — Anexo II",
    )
    descricao = models.TextField(blank=True, help_text="Para que serve e quando usar.")
    instrucoes_uso = models.TextField(blank=True, help_text="Exibido na tela de detalhe do documento.")

    # Escopo: vazio = vale para todas
    distribuidoras = models.ManyToManyField(
        Distribuidora, blank=True, related_name="documentos_modelo",
        help_text="Vazio = documento corporativo (todas as 7).",
    )
    gerencias = models.JSONField(
        default=list, blank=True,
        help_text="Lista de gerências a que o documento se aplica. Vazio = todas.",
    )
    etapa = models.CharField(max_length=20, choices=Etapa.choices, blank=True)

    status = models.CharField(max_length=3, choices=Status.choices, default=Status.VIGENTE, db_index=True)
    obrigatorio_no_processo = models.BooleanField(
        default=False, help_text="Documento exigido pelo POP (aparece destacado)."
    )
    destaque = models.BooleanField(default=False, help_text="Fixa no topo da aba Documentos Modelo.")
    tags = models.JSONField(default=list, blank=True)
    total_downloads = models.PositiveIntegerField(default=0, editable=False)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-destaque", "categoria__ordem", "nome"]
        verbose_name = "Documento modelo"
        verbose_name_plural = "Documentos modelo"
        constraints = [models.UniqueConstraint(fields=["categoria", "slug"], name="uniq_doc_cat_slug")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)[:200]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

    @property
    def versao_vigente(self):
        return self.versoes.filter(vigente=True).first() or self.versoes.first()

    @property
    def extensao(self) -> str:
        v = self.versao_vigente
        return os.path.splitext(v.arquivo.name)[1].lower() if v else ""

    def visivel_para(self, user) -> bool:
        from apps.core.permissions import is_dev
        if is_dev(user):
            return True
        if self.status == self.Status.ARQUIVADO:
            return False
        if self.distribuidoras.exists():
            if not self.distribuidoras.filter(pk__in=user.perfil.distribuidoras.values("pk")).exists():
                return False
        if self.gerencias:
            if user.perfil.gerencia not in self.gerencias:
                return False
        return True


class VersaoDocumento(TimeStamped):
    """Cada publicação gera uma versão nova. Nada é sobrescrito."""
    documento = models.ForeignKey(DocumentoModelo, on_delete=models.CASCADE, related_name="versoes")
    numero = models.PositiveSmallIntegerField(help_text="1, 2, 3…")
    rotulo = models.CharField(
        max_length=40, blank=True, help_text="Ex.: 'Rev. 00', '7.1.2' — como consta no próprio arquivo."
    )
    arquivo = models.FileField(upload_to=caminho_versao, validators=[valida_arquivo_modelo])
    tamanho_bytes = models.BigIntegerField(default=0, editable=False)
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    nome_original = models.CharField(max_length=255, blank=True, editable=False)

    data_vigencia = models.DateField(null=True, blank=True, help_text="Data da revisão do documento.")
    notas_da_versao = models.TextField(blank=True, help_text="O que mudou nesta versão.")
    vigente = models.BooleanField(default=True, db_index=True)
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="versoes_publicadas"
    )
    total_downloads = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-numero"]
        verbose_name = "Versão do documento"
        verbose_name_plural = "Versões do documento"
        constraints = [models.UniqueConstraint(fields=["documento", "numero"], name="uniq_versao_doc")]

    def save(self, *args, **kwargs):
        if not self.numero:
            ultimo = self.documento.versoes.aggregate(m=models.Max("numero"))["m"] or 0
            self.numero = ultimo + 1
        if self.arquivo and not self.sha256:
            self.nome_original = os.path.basename(self.arquivo.name)
            self.arquivo.seek(0)
            h = hashlib.sha256()
            for chunk in self.arquivo.chunks():
                h.update(chunk)
            self.sha256 = h.hexdigest()
            self.tamanho_bytes = self.arquivo.size
            self.arquivo.seek(0)
        super().save(*args, **kwargs)
        if self.vigente:
            self.documento.versoes.exclude(pk=self.pk).update(vigente=False)

    @property
    def tamanho_legivel(self) -> str:
        n = float(self.tamanho_bytes)
        for u in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} TB"

    def __str__(self):
        return f"{self.documento.nome} v{self.numero} {self.rotulo}".strip()


class DownloadLog(models.Model):
    """
    Trilha de auditoria de TODO download de documento modelo.
    Responde: quem baixou, quando, qual versão, de onde.
    """
    versao = models.ForeignKey(VersaoDocumento, on_delete=models.CASCADE, related_name="downloads")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="downloads")
    distribuidora = models.ForeignKey(Distribuidora, null=True, blank=True, on_delete=models.SET_NULL)
    perfil_no_momento = models.CharField(max_length=20, blank=True)
    nota = models.CharField(max_length=20, blank=True, help_text="Se o download partiu de uma nota específica.")
    baixado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-baixado_em"]
        verbose_name = "Log de download"
        verbose_name_plural = "Logs de download"
        indexes = [models.Index(fields=["versao", "baixado_em"]), models.Index(fields=["usuario", "baixado_em"])]

    def __str__(self):
        return f"{self.usuario} baixou {self.versao} em {self.baixado_em:%d/%m/%Y %H:%M}"


class AnexoNota(TimeStamped):
    """Documento ENVIADO pelo cliente/analista, amarrado à nota e ao item do checklist."""
    nota = models.ForeignKey("incorporacao.Nota", on_delete=models.CASCADE, related_name="anexos")
    item_checklist = models.ForeignKey(
        "checklist.RespostaItem", null=True, blank=True, on_delete=models.SET_NULL, related_name="anexos"
    )
    tipo_documento = models.ForeignKey(
        "checklist.GrupoDocumento", null=True, blank=True, on_delete=models.SET_NULL, related_name="anexos"
    )
    arquivo = models.FileField(upload_to="anexos_nota/%Y/%m/", validators=[valida_arquivo_modelo])
    nome_exibicao = models.CharField(max_length=200, blank=True)
    observacao = models.TextField(blank=True)
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Anexo da nota"
        verbose_name_plural = "Anexos da nota"

    def __str__(self):
        return f"{self.nota.nota} — {self.nome_exibicao or self.arquivo.name}"
```

### 6.5 `apps/orcamento/models.py`

```python
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import Distribuidora, Municipio, Regional, TimeStamped

Z2 = Decimal("0.01")


def r2(v) -> Decimal:
    return (Decimal(v or 0)).quantize(Z2, rounding=ROUND_HALF_UP)


class CatalogoServico(models.Model):
    """
    Aba 'Serviços' da planilha: ~117 mil linhas.
    Chave de busca: distribuidora + regional + numero_servico (ALAGOAS: sem regional).
    """
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="servicos")
    regional = models.ForeignKey(
        Regional, null=True, blank=True, on_delete=models.CASCADE, related_name="servicos"
    )
    numero_servico = models.CharField(max_length=20, db_index=True)       # 5021000013
    texto_breve = models.CharField(max_length=200)
    unidade = models.CharField(max_length=10)                             # UN, M, M2, KM, VAO, CDA, UA, CJ, M3, H, DIA
    tipo = models.CharField(max_length=40, blank=True)
    quantidade_padrao = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    preco_bruto = models.DecimalField(max_digits=16, decimal_places=4)
    vigencia_inicio = models.DateField(null=True, blank=True)
    vigencia_fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True, db_index=True)
    importado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Serviço do catálogo"
        verbose_name_plural = "Catálogo de serviços"
        indexes = [
            models.Index(fields=["distribuidora", "regional", "numero_servico"]),
            models.Index(fields=["distribuidora", "numero_servico"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["distribuidora", "regional", "numero_servico", "vigencia_inicio"],
                name="uniq_servico_catalogo",
            )
        ]

    def __str__(self):
        return f"{self.numero_servico} — {self.texto_breve}"

    @property
    def chave_juntar(self) -> str:
        """Reproduz a coluna JUNTAR da planilha."""
        return f"{self.distribuidora.nome_catalogo}{self.regional.nome if self.regional else ''}{self.numero_servico}"


class Orcamento(TimeStamped):
    """
    Substitui a aba 'Orcamento RDU'. 1 orçamento por obra/PEP.
    Todos os totais são calculados por `recalcular()`.
    """
    class Status(models.TextChoices):
        RASCUNHO = "RAS", "Rascunho"
        EM_ANALISE = "ANA", "Em análise"
        APROVADO = "APR", "Aprovado"
        REPROVADO = "REP", "Reprovado"
        CANCELADO = "CAN", "Cancelado"

    # cabeçalho (B1..F9 da planilha)
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.PROTECT, related_name="orcamentos")
    nota = models.ForeignKey(
        "incorporacao.Nota", null=True, blank=True, on_delete=models.SET_NULL, related_name="orcamentos"
    )
    nome_obra = models.CharField("Obra", max_length=200)
    pep = models.CharField("PEP", max_length=40, blank=True)
    cliente = models.CharField(max_length=200, blank=True)
    data_energizacao = models.DateField("Dt Energização", null=True, blank=True)
    municipio = models.ForeignKey(Municipio, null=True, blank=True, on_delete=models.PROTECT, related_name="orcamentos")
    regional = models.ForeignKey(
        Regional, null=True, blank=True, on_delete=models.PROTECT, related_name="orcamentos",
        help_text="Preenchida automaticamente a partir do município.",
    )

    # entradas do bloco da direita (L90..M100)
    demanda_kw = models.DecimalField(
        "Demanda (kW)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    constante_k = models.DecimalField(
        "Constante K", max_digits=12, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    erc = models.DecimalField("ERC", max_digits=16, decimal_places=2, default=0)

    # totais calculados
    total_materiais = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total_mao_obra = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total_transporte = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total_obra = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total_proporcionalizado = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    erd = models.DecimalField("ERD", max_digits=16, decimal_places=2, default=0, editable=False)
    participacao_financeira_cliente = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total_nf_materiais = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total_nf_servicos = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    custo_comprovado_cliente = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    erd_mais_erc = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    valor_a_restituir = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)

    status = models.CharField(max_length=3, choices=Status.choices, default=Status.RASCUNHO, db_index=True)
    aprovado_por = models.ForeignKey(
        "core.Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="orcamentos_aprovados"
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Orçamento RDU"
        verbose_name_plural = "Orçamentos RDU"

    def __str__(self):
        return f"Orçamento {self.pk} — {self.nome_obra}"

    # ================= MOTOR DE CÁLCULO (fórmulas 1 a 9) =================

    def recalcular(self, salvar=True):
        itens = self.itens.all()

        mat = sum((r2(i.total) for i in itens if i.bloco == ItemOrcamento.Bloco.MATERIAL), Decimal(0))
        mo = sum((r2(i.total) for i in itens if i.bloco == ItemOrcamento.Bloco.MAO_OBRA), Decimal(0))
        tr = sum((r2(i.total) for i in itens if i.bloco == ItemOrcamento.Bloco.TRANSPORTE), Decimal(0))

        nf_mat = sum((r2(i.valor_nota_fiscal) for i in itens if i.bloco == ItemOrcamento.Bloco.MATERIAL), Decimal(0))
        nf_srv = sum((r2(i.valor_nota_fiscal) for i in itens if i.bloco == ItemOrcamento.Bloco.MAO_OBRA), Decimal(0))

        self.total_materiais = r2(mat)                                   # (1)
        self.total_mao_obra = r2(mo)                                     # (2)
        self.total_transporte = r2(tr)                                   # (3)
        self.total_obra = r2(mat + mo + tr)                              # (4) = G92
        self.total_proporcionalizado = r2(self.total_obra - r2(self.erc))  # (6) = G96

        # (7) ERD = demanda × K
        self.erd = r2((self.demanda_kw or 0) * (self.constante_k or 0))

        # (8) participação financeira do cliente
        dif = self.total_proporcionalizado - self.erd
        self.participacao_financeira_cliente = r2(dif) if dif > 0 else Decimal("0.00")

        # bloco da direita
        self.total_nf_materiais = r2(nf_mat)
        self.total_nf_servicos = r2(nf_srv)
        self.custo_comprovado_cliente = r2(nf_mat + nf_srv)              # M96
        orcamento_distribuidora = self.total_obra                        # M98
        self.erd_mais_erc = self.erd if self.erd >= orcamento_distribuidora \
            else r2(self.erd + r2(self.erc))                             # M100

        # (9) a restituir
        from apps.core.models import ParametroSistema
        try:
            limite = Decimal(ParametroSistema.objects.get(chave="DEMANDA_LIMITE_RESTITUICAO_KW").valor)
        except ParametroSistema.DoesNotExist:
            limite = Decimal("50")

        if self.demanda_kw in (None, ""):
            self.valor_a_restituir = Decimal("0.00")
        elif Decimal(self.demanda_kw) < limite:
            self.valor_a_restituir = min(self.custo_comprovado_cliente, orcamento_distribuidora)
        else:
            self.valor_a_restituir = min(
                self.custo_comprovado_cliente, orcamento_distribuidora, self.erd_mais_erc
            )

        if salvar:
            self.save()
        return self


class ItemOrcamento(models.Model):
    class Bloco(models.TextChoices):
        MATERIAL = "MAT", "1 - Materiais"
        MAO_OBRA = "MO", "2 - Mão de obra de instalação"
        TRANSPORTE = "TRA", "3 - Transporte"

    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="itens")
    bloco = models.CharField(max_length=3, choices=Bloco.choices)
    ordem = models.PositiveSmallIntegerField(default=0)

    codigo = models.CharField(max_length=20, blank=True, help_text="Código SAP do material ou nº do serviço.")
    servico_catalogo = models.ForeignKey(
        CatalogoServico, null=True, blank=True, on_delete=models.SET_NULL, related_name="itens",
        help_text="Preenchido automaticamente no bloco de Mão de obra.",
    )
    descricao = models.CharField(max_length=240, blank=True)
    unidade = models.CharField(max_length=10, blank=True)
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    preco_unitario = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)

    # colunas H/I da planilha
    quantidade_nota_fiscal = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    valor_nota_fiscal = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    preco_travado = models.BooleanField(
        default=False, help_text="Impede que o recálculo sobrescreva o preço vindo do catálogo.",
    )

    class Meta:
        ordering = ["bloco", "ordem", "id"]
        verbose_name = "Item do orçamento"
        verbose_name_plural = "Itens do orçamento"

    def resolver_preco_catalogo(self):
        """
        Reproduz F74 da planilha:
          se distribuidora == ALAGOAS: chave = distribuidora + nº serviço
          senão:                       chave = distribuidora + regional + nº serviço
        """
        if self.bloco != self.Bloco.MAO_OBRA or not self.codigo:
            return None
        orc = self.orcamento
        qs = CatalogoServico.objects.filter(
            distribuidora=orc.distribuidora, numero_servico=self.codigo, ativo=True
        )
        if orc.distribuidora.nome_catalogo != "ALAGOAS" and orc.regional_id:
            qs = qs.filter(regional=orc.regional)
        serv = qs.order_by("-vigencia_inicio").first()
        if serv:
            self.servico_catalogo = serv
            self.descricao = self.descricao or serv.texto_breve
            self.unidade = self.unidade or serv.unidade
            if not self.preco_travado:
                self.preco_unitario = serv.preco_bruto
        return serv

    def save(self, *args, **kwargs):
        if self.bloco == self.Bloco.MAO_OBRA:
            self.resolver_preco_catalogo()
        self.total = r2(Decimal(self.quantidade or 0) * Decimal(self.preco_unitario or 0))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_bloco_display()} · {self.codigo} · {self.descricao[:40]}"


class ImportacaoProjeto(TimeStamped):
    """
    Substitui a aba oculta 'Colar Serviços PROJ': o usuário cola/sobe o extrato
    do projeto (SGO/PROJ) e o sistema agrega por código e joga no bloco de mão de obra.
    Colunas esperadas: Tipo de Componente, Elemento, Código Material/Serviço,
                       Descrição, Quantidade, Unidade, Aplicação, Valor
    """
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="importacoes")
    arquivo = models.FileField(upload_to="importacao_projeto/%Y/%m/", null=True, blank=True)
    conteudo_colado = models.TextField(blank=True, help_text="Alternativa ao upload: colar TSV/CSV.")
    linhas_lidas = models.IntegerField(default=0)
    linhas_agregadas = models.IntegerField(default=0)
    codigos_nao_encontrados = models.JSONField(default=list, blank=True)
    aplicado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Importação de projeto"
        verbose_name_plural = "Importações de projeto"
```

### 6.6 `apps/checklist/models.py`

```python
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import Distribuidora, TimeStamped


class GrupoDocumento(TimeStamped):
    """Os 12 grupos do resumo gerencial (linha 24 da planilha)."""
    nome = models.CharField(max_length=120, unique=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    aceita_multiplos_anexos = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordem"]
        verbose_name = "Grupo de documento"
        verbose_name_plural = "Grupos de documento"

    def __str__(self):
        return self.nome


class ChecklistTemplate(TimeStamped):
    """Versão do checklist. Hoje: POP.00813 Anexo II, Rev. 00 (16/01/2024)."""
    codigo = models.CharField(max_length=60, help_text="POP.00813.EQTL - Anexo II")
    revisao = models.CharField(max_length=20, default="00")
    data_revisao = models.DateField(null=True, blank=True)
    vigente = models.BooleanField(default=True, db_index=True)
    distribuidoras = models.ManyToManyField(Distribuidora, blank=True, related_name="checklists")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Template de checklist"
        verbose_name_plural = "Templates de checklist"
        constraints = [models.UniqueConstraint(fields=["codigo", "revisao"], name="uniq_checklist_rev")]

    def __str__(self):
        return f"{self.codigo} — Rev. {self.revisao}"


class ItemChecklist(TimeStamped):
    """Os 16 itens do Anexo II."""
    class Obrigatoriedade(models.TextChoices):
        NECESSARIO = "NEC", "Necessário"
        SE_RESTITUICAO = "RES", "Quando houver restituição"
        CONDICIONAL = "CON", "Condicional"
        POS_FISCALIZACAO = "POS", "Apresentar após fiscalização de campo"

    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="itens")
    numero = models.PositiveSmallIntegerField()
    documento_exigido = models.TextField(help_text="Coluna D da planilha.")
    texto_pendencia = models.CharField(
        max_length=200, help_text="Coluna B — texto gerado quando a resposta é NÃO.",
    )
    codigo_pendencia = models.CharField(max_length=10, blank=True, help_text="IT1…IT16")
    codigo_hierarquico = models.CharField(max_length=10, blank=True, help_text="1.1 … 6.2")
    observacao = models.TextField(blank=True, help_text="Coluna F da planilha.")
    obrigatoriedade = models.CharField(max_length=3, choices=Obrigatoriedade.choices, default=Obrigatoriedade.NECESSARIO)
    impeditivo_ligacao = models.BooleanField(
        default=False, help_text="Marcar para Licenças Ambientais (impeditivo para ligação da UC/RD).",
    )
    grupo_documento = models.ForeignKey(
        GrupoDocumento, null=True, blank=True, on_delete=models.SET_NULL, related_name="itens"
    )
    exige_anexo = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "Item do checklist"
        verbose_name_plural = "Itens do checklist"
        constraints = [models.UniqueConstraint(fields=["template", "numero"], name="uniq_item_template")]

    def __str__(self):
        return f"{self.numero}. {self.documento_exigido[:60]}"


class ChecklistNota(TimeStamped):
    """Preenchimento do checklist para uma nota."""
    class Resultado(models.TextChoices):
        EM_ANALISE = "ANA", "Em análise"
        APROVADA = "APR", "Documentação Aprovada"
        REPROVADA = "REP", "Documentação Reprovada"

    nota = models.ForeignKey("incorporacao.Nota", on_delete=models.CASCADE, related_name="checklists")
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.PROTECT, related_name="preenchimentos")
    resultado = models.CharField(max_length=3, choices=Resultado.choices, default=Resultado.EM_ANALISE, db_index=True)
    analisado_por = models.ForeignKey(
        "core.Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="checklists_analisados"
    )
    analisado_em = models.DateTimeField(null=True, blank=True)

    texto_pendencias = models.TextField(
        blank=True, editable=False,
        help_text="Gerado automaticamente: pendências separadas por ';' (equivale a D20 da planilha).",
    )
    qtd_pendencias = models.PositiveSmallIntegerField(default=0, editable=False)
    tem_impeditivo = models.BooleanField(default=False, editable=False)

    comunicado_ao_cliente_em = models.DateField(null=True, blank=True)
    prazo_retorno_cliente = models.DateField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Checklist da nota"
        verbose_name_plural = "Checklists das notas"

    def __str__(self):
        return f"Checklist nota {self.nota.nota} — {self.get_resultado_display()}"

    def gerar_pendencias(self, salvar=True):
        """Reproduz C4:C19 + D20 e o resumo dos 12 grupos."""
        respostas = self.respostas.select_related("item").order_by("item__numero")
        partes = [
            r.item.texto_pendencia if r.resposta == RespostaItem.Resposta.NAO else ""
            for r in respostas
        ]
        self.texto_pendencias = ";".join(partes)
        self.qtd_pendencias = sum(1 for p in partes if p)
        self.tem_impeditivo = respostas.filter(
            resposta=RespostaItem.Resposta.NAO, item__impeditivo_ligacao=True
        ).exists()
        if salvar:
            self.save(update_fields=["texto_pendencias", "qtd_pendencias", "tem_impeditivo"])
        return self.texto_pendencias

    @property
    def resumo_grupos(self) -> dict:
        """
        {'Projeto/As Built em CAD': 'ok' | 'Falta' | 'N/A' | ''}
        Equivale à linha 25 da planilha.
        """
        mapa = {"SIM": "ok", "NAO": "Falta", "NA": "N/A"}
        out = {}
        for r in self.respostas.select_related("item__grupo_documento"):
            grupo = r.item.grupo_documento
            if grupo:
                out[grupo.nome] = mapa.get(r.resposta, "")
        return out


class RespostaItem(models.Model):
    class Resposta(models.TextChoices):
        SIM = "SIM", "SIM"
        NAO = "NAO", "NÃO"
        NAO_SE_APLICA = "NA", "NÃO SE APLICA"

    checklist = models.ForeignKey(ChecklistNota, on_delete=models.CASCADE, related_name="respostas")
    item = models.ForeignKey(ItemChecklist, on_delete=models.PROTECT, related_name="respostas")
    resposta = models.CharField(max_length=3, choices=Resposta.choices, blank=True)
    observacao = models.TextField(blank=True)
    respondido_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item__numero"]
        verbose_name = "Resposta do checklist"
        verbose_name_plural = "Respostas do checklist"
        constraints = [models.UniqueConstraint(fields=["checklist", "item"], name="uniq_resposta_item")]

    @property
    def status_grupo(self) -> str:
        return {"SIM": "ok", "NAO": "Falta", "NA": "N/A"}.get(self.resposta, "")

    def __str__(self):
        return f"{self.item.numero} = {self.resposta}"
```

---
## Módulo 1 — Painel / BI

Substitui as páginas *Home* e *Desempenho* do Power BI.

### F1.1 Barra de filtros global (persistida na sessão)

| Filtro | Origem no BI | Comportamento |
|---|---|---|
| Distribuidora | slicer `ESTADO` | Multi-seleção, limitada às distribuidoras do perfil. Dev vê todas. |
| Regional | slicer `REGIONAL` | Dependente da distribuidora |
| Município | — (novo) | Dependente da regional |
| Gerência | slicer `GERENCIA` | TÁTICO / RELACIONAMENTO / ATIVOS / CADASTRO / FINANCEIRO / NÃO MAPEADA |
| Etapa | — (novo) | As 11 etapas |
| Status da demanda | slicer `status_demanda` | ATIVA / FINALIZADA / CANCELADA |
| Status fiscalização (macro) | slicer `STATUS_FISCALIZACAO_FORMAT` | 7 valores da tabela de status |
| Compulsória | slicer `Flag_compulsoria` | Mais de 5 anos / Até 5 anos / Sem data |
| Ciclo RTP | slicer `status_rtp` | RTP26 / RTP_Anterior |
| Classificação | — (novo, já existe a coluna) | GIRO / PASSIVO |
| Período de criação | — (novo) | Range de `data_criacao` |
| Busca por Nota | caixa de texto | `nota` exato ou contém |
| Busca por Nota PROJ | caixa de texto | `nota_proj` |

Requisitos:
- Filtros em `?querystring` (URL compartilhável) e salvos em `request.session["painel_filtros"]`.
- Botão **Limpar filtros** e **Salvar como visão** (visão nomeada por usuário).
- Todo recarregamento via HTMX (sem reload de página).

### F1.2 Cards de KPI (12)

| Card | Fórmula | Clique leva para |
|---|---|---|
| Total de Notas | `COUNT(DISTINCT nota)` | Carteira sem filtro adicional |
| Orçamento Estimado | `SUM(vl_total_orcamento)` | Carteira ordenada por valor |
| Documentação | `etapa = DOCUMENTAÇÃO` | Carteira filtrada |
| Vistoria | `etapa = VISTORIA` | ” |
| Orçamento | `etapa = ORÇAMENTO` | ” |
| Criação de PEP | `etapa = PEP` | ” |
| Etapa Cadastro | `etapa = CADASTRO` | ” |
| Pend. Tático | `etapa = TÁTICO` | ” |
| Pend. Relacionamento | `etapa = RELACIONAMENTO` | ” |
| Pend. Ativos | `etapa = ATIVOS` | ” |
| Pend. Financeiro | `etapa = FINANCEIRO` | ” |
| BDGD / Capitalização | `etapa = BDGD` / `CAPITALIZAÇÃO` | ” |

Cards extras (novos, úteis e já possíveis com os dados):
- **Fora de prazo** — `status_prazo = "Fora prazo"`
- **Vencem em 5 dias** — `status_prazo ∈ {Vence Hoje, Prestes a Vencer}`
- **Em campo** — `status_fiscalizacao.considera_em_campo = True`
- **Clientes ligados** — `SUM(qtd_clientes_ligados)`
- **Multas** — `SUM(multa)`
- **Não mapeadas** — `gerencia_responsavel = "NÃO MAPEADA"` ← fila de trabalho do Desenvolvedor

### F1.3 Gráficos (ECharts)

| Gráfico | Tipo | Eixos | Rótulo |
|---|---|---|---|
| Incorporações por Gerência | coluna | gerência × qtd | `n (x%)` |
| Incorporações por Medidas | barra horizontal | `texto_breve_grupo_codigo` × qtd | `n (x%)` |
| Incorporações por Regional | waterfall | regional × qtd | `n (x%)` |
| Incorporações por Distribuidora | coluna | distribuidora × qtd | `n (x%)` |
| Tipo de Demanda | treemap | `classificacao_demanda` / `status_demanda` | n |
| Prazo da Nota IR | coluna | `status_prazo_nota_ir` × qtd | n |
| Prazo da Medida | coluna | `status_prazo_medida` × qtd (ordenado pela ordem 1..6) | n |
| Entrantes × Mês × Ano | coluna agrupada | mês × qtd, série = ano | n |
| Orçamento por Ano | linha + coluna combinados | ano × qtd notas + soma orçamento | — |
| Funil de etapas | funnel (novo) | etapas na ordem do processo | n |

### F1.4 Matrizes (página Desempenho)

1. Gerência × Total de notas (+ %)
2. Etapa × Total de notas (+ %)
3. Medida (`texto_breve_grupo_codigo`) × Total de notas (+ %)
4. **Nova:** Gerência × Faixa de SLA (Fora prazo / Vence hoje / Prestes a vencer / No prazo)
5. **Nova:** Gerência × Tempo médio de permanência (dias) — vem de `HistoricoMedida.dias_na_medida`

### F1.5 Mapa

- Marcadores por `latitude`/`longitude`; fallback por `localizacao_mapa` (município + UF).
- Cor do marcador pelo `status_prazo`.
- Clique abre o detalhe da nota.

### F1.6 Exportações

- `XLSX` da tabela detalhe (49 colunas do BI) — via `openpyxl`, respeitando filtros.
- `PDF` do painel (cards + gráficos) — via WeasyPrint.
- `CSV` bruto (só Dev).

### F1.7 Timestamp de atualização

Exibir no topo: `Dados atualizados em: dd/mm/aaaa HH:mm` — vem da última `ExecucaoETL` com status `OK` (substitui a medida `ultima_atualizacao`).

---

## Módulo 2 — Carteira de Notas (Incorporações)

### F2.1 Lista

- Tabela paginada (server-side, 50/pág) com as 49 colunas do BI; seletor de colunas visíveis persistido por usuário.
- Ordenação por qualquer coluna; default: `ordem_status_prazo_medida`, depois `data_criacao`.
- **Badges de SLA** com cor: vermelho (Fora prazo) · laranja (Vence hoje) · amarelo (Prestes a vencer) · verde (No prazo) · cinza (sem prazo).
- Chips de contexto: `GIRO/PASSIVO`, `RTP26`, `Mais de 5 anos`, `Documentação Aprovada/Reprovada`.
- Seleção múltipla → ações em lote (exportar, atribuir responsável, registrar tratativa em massa).
- **"Minha fila"**: atalho que aplica `gerencia_responsavel = gerência do meu perfil` + `status_ccs ∉ (FINL, CANC)`.

### F2.2 Detalhe da nota (abas)

| Aba | Conteúdo | Quem edita |
|---|---|---|
| **Resumo** | Identificação, cliente, localização, mapa, status, valores, prazos calculados | leitura |
| **Esteira** | Timeline de `HistoricoMedida` (medida, gerência, entrada, saída, dias) + gráfico de barras do tempo por gerência | leitura |
| **Checklist** | Formulário dos 16 itens + anexos + texto de pendência gerado | Tático, Dev |
| **Orçamento** | Orçamentos vinculados, totais, botão de exportar XLSX | Tático cria/edita; Ativos aprova |
| **Documentos** | Anexos do cliente + **atalho para baixar os modelos relevantes da etapa** | todos criam anexo |
| **Tratativas** | Histórico de comentários/contatos, com autor e data | todos criam |
| **Notas vinculadas** | Lista de notas OC vinculadas, qtd ligadas/não ligadas, datas de energização | leitura |
| **Auditoria** | `django-simple-history` — o que mudou, quem e quando | Dev |

### F2.3 Regras de edição

```python
# apps/incorporacao/views.py (recorte)
from django.core.exceptions import PermissionDenied
from apps.core.permissions import pode_editar_nota

class NotaUpdateView(DistribuidoraQuerysetMixin, PerfilRequiredMixin, UpdateView):
    model = Nota
    form_class = NotaTratativaForm   # só campos de tratativa, nunca campos do SAP

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not pode_editar_nota(self.request.user, obj):
            raise PermissionDenied(
                f"Esta nota está na gerência {obj.gerencia_responsavel}. "
                "Você só pode editar notas da sua gerência."
            )
        return obj
```

Campos vindos do Snowflake são **sempre** read-only na UI (só o ETL escreve).

### F2.4 Alertas

- Job diário (Celery Beat, 07:00) que envia e-mail/notificação ao responsável:
  - notas da minha gerência com `status_prazo_medida = "Medida fora prazo"`
  - notas com `tem_impeditivo = True` no checklist
  - notas `Mais de 5 anos` sem tratativa nos últimos 30 dias
- Central de notificações no header (ícone + contador, HTMX polling).

---

## Módulo 3 — Documentos Modelo (central de downloads)

> **Este é o módulo que centraliza os arquivos modelo que vocês usam, com download direto pelo usuário.**

### F3.1 Tela "Documentos Modelo" (aba principal do menu)

Layout:

```
┌─────────────────────────────────────────────────────────────────────┐
│  📁 Documentos Modelo                        [+ Novo documento]*    │
│  Busca: [____________]  Categoria ▾  Gerência ▾  Distribuidora ▾    │
│                                                      * só perfil Dev │
├─────────────────────────────────────────────────────────────────────┤
│ ⭐ DESTAQUES                                                         │
│ ┌─────────────────────────┐ ┌─────────────────────────┐             │
│ │ 📊 Orçamento RDU        │ │ ✅ Checklist POP.00813  │             │
│ │ v7.1.2 · XLSX · 12,4 MB │ │ Rev. 00 · XLSX · 38 KB  │             │
│ │ Vigente · 14/11/2026    │ │ Vigente · 16/01/2024    │             │
│ │ [⬇ Baixar]  [ℹ Detalhes]│ │ [⬇ Baixar]  [ℹ Detalhes]│             │
│ └─────────────────────────┘ └─────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ ORÇAMENTO E CUSTOS                                      3 arquivos  │
│  📊 Orçamento NOME_DO_EMPREENDIMENTO_PEP     v7.1.2  XLSX  [⬇]      │
│  📄 Instrução de preenchimento do orçamento  v1      PDF   [⬇]      │
│ DOCUMENTAÇÃO DO CLIENTE                                 6 arquivos  │
│  ✅ Anexo II — Checklist de documentos       Rev.00  XLSX  [⬇]      │
│  📝 Termo de Incorporação de Redes           v2      DOCX  [⬇]      │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

### F3.2 Funcionalidades

| ID | Funcionalidade | Perfis |
|---|---|---|
| F3.2.1 | Listar documentos agrupados por categoria, com badge de status (Vigente / Em revisão / Arquivado) | todos |
| F3.2.2 | **Baixar o arquivo da versão vigente** (1 clique) | todos |
| F3.2.3 | Baixar versão anterior específica (histórico) | todos |
| F3.2.4 | Baixar **vários documentos em .zip** (seleção múltipla) | todos |
| F3.2.5 | Busca full-text por nome, código do POP, descrição e tags | todos |
| F3.2.6 | Filtrar por categoria, gerência, etapa, distribuidora, extensão | todos |
| F3.2.7 | Ver detalhe: descrição, instruções de uso, histórico de versões, notas da versão, hash SHA-256, quem publicou | todos |
| F3.2.8 | **Pacote da etapa**: botão "Baixar documentos desta etapa" dentro da nota — zip com todos os modelos da etapa atual da nota | todos |
| F3.2.9 | Publicar novo documento | **Dev** |
| F3.2.10 | Publicar nova versão (mantém histórico; versão anterior deixa de ser vigente automaticamente) | **Dev** |
| F3.2.11 | Editar metadados, categoria, escopo, destaque | **Dev** |
| F3.2.12 | Arquivar / reativar documento | **Dev** |
| F3.2.13 | Ver relatório de downloads (por documento, usuário, período, distribuidora) | **Dev** |
| F3.2.14 | Favoritar documento (aparece em "Meus favoritos") | todos |
| F3.2.15 | Link direto estável: `/documentos/<categoria>/<slug>/baixar/` (sempre entrega a versão vigente) | todos |

### F3.3 View de download com log e controle de acesso

```python
# apps/documentos/views.py
import mimetypes

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from apps.documentos.models import DocumentoModelo, DownloadLog, VersaoDocumento


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


@login_required
@require_GET
def baixar_documento(request, categoria_slug, doc_slug, versao=None):
    doc = get_object_or_404(
        DocumentoModelo.objects.select_related("categoria"),
        categoria__slug=categoria_slug, slug=doc_slug,
    )
    if not doc.visivel_para(request.user):
        raise Http404("Documento não disponível para o seu perfil.")

    if versao:
        ver = get_object_or_404(VersaoDocumento, documento=doc, numero=versao)
    else:
        ver = doc.versao_vigente
    if not ver or not ver.arquivo:
        raise Http404("Nenhuma versão publicada.")

    # --- auditoria ---
    DownloadLog.objects.create(
        versao=ver,
        usuario=request.user,
        distribuidora=getattr(request, "distribuidora", None),
        perfil_no_momento=getattr(request.user.perfil, "tipo", ""),
        nota=request.GET.get("nota", "")[:20],
        ip=_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
    )
    VersaoDocumento.objects.filter(pk=ver.pk).update(total_downloads=F("total_downloads") + 1)
    DocumentoModelo.objects.filter(pk=doc.pk).update(total_downloads=F("total_downloads") + 1)

    # nome amigável: Checklist_POP00813_Rev00.xlsx
    import os
    ext = os.path.splitext(ver.arquivo.name)[1]
    nome = f"{doc.slug}_{ver.rotulo or ('v' + str(ver.numero))}{ext}".replace(" ", "_")

    ctype = mimetypes.guess_type(nome)[0] or "application/octet-stream"
    resp = FileResponse(ver.arquivo.open("rb"), as_attachment=True, filename=nome, content_type=ctype)
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@login_required
@require_GET
def baixar_pacote_etapa(request, nota_id):
    """F3.2.8 — zip com todos os modelos da etapa atual da nota."""
    import io, zipfile
    from apps.incorporacao.models import Nota

    nota = get_object_or_404(Nota.objects.for_user(request.user), pk=nota_id)
    docs = [
        d for d in DocumentoModelo.objects.filter(
            status=DocumentoModelo.Status.VIGENTE
        ).filter(etapa__in=["", nota.etapa]).select_related("categoria")
        if d.visivel_para(request.user)
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for d in docs:
            ver = d.versao_vigente
            if not ver:
                continue
            import os
            ext = os.path.splitext(ver.arquivo.name)[1]
            z.writestr(f"{d.categoria.nome}/{d.slug}{ext}", ver.arquivo.read())
            DownloadLog.objects.create(
                versao=ver, usuario=request.user,
                distribuidora=nota.distribuidora,
                perfil_no_momento=getattr(request.user.perfil, "tipo", ""),
                nota=nota.nota, ip=_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            )
    buf.seek(0)
    return FileResponse(
        buf, as_attachment=True,
        filename=f"modelos_{nota.etapa or 'nota'}_{nota.nota}.zip",
        content_type="application/zip",
    )
```

```python
# apps/documentos/urls.py
from django.urls import path
from . import views

app_name = "documentos"

urlpatterns = [
    path("", views.DocumentoListView.as_view(), name="lista"),
    path("favoritos/", views.FavoritosView.as_view(), name="favoritos"),
    path("relatorio-downloads/", views.RelatorioDownloadsView.as_view(), name="relatorio"),
    path("pacote/<int:nota_id>/", views.baixar_pacote_etapa, name="pacote_etapa"),
    path("zip/", views.baixar_selecionados_zip, name="zip"),
    path("<slug:categoria_slug>/<slug:doc_slug>/", views.DocumentoDetailView.as_view(), name="detalhe"),
    path("<slug:categoria_slug>/<slug:doc_slug>/baixar/", views.baixar_documento, name="baixar"),
    path("<slug:categoria_slug>/<slug:doc_slug>/baixar/v<int:versao>/", views.baixar_documento, name="baixar_versao"),
]
```

### F3.4 Carga inicial (seed)

Categorias e documentos a criar na primeira migração de dados:

| Categoria | Documento | Arquivo de origem |
|---|---|---|
| Orçamento e custos | Orçamento NOME_DO_EMPREENDIMENTO_PEP | `Orçamento ... PEP 7.1.2.xlsx` (rótulo `7.1.2`) |
| Documentação do cliente | POP.00813 Anexo II — Checklist de documentos | `POP.00813.EQTL - 00 - Anexo II ... 4.xlsx` (rótulo `Rev. 00`) |
| Normas e POPs | POP.00813 — Incorporação de Redes | *a subir* |
| Normas e POPs | NT-017 EQTL — Incorporação RD | *a subir* |
| Termos e contratos | Termo de Incorporação de Redes | *a subir* |
| Termos e contratos | Termo de Doação | *a subir* |
| Termos e contratos | Contrato EQTL × Cliente (execução de obra) | *a subir* |
| Cliente e cadastro | Ficha cadastral de fornecedor | *a subir* |
| Cliente e cadastro | Modelo de dados bancários | *a subir* |
| Comunicação | Carta de comunicação de pendências | *a subir* |
| Vistoria | Relatório de vistoria de campo | *a subir* |

> Ação para você: subir os demais arquivos pela tela do módulo depois do deploy. O seed cria as fichas vazias com `status = "Em revisão"` para não ficarem órfãs.

---

## Módulo 4 — Orçamento RDU

### F4.1 Funcionalidades

| ID | Funcionalidade | Detalhe |
|---|---|---|
| F4.1.1 | Criar orçamento (avulso ou amarrado a uma nota) | Cabeçalho: distribuidora, obra, PEP, cliente, data de energização, município |
| F4.1.2 | **Regional automática** | Ao escolher o município, preenche a regional (substitui `VLOOKUP(C1&C9, Distribuidoras!C:D, 2, 0)`) |
| F4.1.3 | Bloco 1 — Materiais | Grid editável: código, descrição, unidade, quantidade, preço unitário → total = `round(qtd×preço,2)`; colunas de NF (quantidade e valor) |
| F4.1.4 | Bloco 2 — Mão de obra com **busca no catálogo** | Autocomplete por nº de serviço ou texto breve; preencher descrição, unidade e **preço do catálogo** da distribuidora+regional |
| F4.1.5 | Bloco 3 — Transporte | Grid simples |
| F4.1.6 | Totais em tempo real | Recalcula via HTMX a cada alteração de linha |
| F4.1.7 | Bloco regulatório | Entradas: demanda (kW), constante K, ERC → calcula ERD, participação financeira, custo comprovado, ERD+ERC, **valor a restituir** |
| F4.1.8 | **Exportar XLSX no layout oficial** | Gera arquivo idêntico à planilha (mesmas células e rótulos) usando template `openpyxl` |
| F4.1.9 | Exportar PDF | Para anexar ao processo |
| F4.1.10 | Importar extrato do projeto | Upload/colagem do extrato PROJ/SGO; agrega por código (substitui a tabela dinâmica da aba oculta) e cria as linhas de mão de obra |
| F4.1.11 | Versionar orçamento | Duplicar com incremento de versão; comparar duas versões lado a lado |
| F4.1.12 | Fluxo de aprovação | Rascunho → Em análise (Tático envia) → Aprovado/Reprovado (Ativos decide) |
| F4.1.13 | Alerta de preço travado | Se o preço digitado difere do catálogo, mostra aviso e exige marcar `preco_travado` + justificativa |
| F4.1.14 | Importar catálogo de serviços | Só Dev. Upload do XLSX; valida colunas; cria lote com vigência; mantém histórico de preço |
| F4.1.15 | Consultar catálogo | Tela de busca no catálogo (117 mil linhas) com filtro por distribuidora/regional, paginada |

### F4.2 Importador do catálogo (Celery)

```python
# apps/orcamento/tasks.py
from celery import shared_task
from django.utils import timezone
import openpyxl

from apps.core.models import Distribuidora, Regional
from apps.orcamento.models import CatalogoServico
from apps.integracao.models import ExecucaoETL

COLUNAS_ESPERADAS = [
    "DISTRIBUIDORA", "REGIONAL", "JUNTAR", "TIPO",
    "Nº SERVIÇO", "TEXTO BREVE", "QUANT", "UN", "PREÇO BRUTO",
]


@shared_task
def importar_catalogo_servicos(caminho_xlsx: str, vigencia_inicio=None, desativar_anteriores=True):
    exec_log = ExecucaoETL.objects.create(job="catalogo_servicos")
    vigencia_inicio = vigencia_inicio or timezone.localdate()
    try:
        wb = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
        ws = wb["Serviços"]
        rows = ws.iter_rows(min_row=1, max_col=9, values_only=True)
        header = [str(c).strip().upper() if c else "" for c in next(rows)]
        if header[:9] != COLUNAS_ESPERADAS:
            raise ValueError(f"Cabeçalho inesperado: {header[:9]}")

        cache_dist, cache_reg, lote = {}, {}, []
        lidas = 0

        for row in rows:
            nome_dist, nome_reg, _juntar, tipo, num, texto, quant, un, preco = row
            if not nome_dist or not num:
                continue
            lidas += 1

            if nome_dist not in cache_dist:
                cache_dist[nome_dist] = Distribuidora.objects.get(nome_catalogo=str(nome_dist).strip())
            dist = cache_dist[nome_dist]

            reg = None
            if nome_reg:
                key = (dist.pk, str(nome_reg).strip())
                if key not in cache_reg:
                    cache_reg[key] = Regional.objects.get_or_create(distribuidora=dist, nome=key[1])[0]
                reg = cache_reg[key]

            lote.append(CatalogoServico(
                distribuidora=dist, regional=reg,
                numero_servico=str(num).strip(),
                texto_breve=(texto or "")[:200],
                unidade=(un or "")[:10].upper(),
                tipo=(tipo or "")[:40],
                quantidade_padrao=quant or 0,
                preco_bruto=preco or 0,
                vigencia_inicio=vigencia_inicio,
            ))
            if len(lote) >= 5000:
                CatalogoServico.objects.bulk_create(lote, ignore_conflicts=True)
                lote.clear()

        if lote:
            CatalogoServico.objects.bulk_create(lote, ignore_conflicts=True)

        if desativar_anteriores:
            CatalogoServico.objects.filter(
                distribuidora__in=cache_dist.values(), vigencia_inicio__lt=vigencia_inicio
            ).update(ativo=False, vigencia_fim=vigencia_inicio)

        for d in cache_dist.values():
            d.catalogo_carregado = True
            d.save(update_fields=["catalogo_carregado"])

        exec_log.status = ExecucaoETL.Status.SUCESSO
        exec_log.registros_lidos = lidas
        exec_log.registros_inseridos = CatalogoServico.objects.filter(vigencia_inicio=vigencia_inicio).count()
    except Exception as e:
        exec_log.status = ExecucaoETL.Status.ERRO
        exec_log.mensagem = f"{type(e).__name__}: {e}"
        raise
    finally:
        exec_log.finalizado_em = timezone.now()
        exec_log.save()
```

### F4.3 Exportador XLSX no layout oficial

```python
# apps/orcamento/export.py
"""
Preenche uma cópia do template oficial mantendo formatação, cabeçalho e fórmulas
dos blocos que o usuário não mexe. Células escritas:
  C1 distribuidora · C5 obra · E5 PEP · C7 cliente · E7 dt energização
  C9 município · F9 regional
  Materiais  B14:I68   (código, descrição, unid., quant, preço, total, qtd NF, valor NF)
  Mão de obra B74:I83
  Transporte  B88:I88
  M90 demanda · M92 constante K · G94 ERC
Os totais (G70, G84, G90, G92, G96, G98, G100, G102, M94, M96, M98, M100)
permanecem como FÓRMULA do template — garantia de que o número do sistema
e o número do Excel são o mesmo.
"""
from pathlib import Path
import openpyxl

from apps.orcamento.models import ItemOrcamento

TEMPLATE = Path("apps/orcamento/templates_xlsx/orcamento_rdu_base.xlsx")

LINHA_INICIAL = {
    ItemOrcamento.Bloco.MATERIAL: 14,
    ItemOrcamento.Bloco.MAO_OBRA: 74,
    ItemOrcamento.Bloco.TRANSPORTE: 88,
}
LINHA_FINAL = {
    ItemOrcamento.Bloco.MATERIAL: 68,
    ItemOrcamento.Bloco.MAO_OBRA: 83,
    ItemOrcamento.Bloco.TRANSPORTE: 88,
}


def exportar_orcamento_xlsx(orcamento, destino: Path) -> Path:
    wb = openpyxl.load_workbook(TEMPLATE, keep_vba=False)
    ws = wb["Orcamento RDU"]

    ws["C1"] = orcamento.distribuidora.nome_catalogo
    ws["C5"] = orcamento.nome_obra
    ws["E5"] = orcamento.pep
    ws["C7"] = orcamento.cliente
    ws["E7"] = orcamento.data_energizacao
    ws["C9"] = orcamento.municipio.nome if orcamento.municipio else ""
    ws["F9"] = orcamento.regional.nome if orcamento.regional else ""
    ws["M90"] = orcamento.demanda_kw
    ws["M92"] = orcamento.constante_k
    ws["G94"] = orcamento.erc

    for bloco, inicio in LINHA_INICIAL.items():
        itens = list(orcamento.itens.filter(bloco=bloco).order_by("ordem", "id"))
        limite = LINHA_FINAL[bloco] - inicio + 1
        if len(itens) > limite:
            raise ValueError(
                f"Bloco {bloco} tem {len(itens)} itens, o template só aceita {limite}. "
                "Aumente a faixa no template ou divida o orçamento."
            )
        for n, it in enumerate(itens):
            r = inicio + n
            ws.cell(r, 2, it.codigo)                 # B
            if bloco != ItemOrcamento.Bloco.MAO_OBRA:
                ws.cell(r, 3, it.descricao)          # C (na MO é fórmula INDEX/MATCH)
                ws.cell(r, 4, it.unidade)            # D
            ws.cell(r, 5, float(it.quantidade))      # E
            if bloco != ItemOrcamento.Bloco.MAO_OBRA:
                ws.cell(r, 6, float(it.preco_unitario))  # F (na MO é VLOOKUP)
            ws.cell(r, 8, float(it.quantidade_nota_fiscal))  # H
            ws.cell(r, 9, float(it.valor_nota_fiscal))       # I

    destino.parent.mkdir(parents=True, exist_ok=True)
    wb.save(destino)
    return destino
```

> ⚠️ **Limites do template:** 55 linhas de material (14–68), 10 de mão de obra (74–83) e **1 de transporte** (linha 88). Se o orçamento real estourar isso, o template precisa ser estendido — tratar como requisito antes do go-live.

---

## Módulo 5 — Checklist documental

### F5.1 Funcionalidades

| ID | Funcionalidade | Perfil |
|---|---|---|
| F5.1.1 | Abrir checklist da nota (instancia o template vigente com as 16 respostas em branco) | Tático, Dev |
| F5.1.2 | Responder item: SIM / NÃO / NÃO SE APLICA + observação | Tático, Dev |
| F5.1.3 | Anexar documento por item (múltiplos arquivos) | Tático, Relacionamento, Ativos |
| F5.1.4 | **Gerar texto de pendência automaticamente** (`;` entre pendências — igual a D20) com botão *Copiar* para colar no SAP | Tático, Dev |
| F5.1.5 | Painel dos 12 grupos de documento com `ok / Falta / N/A` | todos |
| F5.1.6 | Destaque de **impeditivo de ligação** (licenças ambientais) com banner vermelho | todos |
| F5.1.7 | Aprovar / Reprovar documentação → grava `resultado` e alimenta `status_documentacao` | Tático, Dev |
| F5.1.8 | Comunicar pendências ao cliente: gera carta em PDF, registra data e prazo de retorno | Relacionamento, Dev |
| F5.1.9 | Exportar checklist preenchido em XLSX (layout do Anexo II) e PDF | todos |
| F5.1.10 | Histórico de preenchimentos (checklist é versionado por análise) | todos |
| F5.1.11 | Alerta de SLA de restituição (90 dias) quando houver valor a restituir | Ativos, Financeiro |
| F5.1.12 | Gerenciar o template: adicionar/editar itens, criar nova revisão | **Dev** |

### F5.2 Seed dos 16 itens + 12 grupos

```python
# apps/checklist/migrations/0002_seed_pop00813.py
from django.db import migrations

ITENS = [
    # (nº, documento_exigido, texto_pendencia, cod_pend, cod_hier, obrigatoriedade, impeditivo, grupo, observacao)
    (1,  "TERMO DE INCORPORAÇÃO DE REDES",
         "Falta solicitação de incorporação", "IT3", "1.3", "POS", False, "TERMO DE DOAÇÃO",
         "APRESENTAR APÓS A FISCALIZAÇÃO DE CAMPO"),
    (2,  "PROJETO APROVADO PELA EQTL – CÓPIA E ARQUIVO MAGNÉTICO (CAD GEORREFERENCIADA)",
         "Encaminhar DWG", "IT1", "1.1", "NEC", False, "Projeto/As Built em CAD",
         "NECESSÁRIO (RESOLUÇÃO 1000/21 RESPONSABILIDADE DA DISTRIBUIDORA)"),
    (3,  "ART – PROJETO E EXECUÇÃO",
         "Projeto sem ART de execução", "IT4", "1.4", "NEC", False, "ART de Execução", "NECESSÁRIO"),
    (4,  "NOTA FISCAL DE MATERIAL APLICADO NA EXECUÇÃO DA OBRA",
         "Falta Nota fiscal(Material ou serviço)", "IT2", "1.2", "NEC", False,
         "Notas Fiscais de Materiais", "NECESSÁRIO"),
    (5,  "NOTA FISCAL DE SERVIÇOS (ESPECIFICANDO O DETALHAMENTO DO SERVIÇO EXECUTADO EM CAMPO)",
         "Falta Nota fiscal(Material ou serviço)", "IT2", "1.2", "NEC", False,
         "Notas Fiscais de Serviços", "NECESSÁRIO (COMPROVANTE DE PAGAMENTO VÁLIDO - IDEAL NF)"),
    (6,  "LAUDO DE ENSAIO DOS EQUIPAMENTOS APLICADOS NA OBRA (TRANSFORMADOR, REGULADOR, RELIGADOR...)",
         "Falta laudo de equipamentos", "IT5", "1.5", "NEC", False,
         "Laudo de Ensaios de Equipamentos", "NECESSÁRIO"),
    (7,  "CÓPIA DE RG E CPF – CLIENTE (PESSOA FÍSICA) OU CÓPIA DE CPF/CNPJ E CONTRATO SOCIAL (PESSOA JURÍDICA)",
         "Sem documentos (CPF, RG ou CNPJ)", "IT6", "1.6", "NEC", False,
         "Documentos Cliente (RG-CPF-CNPJ)", "PESSOA FÍSICA OU PESSOA JURÍDICA"),
    (8,  "DADOS BANCÁRIOS EM NOME DO CLIENTE – DONO DA RD/UC",
         "Falta dados bancarios", "IT7", "2.1", "RES", False,
         "Dados Bancários-Comprovante", "QUANDO HOUVER RESTITUIÇÃO."),
    (9,  "CÓPIA DA PROCURAÇÃO RECONHECIDA EM CARTÓRIO – QUANDO RECLAMANTE NÃO FOR O DONO DA RD/UC",
         "Falta cópia de procuração", "IT8", "3.1", "CON", False, None,
         "NOS CASOS EM QUE NÃO FOR O PRÓPRIO INTERESSADO. EM CNPJ, QUANDO NÃO FOR O REPRESENTANTE LEGAL."),
    (10, "DOCUMENTO DE PROPRIEDADE DO TERRENO OU AUTORIZAÇÃO PARA EXECUÇÃO DE OBRAS NO MESMO",
         "Falta de documento da propriedade", "IT9", "3.2", "NEC", False,
         "Documento Terreno", "NECESSÁRIO (INFORMANDO SE É DE PROPRIEDADE OU ARRENDADO AO SOLICITANTE)"),
    (11, "QUANDO PROJETO MCMV (MINHA CASA MINHA VIDA): CONTRATO COM A CEF",
         "Falta contrato assinado MINHA CASA MINHA VIDA", "IT15", "6.1", "CON", False, None,
         "VERIFICAR QUAL FOI A DATA DE CORTE DA NECESSIDADE DE RESTITUIÇÃO"),
    (12, "LICENÇAS AMBIENTAIS - LICENÇA DE INSTALAÇÃO (LI) E LICENÇA DE OPERAÇÃO (LO)",
         "Projeto sem licenças ambientais", "IT10", "3.3", "NEC", True,
         "Licença Ambiental",
         "OBRIGATÓRIAS E IMPEDITIVAS PARA LIGAÇÃO DA UC/RD. (RESOLUÇÃO 1000/21)"),
    (13, "FICHA CADASTRAL DE FORNECEDOR PREENCHIDA E ASSINADA NO CASO DE RESTITUIÇÃO DE VALORES",
         "Falta ficha de cadastro de fornecedor", None, None, "RES", False, None,
         "QUANDO HOUVER RESTITUIÇÃO."),
    (14, "CONTRATO ASSINADO ENTRE EQTL E CLIENTE COM OPÇÃO POR EXECUÇÃO DA OBRA",
         "Falta contrato assinado para execução", "IT16", "6.2", "RES", False,
         "Contrato de Obras", "QUANDO HOUVER RESTITUIÇÃO."),
    (15, "RELAÇÃO DE MATERIAIS APLICADOS NA REDE A SER INCORPORADA",
         "Falta relação de materiais aplicados", "IT11", "3.4", "NEC", False, None, "NECESSÁRIO"),
    (16, "VIABILIDADE TÉCNICA",
         "Falta viabilidade técnica", "IT12", "4.1", "NEC", False, "Viabilidade técnica", "NECESSÁRIO"),
    # itens 17/18: pendências do catálogo (Planilha2) sem item correspondente — confirmar com o negócio
    (17, "DOCUMENTAÇÃO ANEXADA CORRESPONDE AO PROCESSO",
         "Documentação anexada não corresponde ao processo", "IT13", "4.2", "NEC", False, None, ""),
    (18, "NOTA COM ANEXOS",
         "Nota sem anexos", "IT14", "5.1", "NEC", False, None, ""),
]

GRUPOS = [
    "Projeto/As Built em CAD", "ART de Execução", "Notas Fiscais de Materiais",
    "Laudo de Ensaios de Equipamentos", "Notas Fiscais de Serviços",
    "Documentos Cliente (RG-CPF-CNPJ)", "Documento Terreno", "Viabilidade técnica",
    "Contrato de Obras", "TERMO DE DOAÇÃO", "Dados Bancários-Comprovante", "Licença Ambiental",
]


def seed(apps, schema_editor):
    Grupo = apps.get_model("checklist", "GrupoDocumento")
    Template = apps.get_model("checklist", "ChecklistTemplate")
    Item = apps.get_model("checklist", "ItemChecklist")

    grupos = {}
    for i, nome in enumerate(GRUPOS, start=1):
        grupos[nome] = Grupo.objects.create(nome=nome, ordem=i)

    tpl = Template.objects.create(
        codigo="POP.00813.EQTL - Anexo II", revisao="00",
        data_revisao="2024-01-16", vigente=True,
    )
    for (num, doc, pend, cod, hier, obrig, imped, grupo, obs) in ITENS:
        Item.objects.create(
            template=tpl, numero=num, documento_exigido=doc, texto_pendencia=pend,
            codigo_pendencia=cod or "", codigo_hierarquico=hier or "",
            obrigatoriedade=obrig, impeditivo_ligacao=imped,
            grupo_documento=grupos.get(grupo), observacao=obs,
        )


class Migration(migrations.Migration):
    dependencies = [("checklist", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
```

---

## Módulo 6 — Esteira de medidas e gerências

### F6.1 Funcionalidades

| ID | Funcionalidade |
|---|---|
| F6.1.1 | Timeline da nota: cada medida com gerência, data de entrada, saída, dias na medida, ciclo |
| F6.1.2 | Gráfico de barras: dias por gerência (identifica onde a nota ficou parada) |
| F6.1.3 | Indicar quando a nota **voltou** para a mesma gerência (`ciclo_gerencia > 1`) — retrabalho |
| F6.1.4 | **Painel de SLA por gerência**: tempo médio, mediana, p90 de permanência; nº de notas entrantes e saídas por mês |
| F6.1.5 | Ranking de medidas mais demoradas |
| F6.1.6 | Fila de **medidas não mapeadas** (`gerencia_responsavel = "NÃO MAPEADA"`) com botão "Mapear agora" que abre o formulário de DE-PARA (só Dev) |
| F6.1.7 | Matriz de transição: gerência de origem × gerência de destino (quem passa trabalho para quem) |
| F6.1.8 | Exportar esteira da nota em PDF (para anexar ao processo) |

### F6.2 Consultas de apoio

```python
# apps/incorporacao/metrics.py
from django.db.models import Avg, Count, F, Q, StdDev
from django.db.models.functions import TruncMonth

from apps.incorporacao.models import HistoricoMedida, Nota


def sla_por_gerencia(qs_notas):
    """Tempo médio de permanência por gerência (F6.1.4)."""
    return (
        HistoricoMedida.objects
        .filter(nota__in=qs_notas)
        .values("gerencia_responsavel")
        .annotate(
            notas=Count("nota", distinct=True),
            medidas=Count("id"),
            dias_medio=Avg("dias_na_medida"),
            dias_desvio=StdDev("dias_na_medida"),
            em_aberto=Count("id", filter=Q(is_medida_atual=True)),
        )
        .order_by("-dias_medio")
    )


def entrantes_por_mes(qs_notas):
    """Gráfico 'Entrantes × Mês × Ano'."""
    return (
        qs_notas.annotate(mes=TruncMonth("data_criacao"))
        .values("mes")
        .annotate(total=Count("id", distinct=True))
        .order_by("mes")
    )


def matriz_transicao(qs_notas):
    """F6.1.7 — de qual gerência para qual gerência."""
    return (
        HistoricoMedida.objects
        .filter(nota__in=qs_notas, saiu_da_gerencia=True)
        .exclude(proxima_gerencia="")
        .values("gerencia_responsavel", "proxima_gerencia")
        .annotate(total=Count("id"))
        .order_by("-total")
    )


def retrabalho(qs_notas):
    """Notas que voltaram para a mesma gerência (ciclo > 1)."""
    return (
        HistoricoMedida.objects
        .filter(nota__in=qs_notas, ciclo_gerencia__gt=1)
        .values("nota__nota", "gerencia_responsavel")
        .annotate(ciclos=Count("ciclo_gerencia", distinct=True))
        .filter(ciclos__gt=1)
        .order_by("-ciclos")
    )
```

---

## Módulo 7 — Administração e Desenvolvedor

| ID | Funcionalidade | Detalhe |
|---|---|---|
| F7.1 | CRUD de **DE-PARA medida → gerência → etapa** | Com histórico (`simple_history`). Ao salvar, dispara recálculo em lote das notas afetadas. |
| F7.2 | CRUD de status de fiscalização | Inclui a flag `considera_em_campo` |
| F7.3 | CRUD de distribuidoras, regionais, municípios, centros de trabalho | Importação por CSV |
| F7.4 | CRUD de parâmetros do sistema | Nenhum número de regra fica hardcoded |
| F7.5 | Gestão de usuários e perfis | Atribuir perfil, distribuidoras e regionais; desativar usuário |
| F7.6 | Monitor de ETL | Lista de `ExecucaoETL`, status, contagens, mensagem de erro; botão "Executar agora" por job |
| F7.7 | Trilha de auditoria | Consulta unificada de `Historical*`: modelo, objeto, campo, antes, depois, usuário, data |
| F7.8 | Relatório de downloads | Por documento, usuário, período, distribuidora; export CSV |
| F7.9 | Fila de não mapeados | Medidas/centros sem DE-PARA, ordenados por volume de notas |
| F7.10 | Health check | `/healthz` (banco, Redis, Celery, Snowflake, storage) |
| F7.11 | Impersonar usuário | `django-hijack`, para testar a visão de cada perfil (loga a ação) |
| F7.12 | Django Admin completo | `/admin/` restrito a `DEV` |

---
## Módulo 8 — Acompanhamento de Tratativas

> Porte do painel **"Tratativa das notas de incorporação"** (hoje página única em HTML+JS com banco documental) para dentro da Central, em Django + Postgres.
>
> **O que muda em relação ao original:** o banco documental (`bases` / `dias` / `tratativas` com blocos de 40 linhas) desaparece — era contorno de limite de documento. Aqui vira modelo relacional (`BaseDia` / `NotaDia` / `TratativaNota`), o parsing da planilha roda no **servidor** (Celery, não SheetJS no browser), e o "dono/admin" passa a ser o perfil **Desenvolvedor** + **Tático** (ver matriz abaixo). O resto da lógica — regra de status, comparação, agregações, drill-down, conferências — é mantido **idêntico**, porque é ela que dá o número.

### F8.1 Para que serve

Acompanhar, dia a dia, a carteira de notas IR exportada do SAP/Power BI:

1. Importar a **base do dia** (.xlsx/.xls/.csv) associada a uma data.
2. Mostrar a **foto da base de hoje** por Regional / Gerência / Carteira, em quantidade e em valor.
3. **Comparar** hoje contra uma **data de referência** e explicar o destino de cada nota: continuou ativa, mudou de grupo, finalizou, cancelou, saiu sem status, ou é nova.
4. **Drill-down**: qualquer número clicável abre a lista nota a nota já filtrada.
5. **Exportar** qualquer tabela para Excel.
6. Mostrar a **evolução de notas ativas por dia**.

> 💡 Este módulo é complementar ao Módulo 1 (Painel). O Painel mostra o **estado atual** vindo do ETL do Snowflake; o Acompanhamento de Tratativas mostra o **movimento entre duas fotos**, a partir de bases importadas manualmente. São duas perguntas diferentes: "como está" e "o que mudou".

### F8.2 Colunas aceitas na importação (`KEEP`)

Apenas estas colunas são extraídas, **nesta ordem**:

```
STATUS_DEMANDA, STATUS_CCS_NOTA_OC, NOTA, DATA_CRIACAO, STATUS_CCS, NOTA_PROJ,
REGIONAL, MUNICIPIO, MEDIDA_ATUAL, TEXTO_BREVE_GRUPO_CODIGO, Status_Prazo_medida,
FIM_PROGRAMADO_MEDIDA, NOME, CENTRO_TRABALHO, GERENCIA, CLIENTE_LIGADO,
STATUS_FISCALIZACAO, STATUS_SGO, CLASSIFICACAO_DEMANDA, status_rtp,
TEXTO_OBSERVACAO_MEDIDA_ANTERIOR, CARTEIRA_CLIENTE, VL_TOTAL_ORCAMENTO,
PEP, STATUS_USUARIO_PEP
```

Chave: `NOTA`. Usadas na lógica: `STATUS_CCS`, `STATUS_DEMANDA`, `REGIONAL`, `GERENCIA`, `CARTEIRA_CLIENTE`, `MEDIDA_ATUAL`, `MUNICIPIO`, `NOME`, `VL_TOTAL_ORCAMENTO`, `PEP`, `STATUS_USUARIO_PEP`.

> Todas essas colunas existem no modelo do PBIX — ver [§2.3](#23-colunas-da-tabela-fato-baseincorporacao). `STATUS_USUARIO_PEP` é a única que **não aparece** no `.pbix` analisado: confirmar origem (ver D13).

### F8.3 Modelo de dados

```python
# apps/tratativas/models.py
from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import Distribuidora, TimeStamped


class BaseDia(TimeStamped):
    """Uma foto da carteira, importada para uma data. Reimportar a mesma data substitui."""
    class FonteStatus(models.TextChoices):
        CCS = "ccs", "STATUS_CCS"
        DEMANDA = "demanda", "STATUS_DEMANDA"
        NENHUMA = "", "Base sem status (só ativas)"

    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="bases_dia")
    data = models.DateField(db_index=True)
    total = models.IntegerField(default=0)
    total_ativas = models.IntegerField(default=0)
    total_encerradas = models.IntegerField(default=0)
    tem_status = models.BooleanField(default=True)
    fonte_status = models.CharField(max_length=10, choices=FonteStatus.choices, blank=True)
    tem_valor = models.BooleanField(default=True, help_text="Base trouxe VL_TOTAL_ORCAMENTO.")
    tem_carteira = models.BooleanField(default=True, help_text="Base trouxe CARTEIRA_CLIENTE.")
    origem = models.CharField(max_length=120, blank=True, help_text="Nome do arquivo importado.")
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="bases_importadas"
    )
    aviso_caracteres = models.BooleanField(default=False)

    class Meta:
        ordering = ["-data"]
        verbose_name = "Base do dia"
        verbose_name_plural = "Bases do dia"
        constraints = [models.UniqueConstraint(fields=["distribuidora", "data"], name="uniq_base_dia")]

    def __str__(self):
        return f"{self.distribuidora.sigla} · {self.data:%d/%m/%Y} ({self.total_ativas} ativas)"


class NotaDia(models.Model):
    """Uma linha da planilha. PK lógica = (base, nota)."""
    base = models.ForeignKey(BaseDia, on_delete=models.CASCADE, related_name="notas")
    nota = models.CharField(max_length=20, db_index=True)
    ativa = models.BooleanField(db_index=True)
    motivo_encerramento = models.CharField(max_length=60, blank=True)

    # colunas KEEP
    status_demanda = models.CharField(max_length=60, blank=True)
    status_ccs_nota_oc = models.CharField(max_length=20, blank=True)
    data_criacao = models.DateField(null=True, blank=True)
    status_ccs = models.CharField(max_length=20, blank=True)
    nota_proj = models.CharField(max_length=20, blank=True)
    regional = models.CharField(max_length=60, blank=True, db_index=True)
    municipio = models.CharField(max_length=120, blank=True)
    medida_atual = models.CharField(max_length=20, blank=True)
    texto_breve_grupo_codigo = models.CharField(max_length=160, blank=True)
    status_prazo_medida = models.CharField(max_length=60, blank=True)
    fim_programado_medida = models.DateField(null=True, blank=True)
    nome = models.CharField(max_length=180, blank=True)
    centro_trabalho = models.CharField(max_length=20, blank=True)
    gerencia = models.CharField(max_length=60, blank=True, db_index=True)
    cliente_ligado = models.CharField(max_length=40, blank=True)
    status_fiscalizacao = models.CharField(max_length=160, blank=True)
    status_sgo = models.CharField(max_length=60, blank=True)
    classificacao_demanda = models.CharField(max_length=20, blank=True)
    status_rtp = models.CharField(max_length=20, blank=True)
    texto_observacao_medida_anterior = models.TextField(blank=True)
    carteira_cliente = models.CharField(max_length=80, blank=True, db_index=True)
    vl_total_orcamento = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    pep = models.CharField(max_length=40, blank=True)
    status_usuario_pep = models.CharField(max_length=60, blank=True)

    class Meta:
        verbose_name = "Nota da base"
        verbose_name_plural = "Notas da base"
        constraints = [models.UniqueConstraint(fields=["base", "nota"], name="uniq_nota_base")]
        indexes = [
            models.Index(fields=["base", "ativa"]),
            models.Index(fields=["nota"]),
            models.Index(fields=["base", "gerencia"]),
            models.Index(fields=["base", "regional"]),
            models.Index(fields=["base", "carteira_cliente"]),
        ]

    def grupo(self, dim: str) -> str:
        """gv(r, dim) do original: vazio vira '(vazio)'."""
        return (getattr(self, dim, "") or "").strip() or "(vazio)"

    def __str__(self):
        return f"{self.nota} @ {self.base.data:%d/%m/%Y}"


class TratativaNota(TimeStamped):
    """Marcação manual de 'já tratei esta nota'. Vive fora da base (persiste entre dias)."""
    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="tratativas_nota")
    nota = models.CharField(max_length=20, db_index=True)
    tratada = models.BooleanField(default=False)
    tratada_em = models.DateField(null=True, blank=True)
    tratado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="notas_tratadas"
    )
    observacao = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Tratativa (marcação)"
        verbose_name_plural = "Tratativas (marcações)"
        constraints = [models.UniqueConstraint(fields=["distribuidora", "nota"], name="uniq_tratativa_nota")]
```

> **Volumetria:** uma base diária de ~30 mil notas × 250 dias = 7,5 M linhas em `NotaDia`. Prever **particionamento por range de `data`** (via `base_id` ou coluna desnormalizada `data`) ou job de expurgo/arquivamento após N meses (parâmetro `TRATATIVAS_RETENCAO_DIAS`, default 400).

### F8.4 Importação (server-side)

UI: campo de data (default hoje) + distribuidora + botão **"Importar base do dia"** (aceita `.xlsx,.xls,.csv`). Visível só para perfis com permissão de escrita (ver F8.9).

Pipeline (task Celery, com progresso via polling):

| Passo | Regra |
|---|---|
| 1 | Ler **primeira aba** com `openpyxl` (`read_only=True`, `data_only=True`) ou `csv` conforme a extensão |
| 2 | **Achar cabeçalho**: nas 20 primeiras linhas, a primeira que contenha `NOTA` **e** `MEDIDA_ATUAL` (após normalizar). Se não achar → erro *"Não encontrei a linha de cabeçalho com NOTA e MEDIDA_ATUAL."* |
| 3 | **Normalizar cabeçalho** (`norm_head`): `strip`; se houver texto entre colchetes (`Tabela[NOTA]`, padrão de export do Power BI) usar só o conteúdo interno; comparar em maiúsculas com `KEEP` e devolver o nome canônico |
| 4 | Mapear índice de cada coluna de `KEEP` (**primeira ocorrência**). Coluna ausente → valor vazio |
| 5 | Por linha: `NOTA` numérica → `str(round(n))`; senão `fmt_cell`. Pular vazia ou **duplicada** (fica a primeira) |
| 6 | `fmt_cell` nas demais: `date/datetime` válido → `YYYY-MM-DD` (**somar 12 h antes de converter**, evita deslocamento de fuso); `dd/mm/aaaa…` → `aaaa-mm-dd`; `aaaa-mm-dd hh:mm` → só a data; `"123.0"` → `"123"`; remover caracteres de controle e surrogates órfãos; cortar em **300** chars |
| 7 | Nenhuma linha → erro *"A planilha não tem notas."* |
| 8 | **Detectar modo de status**: `ccs` se algum `STATUS_CCS` for exatamente `FINL`, `FNL` ou `CANC`; senão `demanda` se algum `STATUS_DEMANDA` estiver preenchido; senão `""` (base só com ativas → `tem_status = False`) |
| 9 | **Quem é ativa**: modo `demanda` → `STATUS_DEMANDA` contém `ATIV` (case-insensitive); modo `ccs` → `STATUS_CCS` vazio ou `ATIV`; modo `""` → todas |
| 10 | `motivo_encerramento`: `FINL`/`FNL` → `Finalizada`; `CANC` → `Cancelada`; outro → `Status X`; no modo `demanda` → o próprio `STATUS_DEMANDA` |
| 11 | Gravar em **transação**: `delete` da base da mesma `(distribuidora, data)` + `bulk_create` de `NotaDia` em lotes de 2.000 |
| 12 | Se algum lote falhar por caractere inválido, repetir com `hard_clean` (NFC + manter só `\x20-\x7e` e ` -ſ`) e marcar `aviso_caracteres = True` → mensagem *"Alguns caracteres especiais foram removidos."*; falhando de novo, erro informando o intervalo de linhas/notas |
| 13 | Toast: `Base de DD/MM/AAAA importada: N notas ativas, M encerradas.` |

```python
# apps/tratativas/parser.py
import re
import unicodedata
from datetime import date, datetime, timedelta

KEEP = [
    "STATUS_DEMANDA", "STATUS_CCS_NOTA_OC", "NOTA", "DATA_CRIACAO", "STATUS_CCS", "NOTA_PROJ",
    "REGIONAL", "MUNICIPIO", "MEDIDA_ATUAL", "TEXTO_BREVE_GRUPO_CODIGO", "Status_Prazo_medida",
    "FIM_PROGRAMADO_MEDIDA", "NOME", "CENTRO_TRABALHO", "GERENCIA", "CLIENTE_LIGADO",
    "STATUS_FISCALIZACAO", "STATUS_SGO", "CLASSIFICACAO_DEMANDA", "status_rtp",
    "TEXTO_OBSERVACAO_MEDIDA_ANTERIOR", "CARTEIRA_CLIENTE", "VL_TOTAL_ORCAMENTO",
    "PEP", "STATUS_USUARIO_PEP",
]
KEEP_UPPER = {k.upper(): k for k in KEEP}

RE_COLCHETE = re.compile(r"\[([^\]]+)\]")
RE_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]")
RE_DDMMYYYY = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")
RE_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})")
RE_NUM_PONTO_ZERO = re.compile(r"^(-?\d+)\.0+$")


def norm_head(v) -> str:
    """'Tabela[NOTA]' -> 'NOTA'; devolve o nome canônico de KEEP ou '' se não reconhecer."""
    s = str(v or "").strip()
    m = RE_COLCHETE.search(s)
    if m:
        s = m.group(1).strip()
    return KEEP_UPPER.get(s.upper(), "")


def fmt_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return (v + timedelta(hours=12)).date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (int, float)):
        s = str(v)
        m = RE_NUM_PONTO_ZERO.match(s)
        return m.group(1) if m else s
    s = str(v).strip()
    m = RE_DDMMYYYY.match(s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = RE_ISO.match(s)
    if m and len(s) > 10:
        return m.group(1)
    m = RE_NUM_PONTO_ZERO.match(s)
    if m:
        return m.group(1)
    s = RE_CTRL.sub("", s)
    return s[:300]


def hard_clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    return "".join(c for c in s if (" " <= c <= "~") or (" " <= c <= "ſ"))


def achar_cabecalho(linhas, limite=20):
    """Primeira das 20 primeiras linhas que tenha NOTA e MEDIDA_ATUAL."""
    for i, linha in enumerate(linhas[:limite]):
        nomes = {norm_head(c) for c in linha}
        if "NOTA" in nomes and "MEDIDA_ATUAL" in nomes:
            return i, [norm_head(c) for c in linha]
    raise ValueError("Não encontrei a linha de cabeçalho com NOTA e MEDIDA_ATUAL.")


def detectar_modo_status(registros) -> str:
    for r in registros:
        if (r.get("STATUS_CCS") or "").strip().upper() in {"FINL", "FNL", "CANC"}:
            return "ccs"
    for r in registros:
        if (r.get("STATUS_DEMANDA") or "").strip():
            return "demanda"
    return ""


def eh_ativa(r, modo: str) -> bool:
    if modo == "demanda":
        return "ATIV" in (r.get("STATUS_DEMANDA") or "").upper()
    if modo == "ccs":
        v = (r.get("STATUS_CCS") or "").strip().upper()
        return v == "" or v == "ATIV"
    return True


def motivo_encerramento(r, modo: str) -> str:
    if modo == "demanda":
        return (r.get("STATUS_DEMANDA") or "").strip()
    v = (r.get("STATUS_CCS") or "").strip().upper()
    if v.startswith(("FINL", "FNL")):
        return "Finalizada"
    if v.startswith("CANC"):
        return "Cancelada"
    return f"Status {v}" if v else ""
```

### F8.5 Regra de status e rótulos

```python
# apps/tratativas/logic.py
def st_ccs(status_ccs: str) -> str:
    """'fin' | 'canc' | 'ativa' | 'outro'"""
    v = (status_ccs or "").strip().upper()
    if v.startswith(("FINL", "FNL")):
        return "fin"
    if v.startswith("CANC"):
        return "canc"
    if v in ("", "ATIV"):
        return "ativa"
    return "outro"          # ex.: RECE
```

| Chave | Rótulo | Chip |
|---|---|---|
| `ativa` | Ativa | warn (amarelo) |
| `fin` | Finalizada | ok (verde) |
| `canc` | Cancelada | crit (vermelho) |
| `sem` | Saiu sem status | gray |
| `outro` | Outro status | gray |

Grupo vazio sempre exibido como `(vazio)`.

### F8.6 Cálculo da comparação (núcleo)

Entradas: `distribuidora`, `ref` (data escolhida em *Comparar com*, default = mais antiga), `hoje` (última base importada).

- `r_rows` = notas da base `ref` indexadas por `nota`; `h_rows` = idem para `hoje`
- `ref_ids` = notas **ativas** em `ref`; `h_set` = notas **ativas** em `hoje`

**Último visto:** para notas de `ref` que não estão em `h_set` **nem** em `h_rows`, percorrer as bases intermediárias de `hoje-1` até `ref+1` **de trás para frente** e guardar a linha mais recente em que a nota aparece → `last[n] = (linha, data)`.

Para cada nota **ativa na ref** (`n ∈ ref_ids`), com `o = r_rows[n]`:

| Caso | `d` (dados atuais) | `st` |
|---|---|---|
| `n ∈ h_set` | `h_rows[n]` ou `o` | `ativa` |
| está em `h_rows` mas não ativa | `h_rows[n]` | `st_ccs(d)`; se `ativa`/`outro` → **`sem`** |
| achada em `last` | `last[n].linha` (`visto` = data dela) | idem acima |
| sumiu de tudo | `o` (`visto` = `ref`) | `sem` |

Objeto resultante:
```python
{"n": nota, "ref": True, "novo": False, "o": o, "d": d, "st": st,
 "visto": visto, "in_hoje": nota in h_rows, "sh": sh, "ccs": d.status_ccs}
```
onde `sh` = status na base de hoje (`ativa` se em `h_set`, senão `st_ccs(h_rows[n])`, ou `""` se não está em hoje).

Para cada nota **da base de hoje que não estava ativa na ref**:
```python
{"n": nota, "ref": False, "novo": nota in h_set, "o": None,
 "d": h_rows[nota], "st": sh, "in_hoje": True, "sh": sh}
```
Só `novo=True` conta como **Nova**; as demais aparecem apenas na visão "base de hoje", com chip `fora de DD/MM`.

Também calcular: `serie` = para cada dia ≥ `ref`, `{data, v: total_ativas}`; `tem_val` = base de hoje tem `VL_TOTAL_ORCAMENTO`; `filtrada = not hoje.tem_status`; `sem_cart` = base de hoje sem `CARTEIRA_CLIENTE` → **copia a carteira da ref** e mostra aviso.

**Concorrência:** usar token de cálculo (ou cache key com `ref`+`hoje`); se o usuário trocar a referência durante o carregamento, descartar o resultado antigo. No Django, resolver com cache em Redis (`cache.set(f"trat:{dist}:{ref}:{hoje}", ...)`, TTL 10 min) e invalidação a cada importação.

### F8.7 Agregações

**F8.7.1 Base de hoje por grupo (`hoje_agg(dim)`)** — só notas com `in_hoje`. Por grupo: `t, ativa, fin, canc, outro` + os mesmos em valor (`v_*` = soma de `vl_total_orcamento`). Ordena por `t` desc. Coluna **% encerrado** = `(fin+canc)/t` (em valor, se modo valor).

**F8.7.2 Movimentação por grupo (`mov(dim)`)** — colunas `tinha, fica, foi, fin, canc, sem, veio, nova, hoje` + **Variação** (`hoje − tinha`; negativo em verde, positivo em vermelho).

```
Nota da ref → tinha++ no grupo de ORIGEM (o)
   ativa e mesmo grupo       → fica++ e hoje++ na origem
   ativa e grupo diferente   → foi++ na origem; veio++ e hoje++ no destino
   não ativa                 → fin/canc/sem ++ na origem
Nota nova    → nova++ e hoje++ no grupo de hoje
```

**Conferência** (exibir abaixo da tabela, em vermelho se falhar):
```
tinha = fica + foi + fin + canc + sem    ✓/✗
hoje  = fica + veio + nova               ✓/✗
```

**F8.7.3 Formatação de valor**
- `num(v)`: aceita número ou texto `R$ 1.234,56` / `1.234.567` → `Decimal`
- `brl(v)` = `R$ 1.234` (inteiro, pt-BR); `brl_c` compacto (`R$ 1,2 mi`, `R$ 350 mil`)
- No XLSX exportado, `1234,56` sai como **número**, não texto

### F8.8 Telas (uma página, de cima para baixo)

1. **Faixa da marca** — logo, eyebrow *"Incorporação de redes · força-tarefa"*, título *"Tratativa das notas de incorporação"*, subtítulo *"Base de hoje **DD/MM/AAAA** comparada com **DD/MM/AAAA**"*. À direita: seletor **Comparar com** (todas as datas disponíveis), link **Abrir no Power BI ↗**, e o importador (só quem tem permissão). Em telas ≥ 1640 px o link do Power BI vira cartão fixo lateral.
2. **Avisos** (amarelo) — base veio filtrada (só ativas) · base sem carteira · base sem valor.
3. **Base de hoje: todas as notas por {grupo}** — alternador Regional | Gerência | Carteira; alternador Quantidade | Valor (R$); **5 KPIs** (Total na base — destacado, Ativas, Finalizadas, Canceladas, Outro status), cada um com % e valor; tabela com linha TOTAL no topo e números clicáveis; botão Exportar Excel.
4. **Comparado com a referência de DD/MM/AAAA (N notas ativas)** — **6 KPIs**: Ativas hoje (destacado, *"eram X em DD/MM (+/−Y)"*), Finalizadas, Canceladas (com % das da ref), Saíram sem status, Mudaram de gerência (continuam ativas), Novas.
5. **Movimentação por {grupo}** — tabela F8.7.2, linha TOTAL, conferências, exportar.
6. **Caminho das notas por gerência** (só quando agrupamento = Gerência) — alternador **Cartões | Matriz**.
   - *Cartões* (grid auto-fill min 280 px), um por gerência:
     ```
       42  notas ativas em 01/11
     − 10  finalizadas (3 já estavam na gerência X)
     −  2  canceladas
     −  1  saiu sem status final (ex.: RECE)
     −  4  foram para a gerência Y (continuam ativas)
     =  25 continuam ativas na gerência Z
     +  3  chegaram da gerência W
     +  6  novas (não estavam em 01/11)
     =  34 ativas hoje · R$ 1.234.567
     ```
     Finalizadas em verde, canceladas em vermelho; linha final em vermelho se a conta não fechar; plural/singular correto.
   - *Matriz*: linhas = grupo na ref, colunas = grupo hoje (ou onde encerrou); diagonal com fundo cinza; cada célula com total + mini-etiquetas `N ativ / N fin / N canc / N s/st`; colunas Total e Valor; linha TOTAL.
7. **Validação nota a nota**
   - Alternador de colunas: **Visualização Relacionamento** | **Visualização Tático**
   - Filtros: busca livre (nota, município, cliente/NOME, regional, gerência, carteira, medida), Origem (grupo na ref), Destino (grupo hoje), Situação, Mudança de grupo (mudou / mesmo), **Limpar filtros**. Contador *"X de Y notas"*. Exportar Excel.
   - Situação: todas · Estavam na referência · Ativas hoje · Continuam ativas · Finalizadas · Canceladas · Saíram sem status · Novas; grupo *"Na base de hoje"*: Todas da base de hoje · Hoje: ativas / finalizadas / canceladas / outro status
   - Colunas **Relacionamento**: Nota · Regional · Carteira · Gerência ref→hoje · Medida ref→hoje · STATUS_CCS · Valor (R$) · Situação
   - Colunas **Tático**: Nota · Regional · Gerência ref→hoje · Medida ref→hoje · PEP · STATUS_USUARIO_PEP · Valor (R$) · Situação
   - Quando muda: `antigo → **novo**`; quando igual: só o valor
   - Chips na nota: `nova` (azul) · `fora de DD/MM` (cinza)
   - Ordenação: notas da ref primeiro, depois novas, depois outras; dentro, `canc → fin → sem → outro → ativa`; depois por número da nota
   - Coluna **Tratada** com checkbox → modal de confirmação → grava `TratativaNota` com data e usuário; linha tratada com fundo azul claro
8. **Notas ativas por dia** — gráfico de área/linha (altura 200), eixo Y em múltiplos de 40, rótulos `DD/MM`, tooltip *"DD/MM/AAAA · Notas ativas: N"*, redesenha no resize.
9. **Atalhos para a Central** (novo, não existia no original): em cada nota da lista, link para o **detalhe da nota** (Módulo 2), para o **checklist** (Módulo 5) e botão **baixar modelos da etapa** (Módulo 3). É isso que transforma o painel em ferramenta de trabalho e não só de leitura.

**Drill-down (regra global).** Todo número clicável carrega o filtro `{o, d, st, mud}`. Ao clicar: reseta filtros, aplica esse, redesenha a lista e rola suavemente até *Validação nota a nota*.

| Coluna | Filtro |
|---|---|
| tinha | `{o, st:'ref'}` |
| fica | `{o, d:o, st:'ativa', mud:'n'}` |
| foi | `{o, st:'ativa', mud:'s'}` |
| veio | `{d:o, st:'ativa', mud:'s'}` |
| nova | `{d:o, st:'novo'}` |
| hoje | `{d:o, st:'hoje'}` |
| fin / canc / sem | `{o, st:col}` |
| base de hoje | `{d, st:'h_'+col}` (`h_tot` para Total) |

Linha TOTAL usa grupo vazio (= todos). Trocar agrupamento ou referência zera os filtros.

### F8.9 Permissões do módulo

| Ação | Tático | Relacion. | Ativos | Cadastro | Dev |
|---|---|---|---|---|---|
| Ver o painel de tratativas | V | V | V | V | V |
| Trocar referência / agrupamento / filtros | V | V | V | V | V |
| Exportar Excel | V | V | V | V | V |
| **Importar base do dia** | **C** | — | — | — | **C** |
| Reimportar (substituir) uma data | **C** | — | — | — | **C** |
| Excluir uma base | — | — | — | — | **D** |
| Marcar nota como **tratada** | E | **E** | E | — | E |
| Desmarcar tratada de outro usuário | — | — | — | — | E |

> No original quem importava era "o dono/admin". Aqui: **Tático** (quem exporta a base do BI) e **Desenvolvedor**. As duas gerências de força-tarefa citadas no documento original — **Relacionamento** e **Tático** — são o público-alvo da tela; marcar tratada é liberado para as três gerências operacionais.

Toda base importada é sempre vinculada a uma distribuidora, e o usuário só vê bases das suas (mesma regra do resto do sistema, [§4.3](#43-multi-distribuidora-multi-tenant-leve)).

### F8.10 Exportações

| Arquivo | Conteúdo |
|---|---|
| `base-{hoje}-por-{dim}.xlsx` | Tabela da seção 3 |
| `movimentacao-{dim}-{ref}-a-{hoje}.xlsx` | Tabela da seção 5 |
| `notas-{ref}-a-{hoje}.xlsx` | Nota · Na referência · Regional ref/hoje · Carteira ref/hoje · Gerência ref/hoje · Medida ref/hoje · STATUS_CCS · STATUS_USUARIO_PEP · PEP · VL_TOTAL_ORCAMENTO · Situação |

Uma aba, largura de coluna automática (máx 40), autofiltro no cabeçalho, valores numéricos como número. Fallback quando o download não é permitido: modal *"Copiar tabela para o Excel"* com textarea em TSV e botão Copiar.

### F8.11 Casos de borda

| Situação | Comportamento |
|---|---|
| Nenhuma base | Estado vazio: *"Importe a primeira base pelo botão acima."* |
| Só uma base | `ref = hoje` (tudo "ficou", nada novo) |
| Base sem `VL_TOTAL_ORCAMENTO` | Esconder alternador de valor + aviso para reimportar |
| Base sem status (só ativas) | Aviso: notas que saíram ficam como *"saíram sem status"* |
| Base sem `CARTEIRA_CLIENTE` | Copia a carteira da ref + aviso |
| Mesma data reimportada | Substitui (delete + insert em transação) |
| `NOTA` numérica (`1.2345E+9`, `123.0`) | Normalizar para string inteira |
| Datas do Excel em serial/`datetime` | ISO sem deslocamento de fuso (+12 h antes de converter) |
| Cabeçalho `Tabela[COLUNA]` do Power BI | Tratado em `norm_head` |
| Importação muito grande | Task Celery com progresso; botão desabilitado com `Importando… i/n` |

### F8.12 Critérios de aceite

- [ ] Importar a mesma planilha duas vezes na mesma data **não duplica** nada
- [ ] Conferência da movimentação sempre ✓ (`tinha = fica+foi+fin+canc+sem` e `hoje = fica+veio+nova`)
- [ ] *Ativas hoje* do KPI de comparação = soma da coluna `hoje` = total dos cartões
- [ ] Clicar em qualquer número leva à lista com **exatamente** essa quantidade de notas
- [ ] Trocar referência / agrupamento recalcula tudo e zera filtros
- [ ] Busca encontra por nota, município, cliente, regional, gerência, carteira e medida
- [ ] Excel exportado abre com colunas certas, autofiltro e valores numéricos
- [ ] Usuário sem permissão não vê o importador e não consegue gravar
- [ ] Layout funciona em 375 px sem scroll horizontal da página
- [ ] Usuário de uma distribuidora não vê bases de outra

### F8.13 Ordem de implementação do módulo

```
1. Modelos + migrações (F8.3) e utilitários (fmt_d, pct, num, brl, brl_c, grupo, st_ccs)
2. Parser (F8.4) COM TESTES: cabeçalho com colchetes, duplicadas, datas, modos ccs/demanda/sem status
3. Task Celery de importação + UI do importador (progresso + toasts)
4. compute() (F8.6) COM TESTES cobrindo os 4 casos da tabela
5. Agregações hoje_agg, mov, cartões, matriz (F8.7) com testes das conferências
6. Telas na ordem de F8.8; depois o drill-down
7. Exportação Excel + fallback copiar
8. Gráfico, responsivo, acessibilidade, estados vazios/erro
9. Marcação de tratativa + atalhos para os outros módulos (F8.8 item 9)
```

### F8.14 Link externo (manter no cabeçalho)

```
Power BI — Gestão de Incorporação RD:
https://bi.equatorialenergia.com.br/reports/powerbi/EQTL%20PA%20-%20DISTRIBUIDORA/T%C3%81TICO%20DE%20PROJETOS/Gest%C3%A3o%20de%20Incorpora%C3%A7%C3%A3o%20RD?rs:Command=Render&rc:Toolbar=false
```

> Guardar como `ParametroSistema` (`LINK_POWERBI_GESTAO_IR`), **por distribuidora**, já que o caminho tem `EQTL PA - DISTRIBUIDORA` no meio. Campo novo em `Distribuidora`: `link_powerbi`.

---

## Identidade visual, login e navegação

### V1. Design tokens

> **Atualizado na v1.2.** A paleta oficial da Central passou a ser a da **referência visual do login**
> (azul-marinho profundo, azul royal, laranja e amarelo Equatorial). Ela é aplicada ao sistema inteiro
> via tokens em `static/css/app.css` (`:root`). A paleta antiga (`--accent:#00548a`, IBM Plex) foi substituída.

```css
/* static/css/app.css — :root (implementado) */
:root{
  /* Paleta da Central (referência visual do login) */
  --brand-navy-deep:#071c48;   /* fundo do login, base dos gradientes, fim do menu lateral */
  --brand-navy:#0a2463;        /* menu lateral, títulos de KPI, cabeçalho de tabela (texto) */
  --brand-blue:#1a4ea3;        /* links, barras de gráfico */
  --brand-blue-light:#2f6fd6;  /* brilho do gradiente, foco de input */
  --brand-blue-soft:#e8effc;   /* cabeçalho de tabela, avisos (notice/info) */
  --brand-orange:#f26a1b;      /* botão primário, borda superior dos KPIs, destaque "mais forte." */
  --brand-orange-dark:#d9550c; /* hover do botão primário, eyebrow */
  --brand-yellow:#f6c21c;      /* item ativo do menu, foco, sublinhado do título, molduras */

  /* superfícies e texto */
  --ink:#0f2147; --muted:#5d6b85; --line:#dfe5f0; --surface:#fff; --canvas:#f2f5fb;

  /* estados */
  --success:#24734b; --success-surface:#eaf5ee;
  --danger:#a63e38;  --danger-surface:#fbeeed;
}
```

Uso da paleta:

| Elemento | Cor |
|---|---|
| Menu lateral | gradiente `--brand-navy` → `--brand-navy-deep`, item ativo com barra `--brand-yellow` |
| Botão primário (todas as telas) | `--brand-orange`, hover `--brand-orange-dark` |
| KPIs (`.metric`) | borda superior 3 px `--brand-orange`, valor em `--brand-navy` |
| Tabelas | cabeçalho `--brand-blue-soft` com texto `--brand-navy` |
| Barras de gráfico | gradiente `--brand-blue` → `--brand-blue-light` |
| Foco de teclado | contorno amarelo `rgb(246 194 28 / 85%)` |
| Páginas de erro 403/404/500 | mesmo gradiente do login, cartão translúcido |

Fonte: `"Segoe UI", Arial, sans-serif` (padrão Windows corporativo, sem dependência de CDN).

Regras gerais:
- Container máx **1280 px**, gap 18 px, padding lateral 16 px; painéis brancos, borda 1 px `--line`, raio 8 px, padding 16 px
- **KPI**: eyebrow 11 px maiúsculo, valor 30 px mono tabular; KPI destacado com borda e fundo `--accent` / `--accent-soft`
- **Tabelas** 13 px, cabeçalho 11 px maiúsculo *sticky*, números à direita em mono; linha TOTAL com fundo `--line2` e borda inferior 2 px
- Números clicáveis: azul sublinhado discreto; zero em cinza, sem link
- Alternadores = grupo de botões segmentados com `aria-pressed`
- Responsivo: grids viram 1 coluna < 900 px; logo menor < 640 px; tabelas com scroll horizontal
- Acessibilidade: foco visível (outline 2 px accent), `Esc` fecha modais, respeitar `prefers-reduced-motion`
- Fontes IBM Plex via Google Fonts (ou auto-hospedadas em `static/fonts/` para ambiente sem internet)
- Assets em `static/img/`: `logo-equatorial-branco.svg`, `grafismo-flor.svg` (decorativo, opacidade .55)

### V2. Tela de login

**Rota implementada:** `/login/` (a especificação original previa `/entrar/`; `/` redireciona para o painel, que exige login)
**Nome exibido:** **Central de Soluções de Incorporação de Redes**
**Arquivos:** `templates/registration/login.html`, `static/css/app.css` (seção "Login"), `static/js/app.js`

#### V2.0 Layout implementado (v1.2) — referência visual aprovada

Tela única em tela cheia, fundo em gradiente azul-marinho com torre de transmissão e cabos em
traço (SVG inline, opacidade baixa), faixas diagonais laranja no canto inferior direito e molduras
amarelas em paralelogramo. **Sem a marca "Escola de Eletricistas"**: só o logo Grupo Equatorial.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  GRUPO equatorial (logo branco)              torre ╳╳╳        ╱▔▔▔╲ (amarelo)  │
│                                                                              │
│  Central de Soluções de                          ┌─────────────┐   ╱╱ laranja│
│  **Incorporação de Redes**                       │  mascote    │  ╱╱         │
│  ▬▬▬▬ (amarelo)                                  │  engenheiro │ ╱╱          │
│  ┌───────────────── cartão translúcido ─┐        │  com projeto│╱╱           │
│  │ 👤 Usuário                           │        │  e tablet   │             │
│  │ 🔒 Senha                         👁  │        └─────────────┘             │
│  │ [        Acessar  →        ] laranja │                                    │
│  └──────────────────────────────────────┘                                    │
│  ┃ Juntos por uma rede                                                       │
│  ┃ cada vez **mais forte.** (laranja)                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Mascote: `static/img/engenheiro-equatorial.png` (PNG transparente), ancorado no canto inferior direito.
- Abaixo de 1100 px o mascote fica translúcido; abaixo de 760 px é ocultado e o formulário ocupa a largura (margem 16 px).
- Mensagens (`Sessão encerrada.`, erros) aparecem acima/dentro do cartão, uma de cada vez.
- O login é enviado por `fetch` com trava (ver [§24](#24-padrões-de-envio-validação-e-concorrência)); sem JavaScript o formulário funciona por POST tradicional.

#### Layout original da v1.0 (substituído pelo V2.0 acima)

Layout em duas colunas (empilha abaixo de 900 px):

```
┌───────────────────────────────────┬─────────────────────────────────┐
│  [ faixa --band #003b5c ]         │                                 │
│                                   │        ENTRAR                   │
│  ⬡ logo Equatorial (branco)       │                                 │
│                                   │  Usuário de rede ou e-mail      │
│  INCORPORAÇÃO DE REDES            │  [___________________________]  │
│                                   │                                 │
│  Central de Soluções              │  Senha                          │
│  de Incorporação de Redes         │  [___________________] 👁        │
│                                   │                                 │
│  Painel, documentos modelo,       │  [ ] Manter-me conectado        │
│  orçamento RDU, checklist         │                                 │
│  documental e acompanhamento      │  [        Entrar        ]       │
│  das tratativas — as 7            │   (botão amarelo #f9b200)       │
│  distribuidoras em um só lugar.   │                                 │
│                                   │  ─────────  ou  ─────────       │
│  ✓ Painel corporativo             │                                 │
│  ✓ Documentos modelo              │  [ Entrar com conta Equatorial ]│
│  ✓ Orçamento RDU                  │        (SSO Azure AD)           │
│  ✓ Checklist POP.00813            │                                 │
│  ✓ Tratativas diárias             │  Esqueci minha senha            │
│                                   │                                 │
│  [grafismo flor, opacidade .55]   │  Problemas de acesso? Fale com  │
│                                   │  a equipe de Tático de Projetos.│
└───────────────────────────────────┴─────────────────────────────────┘
          Desenvolvido por Henry Matheus · v1.0
```

Requisitos:

| ID | Requisito |
|---|---|
| V2.1 | Campo único de identificação aceitando **usuário de rede** ou **e-mail** (`AUTHENTICATION_BACKENDS` resolve os dois) |
| V2.2 | Senha com botão mostrar/ocultar (ícone olho), `autocomplete="current-password"` |
| V2.3 | Checkbox **Manter-me conectado** → sessão de 14 dias; sem ele, expira ao fechar o navegador |
| V2.4 | Botão primário amarelo `--brand-yellow`, texto escuro, altura 44 px, largura total |
| V2.5 | Botão secundário **Entrar com conta Equatorial** (SSO Azure AD via `django-auth-adfs`); exibido só se o SSO estiver configurado |
| V2.6 | **Proteção contra força bruta** com `django-axes`: 5 tentativas → bloqueio de 30 min por usuário+IP, com mensagem clara e sem revelar se o usuário existe |
| V2.7 | Mensagem de erro genérica: *"Usuário ou senha incorretos."* — nunca dizer qual dos dois |
| V2.8 | Link **Esqueci minha senha** → fluxo padrão do Django por e-mail (ou, com SSO, texto orientando trocar pelo portal corporativo) |
| V2.9 | `next` preservado: quem tentou abrir uma URL protegida volta para ela após entrar |
| V2.10 | Primeiro acesso: se o usuário não tem `Perfil`, exibir tela *"Seu acesso ainda não foi liberado"* com orientação, em vez de erro 500 |
| V2.11 | Se o perfil tem mais de uma distribuidora e nenhuma padrão, após o login pedir **"Selecione a distribuidora"** (troca depois pelo header) |
| V2.12 | Rodapé: *Desenvolvido por Henry Matheus* + versão do sistema |
| V2.13 | Acessível: labels associados, foco visível, contraste AA, navegável por teclado, 375 px sem scroll horizontal |
| V2.14 | Sem autenticação, qualquer rota de módulo redireciona para `/entrar/?next=...`; a API devolve 401 JSON |
| V2.15 | Logout em `/sair/` (POST, com CSRF) → volta ao login com toast *"Sessão encerrada."* |

**Situação dos requisitos V2 (v1.2):**

| ID | Situação |
|---|---|
| V2.2, V2.7, V2.9, V2.13 | ✅ Implementados (`next` validado contra outros domínios; labels acessíveis ocultos visualmente) |
| V2.4 | 🔄 **Alterado**: botão primário agora é **laranja** `--brand-orange` com seta, conforme a referência visual |
| V2.6 | ✅ Implementado sem `django-axes`: contador em cache por usuário+IP, 5 falhas → 30 min (`LOGIN_MAX_TENTATIVAS`, `LOGIN_BLOQUEIO_SEGUNDOS`). Em produção com vários workers, usar cache Redis |
| V2.15 | ✅ Implementado em `/logout/` (POST + CSRF; GET → 405) com mensagem "Sessão encerrada." |
| V2.1, V2.3, V2.5, V2.8, V2.10, V2.11, V2.12, V2.14 | ⏳ Pendentes (e-mail como login, "manter conectado", SSO, esqueci a senha, primeiro acesso, seleção de distribuidora, rodapé de versão, API 401) |

```python
# apps/core/views_auth.py
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from apps.core.forms import LoginForm


class LoginView(auth_views.LoginView):
    template_name = "core/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nome_sistema"] = "Central de Soluções de Incorporação de Redes"
        ctx["sso_habilitado"] = bool(getattr(settings, "AZURE_AD_TENANT_ID", ""))
        ctx["versao"] = getattr(settings, "VERSAO_SISTEMA", "1.0")
        return ctx

    def form_valid(self, form):
        resp = super().form_valid(form)
        lembrar = form.cleaned_data.get("lembrar_me")
        self.request.session.set_expiry(60 * 60 * 24 * 14 if lembrar else 0)
        return resp

    def get_success_url(self):
        user = self.request.user
        perfil = getattr(user, "perfil", None)
        if perfil and not perfil.distribuidora_padrao and perfil.distribuidoras.count() > 1:
            return reverse_lazy("core:selecionar_distribuidora")
        return super().get_success_url() or reverse_lazy("painel:home")
```

```python
# apps/core/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário de rede ou e-mail",
        widget=forms.TextInput(attrs={
            "autofocus": True, "autocomplete": "username",
            "placeholder": "seu.usuario ou nome@equatorialenergia.com.br",
            "class": "input",
        }),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "input"}),
    )
    lembrar_me = forms.BooleanField(label="Manter-me conectado", required=False)

    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Este acesso está desativado. Fale com a equipe de Tático de Projetos.",
    }

    def clean_username(self):
        """Permite entrar com e-mail: resolve para o username antes de autenticar."""
        valor = (self.cleaned_data.get("username") or "").strip()
        if "@" in valor:
            u = User.objects.filter(email__iexact=valor).first()
            if u:
                return u.get_username()
        return valor
```

```python
# config/settings/base.py (recorte de autenticação)
LOGIN_URL = "/entrar/"
LOGIN_REDIRECT_URL = "/painel/"
LOGOUT_REDIRECT_URL = "/entrar/"
VERSAO_SISTEMA = "1.0"
NOME_SISTEMA = "Central de Soluções de Incorporação de Redes"

SESSION_COOKIE_AGE = 60 * 60 * 8          # 8 h sem "manter-me conectado"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5                    # 30 min
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS = True
```

### V3. Navegação (menu lateral)

```
Central de Soluções de Incorporação de Redes      [Distribuidora ▾] [🔔] [Henry ▾]
┌──────────────────────┐
│ 📊 Painel            │   todos
│ 📋 Carteira de notas │   todos
│ 🔁 Tratativas        │   todos (importar: Tático/Dev)
│ 📁 Documentos modelo │   todos
│ 🧮 Orçamento RDU     │   Tático cria · Ativos aprova
│ ✅ Checklist         │   Tático preenche · Relacionamento comunica
│ ⏱ Esteira e SLA      │   todos
│ ──────────────────── │
│ ⚙ Administração      │   só Desenvolvedor
│   · DE-PARA medidas  │
│   · Parâmetros       │
│   · Usuários         │
│   · Monitor de ETL   │
│   · Auditoria        │
│   · Downloads        │
└──────────────────────┘
```

O header mostra sempre: nome do sistema, **seletor de distribuidora ativa** (só as do perfil; "Todas" para Dev), notificações e o menu do usuário com o **perfil em chip** (`Tático`, `Relacionamento`, `Ativos`, `Cadastro`, `Desenvolvedor`).

---

## Consolidação dos sistemas das 7 distribuidoras

A Central é o destino final das soluções locais que hoje existem em cada distribuidora. Como cada uma resolveu o processo do seu jeito, a absorção precisa de método — não basta "subir o sistema e avisar".

### C1. Inventário (fazer antes da Sprint 2)

Para cada uma das 7 distribuidoras, levantar e registrar no sistema (modelo `SistemaLegado`, abaixo):

| Campo | Pergunta a responder |
|---|---|
| Nome da solução | Como chamam internamente |
| Tipo | Planilha compartilhada · Power BI · Access/VBA · app web próprio · Forms/SharePoint · nenhum |
| Dono | Quem mantém hoje |
| Processo coberto | Qual etapa (vistoria, orçamento, documentação, tratativa, restituição…) |
| Módulo equivalente na Central | 1 a 8 — ou **lacuna** (nada cobre ainda) |
| Dados a migrar | Volume, período, formato |
| Regras próprias | Cálculo, prazo ou nomenclatura que diverge do corporativo |
| Usuários | Quantos e de quais gerências |
| Data alvo de desligamento | Quando a solução local é descontinuada |

```python
# apps/core/models.py (adicionar)
class SistemaLegado(TimeStamped):
    """Inventário das soluções locais a serem absorvidas pela Central."""
    class Tipo(models.TextChoices):
        PLANILHA = "XLS", "Planilha compartilhada"
        POWERBI = "PBI", "Relatório Power BI"
        ACCESS = "ACC", "Access / VBA"
        WEB = "WEB", "Aplicação web própria"
        FORMS = "FRM", "Forms / SharePoint / Lista"
        NENHUM = "NEN", "Sem sistema (processo manual)"

    class Situacao(models.TextChoices):
        MAPEADO = "MAP", "Mapeado"
        EM_MIGRACAO = "MIG", "Em migração"
        COEXISTINDO = "COE", "Coexistindo (dupla escrita)"
        DESLIGADO = "OFF", "Desligado"

    distribuidora = models.ForeignKey(Distribuidora, on_delete=models.CASCADE, related_name="sistemas_legados")
    nome = models.CharField(max_length=160)
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    dono = models.CharField(max_length=160, blank=True)
    processo_coberto = models.CharField(max_length=200, blank=True)
    modulo_equivalente = models.CharField(
        max_length=60, blank=True,
        help_text="Painel, Carteira, Tratativas, Documentos, Orçamento, Checklist, Esteira, Admin — ou LACUNA.",
    )
    regras_divergentes = models.TextField(blank=True)
    qtd_usuarios = models.PositiveSmallIntegerField(default=0)
    volume_dados = models.CharField(max_length=120, blank=True)
    situacao = models.CharField(max_length=3, choices=Situacao.choices, default=Situacao.MAPEADO)
    data_alvo_desligamento = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["distribuidora", "nome"]
        verbose_name = "Sistema legado"
        verbose_name_plural = "Sistemas legados"
```

Tela correspondente em Administração: **Mapa de consolidação** — matriz `distribuidora × módulo` mostrando, por célula, se já usa a Central, se coexiste ou se ainda está no sistema local. É o painel de progresso da consolidação.

### C2. Estratégia por tipo de solução local

| Tipo encontrado | Como absorver |
|---|---|
| Planilha compartilhada | Virar **Documento Modelo** (se é formulário) ou **importador** (se é base). Nunca manter a planilha como fonte de verdade depois do go-live. |
| Relatório Power BI | Reproduzir como módulo (Painel / Tratativas). Manter o link do BI no header durante a coexistência. |
| Access / VBA | Exportar dados, mapear regras divergentes, reimplementar no módulo equivalente. É onde mais aparecem regras não documentadas — reservar tempo de descoberta. |
| App web próprio | Avaliar se vale integrar via API em vez de reescrever; se reescrever, migrar dados por script e congelar a escrita no legado. |
| Forms / SharePoint | Virar formulário nativo do módulo (checklist, tratativa). |
| Sem sistema | A Central é o primeiro — treinar com mais cuidado, sem comparativo. |

### C3. Regras locais × regra corporativa

Toda divergência encontrada vai para um dos três destinos, **registrado**:

1. **Parametrizar** — a diferença é um número ou uma data. Vai para `ParametroSistema`, com valor por distribuidora quando necessário (criar `ParametroDistribuidora` se houver mais de 3 casos).
2. **Modelar** — a diferença é estrutural (uma etapa que só existe em uma distribuidora). Vai para o DE-PARA, que já é por distribuidora.
3. **Padronizar** — a diferença é só histórica. Decisão formal do dono do processo, registrada em ata, e a distribuidora passa a usar a regra corporativa.

> Nunca resolver divergência com `if distribuidora == "X"` no código. Isso é o que torna o sistema insustentável a partir da terceira distribuidora.

### C4. Onboarding de cada distribuidora (checklist repetível)

```
[ ] 1. Inventário preenchido (C1) e validado com o dono local
[ ] 2. Distribuidora cadastrada: sigla, nome_catalogo, uf, schema_snowflake, link_powerbi
[ ] 3. Regionais e municípios importados
[ ] 4. Centros de trabalho cadastrados e amarrados à distribuidora
[ ] 5. DE-PARA medida → gerência → etapa revisado para a distribuidora (as 53 linhas valem? faltam medidas?)
[ ] 6. Catálogo de serviços importado (XLSX de preços da distribuidora)
[ ] 7. ETL de notas validado: contagem do sistema = contagem do BI na mesma data de corte
[ ] 8. ETL da esteira validado (schema Snowflake correto e com permissão de leitura)
[ ] 9. Checklist: o POP.00813 vale integralmente? Itens extras locais?
[ ] 10. Documentos modelo locais publicados no Módulo 3
[ ] 11. Usuários criados com perfil, distribuidora e regionais
[ ] 12. Primeira base de tratativas importada e conferida
[ ] 13. Treinamento por perfil (1 h cada) + guia rápido de 2 páginas
[ ] 14. Período de coexistência (2 a 4 semanas) com dupla conferência
[ ] 15. Aceite formal do dono local → situacao = DESLIGADO no sistema legado
```

### C5. Ordem de implantação sugerida

| Onda | Distribuidoras | Por quê |
|---|---|---|
| 1 | **PA** | Origem do BI e das planilhas; é onde os dados e as regras já estão prontos |
| 2 | **MA, PI** | Mesmo perfil operacional do PA, catálogo já carregado |
| 3 | **AL, AP** | Catálogo carregado; AL tem a exceção de preço (ver D5), AP é a menor (16 municípios) |
| 4 | **RS** | Catálogo carregado, mas estrutura regional própria (CEEE) |
| 5 | **GO** | Depende da carga do catálogo de serviços (ver D4) |

---
## Integração Snowflake (ETL)

### I.1 Princípio

O sistema **nunca consulta o Snowflake em tempo de request**. Um job replica as tabelas para o Postgres local; a aplicação só lê o Postgres. Isso garante tempo de resposta e permite enriquecer os dados (tratativas, checklist, orçamento) sem tocar na origem.

### I.2 Jobs

| Job | Origem | Frequência | Destino |
|---|---|---|---|
| `etl_notas_ir` | `EQTLINFO_RAW.SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO` | a cada 4 h (e manual) | `incorporacao.Nota` |
| `etl_historico_medidas` | SQL da esteira, **por distribuidora** (`{schema}.MEDIDAS_NOTAS_SERVICOS`, `{schema}.NOTAS_SERVICOS`, `{schema}.TAB_GRPCODES_MEDIDAS`, `SB_ATENDIMENTO.{schema_curto}.TAB_CENTRO_TRABALHO_GERENCIA`) | diário 02:00 | `incorporacao.HistoricoMedida` |
| `etl_municipios` | `TAB_CENTRO_TRABALHO_GERENCIA` + carga manual | mensal | `core.Municipio`, `core.Regional` |
| `recalcular_derivados` | local | após qualquer alteração de DE-PARA | atualiza `gerencia_responsavel`, `etapa` |

### I.3 Conector

```python
# apps/integracao/snowflake.py
import os
from contextlib import contextmanager

import snowflake.connector
from django.conf import settings


@contextmanager
def conexao_snowflake():
    cfg = settings.SNOWFLAKE
    conn = snowflake.connector.connect(
        account=cfg["ACCOUNT"],            # CFGKDTB-ISB76799
        user=cfg["USER"],
        password=cfg.get("PASSWORD") or None,
        private_key_file=cfg.get("PRIVATE_KEY_FILE") or None,   # preferir key-pair
        warehouse=cfg["WAREHOUSE"],        # WH_EQTLINFO
        database=cfg["DATABASE"],          # EQTLINFO_RAW
        role=cfg.get("ROLE"),
        client_session_keep_alive=False,
        login_timeout=30,
    )
    try:
        yield conn
    finally:
        conn.close()


def consultar(sql: str, params: dict | None = None):
    """Gera dicts; usa fetchmany para não estourar memória."""
    with conexao_snowflake() as conn:
        cur = conn.cursor(snowflake.connector.DictCursor)
        try:
            cur.execute(sql, params or {})
            while True:
                lote = cur.fetchmany(5000)
                if not lote:
                    break
                yield from lote
        finally:
            cur.close()
```

### I.4 Task de carga das notas

```python
# apps/integracao/tasks.py
from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.core.models import CentroTrabalho, Distribuidora, Municipio, Regional
from apps.incorporacao.models import Nota
from apps.integracao.models import ExecucaoETL, Medida, StatusFiscalizacao

SQL_NOTAS = "SELECT * FROM SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO"

# normalizações que o Power Query fazia
SUBST_GERENCIA = {
    "RELACIONAMENTO COM O CLIENTE": "RELACIONAMENTO",
    "RELACIONAMENTO ¿ APOIO": "RELACIONAMENTO",
    "EXPANSÃO DE REDE": "EXPANSÃO",
    "OPERAÇÃO SISTEMA": "OPERAÇÃO",
}
DEFAULTS = {
    "STATUS_FISCALIZACAO": "Fora SISCO",
    "STATUS_SGO": "Sem Nota Proj",
    "STATUS_SAP": "Projeto Não Elaborado",
    "CLIENTE_LIGADO": "NOTA NÃO MAPEADA",
    "GERENCIA": "Não Mapeado",
}
MAPA_ESTADO_SIGLA = {
    "PARÁ": "EQTL-PA", "PA": "EQTL-PA",
    "MARANHÃO": "EQTL-MA", "MA": "EQTL-MA",
    "PIAUÍ": "EQTL-PI", "PI": "EQTL-PI",
    "ALAGOAS": "EQTL-AL", "AL": "EQTL-AL",
    "AMAPÁ": "EQTL-AP", "AMAPA": "EQTL-AP", "AP": "EQTL-AP",
    "RIO GRANDE DO SUL": "EQTL-RS", "RIO.GRANDE.DO.SUL": "EQTL-RS", "RS": "EQTL-RS",
    "GOIÁS": "EQTL-GO", "GOIAS": "EQTL-GO", "GO": "EQTL-GO",
}


def _norm_gerencia(v):
    v = (v or "").strip()
    v = " ".join(v.split())
    return SUBST_GERENCIA.get(v.upper(), v) or DEFAULTS["GERENCIA"]


def _data(v):
    if not v:
        return None
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v[:10]).date()
        except ValueError:
            return None
    return getattr(v, "date", lambda: v)()


@shared_task(bind=True, max_retries=2)
def etl_notas_ir(self):
    from apps.integracao.snowflake import consultar

    log = ExecucaoETL.objects.create(job="notas_ir")
    agora = timezone.now()
    lidos = inseridos = atualizados = 0
    vistos = set()

    cache_dist = {d.sigla: d for d in Distribuidora.objects.all()}
    cache_centro = {c.codigo: c for c in CentroTrabalho.objects.all()}
    cache_medida = {m.codigo: m for m in Medida.objects.all()}
    cache_status = {s.status_sisco: s for s in StatusFiscalizacao.objects.all()}

    try:
        for row in consultar(SQL_NOTAS):
            lidos += 1
            num = (row.get("NOTA") or "").lstrip("0")
            if not num:
                continue
            estado = (row.get("ESTADO") or "").strip().upper()
            sigla = MAPA_ESTADO_SIGLA.get(estado)
            dist = cache_dist.get(sigla)
            if not dist:
                continue                     # distribuidora não cadastrada: ignora e loga
            chave = (dist.pk, num)
            if chave in vistos:              # Table.Distinct por NOTA
                continue
            vistos.add(chave)

            cod_centro = (row.get("CENTRO_TRABALHO") or "").strip()
            if cod_centro and cod_centro not in cache_centro:
                cache_centro[cod_centro] = CentroTrabalho.objects.create(codigo=cod_centro)

            cod_medida = (row.get("MEDIDA_ATUAL") or "").strip()
            if cod_medida and cod_medida not in cache_medida:
                cache_medida[cod_medida] = Medida.objects.create(
                    codigo=cod_medida, texto_breve=row.get("TEXTO_BREVE_GRUPO_CODIGO") or cod_medida
                )

            st_fisc = (row.get("STATUS_FISCALIZACAO") or DEFAULTS["STATUS_FISCALIZACAO"]).strip()

            municipio_txt = (row.get("MUNICIPIO") or "").strip()
            regional = Regional.objects.filter(
                distribuidora=dist, nome=(row.get("REGIONAL") or "").strip()
            ).first()
            municipio = Municipio.objects.filter(distribuidora=dist, nome=municipio_txt).first()

            defaults = dict(
                tipo_nota=row.get("TIPO_NOTA") or "IR",
                nota_proj=(row.get("NOTA_PROJ") or "").strip(),
                pep=row.get("PEP") or "",
                pep_i=row.get("PEP_I") or "",
                instalacao=row.get("INSTALACAO") or "",
                conta_contrato=row.get("CONTA_CONTRATO") or "",
                texto_breve=row.get("TEXTO_BREVE") or "",
                nota_oc_vinculada=row.get("NOTA_OC_VINCULADA") or "",
                estado=estado,
                regional=regional,
                area_estrut_regional=row.get("AREA_ESTRUT_REGIONAL") or "",
                municipio=municipio,
                municipio_txt=municipio_txt,
                bairro=row.get("BAIRRO") or "",
                perimetro=row.get("PERIMETRO") or "",
                endereco=row.get("ENDERECO") or "",
                latitude=row.get("LATITUDE") or "",
                longitude=row.get("LONGITUDE") or "",
                nome_cliente=row.get("NOME") or "",
                carteira_cliente=row.get("CARTEIRA_CLIENTE") or "",
                sli_solicitante=row.get("SLI_SOLICITANTE") or "",
                sli_desc_obra=row.get("SLI_DESC_OBRA") or "",
                medida_atual=cache_medida.get(cod_medida),
                codigo_medida_atual=row.get("CODIGO_MEDIDA_ATUAL") or cod_medida,
                texto_medida_atual=row.get("TEXTO_MEDIDA_ATUAL") or "",
                medida_anterior=row.get("MEDIDA_ANTERIOR") or "",
                codigo_medida_anterior=row.get("CODIGO_MEDIDA_ANTERIOR") or "",
                texto_medida_anterior=row.get("TEXTO_MEDIDA_ANTERIOR") or "",
                texto_observacao_medida_anterior=row.get("TEXTO_OBSERVACAO_MEDIDA_ANTERIOR") or "",
                grupo_codes=row.get("GRUPO_CODES") or "",
                codificacao=row.get("CODIFICACAO") or "",
                texto_breve_grupo_codigo=row.get("TEXTO_BREVE_GRUPO_CODIGO") or "",
                centro_trabalho=cache_centro.get(cod_centro),
                gerencia_sap=_norm_gerencia(row.get("GERENCIA")),
                status_ccs=(row.get("STATUS_CCS") or "ATIV").strip(),
                status_ccs_nota_oc=row.get("STATUS_CCS_NOTA_OC") or "",
                status_fiscalizacao=cache_status.get(st_fisc),
                status_sgo=row.get("STATUS_SGO") or DEFAULTS["STATUS_SGO"],
                status_sap=row.get("STATUS_SAP") or DEFAULTS["STATUS_SAP"],
                status_proj=row.get("STATUS_PROJ") or "",
                status_demanda_interna=row.get("STATUS_DEMANDA_INTERNA") or "",
                data_criacao=_data(row.get("DATA_CRIACAO")),
                data_alteracao=_data(row.get("DATA_ALTERACAO")),
                inicio_desejado=_data(row.get("INICIO_DESEJADO")),
                fim_desejado=_data(row.get("FIM_DESEJADO")),
                inicio_avaria=_data(row.get("INICIO_AVARIA")),
                inicio_avaria_nota_vinculada=_data(row.get("INICIO_AVARIA_NOTA_VINCULADA")),
                data_encerramento_nota=_data(row.get("DATA_ENCERRAMENTO_NOTA")),
                data_criacao_medida=_data(row.get("DATA_CRIACAO_MEDIDA")),
                data_conclusao_medida=_data(row.get("DATA_CONCLUSAO_MEDIDA")),
                inicio_programado_medida=_data(row.get("INICIO_PROGRAMADO_MEDIDA")),
                fim_programado_medida=_data(row.get("FIM_PROGRAMADO_MEDIDA")),
                data_agendamento=_data(row.get("DATA_AGENDAMENTO")),
                data_atribuicao_fiscal=_data(row.get("DATA_ATRIBUICAO_FISCAL")),
                data_da_fiscalizacao=_data(row.get("DATA_DA_FISCALIZACAO")),
                data_previsao_entrega=_data(row.get("DATA_PREVISAO_ENTREGA")),
                data_solicitacao=_data(row.get("DATA_SOLICITACAO")),
                data_devolucao=_data(row.get("DATA_DEVOLUCAO")),
                data_conclusao=_data(row.get("DATA_CONCLUSAO")),
                data_entrega_relatorio_campo=_data(row.get("DATA_ENTREGA_RELATORIO_CAMPO")),
                data_ligacao=_data(row.get("DATA_LIGACAO")),
                data_primeira_energizacao=_data(row.get("DATA_PRIMEIRA_ENERGIZACAO")),
                data_ultima_energizacao=_data(row.get("DATA_ULTIMA_ENERGIZACAO")),
                data_energizacao_nota_ir=_data(row.get("DATA_ENERGIZACAO_NOTA_IR")),
                data_ultima_nota_vinculada=_data(row.get("DATA_ULTIMA_NOTA_VINCULADA")),
                concluido_por=row.get("CONCLUIDO_POR") or "",
                duracao_dias=row.get("DURACAO_DIAS"),
                prazo_anexo_iv=row.get("PRAZO_ANEXOIV"),
                multa=row.get("MULTA"),
                vl_material_total=row.get("VL_MATERIAL_TOTAL"),
                vl_mo_total=row.get("VL_MO_TOTAL"),
                vl_total_orcamento=row.get("VL_TOTAL_ORCAMENTO"),
                qtd_notas_vinculadas=int(row.get("QTD_NOTAS_VINCULADAS") or 0),
                tipos_notas_vinculadas=row.get("TIPOS_NOTAS_VINCULADAS") or "",
                notas_vinculadas=row.get("NOTAS_VINCULADAS") or "",
                qtd_notas_vinculadas_ligadas=int(row.get("QTD_NOTAS_VINCULADAS_LIGADAS") or 0),
                qtd_notas_vinculadas_nao_ligadas=int(row.get("QTD_NOTAS_VINCULADAS_NAO_LIGADAS") or 0),
                notas_vinculadas_ligadas=row.get("NOTAS_VINCULADAS_LIGADAS") or "",
                tem_vinculada_ligada=row.get("TEM_VINCULADA_LIGADA") or "",
                cliente_ligado=row.get("CLIENTE_LIGADO") or DEFAULTS["CLIENTE_LIGADO"],
                cliente_ligado_nota_ir=row.get("CLIENTE_LIGADO_NOTA_IR") or "",
                qtd_clientes_ligados=int(row.get("QTD_CLIENTES_LIGADOS") or 0),
                sincronizado_em=agora,
            )

            with transaction.atomic():
                obj, criado = Nota.objects.update_or_create(
                    distribuidora=dist, nota=num, defaults=defaults
                )
                obj.recalcular_derivados(salvar=True)
            inseridos += int(criado)
            atualizados += int(not criado)

        log.status = ExecucaoETL.Status.SUCESSO
        log.registros_lidos = lidos
        log.registros_inseridos = inseridos
        log.registros_atualizados = atualizados
    except Exception as e:
        log.status = ExecucaoETL.Status.ERRO
        log.mensagem = f"{type(e).__name__}: {e}"
        raise self.retry(exc=e, countdown=300)
    finally:
        log.finalizado_em = timezone.now()
        log.save()
```

### I.5 ETL da esteira — SQL parametrizado por distribuidora

O SQL do PBIX está hardcoded em `EQTL_PA`. Parametrize:

```python
# apps/integracao/sql/historico_medidas.sql  (template)
WITH GRUPOS_MEDIDAS AS (
    SELECT GRUPO_CODIGO, TEXTO_BREVE_GRUPO_CODIGO
    FROM {schema}.TAB_GRPCODES_MEDIDAS
    WHERE CATALOGO = '2' AND CODIGO_IDIOMA = 'P'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY GRUPO_CODIGO ORDER BY DATA_DADOS DESC) = 1
),
HISTORICO_BASE AS (
    SELECT m.NOTA, m.MEDIDA, m.GRUPO_MEDIDA, m.CODIGO_MEDIDA,
           gm.TEXTO_BREVE_GRUPO_CODIGO,
           m.DATA_CRIACAO_MEDIDA,
           m.DATA_DADOS AS DATA_ATUALIZACAO_REGISTRO
    FROM {schema}.MEDIDAS_NOTAS_SERVICOS m
    LEFT JOIN GRUPOS_MEDIDAS gm ON gm.GRUPO_CODIGO = UPPER(TRIM(m.GRUPO_MEDIDA))
),
HISTORICO_SEQUENCIADO AS (
    SELECT hb.*,
           hb.DATA_CRIACAO_MEDIDA AS DATA_ENTRADA_MEDIDA,
           LEAD(hb.DATA_CRIACAO_MEDIDA) OVER (PARTITION BY hb.NOTA ORDER BY hb.DATA_CRIACAO_MEDIDA, hb.MEDIDA) AS DATA_SAIDA_MEDIDA,
           LEAD(hb.GRUPO_MEDIDA)        OVER (PARTITION BY hb.NOTA ORDER BY hb.DATA_CRIACAO_MEDIDA, hb.MEDIDA) AS PROXIMA_MEDIDA
    FROM HISTORICO_BASE hb
)
SELECT tab1.DATA_CRIACAO AS DATA_CRIACAO_NOTA,
       LTRIM(tab1.NOTA, '0') AS NOTA,
       tab1.TIPO_NOTA, tab1.STATUS_CCS, tab1.CENTRO_TRABALHO,
       ctg.GERENCIA AS GERENCIA_CENTRO_TRABALHO,
       hist.*,
       IFF(hist.DATA_SAIDA_MEDIDA IS NULL, TRUE, FALSE) AS IS_MEDIDA_ATUAL,
       DATEDIFF('DAY', hist.DATA_ENTRADA_MEDIDA,
                COALESCE(hist.DATA_SAIDA_MEDIDA, CURRENT_TIMESTAMP)) AS DIAS_NA_MEDIDA
FROM {schema}.NOTAS_SERVICOS tab1
INNER JOIN HISTORICO_SEQUENCIADO hist ON tab1.NOTA = hist.NOTA
LEFT JOIN SB_ATENDIMENTO.{schema_curto}.TAB_CENTRO_TRABALHO_GERENCIA ctg
       ON ctg.CENTRO_TRABALHO = tab1.CENTRO_TRABALHO
WHERE tab1.TIPO_NOTA = 'IR'
  AND COALESCE(tab1.STATUS_CCS, 'ATIV') <> 'RECE'
```

> **Mudança de arquitetura importante:** a classificação `GRUPO_MEDIDA → GERENCIA_RESPONSAVEL` sai do SQL e passa a vir do DE-PARA no banco (`MapeamentoMedidaGerencia`). Assim a regra vira editável pelo perfil Desenvolvedor, sem precisar alterar o Power Query nem o SQL. O cálculo de `GERENCIA_ANTERIOR`, `CICLO_GERENCIA` e `DATA_ENTRADA_GERENCIA` passa a ser feito em Python após a carga, já com a gerência resolvida.

### I.6 Agendamento

```python
# config/celery.py (recorte)
from celery.schedules import crontab

app.conf.beat_schedule = {
    "etl-notas-ir": {"task": "apps.integracao.tasks.etl_notas_ir", "schedule": crontab(minute=17, hour="*/4")},
    "etl-historico": {"task": "apps.integracao.tasks.etl_historico_medidas", "schedule": crontab(minute=23, hour=2)},
    "alertas-sla":   {"task": "apps.incorporacao.tasks.enviar_alertas_sla", "schedule": crontab(minute=12, hour=7)},
    "limpar-logs":   {"task": "apps.core.tasks.limpar_logs_antigos", "schedule": crontab(minute=40, hour=3, day_of_week=0)},
}
app.conf.timezone = "America/Sao_Paulo"
```

---

## API REST

Base: `/api/v1/`. Autenticação por sessão (front) e token (integrações). Throttling por usuário.

| Método | Endpoint | Descrição | Perfis |
|---|---|---|---|
| GET | `/notas/` | Lista paginada, todos os filtros do painel como query params | todos |
| GET | `/notas/{id}/` | Detalhe | todos |
| GET | `/notas/{id}/esteira/` | Histórico de medidas | todos |
| POST | `/notas/{id}/tratativas/` | Registra tratativa | gerência responsável |
| GET | `/painel/kpis/` | Os 12+6 cards com os filtros aplicados | todos |
| GET | `/painel/series/{grafico}/` | Dados de um gráfico (`gerencia`, `medidas`, `regional`, `distribuidora`, `prazo_ir`, `prazo_medida`, `entrantes`) | todos |
| GET | `/documentos/` | Lista de documentos modelo visíveis | todos |
| GET | `/documentos/{id}/download/` | Baixa a versão vigente (loga) | todos |
| POST | `/documentos/` | Publica documento | DEV |
| POST | `/documentos/{id}/versoes/` | Publica nova versão | DEV |
| GET | `/documentos/relatorio-downloads/` | Agregado de downloads | DEV |
| GET/POST | `/orcamentos/` | Lista / cria | Tático, DEV |
| PATCH | `/orcamentos/{id}/` | Edita cabeçalho | Tático, DEV |
| POST | `/orcamentos/{id}/itens/` | Adiciona item (resolve preço do catálogo) | Tático, DEV |
| POST | `/orcamentos/{id}/recalcular/` | Recalcula totais | Tático, DEV |
| POST | `/orcamentos/{id}/aprovar/` | Aprova | Ativos, DEV |
| GET | `/orcamentos/{id}/xlsx/` | Exporta no layout oficial | todos |
| GET | `/catalogo-servicos/` | Busca no catálogo (`?distribuidora=&regional=&q=`) | todos |
| GET/POST | `/checklists/` | Lista / abre checklist da nota | Tático, DEV |
| PATCH | `/checklists/{id}/respostas/{item}/` | Responde item | Tático, DEV |
| POST | `/checklists/{id}/gerar-pendencias/` | Devolve o texto consolidado | Tático, DEV |
| POST | `/checklists/{id}/comunicar/` | Registra comunicação ao cliente | Relacionamento, DEV |
| GET | `/tratativas/bases/` | Datas de base disponíveis por distribuidora | todos |
| POST | `/tratativas/bases/` | Importa base do dia (multipart) — retorna `task_id` | Tático, DEV |
| GET | `/tratativas/bases/{task_id}/progresso/` | Progresso da importação | Tático, DEV |
| DELETE | `/tratativas/bases/{data}/` | Exclui base | DEV |
| GET | `/tratativas/comparacao/?ref=&hoje=&dim=` | KPIs, `hoje_agg`, `mov`, cartões, matriz e série | todos |
| GET | `/tratativas/notas/?o=&d=&st=&mud=&q=` | Lista nota a nota (drill-down) | todos |
| PATCH | `/tratativas/notas/{nota}/tratada/` | Marca / desmarca tratada | Tático, Relacion., Ativos, DEV |
| GET | `/tratativas/export/{tipo}/` | XLSX (`base`, `movimentacao`, `notas`) | todos |
| GET | `/depara/medidas/` | DE-PARA vigente | todos |
| POST/PATCH/DELETE | `/depara/medidas/` | Mantém DE-PARA | DEV |
| POST | `/etl/{job}/executar/` | Dispara job | DEV |
| GET | `/etl/execucoes/` | Log de execuções | DEV |

Exemplo de serializer com as propriedades calculadas:

```python
# apps/api/serializers.py
from rest_framework import serializers
from apps.incorporacao.models import Nota


class NotaListSerializer(serializers.ModelSerializer):
    distribuidora = serializers.CharField(source="distribuidora.sigla", read_only=True)
    regional_nome = serializers.CharField(source="regional.nome", default="", read_only=True)
    municipio_nome = serializers.SerializerMethodField()
    status_fiscalizacao_macro = serializers.CharField(read_only=True)

    # regras DAX migradas
    dias_prazo = serializers.IntegerField(read_only=True)
    status_prazo = serializers.CharField(read_only=True)
    status_prazo_medida = serializers.CharField(read_only=True)
    ordem_status_prazo_medida = serializers.IntegerField(read_only=True)
    status_prazo_nota_ir = serializers.CharField(read_only=True)
    status_demanda = serializers.CharField(read_only=True)
    status_rtp = serializers.CharField(read_only=True)
    classificacao_demanda = serializers.CharField(read_only=True)
    flag_compulsoria = serializers.CharField(read_only=True)
    status_documentacao = serializers.CharField(read_only=True)

    class Meta:
        model = Nota
        fields = [
            "id", "nota", "nota_proj", "pep_i", "distribuidora", "regional_nome", "municipio_nome",
            "bairro", "endereco", "nome_cliente", "carteira_cliente", "sli_desc_obra",
            "codigo_medida_atual", "texto_breve_grupo_codigo", "gerencia_responsavel", "etapa",
            "status_ccs", "status_sgo", "status_fiscalizacao_macro", "data_criacao",
            "vl_total_orcamento", "qtd_clientes_ligados", "qtd_notas_vinculadas",
            "dias_prazo", "status_prazo", "status_prazo_medida", "ordem_status_prazo_medida",
            "status_prazo_nota_ir", "status_demanda", "status_rtp", "classificacao_demanda",
            "flag_compulsoria", "status_documentacao",
        ]

    def get_municipio_nome(self, obj):
        return obj.municipio.nome if obj.municipio else obj.municipio_txt
```

---

## Regras de negócio consolidadas

> **Histórico (v1).** As regras **vigentes** do sistema estão em
> [§23.4 Regras de negócio da gestão](#234-regras-de-negócio-da-gestão-decididas-em-14112026).
> Divergências desta tabela em relação à v2.0: **RN02** — "vence em breve" passou de 5 para **7 dias**;
> **RN12** — sem DE-PARA, a gerência vem da equivalência da GERENCIA do SQL e, depois, do nome do SQL (não mais
> "NÃO MAPEADA"); **RN17** — `STATUS_CCS = 'RECE'` **não** é descartado: conta como nota ativa, como no BI;
> **RN18–RN24** — regras do Orçamento RDU, módulo removido.

Checklist de aceite — cada regra precisa de teste automatizado.

| # | Regra | Fonte | Teste |
|---|---|---|---|
| RN01 | `data_prazo = data_criacao + SLA_NOTA_DIAS (90)` | DAX `Data_Prazo` | `test_data_prazo_90_dias` |
| RN02 | Faixas de prazo: `<0` Fora prazo · `=0` Vence Hoje · `≤5` Prestes a Vencer · senão No Prazo | DAX `Status_Prazo` | `test_faixas_prazo` |
| RN03 | `prazo_nota_vinculada = coalesce(inicio_avaria_nota_vinculada, inicio_avaria) + 30` | DAX | `test_prazo_nota_vinculada` |
| RN04 | `dias_prazo_medida = fim_programado_medida − coalesce(data_conclusao_medida, hoje)` | DAX | `test_prazo_medida` |
| RN05 | 6 status de prazo de medida, com ordem 1..6 | DAX | `test_status_prazo_medida_ordem` |
| RN06 | `prazo_nota_ir = fim_desejado` | DAX | `test_prazo_nota_ir` |
| RN07 | `status_demanda`: FINL→FINALIZADA(2), CANC→CANCELADA(3), senão ATIVA(1) | DAX | `test_status_demanda` |
| RN08 | `status_rtp`: criação > 01/12/2023 → RTP26 | DAX | `test_status_rtp` |
| RN09 | `classificacao_demanda`: criação > 01/01/2026 → GIRO, senão PASSIVO | DAX | `test_classificacao_demanda` |
| RN10 | `flag_compulsoria`: criação ≤ hoje − 5 anos → "Mais de 5 anos" | DAX | `test_flag_compulsoria` |
| RN11 | `chave_mapeamento = trim(medida)+"|"+trim(centro)` | DAX | `test_chave_mapeamento` |
| RN12 | Gerência/etapa vêm do DE-PARA; sem correspondência → "NÃO MAPEADA" | PBIX relacionamento | `test_depara_fallback` |
| RN13 | `status_documentacao` por `contains` em `texto_medida_anterior` | DAX | `test_status_documentacao` |
| RN14 | Deduplicação por `(distribuidora, nota)` na carga | Power Query `Table.Distinct` | `test_etl_dedup` |
| RN15 | Defaults de null na carga (Fora SISCO, Sem Nota Proj, etc.) | Power Query | `test_etl_defaults` |
| RN16 | Normalização de `GERENCIA` (4 substituições + trim/clean) | Power Query | `test_normaliza_gerencia` |
| RN17 | Só `TIPO_NOTA = 'IR'`; descartar `STATUS_CCS = 'RECE'` | SQL | `test_filtros_etl` |
| RN18 | `total_item = round(quantidade × preço, 2)` | XLSX `G14` | `test_total_item` |
| RN19 | Preço de mão de obra: `distribuidora + regional + nº serviço`; ALAGOAS sem regional | XLSX `F74` | `test_preco_catalogo` |
| RN20 | `total_obra = materiais + mão de obra + transporte` | XLSX `G92` | `test_total_obra` |
| RN21 | `total_proporcionalizado = total_obra − erc` | XLSX `G96` | `test_proporcionalizado` |
| RN22 | `erd = demanda_kw × constante_k` | XLSX `M94` | `test_erd` |
| RN23 | `participacao_cliente = max(0, proporcionalizado − erd)` | XLSX `G100` | `test_participacao` |
| RN24 | `custo_comprovado = nf_materiais + nf_serviços` | XLSX `M96` | `test_custo_comprovado` |
| RN25 | `erd_mais_erc = erd se erd ≥ total_obra, senão erd + erc` | XLSX `M100` | `test_erd_mais_erc` |
| RN26 | `a_restituir`: 0 sem demanda · `min(custo, orçamento)` se demanda < 50 · `min(custo, orçamento, erd+erc)` senão | XLSX `G102` | `test_a_restituir_3_casos` |
| RN27 | Regional derivada de `distribuidora + município` | XLSX `F9` | `test_regional_automatica` |
| RN28 | Pendências do checklist: só item com resposta NÃO entra; junção por `;` mantendo as 16 posições | XLSX `C4:C19`+`D20` | `test_texto_pendencias` |
| RN29 | Resumo de grupo: SIM→ok, NÃO→Falta, NÃO SE APLICA→N/A | XLSX `R25` | `test_resumo_grupos` |
| RN30 | Licenças ambientais são impeditivo de ligação | Checklist obs. item 12 | `test_impeditivo_ligacao` |
| RN31 | SLA de restituição = 90 dias | Checklist `D21` | `test_sla_restituicao` |
| RN32 | Usuário só vê notas das suas distribuidoras (e regionais, se houver) | Requisito | `test_isolamento_distribuidora` |
| RN33 | Usuário só edita nota cuja gerência = gerência do seu perfil; DEV edita tudo | Requisito | `test_edicao_por_gerencia` |
| RN34 | Toda publicação de documento gera versão nova; a anterior perde `vigente` | Requisito | `test_versionamento_documento` |
| RN35 | Todo download gera `DownloadLog` e incrementa contadores | Requisito | `test_log_download` |
| RN36 | Documento arquivado não aparece nem baixa para não-DEV | Requisito | `test_documento_arquivado` |
| RN37 | Alterar DE-PARA dispara recálculo das notas afetadas | Requisito | `test_recalculo_pos_depara` |
| RN38 | Cabeçalho da base é a primeira das 20 primeiras linhas com `NOTA` **e** `MEDIDA_ATUAL`; `Tabela[COLUNA]` é normalizado | Espec. tratativas §5 | `test_achar_cabecalho` |
| RN39 | `NOTA` duplicada na planilha: fica a **primeira**; `NOTA` numérica vira string inteira | Espec. tratativas §5 | `test_nota_duplicada_e_numerica` |
| RN40 | Datas da planilha: somar 12 h antes de converter, para não deslocar o fuso | Espec. tratativas §5 | `test_data_sem_deslocamento` |
| RN41 | Modo de status: `ccs` se houver FINL/FNL/CANC; senão `demanda` se houver STATUS_DEMANDA; senão vazio | Espec. tratativas §5 | `test_detectar_modo_status` |
| RN42 | Nota ativa: modo `demanda` contém ATIV · modo `ccs` vazio ou ATIV · modo vazio todas | Espec. tratativas §5 | `test_eh_ativa_3_modos` |
| RN43 | `st_ccs`: FINL/FNL→fin · CANC→canc · vazio/ATIV→ativa · resto→outro | Espec. tratativas §6 | `test_st_ccs` |
| RN44 | Nota da ref presente em hoje mas não ativa, com status `ativa`/`outro`, é classificada como **`sem`** | Espec. tratativas §7 | `test_classificacao_sem_status` |
| RN45 | "Último visto": varrer bases intermediárias de hoje−1 até ref+1, de trás para frente | Espec. tratativas §7 | `test_ultimo_visto` |
| RN46 | Conferência: `tinha = fica + foi + fin + canc + sem` | Espec. tratativas §8.2 | `test_conferencia_tinha` |
| RN47 | Conferência: `hoje = fica + veio + nova` | Espec. tratativas §8.2 | `test_conferencia_hoje` |
| RN48 | Só nota ativa hoje e ausente da ref conta como **Nova**; as demais recebem chip `fora de DD/MM` | Espec. tratativas §7 | `test_novas_vs_fora` |
| RN49 | Reimportar a mesma `(distribuidora, data)` substitui a base, sem duplicar | Espec. tratativas §4.2 | `test_reimportacao_substitui` |
| RN50 | Base sem `CARTEIRA_CLIENTE` copia a carteira da ref e exibe aviso | Espec. tratativas §7 | `test_fallback_carteira` |
| RN51 | Drill-down: o número clicado abre a lista com exatamente aquela quantidade | Espec. tratativas §9 | `test_drilldown_contagem` |
| RN52 | Login: e-mail ou usuário de rede autenticam; mensagem de erro não revela qual campo falhou | Requisito | `test_login_email_e_usuario` |
| RN53 | 5 tentativas falhas bloqueiam por 30 min (usuário + IP) | Requisito | `test_bloqueio_forca_bruta` |
| RN54 | Usuário sem `Perfil` vê tela de "acesso não liberado", não erro 500 | Requisito | `test_usuario_sem_perfil` |
| RN55 | "Manter-me conectado" = sessão de 14 dias; sem ele, expira ao fechar o navegador | Requisito | `test_sessao_lembrar_me` |

---

## Setup no VSCode — passo a passo

### S1. Pré-requisitos

```
Python 3.12+    ·    PostgreSQL 16    ·    Redis 7    ·    Git
VSCode + extensões: Python, Pylance, Django, Ruff, SQLTools, Docker
```

### S2. Criar o projeto

```bash
mkdir csir && cd csir   # Central de Soluções de Incorporação de Redes
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

python -m pip install --upgrade pip
```

`requirements/base.txt`:

```
Django==5.1.*
djangorestframework==3.15.*
django-filter==24.*
psycopg[binary]==3.2.*
python-decouple==3.8
dj-database-url==2.2.*
celery==5.4.*
redis==5.0.*
django-celery-beat==2.7.*
django-celery-results==2.5.*
snowflake-connector-python==3.12.*
openpyxl==3.1.*
XlsxWriter==3.2.*
pandas==2.2.*
python-dateutil==2.9.*
django-simple-history==3.7.*
django-storages[azure]==1.14.*
Pillow==10.*
WeasyPrint==62.*
django-widget-tweaks==1.5.*
django-htmx==1.19.*
whitenoise==6.7.*
gunicorn==23.*
django-axes==6.5.*
django-hijack==3.6.*
```

`requirements/dev.txt`:

```
-r base.txt
pytest==8.*
pytest-django==4.9.*
pytest-cov==5.*
factory-boy==3.3.*
ruff==0.6.*
django-debug-toolbar==4.4.*
django-extensions==3.2.*
ipython
```

```bash
pip install -r requirements/dev.txt
django-admin startproject config .
mkdir -p apps/{core,incorporacao,documentos,orcamento,checklist,tratativas,painel,integracao,api}
for a in core incorporacao documentos orcamento checklist tratativas painel integracao api; do
  python manage.py startapp $a apps/$a
done
```

> Em cada `apps/<app>/apps.py`, ajuste `name = "apps.<app>"`.

### S3. `.env`

```ini
DEBUG=True
SECRET_KEY=troque-isto
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgres://csir:csir@localhost:5432/csir
REDIS_URL=redis://localhost:6379/0

SNOWFLAKE_ACCOUNT=CFGKDTB-ISB76799
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_PRIVATE_KEY_FILE=
SNOWFLAKE_WAREHOUSE=WH_EQTLINFO
SNOWFLAKE_DATABASE=EQTLINFO_RAW
SNOWFLAKE_ROLE=

MEDIA_ROOT=./media
AZURE_ACCOUNT_NAME=
AZURE_CONTAINER=
```

### S4. `config/settings/base.py` — pontos essenciais

```python
from pathlib import Path
from decouple import Csv, config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "django.contrib.humanize",
    # terceiros
    "rest_framework", "django_filters", "simple_history", "django_htmx",
    "widget_tweaks", "django_celery_beat", "django_celery_results", "axes", "hijack",
    # internos
    "apps.core", "apps.integracao", "apps.incorporacao",
    "apps.documentos", "apps.orcamento", "apps.checklist",
    "apps.tratativas", "apps.painel", "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.core.middleware.DistribuidoraAtivaMiddleware",
    "axes.middleware.AxesMiddleware",
]

AUTH_USER_MODEL = "core.Usuario"
DATABASES = {"default": dj_database_url.parse(config("DATABASE_URL"))}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

DATA_UPLOAD_MAX_MEMORY_SIZE = 110 * 1024 * 1024   # documentos modelo até 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

SNOWFLAKE = {
    "ACCOUNT": config("SNOWFLAKE_ACCOUNT", default=""),
    "USER": config("SNOWFLAKE_USER", default=""),
    "PASSWORD": config("SNOWFLAKE_PASSWORD", default=""),
    "PRIVATE_KEY_FILE": config("SNOWFLAKE_PRIVATE_KEY_FILE", default=""),
    "WAREHOUSE": config("SNOWFLAKE_WAREHOUSE", default="WH_EQTLINFO"),
    "DATABASE": config("SNOWFLAKE_DATABASE", default="EQTLINFO_RAW"),
    "ROLE": config("SNOWFLAKE_ROLE", default=""),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

CELERY_BROKER_URL = config("REDIS_URL")
CELERY_RESULT_BACKEND = "django-db"
AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", "django.contrib.auth.backends.ModelBackend"]
```

### S5. `docker-compose.yml` (dev)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: csir
      POSTGRES_USER: csir
      POSTGRES_PASSWORD: csir
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes:
  pgdata:
```

### S6. Rodar

```bash
docker compose up -d
python manage.py makemigrations core integracao incorporacao documentos orcamento checklist tratativas
python manage.py migrate
python manage.py seed_inicial          # management command: distribuidoras, DE-PARA, status, parâmetros, checklist
python manage.py createsuperuser
python manage.py runserver

# em outros dois terminais
celery -A config worker -l info -P solo        # -P solo no Windows
celery -A config beat -l info
```

### S7. `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django runserver",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["runserver", "0.0.0.0:8000"],
      "django": true,
      "justMyCode": false
    },
    {
      "name": "Celery worker",
      "type": "debugpy",
      "request": "launch",
      "module": "celery",
      "args": ["-A", "config", "worker", "-l", "info", "-P", "solo"],
      "justMyCode": false
    },
    {
      "name": "Pytest",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "justMyCode": false
    }
  ]
}
```

### S8. `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["."],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": { "source.organizeImports": "explicit" }
  },
  "files.associations": { "**/templates/**/*.html": "django-html" },
  "emmet.includeLanguages": { "django-html": "html" }
}
```

### S9. Ordem de implementação dos arquivos

```
 1. apps/core/models.py           → Distribuidora, Regional, Municipio, CentroTrabalho, Usuario, Perfil, ParametroSistema
 2. apps/core/permissions.py      → is_dev, pode_editar_nota, mixins
 3. apps/core/middleware.py       → DistribuidoraAtivaMiddleware
 4. apps/integracao/models.py     → Medida, MapeamentoMedidaGerencia, StatusFiscalizacao, ExecucaoETL
 5. migrations de seed            → 7 distribuidoras, 53 linhas de DE-PARA, 7 status, 10 parâmetros
 6. apps/incorporacao/models.py   → Nota (+ properties), HistoricoMedida, Tratativa
 7. apps/integracao/snowflake.py  → conector
 8. apps/integracao/tasks.py      → etl_notas_ir, etl_historico_medidas
 9. apps/core/views_auth.py       → ⭐ tela de login "Central de Soluções de Incorporação de Redes"
10. static/css/tokens.css         → design tokens + templates/base.html com menu lateral
11. apps/documentos/*             → ⭐ módulo de Documentos Modelo + download + log
12. apps/checklist/*              → template, itens, respostas, seed POP.00813
13. apps/orcamento/*              → catálogo, motor de cálculo, importador, exportador XLSX
14. apps/tratativas/*             → parser, compute(), agregações, telas, drill-down, export
15. apps/painel/*                 → KPIs, séries, filtros
16. apps/api/*                    → routers DRF
17. templates/ + static/          → UI dos módulos
18. tests/                        → as 55 regras RN01..RN55
```

---

## Roadmap por sprints

| Sprint | Entrega | Critério de aceite |
|---|---|---|
| **0** — Fundação (1,5 sem) | Projeto, Docker, settings, `core`, perfis, **tela de login da Central**, design tokens, menu lateral, seletor de distribuidora, seed das 7 distribuidoras, inventário de sistemas legados | Login funciona com usuário de rede e e-mail; bloqueio após 5 tentativas; cada perfil vê só suas distribuidoras |
| **1** — ⭐ Documentos Modelo (1 sem) | Módulo completo com upload, versionamento, download, log, zip, relatório | Usuário baixa a planilha de orçamento e o checklist pelo sistema; Dev publica v2 e a v1 fica no histórico |
| **2** — Ingestão (2 sem) | `integracao` + `incorporacao`, ETL de notas, DE-PARA, recálculo | Carteira com todas as notas IR das 7 distribuidoras, gerência/etapa corretas |
| **3** — Painel (2 sem) | KPIs, gráficos, filtros, tabela detalhe, exportações | Números batem com o Power BI na mesma data de corte |
| **4** — Carteira operável (1,5 sem) | Detalhe da nota, tratativas, permissão por gerência, alertas de SLA | Analista de Relacionamento não consegue editar nota do Tático |
| **5** — Checklist (1,5 sem) | 16 itens, anexos, texto de pendência, aprovação, PDF de comunicação | Texto gerado é idêntico ao da planilha para o mesmo conjunto de respostas |
| **6** — Orçamento (2,5 sem) | Catálogo importado (117 mil linhas), motor de cálculo, exportação XLSX | Totais e `a_restituir` iguais à planilha em 10 casos de teste reais |
| **7** — Esteira e SLA (1,5 sem) | ETL do histórico, timeline, painel de SLA por gerência, matriz de transição | Tempo médio por gerência disponível e exportável |
| **8** — ⭐ Tratativas (2,5 sem) | Base diária, parser server-side, `compute()`, movimentação, cartões, matriz, validação nota a nota, drill-down, gráfico, exportações, marcação de tratada | As duas conferências fecham ✓; clicar em qualquer número abre a lista com a mesma contagem; reimportar a mesma data não duplica |
| **9** — Administração (1 sem) | CRUD de DE-PARA, parâmetros, monitor de ETL, auditoria, impersonar, **mapa de consolidação** | Dev altera DE-PARA e vê as notas se reclassificarem |
| **10** — Homologação PA (2 sem) | Testes das 55 RN, treinamento por perfil, coexistência com o BI, go-live no Pará | Aceite das 4 gerências do PA |
| **11+** — Consolidação (por onda) | Onboarding das demais distribuidoras conforme §16.C4/C5, carga de Goiás, desligamento dos sistemas locais | Checklist de 15 itens concluído por distribuidora |

**Total estimado até o go-live no Pará: ~19 semanas.** Cada onda de consolidação posterior: 2 a 3 semanas por distribuidora, em paralelo com a operação.

---

## Decisões pendentes / divergências encontradas

Pontos que precisam da sua decisão antes (ou durante) a implementação:

### D1. Divergência no DE-PARA de gerências 🔴 crítico

O SQL do `HistoricoGerencias` e a `Tabela_medidas_gerencia` classificam as mesmas medidas de forma **diferente**:

| Medida | SQL diz | Tabela DE-PARA diz |
|---|---|---|
| `CORESSPN` | ATIVOS | **FINANCEIRO** (centro ARFNCIFC) |
| `ASSDOANF` | ATIVOS | **RELACIONAMENTO** (centros RELAACCO/RELAARCO) |
| `ARQUPROC` | RELACIONAMENTO | **depende do centro**: RELACIONAMENTO, ATIVOS ou FINANCEIRO |
| `AGENPAGA`, `ATUAMONE`, `CONFPAGA`, `ANEAPRPG` | ATIVOS | **não existem** na tabela |

→ **Decisão necessária:** qual é a classificação correta? A proposta do sistema é usar **apenas** o DE-PARA do banco (chave `MEDIDA|CENTRO`), com a classificação por grupo como fallback. Precisa validar as 4 medidas ausentes.

### D2. Perfil Financeiro

A etapa/gerência **FINANCEIRO** existe no DE-PARA e tem KPI próprio (`pend_financ`), mas você listou 5 perfis sem Financeiro.

→ **Opções:** (a) criar o 6º perfil `FINANCEIRO`; (b) Ativos absorve as notas de Financeiro; (c) Financeiro fica só como visualização. **Recomendação: (a)** — o modelo já suporta, é só adicionar à enum `Perfil.Tipo`.

### D3. Etapas sem medida mapeada

A coluna calculada `ETAPA` no BI cobre só 4 medidas (`VERDOCIN`, `CATEBDGD`, `VISTOBRA`, `VISLEMAT`), mas os cards usam a `ETAPA` da `Tabela_medidas_gerencia`. Além disso, `CAPITALIZAÇÃO` tem medida (`total_etapa_capitalizacao`) mas **nenhuma linha** no DE-PARA.

→ **Decisão:** quais medidas pertencem à etapa CAPITALIZAÇÃO?

### D4. Catálogo de Goiás

O catálogo de serviços não tem Equatorial Goiás. → Precisa do arquivo de preços de GO, ou GO entra sem o módulo de orçamento na v1.

### D5. Exceção ALAGOAS no preço de mão de obra

A fórmula `F74` usa chave **sem regional** para Alagoas (`$C$1&$B74`), mas as linhas de Alagoas no catálogo têm regional preenchida (LESTE/OESTE) — a chave `JUNTAR` seria `ALAGOAS+LESTE+serviço`. Ou existem linhas de Alagoas sem regional, ou essa fórmula **nunca encontra** o preço.

→ **Decisão:** confirmar se o preço de Alagoas é único por distribuidora (ignora regional) ou se é por regional como nas outras.

### D6. Limites do template de orçamento

55 linhas de material, 10 de mão de obra e **1 de transporte**. → Isso atende os orçamentos reais? Se não, o template oficial precisa ser estendido antes do go-live.

### D7. Esteira de medidas fora do Pará

O SQL da esteira está em `EQTL_PA`. → Os schemas das outras 6 distribuidoras seguem o padrão `EQTLINFO_PRD.EQTL_<UF>`? Precisa confirmar nome e permissão de leitura para cada uma.

### D8. Itens 17 e 18 do checklist

`IT13` ("Documentação anexada não corresponde ao processo") e `IT14` ("Nota sem anexos") existem no catálogo de pendências mas não no checklist. → Entram como itens 17/18 (como propus no seed) ou são pendências avulsas, sem item?

### D9. Municípios das 7 distribuidoras

A `Tabela_regional` do BI tem só 49 municípios do Pará; a planilha de orçamento tem 776 municípios de 6 distribuidoras. → A fonte de verdade de município/regional passa a ser a planilha (importada), ou existe cadastro corporativo no Snowflake a usar?

### D10. Escrita de volta no SAP

O texto de pendência consolidado hoje é colado manualmente na medida do SAP. → Existe API/RFC disponível para gravar? Se sim, entra no roadmap como sprint 10. Se não, o sistema mantém o botão **Copiar** e o analista cola.

### D11. Armazenamento de arquivos

Documentos modelo + anexos de cliente vão crescer. → Azure Blob Storage (padrão Equatorial) ou disco do servidor? A config já prevê `django-storages[azure]`.

### D12. Retenção e LGPD

Os anexos contêm RG, CPF, CNPJ, dados bancários e procurações.

→ Requisitos a confirmar com Compliance: tempo de retenção, criptografia em repouso, mascaramento na listagem, trilha de acesso a anexo (não só a download de modelo), e quem pode baixar documento de cliente.

### D13. Coluna `STATUS_USUARIO_PEP`

A especificação do painel de tratativas usa `STATUS_USUARIO_PEP` (coluna da *Visualização Tático*), mas essa coluna **não existe** no modelo do `.pbix` analisado.

→ **Decisão:** de onde vem? É coluna de outra view do Snowflake, campo calculado no relatório, ou foi adicionada depois? Se for nova, precisa entrar no ETL e no modelo `Nota`.

### D14. Base diária × ETL do Snowflake

O Módulo 8 depende de **importação manual** de planilha; o Módulo 1 lê do **ETL**. Em teoria, dá para gerar a "base do dia" diretamente do ETL e dispensar a importação.

→ **Decisão:** manter os dois caminhos (importação manual como contingência e fonte de verdade histórica) ou, depois de estabilizar o ETL, gerar o snapshot automaticamente às 23:59 e deixar a importação só como exceção? **Recomendação:** começar com importação manual (replica o processo atual, não quebra o que funciona) e, a partir da sprint 10, gerar o snapshot automático em paralelo e comparar por 30 dias antes de trocar.

### D15. Retenção das bases diárias

~30 mil notas/dia × 250 dias úteis = 7,5 M linhas/ano em `NotaDia`, por distribuidora.

→ **Decisão:** quanto tempo de histórico é necessário? Proposta: 400 dias online (parâmetro `TRATATIVAS_RETENCAO_DIAS`) + particionamento por data; acima disso, manter só o resumo diário (`BaseDia`) e arquivar as linhas. Precisa confirmar se alguém compara contra bases de mais de um ano.

### D16. Inventário dos sistemas locais

A consolidação ([§16](#consolidação-dos-sistemas-das-7-distribuidoras)) depende de saber **o que existe hoje** em cada distribuidora. Nenhum dos arquivos analisados traz isso.

→ **Ação:** preencher o inventário C1 para as 7 distribuidoras antes da Sprint 2. Sem isso, a consolidação vira descoberta durante a implantação, que é o caminho mais caro.

---

## 23. Estado atual da implementação

> Retrato do código em **14/11/2026 (v2.0)**. Atualizar esta seção a cada entrega.

### 23.0 Escopo atual — sistema próprio de gestão (decisão de 14/11/2026, v2.0)

A v1.4 copiava o Power BI (Dashboard) e o artefato de tratativas (Tratativas). Eram dois produtos com bases,
filtros e vocabulário diferentes para a mesma nota. Na v2.0 o sistema foi **reestruturado como um produto
próprio**, organizado pelo que o usuário quer saber ou fazer, sobre **uma base única** de notas:

| Menu | Pergunta que responde | Conteúdo |
|---|---|---|
| **Visão geral** | "Como estamos hoje?" | 6 indicadores (carteira ativa, entrantes no mês, encerradas no mês, notas vencidas, medidas vencidas, vencem em 7 dias); entradas × encerramentos por dia (60 dias); carteira por estado; gerências com mais vencidas; medidas onde as notas ficam paradas; notas com maior atraso |
| **Análise** | "Onde está o volume?" | Tabela com detalhamento Estado › Regional › Gerência › Medida (ativas, % da carteira, entrantes, encerradas, saldo, vencidas, medidas vencidas, idade média, tempo na medida, valor), período de 7/30/90/365 dias; entrantes × encerradas **por dia ou por mês**; idade da carteira; matriz gerência × estado |
| **Prazos** | "O que está atrasado?" | Prazo da nota e prazo da medida (vencida / vence em até 7 dias / no prazo); **há quanto tempo** as notas estão vencidas (faixas de atraso); prazos por estado, regional, gerência ou medida; gargalos por medida; notas com maior atraso |
| **Notas** | "O que faço com esta nota?" | Lista com busca, filtros (dimensões, situação, prazo, atraso, idade, datas) e ordenação; exportação Excel; **ficha da nota** com prazos, dados em seções, linha do tempo e acompanhamento |
| **Documentos modelo** | "Onde está o modelo?" | Biblioteca com versões (checklists, planilha de orçamento etc.) para todo o grupo |
| Administração | — | DE-PARA, equivalências de gerência, sincronizações, usuários |

**Princípio de navegação:** todo número é um link para a lista das notas que o compõem, com os mesmos filtros.
Os testes garantem que a quantidade da lista é igual ao número clicado.

**Removidos na v2.0:** o Dashboard-réplica do BI (`apps/painel`, cards e gráficos copiados do `.pbix`) e as
Tratativas (`apps/tratativas`: comparação entre fotos, caminho por gerência, marcação de tratada, importação de
planilha). A pedido do usuário, a "atribuição/caminho" do artefato foi descartada. As fotos diárias que existiam
(12/11 e 14/11) foram migradas para o novo histórico. Backup do banco antes da mudança:
`scratchpad/db_antes_v2.sqlite3`. Carteira (Módulo 2 antigo) e Orçamento RDU (Módulo 4) continuam fora.
As seções dos módulos antigos nesta especificação ficam só como referência histórica.

Stack: **Django 5.2 + SQLite** (dev), templates no servidor, CSS próprio (`static/css/app.css`), ECharts 5.5.1
local (`static/vendor/echarts.min.js`), `static/js/app.js` (envio protegido e filtros com envio automático),
`static/js/graficos.js` e conector oficial `snowflake-connector-python`. Ainda **não** há PostgreSQL, Celery, DRF nem SSO.

### 23.1 Rotas

| Rota | View | Método | Quem acessa | O que faz |
|---|---|---|---|---|
| `/` | `gestao.visao_geral` | GET | todos (escopo por UF) | Visão geral |
| `/analise/` | `gestao.analise` | GET | todos | Análise (`nivel`, `periodo`, `grao`) |
| `/prazos/` | `gestao.prazos` | GET | todos | Prazos (`nivel`) |
| `/notas/` | `gestao.notas` | GET | todos | Lista de notas com filtros |
| `/notas/exportar/` | `gestao.exportar` | GET | todos | XLSX da lista filtrada (colunas calculadas + 85 da origem) |
| `/notas/<nota>/` | `gestao.nota` | GET | todos (404 fora do escopo) | Ficha da nota |
| `/notas/<nota>/acompanhamento/` | `gestao.acompanhar` | POST | todos (com escopo) | Novo registro de acompanhamento (idempotente) |
| `/login/` · `/logout/` | `core` | GET/POST · POST | — | Login (bloqueio por tentativas) · logout |
| `/documentos/…` | `documentos.*` | GET/POST | todos / Dev publica | Lista, publica versão, baixa |
| `/admin/` | Django Admin | — | staff | DE-PARA, equivalências, status SISCO, sincronizações, notas, acompanhamentos, usuários |

**Parâmetros de filtro (GET)** — comuns: `estado`, `regional`, `gerencia`, `medida`. Lista: `q`, `situacao`
(`ativa` padrão, `encerradas`, `finalizada`, `cancelada`, `todas`), `prazo_nota`, `prazo_medida`
(`vencida`, `a_vencer`, `no_prazo`, `sem_prazo`, `concluida`), `faixa_atraso`, `faixa_idade`, `criada_de/ate`,
`encerrada_de/ate`, `ordem` (`atraso`, `parada`, `idade`, `recentes`, `valor`). Valores fora da lista são ignorados.

### 23.2 Modelos

| App | Modelos |
|---|---|
| `core` | `Distribuidora`, `Regional`, `Municipio`, `CentroTrabalho`, `Usuario`, `Perfil`, `ParametroSistema`, `EnvioFormulario` |
| `incorporacao` | **`NotaIR`** — estado atual de cada nota (1 linha por NOTA): colunas tipadas (incl. `situacao`, `gerencia`, `origem_gerencia`, `etapa`, `data_encerramento`, `data_criacao_medida`, `medida_anterior`) + `dados` (JSON com as 85 colunas). **`NotaHistorico`** — foto diária (data, nota, estado, regional, gerência, medida, situação, fim programado da medida; única por data+nota). **`Acompanhamento`** — registros da equipe na ficha (ligados pelo número da nota, sobrevivem à substituição da carteira) |
| `integracao` | `DeParaMedidaGerencia` (53 linhas do BI), **`EquivalenciaGerencia`** (GERENCIA do SQL → nome do sistema), `StatusFiscalizacao` (7), `ExecucaoETL` |
| `gestao` | sem modelos: `indicadores.py` (regras e agregações), `ficha.py` (seções e linha do tempo), views e templates |
| `documentos` | `DocumentoModelo`, `RegistroDownload` |

### 23.3 Sincronização com o Snowflake

```
python manage.py sincronizar_snowflake            # lê o Snowflake (somente leitura) e grava a foto do dia
python manage.py sincronizar_snowflake --csv X    # contingência: carrega de um CSV exportado
python manage.py sincronizar_snowflake --data AAAA-MM-DD --sem-foto
```

1. Lê `SELECT * FROM SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO` com o conector oficial (conexão
   `CSIR_SNOWFLAKE_CONNECTION` do `~/.snowflake/connections.toml`; filtro que bloqueia qualquer comando de escrita).
2. Aplica o Power Query do BI (GERENCIA normalizada; nulos → `Fora SISCO`, `Sem Nota Proj`, `Projeto Não Elaborado`,
   `NOTA NÃO MAPEADA`) e deixa **uma linha por NOTA** (fica a primeira, como o `Table.Distinct` do BI).
3. Calcula a **situação** (FINL = finalizada, CANC = cancelada, demais = ativa) e **resolve a gerência** (§23.4.1).
4. Substitui a `NotaIR` numa transação (uma falha não apaga a base anterior) e registra `ExecucaoETL`.
5. Grava a foto do dia em `NotaHistorico` (substitui a mesma data). É ela que alimenta a linha do tempo da ficha.

Última execução real: **9.756 linhas lidas → 3.503 notas** (1.562 ativas, 1.353 finalizadas, 588 canceladas).

**Sobre MCP:** o servidor web **não** usa MCP. MCP é um protocolo para assistentes de IA chamarem ferramentas;
o sistema conecta pelo conector oficial, com usuário de serviço somente leitura em produção.

**Pendente para produção:** usuário de serviço somente leitura (hoje: conta pessoal com OAuth pelo navegador) e
agendamento diário do comando (Agendador de Tarefas do Windows / cron).

### 23.4 Regras de negócio da gestão (decididas em 14/11/2026)

#### 23.4.1 Gerência da nota

Ordem de prioridade (`apps/integracao/gerencia.py`):

1. **DE-PARA `MEDIDA|CENTRO_TRABALHO`** (tabela do BI) → gerência da etapa atual;
2. **GERENCIA do SQL traduzida pela tabela de equivalência** (decisão do usuário: "use a gerência");
3. GERENCIA do SQL como veio (ou "Não mapeada").

Equivalências iniciais, **medidas nas notas do Pará**, onde as duas fontes existem (100% de concordância em cada linha):

| GERENCIA do SQL | Gerência no sistema | Evidência no PA |
|---|---|---|
| RELACIONAMENTO | RELACIONAMENTO | 793 notas |
| RELACIONAMENTO CLIENTE | RELACIONAMENTO | 5 notas |
| CONTROLADORIA | ATIVOS | 507 notas |
| EXPANSÃO | TÁTICO | 207 notas |
| OPERAÇÃO | CADASTRO | 146 notas |
| ARRECADAÇÃO E FINANÇAS | FINANCEIRO | 17 notas |

Ficaram **sem equivalência** (aparecem com o nome do SQL) os nomes sem correspondência clara: OBRAS E MANUTENÇÃO
(AL, 212 ativas), NÃO ATRIBUÍDO (AP), JURÍDICO, RECUPERAÇÃO ENERGIA etc. Um administrador pode cadastrar a
equivalência no Admin. **Editar o DE-PARA ou as equivalências recalcula a carteira na hora** (sinal em `IntegracaoConfig.ready`).
Resultado: nenhuma nota com gerência em branco (antes eram 46%). Origem: 1.876 pelo DE-PARA, 1.335 por equivalência,
292 pelo nome do SQL. A origem aparece na ficha da nota.

#### 23.4.2 Prazos, idade e fluxo

| Conceito | Regra |
|---|---|
| Nota ativa | `STATUS_CCS` diferente de FINL e CANC |
| Prazo da nota | `FIM_DESEJADO` (decisão do usuário: "sim") |
| Prazo da medida | `FIM_PROGRAMADO_MEDIDA`; se há `DATA_CONCLUSAO_MEDIDA`, "Medida concluída" |
| Faixas de prazo | vencida (< hoje) · vence em até **7 dias** · no prazo · sem prazo (só notas ativas) |
| Faixas de atraso | até 30 d · 31–90 · 91–180 · 181 d–1 ano · 1–2 anos · mais de 2 anos |
| Idade | hoje − `DATA_CRIACAO`; faixas até 30 d … mais de 5 anos |
| Tempo na medida | hoje − `DATA_CRIACAO_MEDIDA` (mostra onde a nota está parada) |
| Entrante | nota com `DATA_CRIACAO` no dia/mês |
| Encerrada | nota finalizada/cancelada com `DATA_ENCERRAMENTO_NOTA` no dia/mês |
| Saldo | entrantes − encerradas (positivo: a carteira cresceu) |

Regras dependentes de "hoje" são recalculadas a cada acesso. **Retrato de 14/11/2026:** 90% das notas ativas já
passaram do fim desejado (1.408 de 1.562; atraso mediano de 488 dias) e 93% das medidas estão vencidas. Por isso a
tela de Prazos destaca as **faixas de atraso** e o **tempo na medida**, e não só a contagem de vencidas.

#### 23.4.3 Responsável

Basta a gerência (decisão do usuário). Não há atribuição de nota a pessoa.

### 23.5 Ficha da nota

- Cabeçalho: situação, estado · regional · município, gerência e a origem dela.
- 4 cartões: prazo da nota (dias de atraso), medida atual (prazo, descrição, há quanto tempo está aberta),
  idade, orçamento (nota PROJ e status SGO).
- Seções só com os campos preenchidos: Identificação, Medidas, Projeto e orçamento, Ligação e notas vinculadas,
  Fiscalização, Demanda interna, Cliente e local; e "Todos os campos da origem (85)".
- **Linha do tempo**: criação, abertura/conclusão da medida, encerramento e as **mudanças vistas no histórico
  diário** (mudou de medida, de gerência ou de situação).
- **Acompanhamento**: registros com autor e data (até 2.000 caracteres, idempotente, escopo por estado).

### 23.6 Qualidade

- Testes Django: **56** (`python manage.py test apps`): faixas de prazo/atraso/idade, resumo, agregação que fecha
  com o total, fluxo por dia e mês, lista (filtros e ordenação), matriz, páginas, escopo por estado (inclusive 404 na
  ficha), **número clicado = quantidade da lista**, filtros inválidos, linha do tempo, acompanhamento (idempotência,
  validação, escopo), exportação, sincronização (uma linha por nota, histórico, situação, ordem da gerência,
  recálculo ao editar equivalência), bloqueio de escrita no Snowflake, login e documentos.
- Testes JS: **15** (`node --test tests/js/app.test.js`). Lint: `ruff check .` e `ruff format`.
- Conferência visual (Playwright, 1500 px e 390 px): sem erros de JavaScript e sem rolagem horizontal no celular.
- Desempenho com a base real (3.503 notas): páginas de ~40 KB, ~0,2 s.
- Paleta dos gráficos validada para daltonismo (entrantes azul × encerradas laranja); prazo usa cores de status
  sempre com rótulo; faixas usam escala de um só tom.

### 23.7 Engenharia reversa do Power BI (14/11/2026)

Arquivo analisado (cópia, sem alterar o original): `Documentos\14. BI\Gestão de Incorporação RD - Corporativo.pbix`.
Fonte única `select * from SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO`; relações `STATUS_FISCALIZACAO →
Tabela_status_fisc` e `CHAVE_MAPEAMENTO (MEDIDA|CENTRO) → Tabela_medidas_gerencia`. Das regras do BI, o sistema
mantém: Power Query, uma linha por nota, DE-PARA e as funções de `apps/incorporacao/regras.py`. Os visuais do BI
não são mais reproduzidos.

### 23.8 Pontos de atenção (decisão do negócio)

| # | Ponto | Situação |
|---|---|---|
| A1 | Gerência em branco | **Resolvido** com equivalência + GERENCIA do SQL (§23.4.1). Pendente: decidir as equivalências de OBRAS E MANUTENÇÃO, NÃO ATRIBUÍDO, JURÍDICO e RECUPERAÇÃO ENERGIA |
| A2 | A `TB_NOTAS_IR_CORPORATIVO` repete notas (9.756 linhas / 3.503 notas); o sistema fica com a primeira linha | Ver Q1/Q2 de `docs/MAPEAMENTO_SNOWFLAKE.md` |
| A3 | `FIM_DESEJADO` vencido em 90% da carteira | Confirmar se o `FIM_DESEJADO` é atualizado na origem; se não, o prazo da nota mede o atraso desde o primeiro compromisso |
| A4 | Histórico diário só existe a partir de 12/11/2026 | A linha do tempo enriquece à medida que a sincronização roda todo dia: o agendamento é necessário |
| A5 | Goiás não existe nas fontes | D4 / Q14 |

Mapeamento completo da fonte em **`docs/MAPEAMENTO_SNOWFLAKE.md`** (linhagem das 85 colunas, cardinalidades,
problemas e decisões pendentes).

---

## 24. Padrões de envio, validação e concorrência

Padrão obrigatório para **toda** tela nova. Implementado na v1.2 (ver `CHECKLIST.md`).

### 24.1 Frontend — `static/js/app.js`

Carregado em `base.html` e no login. Usa delegação de eventos (listeners registrados uma única vez).

| Marcação no template | Comportamento |
|---|---|
| `<form method="post">` (qualquer) | Trava real: a flag `data-submitting` é verificada **dentro** do handler de `submit`, de modo que um segundo clique ou o Enter são ignorados. Antes de enviar, faz `trim` dos campos de texto (exceto senha e arquivo), valida e mostra o erro ao lado do campo (`.field-error`, `aria-invalid`), põe o foco no primeiro campo inválido, desabilita os botões e mostra spinner. O estado é restaurado ao voltar pelo histórico (`pageshow`). |
| `data-loading-text="Salvando…"` no botão | Texto exibido durante o envio (padrão: "Processando…"). |
| `data-confirm="…"` no form | `confirm()` antes de enviar (para operações destrutivas). |
| `data-confirm-when="campo"` | Só confirma se o checkbox `campo` estiver marcado. |
| `data-max-mb="50"` no input de arquivo | Recusa no cliente um arquivo acima do limite. |
| `data-no-trim` no input | Não normaliza o campo (usado na senha). |
| `<form data-async-login>` | Envio via `fetch` com `createActionGuard`: uma tentativa por vez, timeout de 30 s, mensagens para rede, timeout, 400, 403 (CSRF), 429 e 5xx, um único redirecionamento (`location.replace`) com a trava mantida até a navegação. |
| `<a data-download>` | Download via `fetch` + blob com trava por link e erro por status HTTP (401/403/404/409/422/5xx); detecta sessão expirada. |

API exposta (`window.CSIR`, também usada pelos testes): `createActionGuard`, `performLogin`,
`decideSubmit`, `normalizeFields`, `confirmMessage`, `httpErrorMessage`, `notify` (notificação sem duplicar), `init`.

### 24.2 Backend — idempotência (`apps/core/idempotencia.py`)

1. No template: `{% load seguranca %}` e `{% chave_envio %}` dentro do `<form>` (gera `idempotency_key` único a cada renderização).
2. Na view, **na mesma transação** da criação:

```python
try:
    with transaction.atomic():
        envio = registrar_envio(request)        # reserva a chave (UNIQUE no banco)
        v = Validador(request.POST)              # valida tudo
        ...; v.verificar()                       # ValidationError → rollback (a chave é liberada)
        obj = Modelo.objects.create(...)
        envio.concluir(reverse("app:detalhe", args=[obj.pk]))
except EnvioDuplicado as dup:                    # 2º clique, Enter+clique, reenvio
    messages.info(request, str(dup)); return redirect(dup.resultado_url or fallback)
except ChaveEnvioInvalida as exc:                # chave ausente ou adulterada
    messages.error(request, str(exc))
except ValidationError as exc:
    for m in exc.messages: messages.error(request, m)
```

Aplicado em (v2.0): registro de acompanhamento na ficha da nota e publicação de documento.

### 24.3 Backend — validação (`apps/core/validacao.py`)

`Validador` acumula erros por campo, com mensagens no formato `"Rótulo: problema."`, que nunca expõem detalhes internos:
`texto` (obrigatório, tamanho), `escolha` (choices), `objeto` (ID numérico dentro de um queryset já filtrado pelo
escopo do usuário), `decimal` (número finito, mínimo, `max_digits`/casas do modelo, aceita vírgula).
`id_numerico()` para parâmetros GET (filtros) — valores inválidos são ignorados, nunca geram 500.

### 24.4 Regras complementares

- Concorrência: `select_for_update` ao ler e alterar um registro que depende do estado (versão de documento, status do orçamento, base do dia); `UniqueConstraint` como última barreira; `IntegrityError` vira mensagem clara.
- Operações destrutivas exigem confirmação no backend (ex.: `substituir=1` na reimportação), não só no frontend.
- Download: abrir o arquivo **antes** de registrar o log; se o arquivo faltar, responder 404.
- Templates: não usar `{{ a|default:b.c }}` quando `b` pode ser nulo (gera 500); usar `{% firstof a b.c "—" %}`.
- Futura API REST: aceitar o cabeçalho `Idempotency-Key` com a mesma tabela `EnvioFormulario` e responder em JSON com 400/401/403/404/409/422/429.

---

## Anexos de referência rápida

### A1. Enumerações completas

```python
GERENCIAS = ["TÁTICO", "RELACIONAMENTO", "ATIVOS", "CADASTRO", "FINANCEIRO", "NÃO MAPEADA"]

ETAPAS = ["VISTORIA", "ORÇAMENTO", "DOCUMENTAÇÃO", "PEP", "TÁTICO", "RELACIONAMENTO",
          "CADASTRO", "BDGD", "ATIVOS", "FINANCEIRO", "CAPITALIZAÇÃO"]

STATUS_CCS = ["ATIV", "FINL", "CANC", "RECE"]   # RECE é descartado na carga

CENTROS_TRABALHO = {
    "EXPCPJCO": "EXPANSÃO", "EXPRBOSU": "EXPANSÃO", "EXPRBOCT": "EXPANSÃO",
    "EXPRBOND": "EXPANSÃO", "EXPRBONO": "EXPANSÃO", "EXPRBOOE": "EXPANSÃO",
    "RELAARCO": "RELACIONAMENTO", "RELAACCO": "RELACIONAMENTO", "ESTCACOC": "RELACIONAMENTO",
    "CONTGTAC": "CONTROLADORIA", "ARFNCIFC": "ARRECADAÇÃO E FINANÇAS",
    "OPSECGCO": "OPERAÇÃO",
}

MEDIDAS = [
    "VISLEMAT", "VISTOBRA", "ORCAFMTS", "ORCAFIMS", "VERDOCIN", "CRIPEPIR", "PENNAOIF",
    "COMPORCA", "VERIUNIV", "COPENDIN", "AGANOUNI", "ENCOPENT", "AGREPENC", "CONVPECL",
    "CORECOPN", "AGURECTM", "AGURECTI", "ENTEINPN", "ENTEINCD", "AGREPENO", "AGREGNVP",
    "CONRECTM", "ASSDOANF", "ARQUPROC", "CATEBDGD", "CONTUNIT", "CONTUNIO", "APRONOFI",
    "REVARESS", "ANREVLPN", "ELAORDPG", "CORESSPN",
    # citadas só no SQL, sem linha no DE-PARA — ver D1
    "ANEAPRPG", "AGENPAGA", "ATUAMONE", "CONFPAGA",
]

UNIDADES_SERVICO = ["UN", "M", "M2", "M3", "KM", "CDA", "VAO", "UA", "CJ", "H", "DIA"]
```

### A2. Comando de seed

```bash
python manage.py seed_inicial
```

Cria, em ordem:
1. 7 distribuidoras (com `nome_catalogo` e `schema_snowflake`)
2. Regionais e municípios (importados da aba `Distribuidoras` da planilha)
3. 12 centros de trabalho
4. 36 medidas
5. 53 linhas de DE-PARA medida → gerência → etapa
6. 7 status de fiscalização (com `considera_em_campo` nas 3 de campo)
7. 10 parâmetros do sistema
8. 12 grupos de documento + template POP.00813 Rev. 00 + 18 itens
9. Categorias de documento modelo + fichas dos 2 arquivos conhecidos
10. 5 grupos de permissão (um por perfil) com as `Permission` de cada módulo
11. Parâmetros do Módulo 8: `TRATATIVAS_RETENCAO_DIAS`, `LINK_POWERBI_GESTAO_IR` (por distribuidora)
12. Registros de `SistemaLegado` em branco, um por distribuidora, para o inventário C1

### A3. Fontes deste documento

| Arquivo analisado | O que forneceu |
|---|---|
| `Gestão de Incorporação RD - Corporativo.pbix` | 48 medidas DAX, 31 colunas calculadas, 2 relacionamentos, 6 queries M, 53 linhas de DE-PARA, 7 status de fiscalização, 49 municípios, 3 páginas de relatório, 49 colunas da tabela detalhe, 2 conexões Snowflake |
| `Orçamento NOME_DO_EMPREENDIMENTO_PEP 7.1.2.xlsx` | 4 abas, 20 fórmulas do formulário, 117.478 linhas de catálogo, 6 distribuidoras, 777 municípios, 9 regras de cálculo |
| `POP.00813.EQTL - 00 - Anexo II - Checklist ... 4.xlsx` | 16 itens, 3 respostas possíveis, 16 textos de pendência, 12 grupos de documento, 16 códigos de pendência, SLA de restituição |
| `ESPEC_painel_tratativa_notas_incorporacao.md` | Módulo 8 completo: 25 colunas `KEEP`, 12 passos do parser, regra `st_ccs`, algoritmo de comparação com 4 casos, 2 conferências, 9 seções de tela, mapa de drill-down, design tokens, 3 arquivos de exportação, 9 casos de borda, link do Power BI |
