// Testes do controle de envio (static/js/app.js). Executar: node --test tests/js
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

// DOM mínimo, suficiente para o validador de formulários.
global.document = {
  createElement() {
    return { className: "", id: "", textContent: "", remove() {} };
  },
  getElementById() {
    return null;
  },
};

const CSIR = require(path.join(__dirname, "..", "..", "static", "js", "app.js"));

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function fakeUi() {
  const calls = { busy: [], errors: [], navigations: [], failures: 0 };
  return {
    calls,
    setBusy: (value) => calls.busy.push(value),
    clearError: () => {},
    showError: (message) => calls.errors.push(message),
    navigate: (url) => calls.navigations.push(url),
    onFailure: () => {
      calls.failures += 1;
    },
  };
}

/* ------------------------------------------------------------------ login */

test("dois cliques rápidos no login geram somente uma requisição", async () => {
  const guard = CSIR.createActionGuard();
  const ui = fakeUi();
  const pending = deferred();
  let requests = 0;
  const request = () => {
    requests += 1;
    return pending.promise;
  };

  const first = CSIR.performLogin(guard, request, ui);
  const second = CSIR.performLogin(guard, request, ui);
  assert.equal(await second, "skipped");

  pending.resolve({ ok: true, status: 200, data: { redirect: "/painel/" } });
  assert.equal(await first, "redirect");
  assert.equal(requests, 1);
  assert.deepEqual(ui.calls.navigations, ["/painel/"]);
});

test("Enter e clique simultâneos geram somente uma requisição", async () => {
  // Enter e clique disparam o mesmo evento submit → a mesma função com a mesma trava.
  const guard = CSIR.createActionGuard();
  const ui = fakeUi();
  const pending = deferred();
  let requests = 0;
  const request = () => {
    requests += 1;
    return pending.promise;
  };
  const viaEnter = CSIR.performLogin(guard, request, ui);
  const viaClique = CSIR.performLogin(guard, request, ui);
  pending.resolve({ ok: false, status: 400, data: { error: "Usuário ou senha incorretos." } });
  await Promise.all([viaEnter, viaClique]);
  assert.equal(requests, 1);
  assert.deepEqual(ui.calls.errors, ["Usuário ou senha incorretos."], "uma única mensagem de erro");
});

test("após erro da API o botão volta a ficar disponível", async () => {
  const guard = CSIR.createActionGuard();
  const ui = fakeUi();
  const result = await CSIR.performLogin(
    guard,
    async () => ({ ok: false, status: 500, data: null }),
    ui
  );
  assert.equal(result, "error");
  assert.deepEqual(ui.calls.busy, [true, false]);
  assert.equal(guard.active, false);
  assert.match(ui.calls.errors[0], /servidor/);
});

test("erro de rede e timeout restauram o estado e mostram mensagem clara", async () => {
  for (const error of [new TypeError("Failed to fetch"), Object.assign(new Error("x"), { name: "AbortError" })]) {
    const guard = CSIR.createActionGuard();
    const ui = fakeUi();
    const result = await CSIR.performLogin(guard, () => Promise.reject(error), ui);
    assert.equal(result, "error");
    assert.deepEqual(ui.calls.busy, [true, false]);
    assert.equal(guard.active, false);
    assert.equal(ui.calls.errors.length, 1);
    assert.equal(ui.calls.failures, 1);
  }
});

test("sucesso mantém a trava e não restaura o botão durante o redirecionamento", async () => {
  const guard = CSIR.createActionGuard();
  const ui = fakeUi();
  await CSIR.performLogin(guard, async () => ({ ok: true, status: 200, data: { redirect: "/painel/" } }), ui);
  assert.deepEqual(ui.calls.busy, [true]);
  assert.equal(guard.active, true);
  assert.equal(await CSIR.performLogin(guard, async () => ({}), ui), "skipped");
  assert.equal(ui.calls.navigations.length, 1, "um único redirecionamento");
});

test("resposta lenta não permite uma segunda submissão", async () => {
  const guard = CSIR.createActionGuard();
  const ui = fakeUi();
  const pending = deferred();
  let requests = 0;
  const request = () => {
    requests += 1;
    return pending.promise;
  };
  const first = CSIR.performLogin(guard, request, ui);
  for (let i = 0; i < 5; i += 1) {
    await Promise.resolve();
    assert.equal(await CSIR.performLogin(guard, request, ui), "skipped");
  }
  pending.resolve({ ok: false, status: 429, data: { error: "Muitas tentativas" } });
  await first;
  assert.equal(requests, 1);
});

test("mensagens de login por status", () => {
  assert.match(CSIR.loginErrorMessage(403), /expirou/);
  assert.equal(CSIR.loginErrorMessage(400), "Usuário ou senha incorretos.");
  assert.equal(CSIR.loginErrorMessage(429, "Bloqueado"), "Bloqueado");
});

/* --------------------------------------------------------------- guard genérico */

test("guard não engole erros e libera a trava", async () => {
  const guard = CSIR.createActionGuard();
  await assert.rejects(
    guard.run(async () => {
      throw new Error("falhou");
    }),
    /falhou/
  );
  assert.equal(guard.active, false);
});

test("dois cliques em Excluir/Salvar via guard executam uma única operação", async () => {
  const guard = CSIR.createActionGuard();
  const pending = deferred();
  let operacoes = 0;
  const excluir = () =>
    guard.run(async () => {
      operacoes += 1;
      await pending.promise;
    });
  const a = excluir();
  const b = excluir();
  pending.resolve();
  const [ra, rb] = await Promise.all([a, b]);
  assert.equal(operacoes, 1);
  assert.equal(ra.skipped, false);
  assert.equal(rb.skipped, true);
});

/* ------------------------------------------------------- formulários comuns */

function fakeField({ name, value = "", type = "text", tag = "INPUT", valid = true, validity = {}, attrs = {} }) {
  const attributes = { ...attrs };
  return {
    name,
    value,
    type,
    tagName: tag,
    disabled: false,
    willValidate: true,
    focused: false,
    validity: { valueMissing: false, ...validity },
    validationMessage: "",
    checkValidity() {
      if (attributes.required !== undefined && !this.value.trim()) {
        this.validity.valueMissing = true;
        return false;
      }
      return valid;
    },
    hasAttribute: (key) => key in attributes,
    getAttribute: (key) => (key in attributes ? attributes[key] : null),
    setAttribute: (key, val) => {
      attributes[key] = String(val);
    },
    removeAttribute: (key) => {
      delete attributes[key];
    },
    setCustomValidity() {},
    closest: () => null,
    insertAdjacentElement() {},
    focus() {
      this.focused = true;
    },
  };
}

function fakeForm(elements, attrs = {}) {
  const attributes = { ...attrs };
  const form = {
    elements,
    getAttribute: (key) => (key in attributes ? attributes[key] : null),
    setAttribute: (key, val) => {
      attributes[key] = String(val);
    },
    removeAttribute: (key) => {
      delete attributes[key];
    },
    querySelectorAll: () => [],
  };
  elements.forEach((el) => {
    form.elements[el.name] = el;
  });
  return form;
}

test("dois cliques no botão Salvar geram somente uma operação", () => {
  const form = fakeForm([fakeField({ name: "nome_obra", value: "Obra" })]);
  const ok = () => true;
  assert.equal(CSIR.decideSubmit(form, ok), "proceed");
  form.setAttribute("data-submitting", "true"); // aplicado por setFormBusy no primeiro envio
  assert.equal(CSIR.decideSubmit(form, ok), "blocked");
});

test("campos inválidos não são enviados e recebem foco", () => {
  const campo = fakeField({ name: "nome_obra", value: "   ", attrs: { required: "" } });
  const form = fakeForm([campo]);
  assert.equal(CSIR.decideSubmit(form, () => true), "invalid");
  assert.equal(campo.value, "", "valor normalizado (trim) antes da validação");
  assert.equal(campo.getAttribute("aria-invalid"), "true");
  assert.equal(campo.focused, true);
});

test("normalização não altera senha", () => {
  const senha = fakeField({ name: "password", value: "  com espaços  ", type: "password" });
  const usuario = fakeField({ name: "username", value: "  joao  " });
  CSIR.normalizeFields(fakeForm([senha, usuario]));
  assert.equal(senha.value, "  com espaços  ");
  assert.equal(usuario.value, "joao");
});

test("operação destrutiva exige confirmação e pode ser cancelada", () => {
  const substituir = fakeField({ name: "substituir", type: "checkbox" });
  substituir.checked = true;
  const form = fakeForm([substituir], {
    "data-confirm": "A base será substituída. Continuar?",
    "data-confirm-when": "substituir",
  });
  const perguntas = [];
  assert.equal(
    CSIR.decideSubmit(form, (m) => {
      perguntas.push(m);
      return false;
    }),
    "cancelled"
  );
  assert.equal(perguntas.length, 1);
  substituir.checked = false;
  assert.equal(CSIR.confirmMessage(form), "", "sem substituição não há confirmação");
});

/* ---------------------------------------------------------------- utilidades */

test("mensagens HTTP cobrem 403, 404, 409, 422 e 500", () => {
  assert.match(CSIR.httpErrorMessage(403), /permissão/);
  assert.match(CSIR.httpErrorMessage(404), /não encontrado/);
  assert.match(CSIR.httpErrorMessage(409), /alterado por outra pessoa/);
  assert.match(CSIR.httpErrorMessage(422), /inválidos/);
  assert.match(CSIR.httpErrorMessage(500), /servidor/);
});

test("nome do arquivo extraído do Content-Disposition", () => {
  assert.equal(CSIR.filenameFromDisposition('attachment; filename="orcamento-1.xlsx"'), "orcamento-1.xlsx");
  assert.equal(CSIR.filenameFromDisposition("attachment; filename*=UTF-8''or%C3%A7amento.xlsx"), "orçamento.xlsx");
  assert.equal(CSIR.filenameFromDisposition(null), "");
});
