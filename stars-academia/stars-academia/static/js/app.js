/* Comportamentos gerais usados em todas as páginas */
(function () {
  "use strict";

  // ---- avisos (flash): fechar no X e sumir sozinhos ----
  function fecharAviso(aviso) {
    aviso.classList.add("aviso--saindo");
    setTimeout(function () { aviso.remove(); }, 300);
  }
  document.querySelectorAll(".aviso").forEach(function (aviso) {
    aviso.querySelector(".aviso__fechar").addEventListener("click", function () { fecharAviso(aviso); });
    setTimeout(function () { if (document.body.contains(aviso)) fecharAviso(aviso); }, 7000);
  });

  // ---- confirmação antes de enviar formulários sensíveis (cancelar etc.) ----
  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
    });
  });

  // ---- máscara de telefone: (11) 98765-4321 ----
  document.querySelectorAll("[data-mascara=telefone]").forEach(function (campo) {
    campo.addEventListener("input", function () {
      var d = campo.value.replace(/\D/g, "").slice(0, 11);
      var r = d;
      if (d.length > 2) r = "(" + d.slice(0, 2) + ") " + d.slice(2);
      if (d.length > 6) r = "(" + d.slice(0, 2) + ") " + d.slice(2, d.length - 4) + "-" + d.slice(-4);
      campo.value = r;
    });
  });

  // ---- tela de horários do estabelecimento: esmaecer dias fechados ----
  document.querySelectorAll("input[data-dia]").forEach(function (check) {
    var linha = check.closest("tr");
    function atualizar() { linha.classList.toggle("fechado", !check.checked); }
    check.addEventListener("change", atualizar);
    atualizar();
  });
})();
