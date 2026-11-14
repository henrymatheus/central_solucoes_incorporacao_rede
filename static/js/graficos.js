/* Gráficos da gestão de notas (ECharts).
 *
 * Os dados vêm do servidor em <script id="dados-graficos" type="application/json">:
 *   { "<nome>": { "tipo": "fluxo" | "barras", "serie": [...] } }
 * e são desenhados em cada <div data-grafico="<nome>">. Cada barra tem uma URL: o clique abre
 * a lista de notas que compõe aquele número.
 *
 * Cores: entrantes (azul) e encerradas (laranja) validadas para daltonismo; prazo usa cores de
 * status sempre com rótulo; faixas de atraso/idade usam escala de um só tom.
 */
(function () {
  "use strict";

  const COR = {
    entrantes: "#1a4ea3",
    encerradas: "#f26a1b",
    texto: "#0f2147",
    secundario: "#5d6b85",
    grade: "#e6ebf3",
  };
  const num = new Intl.NumberFormat("pt-BR");

  function base() {
    return {
      textStyle: { fontFamily: "Segoe UI, Arial, sans-serif", color: COR.texto },
      grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
      tooltip: { confine: true, backgroundColor: "#fff", borderColor: COR.grade, textStyle: { color: COR.texto } },
      animationDuration: 250,
    };
  }

  function fluxo(serie) {
    const o = base();
    const muitos = serie.length > 30;
    o.legend = { top: 0, left: 0, itemWidth: 12, itemHeight: 12, icon: "roundRect", textStyle: { color: COR.secundario } };
    o.tooltip.trigger = "axis";
    o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: "rgba(26,78,163,0.06)" } };
    o.tooltip.formatter = (itens) => {
      const s = serie[itens[0].dataIndex];
      const saldo = s.saldo > 0 ? `+${num.format(s.saldo)}` : num.format(s.saldo);
      return `<b>${s.rotulo}</b><br>` +
        `<span style="color:${COR.entrantes}">■</span> Entrantes: <b>${num.format(s.entrantes)}</b><br>` +
        `<span style="color:${COR.encerradas}">■</span> Encerradas: <b>${num.format(s.encerradas)}</b><br>` +
        `Saldo: <b>${saldo}</b>`;
    };
    o.xAxis = {
      type: "category",
      data: serie.map((s) => s.rotulo),
      axisLabel: { color: COR.secundario, fontSize: 11, interval: muitos ? "auto" : 0 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COR.grade } },
    };
    o.yAxis = { type: "value", minInterval: 1, axisLabel: { color: COR.secundario, fontSize: 11 }, splitLine: { lineStyle: { color: COR.grade } } };
    const barra = (nome, campo, cor) => ({
      name: nome,
      type: "bar",
      barGap: "8%",
      barMaxWidth: 18,
      itemStyle: { color: cor, borderRadius: [4, 4, 0, 0] },
      emphasis: { focus: "series" },
      data: serie.map((s) => ({ value: s[campo], url: s[`url_${campo}`] })),
    });
    o.series = [barra("Entrantes", "entrantes", COR.entrantes), barra("Encerradas", "encerradas", COR.encerradas)];
    return o;
  }

  function barras(serie) {
    const o = base();
    o.grid.top = 16;
    o.grid.right = 96;
    const dados = serie.slice().reverse();
    o.tooltip.trigger = "item";
    o.tooltip.formatter = (p) => `${p.name}<br><b>${num.format(p.value)}</b> notas (${String(p.data.pct).replace(".", ",")}%)`;
    o.xAxis = { type: "value", show: false };
    o.yAxis = {
      type: "category",
      data: dados.map((s) => s.rotulo),
      axisLabel: { color: COR.texto, fontSize: 12 },
      axisTick: { show: false },
      axisLine: { show: false },
    };
    o.series = [{
      type: "bar",
      barMaxWidth: 20,
      data: dados.map((s) => ({ value: s.valor, url: s.url, pct: s.pct, itemStyle: { color: s.cor, borderRadius: [0, 4, 4, 0] } })),
      label: {
        show: true,
        position: "right",
        color: COR.texto,
        fontSize: 12,
        formatter: (p) => `${num.format(p.value)}  ·  ${String(p.data.pct).replace(".", ",")}%`,
      },
    }];
    return o;
  }

  const CONSTRUTORES = { fluxo, barras };

  function iniciar() {
    const fonte = document.getElementById("dados-graficos");
    if (!fonte || typeof echarts === "undefined") return;
    const dados = JSON.parse(fonte.textContent);
    const graficos = [];
    document.querySelectorAll("[data-grafico]").forEach((el) => {
      const cfg = dados[el.dataset.grafico];
      const vazio = !cfg || !cfg.serie.length || cfg.serie.every((s) => !(s.valor || s.entrantes || s.encerradas));
      if (vazio) {
        el.innerHTML = '<p class="empty-state">Sem notas nesta seleção.</p>';
        el.classList.add("vazio");
        return;
      }
      const chart = echarts.init(el, null, { renderer: "svg" });
      chart.setOption(CONSTRUTORES[cfg.tipo](cfg.serie));
      chart.on("click", (p) => {
        if (p.data && p.data.url) window.location.assign(p.data.url);
      });
      graficos.push(chart);
    });
    let pendente = null;
    window.addEventListener("resize", () => {
      cancelAnimationFrame(pendente);
      pendente = requestAnimationFrame(() => graficos.forEach((c) => c.resize()));
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
