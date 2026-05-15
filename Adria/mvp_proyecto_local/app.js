const state = {
  file: null,
  imageUrl: null,
  solution: null,
  chatHistory: [],
  solving: false,
  statusPollingId: null,
  statusPollInFlight: false,
  mathTypesetTimer: null,
  mathTypesetRoots: new Set(),
  columnResize: null,
  language: "castellano",
  academicLevel: "eso_bachillerato",
};

const columnLayoutKey = "mathvision-column-layout";

const api = {
  async health() {
    const response = await fetch("/api/health");
    return readJson(response);
  },

  async solveProblem(file, language) {
    console.log("[PRINT solver] Llamada a /api/solve:", {
      fileName: file?.name,
      language,
    });

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    const response = await fetch("/api/solve", {
      method: "POST",
      body: formData,
    });
    return readJson(response);
  },

  async pipelineStatus() {
    const response = await fetch("/api/solve/status", { cache: "no-store" });
    return readJson(response);
  },

  async answerChat(question) {
    console.log("[PRINT chat] Llamada a /api/chat:", {
      question,
      hasSolution: Boolean(state.solution),
      historyLength: state.chatHistory.length,
    });

    const payload = {
      question,
      statement: state.solution?.statement || "",
      visual_grounding: state.solution?.visual_grounding || "",
      final_answer: state.solution?.final_answer || "",
      summary: state.solution?.summary || "",
      steps: state.solution?.steps || [],
      classification: state.solution?.classification || {},
      option_justifications: state.solution?.option_justifications || [],
      history: state.chatHistory.slice(-6),
    };

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return readJson(response);
  },
};

const languageButtons = document.querySelectorAll("[data-language]");
const academicButtons = document.querySelectorAll("[data-academic-level]");
const imageInput = document.querySelector("#imageInput");
const dropzone = document.querySelector("#dropzone");
const chatForm = document.querySelector("#chatForm");
const chatQuestion = document.querySelector("#chatQuestion");
const chatMessages = document.querySelector("#chatMessages");
const problemPreview = document.querySelector(".problem-preview");
const problemPreviewPlaceholder = document.querySelector("#problemPreviewPlaceholder");
const problemImagePreview = document.querySelector("#problemImagePreview");
const inputStatus = document.querySelector("#inputStatus");
const solveButton = document.querySelector("#solveButton");
const solutionStatus = document.querySelector("#solutionStatus");
const finalAnswer = document.querySelector("#finalAnswer");
const summaryText = document.querySelector("#summaryText");
const reasoningList = document.querySelector("#reasoningList");
const classificationInfo = document.querySelector("#classificationInfo");
const cropGallery = document.querySelector("#cropGallery");
const optionJustifications = document.querySelector("#optionJustifications");
const workspace = document.querySelector(".workspace");
const columnResizers = document.querySelectorAll("[data-resizer]");

async function readJson(response) {
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    console.log("[PRINT api] Respuesta no JSON:", error);
  }

  if (!response.ok) {
    const message = data.error || `Error HTTP ${response.status}`;
    const command = data.install_command ? `\n${data.install_command}` : "";
    throw new Error(`${message}${command}`);
  }

  return data;
}

function setStatus(element, message, type = "") {
  element.textContent = message;
  element.classList.remove("error", "success");
  if (type) {
    element.classList.add(type);
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function parsePixelVariable(name, fallback) {
  if (!workspace) return fallback;
  const value = window.getComputedStyle(workspace).getPropertyValue(name).trim();
  const parsed = Number.parseFloat(value);

  return Number.isFinite(parsed) ? parsed : fallback;
}

function loadColumnLayout() {
  if (!workspace) return;

  try {
    const saved = JSON.parse(window.localStorage.getItem(columnLayoutKey) || "{}");
    if (Number.isFinite(saved.input)) {
      workspace.style.setProperty("--input-col", `${saved.input}px`);
    }
    if (Number.isFinite(saved.chat)) {
      workspace.style.setProperty("--chat-col", `${saved.chat}px`);
    }
  } catch (error) {
    console.log("[PRINT layout] No se pudo cargar la anchura de columnas:", error);
  }
}

function saveColumnLayout() {
  if (!workspace) return;

  const input = parsePixelVariable("--input-col", 310);
  const chat = parsePixelVariable("--chat-col", 330);
  window.localStorage.setItem(columnLayoutKey, JSON.stringify({ input, chat }));
}

function startColumnResize(event) {
  if (!workspace || window.matchMedia("(max-width: 1120px)").matches) return;

  const type = event.currentTarget.dataset.resizer;
  const rect = workspace.getBoundingClientRect();
  const input = parsePixelVariable("--input-col", 310);
  const chat = parsePixelVariable("--chat-col", 330);
  const solution = rect.width - input - chat - 24 - 16;

  state.columnResize = {
    type,
    startX: event.clientX,
    input,
    chat,
    solution,
    handle: event.currentTarget,
  };

  event.currentTarget.classList.add("dragging");
  document.body.classList.add("resizing-columns");
  event.currentTarget.setPointerCapture?.(event.pointerId);
}

function updateColumnResize(event) {
  if (!state.columnResize || !workspace) return;

  const delta = event.clientX - state.columnResize.startX;
  const minInput = 260;
  const minSolution = 360;
  const minChat = 280;

  if (state.columnResize.type === "left") {
    const pairTotal = state.columnResize.input + state.columnResize.solution;
    const input = clamp(state.columnResize.input + delta, minInput, pairTotal - minSolution);
    workspace.style.setProperty("--input-col", `${Math.round(input)}px`);
  } else {
    const pairTotal = state.columnResize.solution + state.columnResize.chat;
    const chat = clamp(state.columnResize.chat - delta, minChat, pairTotal - minSolution);
    workspace.style.setProperty("--chat-col", `${Math.round(chat)}px`);
  }
}

function stopColumnResize() {
  if (!state.columnResize) return;

  state.columnResize.handle?.classList.remove("dragging");
  state.columnResize = null;
  document.body.classList.remove("resizing-columns");
  saveColumnLayout();
}

function clearMathTypeset(root) {
  if (window.MathJax?.typesetClear) {
    try {
      window.MathJax.typesetClear([root]);
    } catch (error) {
      console.log("[PRINT math] No se pudo limpiar MathJax:", error);
    }
  }
}

function renderRichText(element, text) {
  clearMathTypeset(element);
  element.classList.add("rich-text");
  element.textContent = text == null ? "" : String(text);
  queueMathTypeset(element);
}

function queueMathTypeset(root = document.body) {
  state.mathTypesetRoots.add(root);

  if (state.mathTypesetTimer) {
    window.clearTimeout(state.mathTypesetTimer);
  }

  state.mathTypesetTimer = window.setTimeout(() => {
    state.mathTypesetTimer = null;
    const roots = [...state.mathTypesetRoots].filter((item) => item?.isConnected);
    state.mathTypesetRoots.clear();
    const mathJax = window.MathJax;

    if (!mathJax?.typesetPromise) return;

    mathJax
      .typesetPromise(roots.length ? roots : [document.body])
      .catch((error) => console.log("[PRINT math] No se pudo renderizar MathJax:", error));
  }, 0);
}

async function refreshPipelineStatus() {
  if (!state.solving || state.statusPollInFlight) return;
  state.statusPollInFlight = true;
  try {
    const status = await api.pipelineStatus();
    if (state.solving && status.message) {
      setStatus(solutionStatus, status.message);
    }
  } catch (error) {
    console.log("[PRINT solver] No se pudo leer el estado del pipeline:", error);
  } finally {
    state.statusPollInFlight = false;
  }
}

function startPipelineStatusPolling() {
  stopPipelineStatusPolling();
  refreshPipelineStatus();
  state.statusPollingId = window.setInterval(refreshPipelineStatus, 700);
}

function stopPipelineStatusPolling() {
  if (state.statusPollingId) {
    window.clearInterval(state.statusPollingId);
    state.statusPollingId = null;
  }
}

function openImagePicker() {
  console.log("[PRINT UI] Abrir selector de imagen.");
  imageInput.click();
}

function handleImageFile(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    setStatus(inputStatus, "El archivo seleccionado no es una imagen compatible.", "error");
    return;
  }

  console.log("[PRINT UI] Subida de imagen:", {
    name: file.name,
    type: file.type,
    size: file.size,
  });

  state.file = file;
  state.solution = null;
  state.chatHistory = [];
  showImagePreview(file);
  resetSolutionView();
  setStatus(inputStatus, "Imagen lista. Pulsa Resolver problema para ejecutar el pipeline completo.", "success");
  setStatus(solutionStatus, "La solución aparecerá después de resolver.");
  solveButton.disabled = false;
}

function showImagePreview(file) {
  if (state.imageUrl) {
    URL.revokeObjectURL(state.imageUrl);
  }
  state.imageUrl = URL.createObjectURL(file);
  problemImagePreview.src = state.imageUrl;
  problemImagePreview.alt = `Vista previa de ${file.name}`;
  problemImagePreview.hidden = false;
  problemPreviewPlaceholder.hidden = true;
  problemPreview.classList.remove("empty-preview");
}

function resetSolutionView() {
  clearMathTypeset(summaryText);
  clearMathTypeset(reasoningList);
  clearMathTypeset(optionJustifications);
  finalAnswer.textContent = "Respuesta final: pendiente";
  summaryText.textContent = "Todavía no hay una resolución generada.";
  classificationInfo.textContent = "El pipeline mostrará aquí si el enunciado/opciones son texto o figura.";
  cropGallery.innerHTML = "";
  optionJustifications.innerHTML = `
    <article class="option-card">
      <strong>Opciones A-E</strong>
      <p>El pipeline verificará cada opción por separado cuando resuelva el problema.</p>
    </article>
  `;
  reasoningList.innerHTML = `
    <li>
      <span class="step-number">1</span>
      <div>
        <p>Sube una imagen y pulsa "Resolver problema".</p>
      </div>
    </li>
  `;
}

function createBrainIcon() {
  const icon = document.createElement("span");
  icon.className = "mini-brain";
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = `
    <svg viewBox="0 0 48 48">
      <path d="M20.4 7c-3.1 0-5.7 2.3-6 5.4-3.5.3-6.1 3.2-6.1 6.8 0 1 .2 2 .7 2.9-2.1 1.5-3.5 3.8-3.5 6.6 0 4.1 3.2 7.5 7.2 7.9.7 2.7 3.2 4.8 6.2 4.8h3.2V7h-1.7Z" />
      <path d="M27.6 7c3.1 0 5.7 2.3 6 5.4 3.5.3 6.1 3.2 6.1 6.8 0 1-.2 2-.7 2.9 2.1 1.5 3.5 3.8 3.5 6.6 0 4.1-3.2 7.5-7.2 7.9-.7 2.7-3.2 4.8-6.2 4.8h-3.2V7h1.7Z" />
      <path d="M24 11v30M15 17c2.4.1 4.3 2 4.6 4.3M33 17c-2.4.1-4.3 2-4.6 4.3M14 29c1.8-.3 3.4.2 4.6 1.5M34 29c-1.8-.3-3.4.2-4.6 1.5" />
    </svg>
  `;

  return icon;
}

function addChatMessage(author, text, loading = false) {
  const row = document.createElement("div");
  const bubble = document.createElement("p");

  bubble.className = author === "user" ? "chat-bubble user-bubble small" : "chat-bubble ai-bubble";
  renderRichText(bubble, text);
  if (loading) {
    bubble.classList.add("loading-bubble");
  }
  row.className = author === "user" ? "message-row user-row" : "message-row ai-row";

  if (author === "assistant") {
    row.append(createBrainIcon());
  }

  row.append(bubble);
  chatMessages.append(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

function normalizeFinalOption(finalAnswer) {
  const text = String(finalAnswer || "").trim().toUpperCase();
  const match = text.match(/^\$*\s*([A-E])\s*\$*(?:[\s.)\]:,-]|$)/);

  return match ? match[1] : "";
}

function visualOptionStatus(option, finalAnswer, fallbackStatus) {
  const finalOption = normalizeFinalOption(finalAnswer);
  const optionLetter = String(option || "").trim().toUpperCase();

  if (!finalOption || !optionLetter) {
    return fallbackStatus || "uncertain";
  }

  return optionLetter === finalOption ? "correct" : "incorrect";
}

function renderSolution(result) {
  state.solution = result;
  renderRichText(finalAnswer, `Respuesta final: ${result.final_answer || "Respuesta no determinada"}`);
  renderRichText(summaryText, result.summary || "El modelo no devolvió resumen.");
  const statusMessage = result.json_valid
    ? "Resolución generada por CROPEAR."
    : "Resolución generada por CROPEAR con avisos de parseo.";
  setStatus(solutionStatus, statusMessage, "success");

  renderClassification(result);
  renderCropGallery(result.crop_images || {}, result.annotated_crops_image, result.ocr_sections_image);
  renderOptionJustifications(result.option_justifications || [], result.final_answer);

  clearMathTypeset(reasoningList);
  reasoningList.innerHTML = "";
  const steps = Array.isArray(result.steps) && result.steps.length ? result.steps : ["No se generaron pasos."];
  steps.forEach((step, index) => {
    const item = document.createElement("li");
    const number = document.createElement("span");
    const wrapper = document.createElement("div");
    const paragraph = document.createElement("p");

    number.className = "step-number";
    number.textContent = String(index + 1);
    renderRichText(paragraph, step);
    wrapper.append(paragraph);
    item.append(number, wrapper);
    reasoningList.append(item);
  });
}

function renderClassification(result) {
  const classification = result.classification || {};
  const statementLabels = {
    "A.1": "solo texto",
    "A.2": "con figura",
  };
  const optionLabels = {
    "B.1": "texto, números o expresiones",
    "B.2": "figuras",
  };
  const statementType = statementLabels[classification.statement_type] || "sin clasificar";
  const optionsType = optionLabels[classification.options_type] || "sin clasificar";
  const badCrops = Array.isArray(result.bad_crops) && result.bad_crops.length
    ? ` · recortes revisados con imagen completa: ${result.bad_crops.join(", ")}`
    : "";
  classificationInfo.textContent = `Enunciado ${statementType}, opciones ${optionsType}${badCrops}`;
}

function renderCropGallery(cropImages, annotatedCropsImage, ocrSectionsImage) {
  cropGallery.innerHTML = "";

  [
    ["Secciones", ocrSectionsImage],
    ["Recortes", annotatedCropsImage],
  ].forEach(([label, url]) => {
    if (!url) return;
    cropGallery.append(createCropCard(label, url, "Vista de control"));
  });

  Object.entries(cropImages).forEach(([label, crop]) => {
    if (!crop?.url) return;
    cropGallery.append(createCropCard(label, crop.url, crop.color || ""));
  });

  if (!cropGallery.children.length) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "No hay recortes visuales para este caso.";
    cropGallery.append(empty);
  }
}

function createCropCard(label, url, meta) {
  const card = document.createElement("figure");
  const image = document.createElement("img");
  const caption = document.createElement("figcaption");

  card.className = "crop-card";
  image.src = url;
  image.alt = `Recorte ${label}`;
  caption.textContent = meta ? `${label} · ${meta}` : label;

  card.append(image, caption);
  return card;
}

function renderOptionJustifications(options, finalAnswer = "") {
  clearMathTypeset(optionJustifications);
  optionJustifications.innerHTML = "";
  const items = Array.isArray(options) && options.length ? options : [];

  if (!items.length) {
    const empty = document.createElement("article");
    empty.className = "option-card";
    empty.innerHTML = "<strong>Sin opciones</strong><p>No se generó análisis por opción.</p>";
    optionJustifications.append(empty);
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("article");
    const header = document.createElement("div");
    const title = document.createElement("strong");
    const badge = document.createElement("span");
    const reasoning = document.createElement("p");

    card.className = "option-card";
    header.className = "option-header";
    title.textContent = `Opción ${item.option}`;
    const displayStatus = visualOptionStatus(item.option, finalAnswer, item.status);
    badge.className = `option-status status-${displayStatus}`;
    badge.textContent = displayStatus;
    renderRichText(reasoning, item.reasoning || "Sin justificación.");

    header.append(title, badge);
    card.append(header);

    if (item.option_text || item.option_value) {
      const value = document.createElement("p");
      value.className = "option-value";
      renderRichText(value, item.option_text || String(item.option_value));
      card.append(value);
    }

    if (item.crop_url) {
      const image = document.createElement("img");
      image.className = "option-crop";
      image.src = item.crop_url;
      image.alt = `Recorte opción ${item.option}`;
      card.append(image);
    }

    card.append(reasoning);

    const checks = Array.isArray(item.checks) ? item.checks.filter(Boolean) : [];
    if (checks.length) {
      const list = document.createElement("ul");
      checks.forEach((check) => {
        const li = document.createElement("li");
        renderRichText(li, check);
        list.append(li);
      });
      card.append(list);
    }

    optionJustifications.append(card);
  });
}

async function solveCurrentProblem() {
  if (state.solving) return;
  if (!state.file) {
    setStatus(inputStatus, "Selecciona primero una imagen del problema.", "error");
    return;
  }

  state.solving = true;
  solveButton.disabled = true;
  setStatus(solutionStatus, "Preparando pipeline CROPEAR...");
  startPipelineStatusPolling();

  try {
    const result = await api.solveProblem(state.file, state.language);
    console.log("[PRINT solver] Respuesta recibida:", result);
    state.solving = false;
    stopPipelineStatusPolling();
    renderSolution(result);
  } catch (error) {
    console.log("[PRINT solver] Error recibido:", error);
    state.solving = false;
    stopPipelineStatusPolling();
    setStatus(solutionStatus, error.message || "No se pudo resolver el problema.", "error");
  } finally {
    state.solving = false;
    stopPipelineStatusPolling();
    solveButton.disabled = false;
  }
}

languageButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.language = button.dataset.language || "castellano";
    languageButtons.forEach((item) => {
      item.classList.toggle("language-button-active", item === button);
    });
    console.log("[PRINT UI] Idioma seleccionado:", state.language);
    if (state.file) {
      setStatus(inputStatus, "Idioma actualizado. Resolver usará este idioma en todos los prompts.");
    }
  });
});

academicButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.academicLevel = button.dataset.academicLevel || "eso_bachillerato";
    academicButtons.forEach((item) => {
      item.classList.toggle("academic-button-active", item === button);
    });
    console.log("[PRINT UI] Nivel académico seleccionado:", state.academicLevel);
  });
});

dropzone.addEventListener("click", openImagePicker);

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragging");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragging");
});

dropzone.addEventListener("drop", async (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragging");
  await handleImageFile(event.dataTransfer.files[0]);
});

imageInput.addEventListener("change", async (event) => {
  await handleImageFile(event.target.files[0]);
  event.target.value = "";
});

loadColumnLayout();
columnResizers.forEach((resizer) => {
  resizer.addEventListener("pointerdown", startColumnResize);
});
window.addEventListener("pointermove", updateColumnResize);
window.addEventListener("pointerup", stopColumnResize);
window.addEventListener("pointercancel", stopColumnResize);

solveButton.addEventListener("click", solveCurrentProblem);

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = chatQuestion.value.trim();
  if (!question) return;

  if (!state.solution) {
    addChatMessage("assistant", "Primero resuelve un problema para poder usar su contexto.");
    return;
  }

  addChatMessage("user", question);
  chatQuestion.value = "";
  const loadingBubble = addChatMessage("assistant", "Pensando...", true);

  try {
    const response = await api.answerChat(question);
    console.log("[PRINT chat] Respuesta recibida:", response);
    const answer = response.answer || "No se recibió respuesta.";
    renderRichText(loadingBubble, answer);
    loadingBubble.classList.remove("loading-bubble");
    state.chatHistory.push({ role: "user", content: question });
    state.chatHistory.push({ role: "assistant", content: answer });
  } catch (error) {
    console.log("[PRINT chat] Error recibido:", error);
    renderRichText(loadingBubble, error.message || "No se pudo responder.");
    loadingBubble.classList.remove("loading-bubble");
  }
});

document.addEventListener("mathjax-ready", () => queueMathTypeset(document.body));

api
  .health()
  .then((health) => {
    console.log("[PRINT app] Health recibido:", health);
    const pipelineHealth = health.data_pipeline || {};
    const missingModels = pipelineHealth.ollama?.missing_models || [];
    if (missingModels.length) {
      setStatus(inputStatus, `Faltan modelos en Ollama: ${missingModels.join(", ")}`, "error");
    } else if (pipelineHealth.pipeline_dir_exists === false) {
      setStatus(inputStatus, "No se encontró la carpeta pipelinefin.", "error");
    }
  })
  .catch((error) => {
    console.log("[PRINT app] No se pudo consultar /api/health:", error);
  });

console.log("[PRINT app] MathVision AI local cargado.");
