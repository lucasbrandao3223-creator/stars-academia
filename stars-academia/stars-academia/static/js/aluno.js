// =====================================================================
// ÁREA DO ALUNO (Minha área)
//
// Este arquivo faz 5 coisas:
//   1. Abas dos treinos (A, B, C)
//   2. Meta da semana (botões - e +)
//   3. Calendário de frequência (clicar no dia e trocar de mês)
//   4. Cronômetro de descanso
//   5. Modo treino (marcar séries e finalizar o treino)
// =====================================================================

const area = document.getElementById("area-aluno");
const HOJE = area.dataset.hoje;   // data de hoje, ex.: "2026-11-09"
const NOMES_DIAS = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];


// ---------------------------------------------------------------------
// Funções de ajuda
// ---------------------------------------------------------------------

// Mostra uma mensagem no canto da tela (some sozinha depois de 5 segundos)
function mostrarAviso(texto, tipo) {
  let caixa = document.querySelector(".avisos");
  if (!caixa) {
    caixa = document.createElement("div");
    caixa.className = "avisos";
    document.body.appendChild(caixa);
  }
  const aviso = document.createElement("div");
  aviso.className = "aviso aviso--" + tipo;
  aviso.textContent = texto;
  caixa.appendChild(aviso);
  setTimeout(() => aviso.remove(), 5000);
}

// Envia dados para o servidor (Flask) e devolve a resposta em JSON
async function enviarParaServidor(url, dados) {
  const resposta = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
  return resposta.json();
}

// "2026-11-04"  ->  "Quarta, 04/11"
function formatarData(textoData) {
  const [ano, mes, dia] = textoData.split("-");
  const data = new Date(ano, mes - 1, dia);
  return NOMES_DIAS[data.getDay()] + ", " + dia + "/" + mes;
}

// Evita que um texto vindo do banco seja interpretado como HTML
function protegerTexto(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}


// =====================================================================
// 1. ABAS DOS TREINOS
// =====================================================================

function abrirTreino(idTreino) {
  document.querySelectorAll('[role="tab"]').forEach((aba) => {
    const ehEssa = aba.getAttribute("aria-controls") === "treino-" + idTreino;
    aba.setAttribute("aria-selected", ehEssa);
  });
  document.querySelectorAll('[role="tabpanel"]').forEach((painel) => {
    painel.hidden = painel.id !== "treino-" + idTreino;
  });
}

document.querySelectorAll('[role="tab"]').forEach((aba) => {
  aba.addEventListener("click", () => {
    const idTreino = aba.getAttribute("aria-controls").replace("treino-", "");
    abrirTreino(idTreino);
  });
});

// Botão "Treino sugerido para hoje" no topo da página
document.querySelectorAll("[data-ir-treino]").forEach((botao) => {
  botao.addEventListener("click", () => {
    abrirTreino(botao.dataset.irTreino);
    document.getElementById("treinos").scrollIntoView({ behavior: "smooth" });
  });
});


// =====================================================================
// 2. META DA SEMANA
// =====================================================================

let treinosNaSemana = 0;
let metaSemanal = 3;

function desenharMeta() {
  // o anel tem 314,16 de comprimento (2 x 3,1416 x raio 50); quanto mais perto da meta, mais ele enche
  const progresso = Math.min(treinosNaSemana / metaSemanal, 1);
  document.getElementById("meta-anel").style.strokeDashoffset = 314.16 * (1 - progresso);

  document.getElementById("meta-feitos").textContent = treinosNaSemana;
  document.getElementById("meta-valor").textContent = metaSemanal;
  document.getElementById("meta-texto").textContent = metaSemanal;

  let frase;
  if (treinosNaSemana >= metaSemanal) frase = "Meta batida! Você é uma estrela ⭐";
  else if (treinosNaSemana === 0) frase = "Bora começar a semana! 💪";
  else if (metaSemanal - treinosNaSemana === 1) frase = "Quase lá, falta pouco!";
  else frase = "Tá no ritmo, continua!";
  document.getElementById("meta-frase").textContent = frase;
}

document.querySelectorAll("[data-meta]").forEach((botao) => {
  botao.addEventListener("click", async () => {
    const novaMeta = metaSemanal + Number(botao.dataset.meta);   // data-meta é "1" ou "-1"
    if (novaMeta < 1 || novaMeta > 7) return;
    metaSemanal = novaMeta;
    desenharMeta();
    const resposta = await enviarParaServidor(area.dataset.urlMeta, { meta: novaMeta });
    if (!resposta.ok) mostrarAviso(resposta.erro, "erro");
  });
});


// =====================================================================
// 3. CALENDÁRIO DE FREQUÊNCIA
// Os dados do mês vêm do Python em JSON (rota /aluno/frequencia).
// =====================================================================

let frequencia = JSON.parse(document.getElementById("dados-frequencia").textContent);
let diaSelecionado = HOJE;

// Mostra, à direita do calendário, o que aconteceu no dia clicado
function mostrarDetalhesDoDia(dia) {
  const caixa = document.getElementById("dia-detalhe");
  if (!dia) {
    caixa.innerHTML = "<p class='texto-suave'>Clique em um dia do calendário.</p>";
    return;
  }

  let html = `<p class="selo">${dia.hoje ? "Hoje" : "Detalhes do dia"}</p><h3>${formatarData(dia.data)}</h3>`;

  if (dia.futuro) {
    html += "<p class='texto-suave'>Esse dia ainda vai chegar.</p>";
  } else if (!dia.treinou) {
    html += dia.fechado
      ? "<p class='texto-suave'>Academia fechada — dia de descanso.</p>"
      : "<p class='texto-suave'>Sem treino neste dia.</p>";
  } else {
    html += `<div class="dia-detalhe__linha"><span class="dia-detalhe__icone">✓</span>
               <div><strong>Check-in às ${dia.hora}</strong><small>Entrada registrada na academia</small></div></div>`;
    for (const treino of dia.treinos) {
      html += `<div class="dia-detalhe__linha"><span class="dia-detalhe__icone">${treino.letra}</span>
                 <div><strong>${protegerTexto(treino.nome)}</strong>
                 <small>${treino.series_feitas}/${treino.series_total} séries · ${treino.duracao} min</small></div></div>`;
    }
  }
  caixa.innerHTML = html;
}

// Desenha o mês inteiro (uma linha da tabela por semana)
function desenharCalendario() {
  document.getElementById("mes-titulo").textContent = frequencia.titulo;
  document.getElementById("mes-proximo").disabled = !frequencia.proximo;
  document.getElementById("n-mes").textContent = frequencia.no_mes;
  document.getElementById("n-30").textContent = frequencia.ultimos_30;
  document.getElementById("n-media").textContent = String(frequencia.media_semanal).replace(".", ",");
  document.getElementById("n-seq").textContent = frequencia.sequencia;

  const corpo = document.getElementById("calendario-corpo");
  corpo.innerHTML = "";
  let diaParaMostrar = null;

  for (const semana of frequencia.semanas) {
    const linha = document.createElement("tr");
    for (const dia of semana) {
      const celula = document.createElement("td");
      if (dia.fora) celula.classList.add("fora");                 // dia de outro mês
      if (dia.treinou) celula.classList.add("treinou");
      else if (dia.fechado) celula.classList.add("fechado");
      if (dia.hoje) celula.classList.add("hoje");
      if (dia.futuro) celula.classList.add("futuro");
      if (dia.data === diaSelecionado) {
        celula.classList.add("selecionado");
        diaParaMostrar = dia;
      }

      // letra do treino feito no dia (A, B, C...)
      const letras = dia.treinos.map((t) => t.letra).join("");
      celula.innerHTML = `<button type="button">${dia.dia}<span class="marca-treino">${letras}</span></button>`;

      celula.querySelector("button").addEventListener("click", () => {
        diaSelecionado = dia.data;
        corpo.querySelectorAll(".selecionado").forEach((c) => c.classList.remove("selecionado"));
        celula.classList.add("selecionado");
        mostrarDetalhesDoDia(dia);
      });
      linha.appendChild(celula);
    }
    corpo.appendChild(linha);
  }
  mostrarDetalhesDoDia(diaParaMostrar);
  desenharEvolucao();

  treinosNaSemana = frequencia.feitos_semana;
  metaSemanal = frequencia.meta_semanal;
  desenharMeta();
}

// Gráfico de barras: quantos treinos em cada uma das últimas 8 semanas
function desenharEvolucao() {
  const maior = Math.max(1, frequencia.meta_semanal, ...frequencia.evolucao.map((s) => s.total));
  let html = "";
  for (const semana of frequencia.evolucao) {
    let classe = "";
    if (semana.atual) classe = "atual";
    else if (semana.total >= frequencia.meta_semanal) classe = "ok";
    const altura = Math.round((semana.total / maior) * 100);
    html += `<div class="${classe}"><b>${semana.total}</b><i style="--h:${altura}%"></i><span>${semana.rotulo}</span></div>`;
  }
  document.getElementById("evolucao").innerHTML = html;
}

// Busca outro mês no servidor sem recarregar a página
async function carregarMes(mes) {
  if (!mes) return;
  const resposta = await fetch(`${area.dataset.urlFrequencia}?ano=${mes.ano}&mes=${mes.mes}`);
  const dados = await resposta.json();
  frequencia.semanas = dados.semanas;
  frequencia.titulo = dados.titulo;
  frequencia.no_mes = dados.no_mes;
  frequencia.anterior = dados.anterior;
  frequencia.proximo = dados.proximo;
  diaSelecionado = null;
  desenharCalendario();
}

document.getElementById("mes-anterior").addEventListener("click", () => carregarMes(frequencia.anterior));
document.getElementById("mes-proximo").addEventListener("click", () => carregarMes(frequencia.proximo));
desenharCalendario();


// =====================================================================
// 4. CRONÔMETRO DE DESCANSO
// =====================================================================

const cronometro = document.getElementById("timer");
let segundosRestantes = 0;
let segundosTotais = 0;
let intervaloCronometro = null;

function desenharCronometro() {
  const minutos = Math.floor(segundosRestantes / 60);
  const segundos = String(segundosRestantes % 60).padStart(2, "0");
  document.getElementById("timer-tempo").textContent = minutos + ":" + segundos;
  // o anel tem 176 de comprimento e vai esvaziando
  document.getElementById("timer-anel").style.strokeDashoffset = 176 * (1 - segundosRestantes / segundosTotais);
}

function esconderCronometro() {
  clearInterval(intervaloCronometro);
  cronometro.classList.remove("visivel", "acabou");
}

// Toca 3 bipes quando o descanso acaba (e vibra no celular)
function tocarBipe() {
  const audio = new AudioContext();
  for (let i = 0; i < 3; i++) {
    const som = audio.createOscillator();
    som.frequency.value = 880;
    som.connect(audio.destination);
    som.start(audio.currentTime + i * 0.25);
    som.stop(audio.currentTime + i * 0.25 + 0.15);
  }
  if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
}

function iniciarDescanso(segundos, proximoExercicio) {
  clearInterval(intervaloCronometro);
  if (segundos <= 0) return;
  segundosRestantes = segundos;
  segundosTotais = segundos;
  cronometro.classList.remove("acabou");
  cronometro.classList.add("visivel");
  document.getElementById("timer-titulo").textContent = "Descanso";
  document.getElementById("timer-sub").textContent = proximoExercicio ? "Próximo: " + proximoExercicio : "Respira e se hidrata";
  desenharCronometro();

  // a cada 1 segundo, diminui 1
  intervaloCronometro = setInterval(() => {
    segundosRestantes--;
    desenharCronometro();
    if (segundosRestantes <= 0) {
      clearInterval(intervaloCronometro);
      cronometro.classList.add("acabou");
      document.getElementById("timer-titulo").textContent = "Bora! 💪";
      document.getElementById("timer-sub").textContent = "Descanso acabou, próxima série";
      tocarBipe();
      setTimeout(esconderCronometro, 4000);
    }
  }, 1000);
}

document.getElementById("timer-mais").addEventListener("click", () => {
  segundosRestantes += 15;
  segundosTotais += 15;
  desenharCronometro();
});
document.getElementById("timer-pular").addEventListener("click", esconderCronometro);


// =====================================================================
// 5. MODO TREINO
// Cada aba de treino tem botões "Série 1, Série 2...". Ao marcar uma série,
// o cronômetro de descanso começa. O progresso fica guardado no navegador
// (localStorage), então não se perde se a página recarregar.
// =====================================================================

// Chuva de confete quando o treino é finalizado
function soltarConfete() {
  const cores = ["#FFC83D", "#FFF1A8", "#FF8A00", "#3DDC84", "#FFFFFF"];
  for (let i = 0; i < 80; i++) {
    const pedaco = document.createElement("span");
    pedaco.className = "confete";
    pedaco.style.left = Math.random() * 100 + "vw";
    pedaco.style.background = cores[i % cores.length];
    pedaco.style.animationDelay = Math.random() * 0.6 + "s";
    document.body.appendChild(pedaco);
    setTimeout(() => pedaco.remove(), 3500);
  }
}

function prepararTreino(painel) {
  const totalSeries = Number(painel.dataset.total);
  const jaFeitoHoje = painel.dataset.feitoHoje === "1";
  const chaveNoNavegador = "stars-treino-" + painel.dataset.treino + "-" + HOJE;
  const botoesSerie = [...painel.querySelectorAll(".serie")];
  let inicioDoTreino = null;      // hora em que o aluno começou (para medir o tempo)
  let relogio = null;

  // ---- salvar e carregar o progresso no navegador ----
  function salvarProgresso() {
    const marcadas = [];
    botoesSerie.forEach((botao, posicao) => {
      if (botao.classList.contains("feita")) marcadas.push(posicao);
    });
    localStorage.setItem(chaveNoNavegador, JSON.stringify({ inicio: inicioDoTreino, marcadas: marcadas }));
  }

  function carregarProgresso() {
    const salvo = JSON.parse(localStorage.getItem(chaveNoNavegador));
    if (!salvo) return;
    inicioDoTreino = salvo.inicio;
    salvo.marcadas.forEach((posicao) => botoesSerie[posicao].classList.add("feita"));
    comecarTreino();
    abrirTreino(painel.dataset.treino);
  }

  // ---- contar séries e atualizar a barra de progresso ----
  function contarFeitas() {
    return painel.querySelectorAll(".serie.feita").length;
  }

  function atualizarProgresso() {
    const feitas = contarFeitas();
    painel.querySelector("[data-feitas]").textContent = feitas;
    painel.querySelector("[data-barra]").style.width = (feitas / totalSeries) * 100 + "%";
    // exercício com todas as séries marcadas fica verde
    painel.querySelectorAll(".exercicio").forEach((exercicio) => {
      const faltam = exercicio.querySelectorAll(".serie:not(.feita)").length;
      exercicio.classList.toggle("exercicio--feito", faltam === 0);
    });
  }

  // ---- relógio do tempo total de treino ----
  function mostrarTempo() {
    const segundos = Math.floor((Date.now() - inicioDoTreino) / 1000);
    const minutos = String(Math.floor(segundos / 60)).padStart(2, "0");
    const resto = String(segundos % 60).padStart(2, "0");
    painel.querySelector("[data-tempo]").textContent = minutos + ":" + resto;
  }

  function comecarTreino() {
    if (!inicioDoTreino) inicioDoTreino = Date.now();
    painel.classList.add("treino--ativo");          // mostra a barra de progresso
    const botaoIniciar = painel.querySelector("[data-iniciar]");
    if (botaoIniciar) botaoIniciar.hidden = true;
    if (!relogio) relogio = setInterval(mostrarTempo, 1000);
    mostrarTempo();
  }

  function recomecarTreino() {
    localStorage.removeItem(chaveNoNavegador);
    clearInterval(relogio);
    relogio = null;
    inicioDoTreino = null;
    botoesSerie.forEach((botao) => botao.classList.remove("feita"));
    painel.classList.remove("treino--ativo");
    const botaoIniciar = painel.querySelector("[data-iniciar]");
    if (botaoIniciar) botaoIniciar.hidden = false;
    esconderCronometro();
    atualizarProgresso();
  }

  // ---- clicar numa série ----
  botoesSerie.forEach((botao) => {
    botao.addEventListener("click", () => {
      comecarTreino();
      botao.classList.toggle("feita");
      salvarProgresso();
      atualizarProgresso();

      if (!botao.classList.contains("feita")) return;      // desmarcou: não faz mais nada
      if (contarFeitas() === totalSeries) {
        esconderCronometro();
        mostrarAviso("Todas as séries feitas! Toque em Finalizar treino. ⭐", "sucesso");
        return;
      }
      const exercicio = botao.closest(".exercicio");
      const temMaisSerie = exercicio.querySelector(".serie:not(.feita)");
      const proximo = temMaisSerie ? exercicio : exercicio.nextElementSibling;
      iniciarDescanso(Number(exercicio.dataset.descanso), proximo ? proximo.dataset.nome : "");
    });
  });

  // ---- abrir/fechar "como fazer" do exercício ----
  painel.querySelectorAll("[data-detalhes]").forEach((botao) => {
    botao.addEventListener("click", () => botao.closest(".exercicio").classList.toggle("aberto"));
  });

  // ---- botões Iniciar, Recomeçar e Finalizar ----
  const botaoIniciar = painel.querySelector("[data-iniciar]");
  if (botaoIniciar) botaoIniciar.addEventListener("click", comecarTreino);

  painel.querySelector("[data-zerar]").addEventListener("click", () => {
    if (confirm("Recomeçar o treino? As séries marcadas serão apagadas.")) recomecarTreino();
  });

  painel.querySelector("[data-finalizar]").addEventListener("click", async () => {
    const feitas = contarFeitas();
    if (feitas === 0) {
      mostrarAviso("Marque pelo menos uma série antes de finalizar.", "erro");
      return;
    }
    if (feitas < totalSeries && !confirm(`Você fez ${feitas} de ${totalSeries} séries. Finalizar mesmo assim?`)) return;

    const minutos = Math.max(1, Math.round((Date.now() - inicioDoTreino) / 60000));
    const resposta = await enviarParaServidor(painel.dataset.url, { series_feitas: feitas, duracao_min: minutos });
    if (!resposta.ok) {
      mostrarAviso(resposta.erro, "erro");
      return;
    }
    localStorage.removeItem(chaveNoNavegador);
    esconderCronometro();
    soltarConfete();
    setTimeout(() => location.reload(), 1600);     // recarrega para mostrar no histórico
  });

  // se o aluno recarregou a página no meio do treino, continua de onde parou
  if (!jaFeitoHoje) carregarProgresso();
  atualizarProgresso();
}

document.querySelectorAll(".treino[data-treino]").forEach(prepararTreino);
