# CHECKLIST — Validação, concorrência de requisições e UX

Auditoria da Central de Soluções de Incorporação de Redes (Django 5.2, templates server-side, sem SPA).
Data da auditoria: 14/11/2026. Correções aplicadas e status atualizados em 14/11/2026.

**Contexto técnico relevante**

- Todos os formulários são `POST` tradicionais (navegação de página inteira), exceto onde indicado.
- Não existia nenhum JavaScript de controle de envio (`static/js/` inexistente).
- Não existe API REST, modal ou operação de exclusão na interface própria (só no Django Admin).
- O backend não tinha idempotência: cada `POST` repetido criava um novo registro.

> **Atualização de 14/11/2026 (v1.4):** os módulos **Carteira de notas** (§3) e **Orçamento RDU** (§5) foram removidos do
> sistema por decisão do usuário. Os itens dessas seções ficam como histórico. O mesmo padrão de proteção (`app.js`,
> `chave_envio`, `Validador`, `data-confirm`) foi aplicado nas telas novas: importação de base, marcação de tratada e
> exclusão de base das Tratativas, além do Dashboard, que só tem filtros GET.
>
> **Atualização de 14/11/2026 (v2.0):** o Dashboard (§7) e as Tratativas (§6) também foram removidos; os itens
> dessas seções ficam como histórico. O sistema passou a ter Visão geral, Análise, Prazos, Notas e ficha da nota.
> As novas telas só têm filtros GET (valores fora da lista são ignorados; busca limitada a 40 caracteres
> alfanuméricos). O único formulário novo, **registro de acompanhamento na ficha**, segue o mesmo padrão:
> `chave_envio` + `registrar_envio` em `transaction.atomic` (duplo clique = 1 registro), `Validador` (obrigatório,
> até 2.000 caracteres), `data-loading-text` no botão e escopo por estado (404 fora do escopo). Coberto por
> `apps/gestao/tests.py::test_acompanhamento_idempotente_e_validado`.

Legenda de status: **Pendente** · **Corrigido** · **Sem alteração necessária** · **Não aplicável** · **Não corrigido (justificado)**

---

## 1. Login e autenticação

- [x] Login aceita múltiplos envios simultâneos
  - Local: templates/registration/login.html
  - Tipo: múltiplos cliques
  - Problema identificado: nada impede vários cliques em "Acessar"; cada clique gera um `POST /login/`.
  - Risco: várias autenticações concorrentes, rotação repetida de sessão, contagem errada de tentativas falhas.
  - Correção proposta: enviar o login por `fetch` com trava real (`createActionGuard`) que ignora novas chamadas enquanto há uma ativa.
  - Status: Corrigido — `data-async-login` + `createActionGuard` (static/js/app.js). Teste JS: dois cliques → 1 requisição.

- [x] Enter + clique simultâneos disparam duas autenticações
  - Local: templates/registration/login.html
  - Tipo: múltiplos cliques
  - Problema identificado: Enter e clique geram dois eventos `submit` independentes.
  - Risco: chamadas de autenticação duplicadas.
  - Correção proposta: a mesma trava atende os dois caminhos, porque ambos passam pelo evento `submit`.
  - Status: Corrigido — ambos passam pelo mesmo `submit` e pela mesma trava. Teste JS dedicado.

- [x] Botão sem estado de carregamento e sem desabilitar
  - Local: templates/registration/login.html, static/css/app.css
  - Tipo: UX
  - Problema identificado: não há feedback visual de processamento.
  - Risco: o usuário clica de novo achando que nada aconteceu.
  - Correção proposta: desabilitar o botão, aplicar `aria-busy`, mostrar spinner e o texto "Entrando…".
  - Status: Corrigido — botão desabilitado, `aria-busy`, spinner e texto "Entrando…".

- [x] Estado de carregamento não é restaurado após erro, ou é restaurado cedo demais no sucesso
  - Local: static/js/app.js (novo)
  - Tipo: UX
  - Problema identificado: não havia controle de estado.
  - Risco: botão travado após erro, ou liberado durante o redirecionamento (permitindo novo envio).
  - Correção proposta: `try/finally` restaura o estado em erro; no sucesso a trava é mantida até a navegação.
  - Status: Corrigido — `finally` restaura em erro; `keepLocked()` mantém a trava no sucesso. Testes JS de erro, rede, timeout e sucesso.

- [x] Sem tratamento de timeout, erro de rede ou resposta inesperada
  - Local: templates/registration/login.html
  - Tipo: tratamento de erro
  - Problema identificado: falha de rede deixa o usuário na página de erro do navegador; "parar carregamento" deixa a tela sem feedback.
  - Risco: tela travada e sem orientação.
  - Correção proposta: `fetch` com `AbortController` (limite de 30 s de requisição) e mensagens específicas para rede, timeout, 403 (CSRF expirado), 429 (bloqueio) e 5xx.
  - Status: Corrigido — timeout de 30 s via AbortController; mensagens para rede, timeout, 403, 429 e 5xx.

- [x] Mensagem de erro fixa ignora o motivo real
  - Local: templates/registration/login.html, apps/core/forms.py
  - Tipo: UX
  - Problema identificado: qualquer erro mostra "Usuário ou senha inválidos", inclusive conta inativa ou campo vazio.
  - Risco: orientação incorreta. Especificação V2.7 pede "Usuário ou senha incorretos.".
  - Correção proposta: exibir uma única mensagem vinda do servidor, com textos padronizados (V2.7) e mensagem própria para bloqueio.
  - Status: Corrigido — mensagem única vinda do servidor (`primeira_mensagem_erro`), textos V2.7 e mensagem de bloqueio.

- [x] Validação de obrigatórios só pelo balão nativo do navegador
  - Local: templates/registration/login.html
  - Tipo: validação
  - Problema identificado: a mensagem nativa some e não fica próxima ao campo de forma persistente.
  - Risco: baixa clareza e acessibilidade.
  - Correção proposta: validação antes do envio, com mensagem abaixo do campo (`aria-invalid` e `aria-describedby`).
  - Status: Corrigido — validação antes do envio com `.field-error` ao lado do campo.

- [x] Espaços desnecessários no usuário
  - Local: apps/core/forms.py, static/js/app.js
  - Tipo: validação
  - Problema identificado: o backend já remove espaços (`UsernameField` usa `strip=True`); o frontend não normaliza.
  - Risco: baixo. Um usuário digitado só com espaços passava pela validação nativa.
  - Correção proposta: `trim` no frontend antes da validação; a senha nunca é alterada.
  - Status: Corrigido — `trim` no frontend (senha preservada com `data-no-trim`); backend já fazia strip. Teste: `test_login_remove_espacos_do_usuario`.

- [x] Sem proteção contra força bruta
  - Local: apps/core/forms.py
  - Tipo: segurança
  - Problema identificado: tentativas ilimitadas (especificação V2.6 pede 5 tentativas e bloqueio de 30 min por usuário+IP).
  - Risco: adivinhação de senha.
  - Correção proposta: contador em cache por usuário+IP, bloqueio de 30 min, reset no sucesso, sem revelar se o usuário existe.
  - Status: Corrigido — 5 falhas → bloqueio de 30 min por usuário+IP (`LOGIN_MAX_TENTATIVAS`/`LOGIN_BLOQUEIO_SEGUNDOS`). Limitação: cache local por processo; em produção multi-worker configurar Redis.

- [x] Redirecionamentos duplicados após login
  - Local: apps/core/views.py, static/js/app.js
  - Tipo: concorrência
  - Problema identificado: com envios duplicados, cada resposta 302 dispara uma navegação.
  - Risco: navegação repetida e páginas carregadas duas vezes.
  - Correção proposta: o login assíncrono recebe JSON `{redirect}` e navega uma única vez (`location.replace`), com a trava mantida.
  - Status: Corrigido — resposta JSON `{redirect}` e uma única `location.replace`.

- [x] Redirecionamento `next` para outro domínio (open redirect)
  - Local: apps/core/views.py
  - Tipo: segurança
  - Problema identificado: verificado. `LoginView` valida `next` com `url_has_allowed_host_and_scheme`.
  - Risco: nenhum.
  - Correção proposta: nenhuma; manter a mesma validação também na resposta JSON.
  - Status: Sem alteração necessária — validação do Django mantida também na resposta JSON (testes de `next` externo e interno).

- [x] Armazenamento de senha, token ou dados sensíveis
  - Local: config/settings.py, templates
  - Tipo: segurança
  - Problema identificado: não há token em `localStorage` e a senha não é persistida (sessão Django com cookie HttpOnly). Porém os cookies de sessão e CSRF não são marcados como `Secure` fora do modo DEBUG.
  - Risco: cookie de sessão trafegando em HTTP.
  - Correção proposta: `SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` quando `DEBUG=False`, mais `SameSite=Lax`.
  - Status: Corrigido — cookies `Secure` fora de DEBUG e `SameSite=Lax`; nada sensível em localStorage; senha limpa do campo após falha.

- [x] Logout por GET
  - Local: apps/core/views.py, templates/base.html
  - Tipo: segurança
  - Problema identificado: `GET /logout/` encerra a sessão (sujeito a CSRF ou pré-carregamento de link). Especificação V2.15 pede POST.
  - Risco: logout forçado por terceiros.
  - Correção proposta: `@require_POST` e formulário com CSRF e trava contra duplo clique no menu lateral.
  - Status: Corrigido — `@require_POST` e formulário com CSRF no menu lateral (GET → 405).

---

## 2. Formulários (padrão global)

- [x] Nenhum formulário POST protegido contra envio duplicado
  - Local: todos os templates com `method="post"`
  - Tipo: múltiplos cliques
  - Problema identificado: não existe padrão de controle de requisição.
  - Risco: registros duplicados e processamento repetido.
  - Correção proposta: `static/js/app.js` intercepta `submit` de todo formulário POST; a flag `data-submitting` bloqueia a função (não apenas o visual), desabilita os botões e mostra carregamento. O estado é restaurado em `pageshow` (voltar pelo histórico).
  - Status: Corrigido — `static/js/app.js` carregado em `base.html` e no login; trava por `data-submitting` verificada dentro do handler.

- [x] Erros exibidos longe do campo e não limpos
  - Local: todos os formulários
  - Tipo: UX
  - Problema identificado: só há o balão nativo, ou mensagens do servidor no topo da página.
  - Risco: usuário não identifica o campo com erro.
  - Correção proposta: mensagem `.field-error` abaixo de cada campo inválido, com foco no primeiro; removida ao editar o campo.
  - Status: Corrigido — `.field-error` com `aria-invalid`/`aria-describedby`, foco no primeiro campo inválido e remoção ao editar.

- [x] Dados não normalizados antes do envio
  - Local: todos os formulários
  - Tipo: validação
  - Problema identificado: espaços no início e no fim são enviados; campo obrigatório preenchido só com espaços passa no frontend.
  - Risco: dados sujos e erro tardio no servidor.
  - Correção proposta: `trim` em campos de texto (exceto senha e arquivo) antes de validar.
  - Status: Corrigido — `normalizeFields` antes da validação (frontend) e `Validador.texto` com strip (backend).

- [x] Valores digitados perdidos após erro do servidor
  - Local: templates/orcamento/novo.html, templates/documentos/enviar.html
  - Tipo: UX
  - Problema identificado: o formulário volta vazio quando o backend rejeita os dados.
  - Risco: retrabalho e desistência.
  - Correção proposta: reexibir os valores enviados (exceto arquivo).
  - Status: Corrigido — Novo orçamento e Publicar documento reexibem os valores (`dados`). Arquivo precisa ser selecionado de novo (limitação do navegador).

- [x] Arquivo acima do limite só é rejeitado depois do upload completo
  - Local: templates/tratativas/importar.html, templates/documentos/enviar.html
  - Tipo: validação
  - Problema identificado: não há verificação de tamanho no cliente.
  - Risco: upload longo inútil.
  - Correção proposta: `data-max-mb` no input de arquivo, validado antes do envio.
  - Status: Corrigido — `data-max-mb` (100 MB na importação, 50 MB nos documentos) e checagem de `upload.size` no backend.

---

## 3. Carteira de notas (apps/incorporacao)

- [x] Registrar tratativa duplicada por duplo clique ou reenvio
  - Local: apps/incorporacao/views.py (`criar_tratativa`), templates/incorporacao/detalhe.html
  - Tipo: concorrência
  - Problema identificado: cada POST cria uma `Tratativa`.
  - Risco: histórico poluído com registros repetidos.
  - Correção proposta: trava no frontend e chave de idempotência por formulário (`EnvioFormulario`, chave única no banco), dentro de uma transação.
  - Status: Corrigido — trava no frontend e `EnvioFormulario` (chave única) dentro de `transaction.atomic`. Teste: mesma chave → 1 tratativa.

- [x] Formulário de tratativa exibido a quem não pode editar
  - Local: templates/incorporacao/detalhe.html
  - Tipo: UX
  - Problema identificado: o usuário digita e recebe um 403.
  - Risco: frustração (o backend já bloqueia corretamente).
  - Correção proposta: exibir o formulário só quando `pode_editar_nota`; caso contrário, mostrar um aviso explicando a regra.
  - Status: Corrigido — exibido só com `pode_editar`; aviso para as demais gerências. Backend continua com 403.

- [x] Texto da tratativa sem limite de tamanho
  - Local: apps/incorporacao/views.py
  - Tipo: validação
  - Problema identificado: aceita texto de qualquer tamanho.
  - Risco: abuso e registros gigantes.
  - Correção proposta: limite de 5.000 caracteres no backend e `maxlength` no frontend.
  - Status: Corrigido — 5.000 caracteres (backend e `maxlength`).

- [x] Status da demanda em branco no detalhe da nota
  - Local: templates/incorporacao/detalhe.html
  - Tipo: UX
  - Problema identificado: o template usa `nota.get_status_demanda`, que não existe.
  - Risco: informação ausente na tela.
  - Correção proposta: usar a propriedade `nota.status_demanda`.
  - Status: Corrigido — usa `nota.status_demanda`. Também corrigido o erro 500 do detalhe quando a nota não tem medida (`|default:` com objeto nulo → `{% firstof %}`).

- [x] Paginação perde os filtros
  - Local: templates/incorporacao/lista.html
  - Tipo: UX
  - Problema identificado: os links de página preservam só `q`; gerência, etapa e "minha fila" se perdem.
  - Risco: lista errada ao paginar.
  - Correção proposta: preservar toda a querystring, exceto `page`.
  - Status: Corrigido — `filtros_qs` preserva toda a querystring.

---

## 4. Documentos modelo (apps/documentos)

- [x] Publicar versão duas vezes por duplo clique
  - Local: apps/documentos/views.py (`enviar_documento`), templates/documentos/enviar.html
  - Tipo: múltiplos cliques
  - Problema identificado: dois POSTs geram v2 e v3 do mesmo arquivo.
  - Risco: versões falsas e histórico incorreto.
  - Correção proposta: trava no frontend e idempotência no backend.
  - Status: Corrigido — trava no frontend e idempotência. Teste: 2 envios → 1 versão.

- [x] Cálculo de versão sujeito a condição de corrida
  - Local: apps/documentos/views.py, apps/documentos/models.py
  - Tipo: concorrência
  - Problema identificado: `max(versao)+1` sem trava e sem restrição única no banco.
  - Risco: duas versões com o mesmo número, ou duas versões vigentes.
  - Correção proposta: `transaction.atomic` com `select_for_update`, `UniqueConstraint(titulo, categoria, versao)` e tratamento do `IntegrityError` com mensagem clara.
  - Status: Corrigido — `select_for_update` + `UniqueConstraint(titulo, categoria, versao)` (migração 0003) + mensagem de conflito.

- [x] ID da distribuidora digitado livremente e sem validação
  - Local: templates/documentos/enviar.html, apps/documentos/views.py
  - Tipo: validação
  - Problema identificado: valor não numérico ou inexistente gera erro 500 (`ValueError` ou `IntegrityError`).
  - Risco: erro 500 e dado inconsistente.
  - Correção proposta: `select` com as distribuidoras ativas e validação do ID no backend.
  - Status: Corrigido — `select` de distribuidoras e `Validador.objeto`.

- [x] Sem validação de extensão e tamanho do arquivo
  - Local: apps/documentos/views.py
  - Tipo: segurança
  - Problema identificado: aceita qualquer arquivo, de qualquer tamanho.
  - Risco: upload de executáveis e consumo de disco.
  - Correção proposta: lista de extensões permitidas e limite de 50 MB (frontend e backend).
  - Status: Corrigido — lista de extensões, 50 MB, arquivo vazio recusado.

- [x] Duplo clique em "Baixar" gera dois downloads e dois registros de log
  - Local: templates/documentos/lista.html
  - Tipo: múltiplos cliques
  - Problema identificado: o link GET não tem controle.
  - Risco: log de downloads inflado e downloads repetidos.
  - Correção proposta: `data-download` faz o download via `fetch` com trava por link, carregamento e erro tratado por código HTTP.
  - Status: Corrigido — `data-download` (fetch com trava por link, erro por status HTTP, sessão expirada detectada).

- [x] Arquivo ausente no armazenamento gera erro 500
  - Local: apps/documentos/views.py (`baixar_documento`, `baixar_anexo_nota`)
  - Tipo: tratamento de erro
  - Problema identificado: `arquivo.open()` lança `FileNotFoundError`.
  - Risco: erro 500, e o download é registrado no log antes de falhar.
  - Correção proposta: abrir o arquivo antes de registrar o log; responder 404 com mensagem clara.
  - Status: Corrigido — abre o arquivo antes de registrar o log; 404 com mensagem. Teste dedicado.

- [x] Documento sem arquivo responde 403
  - Local: apps/documentos/views.py
  - Tipo: tratamento de erro
  - Problema identificado: ausência de arquivo não é falta de permissão.
  - Risco: código HTTP incorreto.
  - Correção proposta: responder 404.
  - Status: Corrigido — 404.

---

## 5. Orçamento RDU (apps/orcamento)

- [x] Criar orçamento duplicado por duplo clique
  - Local: apps/orcamento/views.py (`novo_orcamento`), templates/orcamento/novo.html
  - Tipo: múltiplos cliques
  - Problema identificado: cada POST cria um orçamento.
  - Risco: orçamentos duplicados.
  - Correção proposta: trava no frontend e idempotência; um reenvio redireciona ao orçamento já criado.
  - Status: Corrigido — trava + idempotência; reenvio redireciona ao orçamento já criado. Teste dedicado.

- [x] Mensagens de erro expõem detalhes internos
  - Local: apps/orcamento/views.py
  - Tipo: segurança
  - Problema identificado: `str(exc)` exibe `[<class 'decimal.ConversionSyntax'>]`, "Field 'id' expected a number…" e `KeyError('descricao')`.
  - Risco: exposição de implementação e mensagens incompreensíveis.
  - Correção proposta: validador central (`apps/core/validacao.py`) com mensagens por campo.
  - Status: Corrigido — `apps/core/validacao.py`; testes garantem ausência de `ConversionSyntax`/`expected a number`.

- [x] Valores numéricos inválidos aceitos pelo backend
  - Local: apps/orcamento/views.py
  - Tipo: validação
  - Problema identificado: aceita negativos, `NaN`, `Infinity` e excesso de dígitos ou casas decimais (o frontend usa `min=0`, mas o backend não confere).
  - Risco: erro de banco (500) ou cálculo de restituição incorreto.
  - Correção proposta: validação de número finito, mínimo 0 e limites de `max_digits`/`decimal_places` do modelo.
  - Status: Corrigido — número finito, mínimo 0, limites de dígitos e casas por campo.

- [x] Nota vinculada pode ser de outra distribuidora
  - Local: apps/orcamento/views.py
  - Tipo: validação
  - Problema identificado: o ID da nota é validado só por visibilidade; um ID não numérico gera 500.
  - Risco: orçamento ligado a uma nota de outra distribuidora.
  - Correção proposta: validar o ID e exigir `nota.distribuidora == distribuidora`.
  - Status: Corrigido — ID validado e mesma distribuidora exigida.

- [x] Limites de tamanho de texto não validados no backend
  - Local: apps/orcamento/views.py
  - Tipo: validação
  - Problema identificado: cliente (180), PEP (40) e nome da obra (180) não são conferidos; o SQLite aceita, o PostgreSQL gera erro 500.
  - Risco: erro 500 em produção.
  - Correção proposta: validar o tamanho no backend e colocar `maxlength` nos inputs.
  - Status: Corrigido — backend e `maxlength`.

- [x] Adicionar item duplicado por duplo clique
  - Local: apps/orcamento/views.py (`adicionar_item`), templates/orcamento/detalhe.html
  - Tipo: múltiplos cliques
  - Problema identificado: cada POST cria um item.
  - Risco: total da obra inflado.
  - Correção proposta: trava no frontend e idempotência.
  - Status: Corrigido — trava + idempotência. Teste: 2 envios → 1 item.

- [x] Item com descrição vazia aceito; status conferido fora de transação
  - Local: apps/orcamento/views.py
  - Tipo: concorrência
  - Problema identificado: `descricao=""` é aceita; o status "rascunho" é lido sem trava (o orçamento pode mudar de status em paralelo).
  - Risco: item sem descrição; item adicionado a orçamento já enviado para análise.
  - Correção proposta: descrição obrigatória e `select_for_update` do orçamento dentro de `transaction.atomic`.
  - Status: Corrigido — descrição obrigatória; `select_for_update` do orçamento dentro de `transaction.atomic`.

- [x] Exportar XLSX sem controle de clique e sem feedback
  - Local: templates/orcamento/detalhe.html
  - Tipo: múltiplos cliques
  - Problema identificado: vários cliques geram várias exportações; erro 403/500 abre uma página de erro.
  - Risco: carga desnecessária e tela sem contexto.
  - Correção proposta: `data-download` (fetch com trava, carregamento e mensagem de erro).
  - Status: Corrigido — `data-download`.

---

## 6. Acompanhamento de tratativas (apps/tratativas)

- [x] Importação processada duas vezes por duplo clique; corrida gera 500
  - Local: apps/tratativas/views.py (`importar_base`), templates/tratativas/importar.html
  - Tipo: concorrência
  - Problema identificado: dois POSTs simultâneos processam a mesma planilha; `get_or_create` concorrente gera `IntegrityError`.
  - Risco: erro 500 e processamento dobrado de até 150 mil linhas.
  - Correção proposta: trava no frontend, idempotência e tratamento do `IntegrityError`.
  - Status: Corrigido — trava + idempotência + tratamento de `IntegrityError`. Teste: mesma chave → processa uma vez.

- [x] Distribuidora vazia ou inválida gera erro 500
  - Local: apps/tratativas/views.py
  - Tipo: validação
  - Problema identificado: `distribuidoras.get(pk="")` lança um `ValueError` não tratado.
  - Risco: erro 500.
  - Correção proposta: validar o ID antes da consulta.
  - Status: Corrigido — `Validador.objeto`; data inexistente (ex.: 30/02) também tratada.

- [x] Planilha corrompida gera erro 500
  - Local: apps/tratativas/views.py (`_read_rows`)
  - Tipo: tratamento de erro
  - Problema identificado: `BadZipFile`/`InvalidFileException` não são tratados.
  - Risco: erro 500.
  - Correção proposta: capturar e exibir "Não foi possível ler a planilha…".
  - Status: Corrigido — mensagem "Não foi possível ler a planilha…".

- [x] Erro de codificação expõe detalhe técnico
  - Local: apps/tratativas/views.py
  - Tipo: segurança
  - Problema identificado: `str(UnicodeDecodeError)` aparece para o usuário.
  - Risco: mensagem incompreensível.
  - Correção proposta: "O CSV deve estar codificado em UTF-8."
  - Status: Corrigido — mensagem orientando "CSV UTF-8".

- [x] Arquivo lido inteiro na memória antes de checar o tamanho
  - Local: apps/tratativas/views.py
  - Tipo: validação
  - Problema identificado: `upload.read()` acontece antes da verificação de tamanho.
  - Risco: consumo de memória.
  - Correção proposta: checar `upload.size` antes de ler.
  - Status: Corrigido — `upload.size` checado antes de `read()`.

- [x] Reimportação substitui a base sem confirmação
  - Local: apps/tratativas/views.py, templates/tratativas/importar.html
  - Tipo: UX
  - Problema identificado: operação destrutiva (apaga as notas da base existente) sem confirmação.
  - Risco: perda acidental da base do dia.
  - Correção proposta: checkbox "Substituir base existente"; sem ela o backend recusa quando a base já existe; com ela o frontend pede `confirm()`.
  - Status: Corrigido — checkbox "Substituir base existente" exigida pelo backend + `confirm()` no frontend.

- [x] Parâmetros `atual`/`referencia` não numéricos geram erro 500
  - Local: apps/tratativas/views.py (`painel`)
  - Tipo: validação
  - Problema identificado: `filter(pk="abc")` lança `ValueError`.
  - Risco: erro 500 com URL manipulada.
  - Correção proposta: ignorar valores não numéricos.
  - Status: Corrigido — `id_numerico`. Também corrigido erro 500 da comparação quando a nota só existe numa das bases (`{% firstof %}`).

- [ ] "Marcar nota como tratada" sem tela ou endpoint
  - Local: apps/tratativas/models.py (`TratativaNota`)
  - Tipo: UX
  - Problema identificado: o modelo existe, mas não há ação na interface.
  - Risco: nenhum na versão atual (não há botão a proteger).
  - Correção proposta: quando for implementado, usar o mesmo padrão (`data-submitting` e `chave_envio`).
  - Status: Não aplicável — não há endpoint/tela; o padrão (`chave_envio` + `data-submitting`) está pronto para quando for criado.

---

## 7. Painel (apps/painel)

- [x] Filtro de distribuidora não numérico gera erro 500
  - Local: apps/painel/views.py
  - Tipo: validação
  - Problema identificado: `?distribuidora=abc` lança `ValueError`.
  - Risco: erro 500.
  - Correção proposta: ignorar valores não numéricos.
  - Status: Corrigido — `id_numerico`.

---

## 8. Camada de backend, autorização e erros

- [x] Autenticação e autorização em cada endpoint
  - Local: apps/*/views.py
  - Tipo: segurança
  - Problema identificado: revisados todos os 14 endpoints. Todos têm `login_required` e escopo por distribuidora ou gerência; importação restrita a Tático/Dev; publicação restrita a Dev; tratativa restrita à gerência responsável. Faltam testes cobrindo isso.
  - Risco: regressão silenciosa.
  - Correção proposta: testes de permissão para ações protegidas.
  - Status: Corrigido — testes de permissão: tratativa de outra gerência (403), importação por perfil Ativos (403), publicação por não-Dev (403), orçamento de outra distribuidora (403), orçamento fora de rascunho (403).

- [x] Sem páginas de erro 403/404/500 próprias
  - Local: templates/
  - Tipo: UX
  - Problema identificado: aparecem as páginas padrão do Django, sem identidade visual nem caminho de volta.
  - Risco: usuário "preso" após um erro.
  - Correção proposta: templates `403.html`, `404.html` e `500.html` independentes (não dependem de contexto).
  - Status: Corrigido — `templates/403.html`, `404.html`, `500.html` (via `erro_base.html`, sem depender de contexto).

- [ ] Exclusões
  - Local: interface própria
  - Tipo: UX
  - Problema identificado: não há botão de exclusão na interface própria; exclusões só pelo Django Admin, que já exige página de confirmação.
  - Risco: nenhum na versão atual.
  - Correção proposta: o padrão `data-confirm` do `app.js` fica disponível para futuras exclusões.
  - Status: Não aplicável — não há exclusão na interface própria; `data-confirm` + trava disponíveis para quando houver. Exclusões do Django Admin usam a página de confirmação nativa.

- [ ] Formulários do Django Admin sem trava de duplo clique
  - Local: /admin/
  - Tipo: múltiplos cliques
  - Problema identificado: o admin usa templates próprios do Django.
  - Risco: baixo (uso restrito ao Desenvolvedor).
  - Correção proposta: sobrescrever `admin/base_site.html` para carregar `app.js`.
  - Status: Não corrigido (justificado) — uso restrito ao Desenvolvedor; injetar o script no admin pode interferir nos botões "Salvar e continuar"/"Salvar e adicionar outro". Revisar manualmente se desejado.

- [ ] API REST
  - Local: —
  - Tipo: segurança
  - Problema identificado: a API DRF prevista na especificação ainda não existe.
  - Risco: —
  - Correção proposta: ao criar a API, aplicar idempotência (`Idempotency-Key`) e respostas 401/403/404/409/422 em JSON.
  - Status: Não aplicável — API ainda não implementada; requisito registrado na especificação (seção "Padrões de envio e validação").

- [x] Lint analisa a pasta `.venv`
  - Local: pyproject.toml
  - Tipo: tratamento de erro
  - Problema identificado: `ruff check .` reporta 1.140 erros, todos de bibliotecas em `.venv`.
  - Risco: ruído que esconde problemas reais.
  - Correção proposta: adicionar `extend-exclude = [".venv"]`.
  - Status: Corrigido — `extend-exclude = [".venv"]`; `ruff check .` limpo.

---

## 9. Modais e componentes

- [ ] Modais
  - Local: —
  - Tipo: UX
  - Problema identificado: o projeto não possui modais.
  - Risco: —
  - Correção proposta: nenhuma.
  - Status: Não aplicável — o projeto não possui modais.

- [x] Listeners registrados mais de uma vez
  - Local: static/js/app.js
  - Tipo: múltiplos cliques
  - Problema identificado: risco ao criar o script global.
  - Risco: handler duplicado executa a ação duas vezes.
  - Correção proposta: delegação de eventos no `document`, com inicialização protegida por flag (`init` idempotente).
  - Status: Corrigido — delegação no `document` e `init()` idempotente.

---

## 10. Testes

- [x] Ausência de testes para duplo envio, validação e permissão
  - Local: apps/*/tests.py
  - Tipo: tratamento de erro
  - Problema identificado: os 11 testes existentes cobrem cálculo, importação e permissão de nota.
  - Risco: regressões.
  - Correção proposta: testes de backend (Django) e de frontend (`node --test`, sem dependências).
  - Status: Corrigido — 59 testes Django (eram 11) + 15 testes JS (`node --test tests/js/app.test.js`).
