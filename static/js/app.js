/*
 * Central de Soluções de Incorporação de Redes — controle de envio e feedback.
 *
 * Padrão único para todo o sistema:
 *  - <form method="post">           → trava real contra duplo envio (clique, Enter, clique+Enter),
 *                                     validação antes do envio com erro ao lado do campo,
 *                                     normalização (trim), botão desabilitado + carregamento.
 *  - <form data-async-login>        → login via fetch: uma tentativa por vez, erro único,
 *                                     timeout/erro de rede tratados, um único redirecionamento.
 *  - <a data-download>              → download via fetch com trava por link e erro por status HTTP.
 *  - data-confirm / data-confirm-when → confirmação de operações destrutivas.
 *  - <select data-autoenvio>         → filtro GET aplicado ao trocar a opção.
 *
 * A trava fica na função (flag/guard), não só na aparência do botão.
 * Funções puras são exportadas para os testes em tests/js (node --test).
 */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (typeof window !== "undefined" && typeof document !== "undefined") {
    window.CSIR = api;
    api.init(document);
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const REQUEST_TIMEOUT_MS = 30000;
  const NO_TRIM_TYPES = ["password", "file", "hidden", "checkbox", "radio", "submit", "button", "reset"];

  /* ------------------------------------------------------------------ guard */

  /**
   * Trava de execução: enquanto uma ação está ativa, novas chamadas são ignoradas.
   * A ação recebe `keepLocked()` para manter a trava após o sucesso (ex.: durante redirecionamento).
   * Erros não são engolidos: são propagados para quem chamou.
   */
  function createActionGuard() {
    let active = false;
    return {
      get active() {
        return active;
      },
      async run(action) {
        if (active) {
          return { skipped: true };
        }
        active = true;
        let keep = false;
        try {
          const result = await action(() => {
            keep = true;
          });
          return { skipped: false, result };
        } finally {
          if (!keep) {
            active = false;
          }
        }
      },
      reset() {
        active = false;
      },
    };
  }

  /* --------------------------------------------------------------- mensagens */

  function httpErrorMessage(status) {
    if (status === 400 || status === 422) return "Dados inválidos. Revise os campos e tente novamente.";
    if (status === 401) return "Sua sessão expirou. Entre novamente.";
    if (status === 403) return "Você não tem permissão para executar esta ação.";
    if (status === 404) return "Registro ou arquivo não encontrado. Ele pode ter sido removido.";
    if (status === 409) return "O registro foi alterado por outra pessoa. Recarregue a página e tente novamente.";
    if (status === 413) return "O arquivo é maior que o permitido.";
    if (status === 429) return "Muitas tentativas. Aguarde alguns minutos e tente novamente.";
    if (status >= 500) return "O servidor encontrou um erro. Tente novamente em instantes.";
    return `Não foi possível concluir a operação (código ${status}).`;
  }

  function loginErrorMessage(status, serverMessage) {
    if (serverMessage) return serverMessage;
    if (status === 403) return "Sua página de acesso expirou. Recarregue a página e tente novamente.";
    if (status === 400) return "Usuário ou senha incorretos.";
    return httpErrorMessage(status);
  }

  function networkErrorMessage(error) {
    if (error && error.name === "AbortError") {
      return "O servidor demorou para responder. Verifique sua conexão e tente novamente.";
    }
    return "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.";
  }

  /* ------------------------------------------------------------------ login */

  /**
   * Fluxo de login independente do DOM (testável).
   * request(): Promise<{ok, status, data}>; ui: {setBusy, clearError, showError, navigate, onFailure}
   */
  async function performLogin(guard, request, ui) {
    try {
      const outcome = await guard.run(async (keepLocked) => {
        ui.clearError();
        ui.setBusy(true);
        let navigating = false;
        try {
          const response = await request();
          const data = response.data || {};
          if (response.ok && typeof data.redirect === "string" && data.redirect) {
            navigating = true;
            keepLocked();
            ui.navigate(data.redirect);
            return "redirect";
          }
          ui.showError(loginErrorMessage(response.status, data.error));
          if (ui.onFailure) ui.onFailure();
          return "error";
        } finally {
          if (!navigating) ui.setBusy(false);
        }
      });
      return outcome.skipped ? "skipped" : outcome.result;
    } catch (error) {
      ui.showError(networkErrorMessage(error));
      if (ui.onFailure) ui.onFailure();
      return "error";
    }
  }

  /* --------------------------------------------------------------- download */

  function filenameFromDisposition(header) {
    if (!header) return "";
    const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (utf8) {
      try {
        return decodeURIComponent(utf8[1].trim().replace(/"/g, ""));
      } catch (e) {
        /* nome inválido: usa o formato simples abaixo */
      }
    }
    const simple = /filename="?([^";]+)"?/i.exec(header);
    return simple ? simple[1].trim() : "";
  }

  /* ------------------------------------------------------- formulários (DOM) */

  function normalizeFields(form) {
    Array.from(form.elements || []).forEach((el) => {
      const tag = el.tagName;
      const type = (el.type || "").toLowerCase();
      const trimmable = tag === "TEXTAREA" || (tag === "INPUT" && !NO_TRIM_TYPES.includes(type));
      if (!trimmable || el.disabled || el.hasAttribute("data-no-trim")) return;
      const trimmed = el.value.trim();
      if (trimmed !== el.value) el.value = trimmed;
    });
  }

  function fieldErrorMessage(el) {
    const v = el.validity;
    if (v.customError) return el.validationMessage;
    if (v.valueMissing) {
      if (el.type === "file") return "Selecione um arquivo.";
      if (el.tagName === "SELECT") return "Selecione uma opção.";
      return "Campo obrigatório.";
    }
    if (v.badInput || v.typeMismatch) return "Valor em formato inválido.";
    if (v.rangeUnderflow) return `O valor mínimo é ${el.min}.`;
    if (v.rangeOverflow) return `O valor máximo é ${el.max}.`;
    if (v.stepMismatch) return "Quantidade de casas decimais acima do permitido.";
    if (v.tooLong) return `Use no máximo ${el.maxLength} caracteres.`;
    if (v.tooShort) return `Use no mínimo ${el.minLength} caracteres.`;
    if (v.patternMismatch) return el.title || "Formato inválido.";
    return el.validationMessage || "Valor inválido.";
  }

  function removeFieldError(el) {
    const id = el.getAttribute("data-error-id");
    if (id) {
      const node = document.getElementById(id);
      if (node) node.remove();
      el.removeAttribute("data-error-id");
    }
    el.removeAttribute("aria-invalid");
    const original = el.getAttribute("data-describedby-original");
    if (original !== null) {
      if (original) el.setAttribute("aria-describedby", original);
      else el.removeAttribute("aria-describedby");
      el.removeAttribute("data-describedby-original");
    }
    if (el.type === "file") el.setCustomValidity("");
  }

  function clearFieldErrors(form) {
    Array.from(form.elements || []).forEach(removeFieldError);
  }

  let errorSeq = 0;
  function showFieldError(el, message) {
    errorSeq += 1;
    const id = `campo-erro-${errorSeq}`;
    const p = document.createElement("p");
    p.className = "field-error";
    p.id = id;
    p.textContent = message;
    const anchor = el.closest(".login-input-wrap") || el;
    anchor.insertAdjacentElement("afterend", p);
    el.setAttribute("aria-invalid", "true");
    el.setAttribute("data-error-id", id);
    el.setAttribute("data-describedby-original", el.getAttribute("aria-describedby") || "");
    el.setAttribute("aria-describedby", `${el.getAttribute("aria-describedby") || ""} ${id}`.trim());
  }

  function checkFileSizes(form) {
    form.querySelectorAll('input[type="file"][data-max-mb]').forEach((input) => {
      const limit = Number(input.dataset.maxMb) * 1024 * 1024;
      const tooBig = Array.from(input.files || []).some((file) => file.size > limit);
      input.setCustomValidity(tooBig ? `O arquivo excede o limite de ${input.dataset.maxMb} MB.` : "");
    });
  }

  function validateForm(form) {
    clearFieldErrors(form);
    checkFileSizes(form);
    const invalid = Array.from(form.elements || []).filter((el) => el.willValidate && !el.checkValidity());
    invalid.forEach((el) => showFieldError(el, fieldErrorMessage(el)));
    if (invalid.length) invalid[0].focus();
    return invalid.length === 0;
  }

  function confirmMessage(form) {
    const message = form.getAttribute("data-confirm");
    if (!message) return "";
    const when = form.getAttribute("data-confirm-when");
    if (!when) return message;
    const field = form.elements[when];
    return field && field.checked ? message : "";
  }

  /**
   * Decide se um envio comum (POST de página inteira) pode seguir.
   * Retorna "blocked" | "invalid" | "cancelled" | "proceed".
   */
  function decideSubmit(form, confirmFn) {
    if (form.getAttribute("data-submitting") === "true") return "blocked";
    normalizeFields(form);
    if (!validateForm(form)) return "invalid";
    const message = confirmMessage(form);
    if (message && !confirmFn(message)) return "cancelled";
    return "proceed";
  }

  function submitButtonsOf(form) {
    const inside = Array.from(form.querySelectorAll('button:not([type]), button[type="submit"], input[type="submit"]'));
    const outside = form.id ? Array.from(document.querySelectorAll(`[type="submit"][form="${form.id}"]`)) : [];
    return inside.concat(outside);
  }

  function setButtonBusy(button, busy) {
    if (busy) {
      if (!button.hasAttribute("data-original-html")) {
        button.setAttribute("data-original-html", button.innerHTML);
      }
      const label = button.getAttribute("data-loading-text") || "Processando…";
      const spinner = document.createElement("span");
      spinner.className = "spinner";
      spinner.setAttribute("aria-hidden", "true");
      const text = document.createElement("span");
      text.textContent = label;
      button.replaceChildren(spinner, text);
      button.disabled = true;
      button.classList.add("is-loading");
    } else {
      if (button.hasAttribute("data-original-html")) {
        button.innerHTML = button.getAttribute("data-original-html");
        button.removeAttribute("data-original-html");
      }
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }

  function setFormBusy(form, busy) {
    if (busy) form.setAttribute("data-submitting", "true");
    else form.removeAttribute("data-submitting");
    form.setAttribute("aria-busy", String(busy));
    submitButtonsOf(form).forEach((button) => setButtonBusy(button, busy));
  }

  /* ---------------------------------------------------------- notificações */

  function messagesRegion() {
    let region = document.querySelector("[data-messages]");
    if (!region) {
      region = document.createElement("div");
      region.className = "messages";
      region.setAttribute("data-messages", "");
      region.setAttribute("role", "status");
      region.setAttribute("aria-live", "polite");
      const host = document.querySelector(".content") || document.body;
      host.prepend(region);
    }
    return region;
  }

  /** Mostra uma notificação; a mesma mensagem nunca aparece duplicada. */
  function notify(message, type) {
    const region = messagesRegion();
    const existing = Array.from(region.querySelectorAll(".message")).find((node) => node.textContent === message);
    if (existing) {
      existing.remove();
    }
    const node = document.createElement("div");
    node.className = `message ${type || ""}`.trim();
    node.textContent = message;
    region.prepend(node);
    return node;
  }

  /* -------------------------------------------------------------- fetch util */

  async function fetchWithTimeout(url, options) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      return await fetch(url, Object.assign({ credentials: "same-origin", signal: controller.signal }, options));
    } finally {
      clearTimeout(timer);
    }
  }

  /* --------------------------------------------------------------- bindings */

  let guards = new WeakMap();
  function guardFor(element) {
    if (!guards.has(element)) guards.set(element, createActionGuard());
    return guards.get(element);
  }

  function loginUi(form) {
    const feedback = form.parentElement.querySelector("[data-login-error]");
    return {
      setBusy: (busy) => setFormBusy(form, busy),
      clearError: () => {
        feedback.textContent = "";
        feedback.hidden = true;
      },
      showError: (message) => {
        feedback.textContent = message;
        feedback.hidden = false;
      },
      onFailure: () => {
        const password = form.elements.password;
        if (password) {
          password.value = "";
          password.focus();
        }
      },
      navigate: (url) => window.location.replace(url),
    };
  }

  function handleLoginSubmit(form) {
    const guard = guardFor(form);
    if (guard.active) return; // tentativa em andamento: ignora clique/Enter extra
    normalizeFields(form);
    if (!validateForm(form)) return;
    performLogin(
      guard,
      async () => {
        const response = await fetchWithTimeout(form.action || window.location.href, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
        });
        const isJson = (response.headers.get("Content-Type") || "").includes("application/json");
        const data = isJson ? await response.json().catch(() => null) : null;
        return { ok: response.ok, status: response.status, data };
      },
      loginUi(form)
    );
  }

  function onSubmit(event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.hasAttribute("data-async-login")) {
      event.preventDefault();
      handleLoginSubmit(form);
      return;
    }
    if ((form.getAttribute("method") || "get").toLowerCase() !== "post") return;
    const decision = decideSubmit(form, (message) => window.confirm(message));
    if (decision !== "proceed") {
      event.preventDefault();
      return;
    }
    // Botão desabilitado não é enviado: preserva name/value do botão clicado.
    const submitter = event.submitter;
    if (submitter && submitter.name && !form.querySelector(`input[type="hidden"][data-submitter]`)) {
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = submitter.name;
      hidden.value = submitter.value;
      hidden.setAttribute("data-submitter", "");
      form.appendChild(hidden);
    }
    setFormBusy(form, true);
  }

  function setLinkBusy(link, busy) {
    link.classList.toggle("is-loading", busy);
    if (busy) link.setAttribute("aria-disabled", "true");
    else link.removeAttribute("aria-disabled");
  }

  async function handleDownload(link) {
    const guard = guardFor(link);
    try {
      await guard.run(async () => {
        setLinkBusy(link, true);
        try {
          const response = await fetchWithTimeout(link.href, { method: "GET" });
          if (response.redirected && /\/login\/?/.test(new URL(response.url).pathname)) {
            throw Object.assign(new Error("sessão"), { status: 401 });
          }
          if (!response.ok) {
            throw Object.assign(new Error("http"), { status: response.status });
          }
          const blob = await response.blob();
          const filename =
            filenameFromDisposition(response.headers.get("Content-Disposition")) ||
            link.getAttribute("data-download") ||
            "arquivo";
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = filename;
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(url);
        } finally {
          setLinkBusy(link, false);
        }
      });
    } catch (error) {
      notify(error && error.status ? httpErrorMessage(error.status) : networkErrorMessage(error), "error");
    }
  }

  function onClick(event) {
    const link = event.target.closest && event.target.closest("a[data-download]");
    if (!link) return;
    event.preventDefault();
    handleDownload(link);
  }

  function onInput(event) {
    const el = event.target;
    if (el && el.getAttribute && el.getAttribute("aria-invalid") === "true") removeFieldError(el);
  }

  function onChange(event) {
    onInput(event);
    // Filtros (GET) com data-autoenvio aplicam ao trocar a opção.
    const el = event.target;
    if (el && el.matches && el.matches("select[data-autoenvio]") && el.form) el.form.requestSubmit();
  }

  function onPageShow(event) {
    // Voltar pelo histórico (bfcache) restaura a página como estava: libera travas e botões.
    if (!event.persisted) return;
    guards = new WeakMap();
    document.querySelectorAll("form[data-submitting]").forEach((form) => setFormBusy(form, false));
    document.querySelectorAll("form[data-async-login]").forEach((form) => setFormBusy(form, false));
    document.querySelectorAll("a[data-download].is-loading").forEach((link) => setLinkBusy(link, false));
  }

  function setupPasswordToggles(doc) {
    doc.querySelectorAll("[data-password-toggle]").forEach((button) => {
      const input = doc.getElementById(button.getAttribute("data-password-toggle"));
      if (!input) return;
      button.addEventListener("click", () => {
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        button.setAttribute("aria-pressed", String(!showing));
        button.setAttribute("aria-label", showing ? "Mostrar senha" : "Ocultar senha");
      });
    });
  }

  let initialized = false;
  function init(doc) {
    if (initialized) return; // listeners registrados uma única vez
    initialized = true;
    const start = () => {
      // A validação é feita por este script (mensagens ao lado do campo);
      // o navegador sem JS continua usando a validação nativa.
      doc.querySelectorAll('form[method="post"], form[data-async-login]').forEach((form) => {
        form.noValidate = true;
      });
      setupPasswordToggles(doc);
    };
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", start);
    else start();
    doc.addEventListener("submit", onSubmit);
    doc.addEventListener("click", onClick);
    doc.addEventListener("input", onInput);
    doc.addEventListener("change", onChange);
    window.addEventListener("pageshow", onPageShow);
  }

  return {
    createActionGuard,
    performLogin,
    decideSubmit,
    normalizeFields,
    confirmMessage,
    httpErrorMessage,
    loginErrorMessage,
    networkErrorMessage,
    filenameFromDisposition,
    notify,
    init,
  };
});
