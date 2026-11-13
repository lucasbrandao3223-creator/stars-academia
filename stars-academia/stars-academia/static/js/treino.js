/* Formulário de montagem de treino: adicionar, remover e reordenar exercícios */
(function () {
  "use strict";
  var lista = document.getElementById("itens");
  var modelo = document.getElementById("modelo-item");
  if (!lista || !modelo) return;

  document.getElementById("adicionar").addEventListener("click", function () {
    var novo = modelo.content.firstElementChild.cloneNode(true);
    lista.appendChild(novo);
    novo.querySelector("select").focus();
  });

  lista.addEventListener("click", function (e) {
    var botao = e.target.closest("[data-acao]");
    if (!botao) return;
    var item = botao.closest(".item-treino");
    var acao = botao.dataset.acao;
    if (acao === "remover") {
      if (lista.children.length > 1) item.remove();
      else item.querySelectorAll("input, select").forEach(function (c) { if (c.name !== "series" && c.name !== "descanso_seg") c.value = ""; });
    } else if (acao === "subir" && item.previousElementSibling) {
      lista.insertBefore(item, item.previousElementSibling);
    } else if (acao === "descer" && item.nextElementSibling) {
      lista.insertBefore(item.nextElementSibling, item);
    }
  });

  document.querySelectorAll("[data-sugestao]").forEach(function (b) {
    b.addEventListener("click", function () { document.getElementById("campo-nome").value = b.dataset.sugestao; });
  });
})();
