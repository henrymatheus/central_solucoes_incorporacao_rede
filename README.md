# Central de Soluções de Incorporação de Redes

Sistema web (Django) para gerir as notas de incorporação de redes de todas as distribuidoras, a partir da
tabela `TB_NOTAS_IR_CORPORATIVO` do Snowflake. Organizado pelo que a equipe precisa saber ou fazer:

- **Visão geral**: carteira ativa, entrantes e encerradas, prazos vencidos e onde as notas estão paradas.
- **Análise**: volume e fluxo por estado › regional › gerência › medida; entrantes × encerradas por dia ou mês; idade da carteira.
- **Prazos**: prazo da nota (fim desejado) e da medida (fim programado), faixas de atraso e gargalos.
- **Notas**: lista com busca e filtros, exportação Excel e **ficha da nota** (dados, linha do tempo e acompanhamento).
- **Documentos modelo**: checklists, planilha de orçamento e outros modelos, com versões, para todo o grupo.

Todo número é um link para a lista das notas que o compõem.

## Requisitos

- Python 3.12 ou superior
- PowerShell no Windows
- Para sincronizar: acesso de leitura à `SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO` e o arquivo `~/.snowflake/connections.toml`

## Ambiente local

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_inicial
python manage.py createsuperuser
python manage.py sincronizar_snowflake   # carrega a carteira e grava a foto do dia (pode abrir o navegador para login)
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`.

## Sincronização com o Snowflake

```powershell
python manage.py sincronizar_snowflake                  # leitura (somente leitura) + foto do dia no histórico
python manage.py sincronizar_snowflake --csv base.csv   # contingência: carrega de um CSV exportado
python manage.py sincronizar_snowflake --sem-foto       # só atualiza a carteira, sem gravar histórico
```

- **Conexão:** usa o nome definido em `CSIR_SNOWFLAKE_CONNECTION`. Hoje é a conta pessoal com OAuth; para produção, peça à equipe de dados um usuário de serviço somente leitura.
- **Agendamento:** ainda não está configurado. Agende o comando uma vez por dia (Agendador de Tarefas do Windows).
- **Tratamento dos dados:** o sistema aplica os tratamentos do Power Query do BI, mantém uma linha por nota e resolve a gerência (DE-PARA → equivalência da GERENCIA do SQL → nome do SQL; editável no Admin). Detalhes em `docs/MAPEAMENTO_SNOWFLAKE.md` e na seção 23.4 da especificação.
- **Histórico:** cada sincronização grava a foto do dia de cada nota; é o que monta a linha do tempo da ficha. Rode todo dia.

## Funcionalidades

- **Login:** identidade visual da Central e bloqueio após 5 tentativas.
- **Acesso:** perfis (Tático, Relacionamento, Ativos, Cadastro, Financeiro, Desenvolvedor) e escopo por distribuidora (estado).
- **Regras de prazo:** nota ativa = STATUS_CCS diferente de FINL/CANC; vencida, vence em até 7 dias, no prazo; atraso em faixas (até 30 dias … mais de 2 anos); tempo na medida atual.
- **Ficha da nota:** prazos, medida atual e anterior, projeto e orçamento, vínculos, fiscalização, cliente e local, as 85 colunas da origem, linha do tempo (datas da origem + mudanças vistas no histórico) e registros de acompanhamento.
- **Exportação:** lista filtrada em Excel, com as colunas calculadas e as 85 da origem.
- **Documentos modelo:** versionamento, download autenticado e registro de downloads.
- **Proteção de envio:** formulários protegidos contra duplo clique e envio duplicado (`static/js/app.js`, `apps/core/idempotencia.py`). Detalhes em `CHECKLIST.md`.

## Testes

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test apps
.\.venv\Scripts\ruff.exe check .
node --test tests/js/app.test.js
```

A especificação (`ESPECIFICACAO_CENTRAL_SOLUCOES_INCORPORACAO_REDES.md`) é a referência viva do sistema. A seção 23 registra o estado atual da implementação.
