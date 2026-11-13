/* Interações do site público: estrelas, contadores, preços, IMC, filtro e perfil dos personais */
(function () {
  "use strict";
  var semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- céu de estrelas piscando ----
  document.querySelectorAll("[data-estrelas]").forEach(function (ceu) {
    var total = Number(ceu.dataset.estrelas) || 30;
    for (var i = 0; i < total; i++) {
      var e = document.createElement("i");
      e.style.left = Math.random() * 100 + "%";
      e.style.top = Math.random() * 100 + "%";
      e.style.animationDelay = (Math.random() * 4).toFixed(2) + "s";
      var t = Math.random() < 0.15 ? 4 : 2;
      e.style.width = e.style.height = t + "px";
      ceu.appendChild(e);
    }
  });

  // ---- contadores animados quando aparecem na tela ----
  var contadores = document.querySelectorAll("[data-contar]");
  function animar(el) {
    var alvo = Number(el.dataset.contar) || 0;
    if (semMovimento || alvo === 0) { el.textContent = alvo.toLocaleString("pt-BR"); return; }
    var inicio = null, duracao = 1400;
    function passo(t) {
      if (!inicio) inicio = t;
      var p = Math.min((t - inicio) / duracao, 1);
      var valor = Math.round(alvo * (1 - Math.pow(1 - p, 3)));
      el.textContent = valor.toLocaleString("pt-BR");
      if (p < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }
  if ("IntersectionObserver" in window) {
    var obs = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (en) { if (en.isIntersecting) { animar(en.target); obs.unobserve(en.target); } });
    }, { threshold: 0.4 });
    contadores.forEach(function (c) { c.textContent = "0"; obs.observe(c); });
  }

  // ---- planos: alternar preço mensal / total ----
  document.querySelectorAll("[data-preco]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var modo = botao.dataset.preco;
      document.querySelectorAll("[data-preco]").forEach(function (b) { b.setAttribute("aria-pressed", b === botao); });
      document.querySelectorAll("[data-mensal][data-total]").forEach(function (el) { el.textContent = el.dataset[modo]; });
    });
  });

  // ---- calculadora de IMC ----
  var peso = document.getElementById("imc-peso"), altura = document.getElementById("imc-altura");
  if (peso && altura) {
    var faixas = [
      { ate: 18.5, nome: "Abaixo do peso", dica: "Foco em ganho de massa: treino de força + alimentação reforçada." },
      { ate: 25, nome: "Peso normal", dica: "Ótimo ponto de partida para ganhar força e condicionamento." },
      { ate: 30, nome: "Sobrepeso", dica: "Musculação + aeróbico ajudam a reduzir gordura e ganhar disposição." },
      { ate: 99, nome: "Obesidade", dica: "Comece com acompanhamento de personal e avaliação física. Passo a passo!" }
    ];
    function calcular() {
      var p = Number(peso.value), a = Number(altura.value) / 100, imc = p / (a * a);
      document.getElementById("imc-peso-txt").textContent = p;
      document.getElementById("imc-altura-txt").textContent = a.toFixed(2).replace(".", ",");
      document.getElementById("imc-valor").textContent = imc.toFixed(1).replace(".", ",");
      var f = faixas.find(function (x) { return imc < x.ate; });
      document.getElementById("imc-classe").textContent = f.nome;
      document.getElementById("imc-dica").textContent = f.dica;
      // posição na barra: 15 -> 0% ... 40 -> 100%
      var pos = Math.max(0, Math.min(100, (imc - 15) / 25 * 100));
      document.getElementById("imc-marcador").style.left = pos + "%";
    }
    peso.addEventListener("input", calcular);
    altura.addEventListener("input", calcular);
    calcular();
  }

  // ---- personais: filtro por especialidade ----
  var cards = document.querySelectorAll("[data-tags]");
  document.querySelectorAll("[data-filtro]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var filtro = botao.dataset.filtro, visiveis = 0;
      document.querySelectorAll("[data-filtro]").forEach(function (b) { b.setAttribute("aria-pressed", b === botao); });
      cards.forEach(function (c) {
        var mostrar = !filtro || c.dataset.tags.split("|").indexOf(filtro) !== -1;
        c.hidden = !mostrar;
        if (mostrar) visiveis++;
      });
      var vazio = document.getElementById("sem-resultado");
      if (vazio) vazio.hidden = visiveis > 0;
    });
  });

  // ---- personais: perfil em janela (modal) ----
  function abrir(id) {
    var modal = document.getElementById(id);
    if (modal && typeof modal.showModal === "function") modal.showModal();
  }
  document.querySelectorAll("[data-modal]").forEach(function (card) {
    card.addEventListener("click", function () { abrir(card.dataset.modal); });
  });
  document.querySelectorAll("dialog.modal").forEach(function (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal || e.target.hasAttribute("data-fechar")) modal.close();
    });
  });
  // veio de um link "#personal-3" da página inicial: abre o perfil direto
  var alvo = location.hash.match(/^#personal-(\d+)$/);
  if (alvo) abrir("modal-" + alvo[1]);
})();
