const app = document.querySelector("#app");

const state = {
  token: localStorage.getItem("ronda_token"),
  user: JSON.parse(localStorage.getItem("ronda_user") || "null"),
  config: { nome_empresa: "Ronda Eletronica", cor_primaria: "#1f6feb", logo_empresa: null },
  activeTab: "operacao",
  shift: null,
  employees: [],
  selectedEmployeeId: null,
  editingPointId: null,
  points: [],
  adminConfig: null,
  scanner: { stream: null, running: false },
  notice: "",
  error: "",
  printTitle: "",
  printPoints: [],
  printPreview: false,
  installPrompt: null,
  canInstall: false,
};

function html(strings, ...values) {
  return strings.reduce((result, part, index) => result + part + (values[index] ?? ""), "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmtDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function fmtTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function minutesUntil(value) {
  if (!value) return 0;
  return Math.max(Math.ceil((new Date(value).getTime() - Date.now()) / 60000), 0);
}

function numberOrNull(value) {
  const text = String(value ?? "").trim();
  return text ? Number(text) : null;
}

function fmtMeters(value) {
  if (value === null || value === undefined || value === "") return "-";
  return `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} m`;
}

function gpsErrorMessage(error) {
  if (error?.code === 1) return "Permissao de GPS negada. Autorize a localizacao para registrar a ronda.";
  if (error?.code === 2) return "Localizacao indisponivel. Verifique se o GPS esta ativado.";
  if (error?.code === 3) return "Nao foi possivel obter o GPS a tempo. Tente novamente em area aberta.";
  return error?.message || "Nao foi possivel capturar a localizacao GPS.";
}

function getCurrentGpsPosition() {
  if (!navigator.geolocation) {
    return Promise.reject(new Error("GPS indisponivel neste navegador ou dispositivo."));
  }
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 0,
    });
  });
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  const body = contentType.includes("application/json") && text ? JSON.parse(text) : text;
  if (!response.ok) {
    const detail = body?.detail || body || "Nao foi possivel concluir a acao.";
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail);
  }
  return body;
}

function readLocalCache(key) {
  // Le dados salvos no celular para reduzir requisicoes e consumo de dados.
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeLocalCache(key, value) {
  // Mantem uma copia local dos cadastros usados com frequencia no turno.
  localStorage.setItem(key, JSON.stringify(value));
}

async function cachedApi(path, cacheKey, forceRefresh = false) {
  // Se ja existir cache e nao for uma atualizacao forcada, carrega direto do aparelho.
  if (!forceRefresh) {
    const cached = readLocalCache(cacheKey);
    if (cached) return cached;
  }

  const data = await api(path);
  writeLocalCache(cacheKey, data);
  return data;
}

function clearOperationalCache() {
  // Limpa caches quando o usuario sair ou quando for preciso reconstruir dados locais.
  localStorage.removeItem("ronda_cache_pontos");
  localStorage.removeItem("ronda_cache_funcionarios");
}

async function buscarFuncionariosAutorizados(forceRefresh = false) {
  // Primeiro tenta carregar a lista salva no celular para economizar internet.
  // Se nao existir cache, ou se for uma atualizacao forcada, busca no backend.
  return cachedApi("/employees", "ronda_cache_funcionarios", forceRefresh);
}

function limparCacheFuncionarios() {
  // Use apos cadastrar, remover ou alterar funcionario para baixar a lista atualizada.
  localStorage.removeItem("ronda_cache_funcionarios");
}

async function boot() {
  await loadPublicConfig();
  if (state.token) {
    try {
      state.user = await api("/auth/me");
      localStorage.setItem("ronda_user", JSON.stringify(state.user));
      await loadAll();
    } catch (error) {
      clearSession();
    }
  }
  render();
}

async function loadPublicConfig() {
  try {
    state.config = await api("/ronda/public-config");
    document.documentElement.style.setProperty("--primary", state.config.cor_primaria);
  } catch {
    document.documentElement.style.setProperty("--primary", state.config.cor_primaria);
  }
}

async function loadAll(forceRefresh = false) {
  await Promise.all([
    api("/ronda/turnos/ativo").then((data) => (state.shift = data)),
    cachedApi("/ronda/pontos", "ronda_cache_pontos", forceRefresh).then(
      (data) => (state.points = data)
    ),
  ]);
  if (isAdmin()) {
    await Promise.all([
      buscarFuncionariosAutorizados(forceRefresh).then((data) => (state.employees = data)),
      api("/ronda/config").then((data) => (state.adminConfig = data)),
    ]);
  }
}

function isAdmin() {
  return ["admin", "supervisor"].includes(state.user?.role);
}

function setError(message) {
  state.error = message;
  state.notice = "";
  render();
}

function setNotice(message) {
  state.notice = message;
  state.error = "";
  render();
}

function render() {
  if (!state.token) {
    renderLogin();
    return;
  }
  app.innerHTML = html`
    <div class="shell">
      <header class="topbar">
        <div class="brand">
          ${state.config.logo_empresa ? `<img src="${escapeHtml(state.config.logo_empresa)}" alt="Logo" />` : `<div class="mark">QR</div>`}
          <div>
            <strong>${escapeHtml(state.config.nome_empresa)}</strong>
            <span>${escapeHtml(state.user?.name || "Funcionario")}</span>
          </div>
        </div>
        <div class="top-actions">
          ${installButton()}
          <button class="icon-btn" title="Sair" onclick="logout()">Sair</button>
        </div>
      </header>
      ${messageArea()}
      <nav class="tabs">
        ${tab("operacao", "Operacao")}
        ${isAdmin() ? tab("admin", "Admin") : ""}
      </nav>
      <main>
        ${state.activeTab === "admin" && isAdmin() ? adminView() : operationView()}
      </main>
      ${state.activeTab === "admin" && isAdmin() ? printSheet() : ""}
    </div>
  `;
}

function renderLogin() {
  app.innerHTML = html`
    <main class="login-screen">
      <section class="login-panel">
        <div class="login-brand">
          ${state.config.logo_empresa ? `<img src="${escapeHtml(state.config.logo_empresa)}" alt="Logo" />` : `<div class="mark large">QR</div>`}
          <h1>${escapeHtml(state.config.nome_empresa)}</h1>
          <p>Ronda eletronica por QR Code</p>
        </div>
        ${messageArea()}
        <form onsubmit="login(event)" class="form" autocomplete="off">
          <label>
            Usuario
            <input name="username" type="email" autocomplete="off" autocapitalize="none" spellcheck="false" required />
          </label>
          <label>
            Senha
            <input name="password" type="password" autocomplete="new-password" required />
          </label>
          <button class="primary" type="submit">Entrar</button>
        </form>
      </section>
    </main>
  `;
}

function messageArea() {
  return html`
    ${state.error ? `<div class="alert error">${escapeHtml(state.error)}</div>` : ""}
    ${state.notice ? `<div class="alert ok">${escapeHtml(state.notice)}</div>` : ""}
  `;
}

function installButton() {
  if (!state.canInstall || isStandaloneApp()) return "";
  return `<button class="ghost install-btn" onclick="installApp()">Instalar no celular</button>`;
}

function isStandaloneApp() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
}

function printSheet() {
  if (!state.printPoints.length) return "";
  const previewClass = state.printPreview ? " preview" : "";
  return html`
    <section class="print-sheet${previewClass}" aria-hidden="${state.printPreview ? "false" : "true"}">
      ${
        state.printPreview
          ? html`
              <div class="print-actions">
                <strong>Pre-visualizacao dos QR Codes</strong>
                <div>
                  <button class="primary" onclick="printNow()">Imprimir agora</button>
                  <button class="ghost" onclick="downloadQrPrintSheet()">Baixar folha HTML</button>
                  <button class="ghost" onclick="closePrintPreview()">Fechar</button>
                </div>
              </div>
            `
          : ""
      }
      <header>
        <h1>${escapeHtml(state.config.nome_empresa || "Ronda Eletronica")}</h1>
        <p>${escapeHtml(state.printTitle || "QR Codes dos pontos de ronda")}</p>
      </header>
      <main class="print-grid">
        ${state.printPoints
          .map(
            (point) => html`
              <article class="print-qr-card">
                <img src="/ronda/pontos/${point.id}/qr.svg" alt="QR ${escapeHtml(point.nome_ponto)}" />
                <h2>${escapeHtml(point.nome_ponto)}</h2>
                <p>${escapeHtml(point.codigo_qr)}</p>
                <small>Meta: ${point.meta_passagens_turno || 1} passagens | Carencia: ${point.carencia_minutos || 0} min</small>
              </article>
            `
          )
          .join("")}
      </main>
    </section>
  `;
}

function tab(id, label) {
  return `<button class="${state.activeTab === id ? "active" : ""}" onclick="switchTab('${id}')">${label}</button>`;
}

function operationView() {
  const shift = state.shift;
  const active = Boolean(shift?.turno);
  const employeeName = shift?.funcionario_nome || state.user?.name || "Funcionario";
  const doneIds = new Set((shift?.leituras || []).map((item) => item.ponto_qr_id));
  return html`
    <section class="hero">
      <div>
        <span>Turno atual</span>
        <strong>${active ? "Em andamento" : "Nao iniciado"}</strong>
        <small>Funcionario: ${escapeHtml(employeeName)}</small>
      </div>
      <div class="progress-ring">
        <strong>${shift?.progresso_percentual || 0}%</strong>
      </div>
    </section>

    <section class="actions">
      ${active ? `<button class="primary" onclick="openScan()">Registrar ponto</button>` : `<button class="primary" onclick="startShift()">Iniciar turno de ${escapeHtml(employeeName)}</button>`}
      ${active ? `<button class="secondary" onclick="finishShift(event)">Finalizar Turno</button>` : ""}
    </section>

    ${active ? html`
      <section class="panel final-panel">
        <label>
          Observacao final do turno
          <textarea id="finalNote" rows="2" placeholder="Opcional"></textarea>
        </label>
      </section>
    ` : ""}

    ${active ? scanPanel() : ""}

    <section class="summary-grid">
      <div><span>Total</span><strong>${shift?.total_pontos || 0}</strong></div>
      <div><span>Realizados</span><strong>${shift?.pontos_realizados || 0}</strong></div>
      <div><span>Pendentes</span><strong>${shift?.pontos_pendentes || 0}</strong></div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h2>Pontos da ronda</h2>
        <button class="ghost" onclick="refresh()">Atualizar</button>
      </div>
      <div class="point-list">
        ${(shift?.pontos || state.points.filter((point) => point.ativo)).map((point) => pointItem(point, doneIds)).join("")}
      </div>
    </section>
  `;
}

function scanPanel() {
  const shiftPoints = state.shift?.pontos || [];
  const activePoints = (shiftPoints.length ? shiftPoints : state.points).filter((point) => point.ativo !== false);
  return html`
    <section class="panel scan-panel" id="scanPanel" hidden>
      <div class="panel-title">
        <h2>Registrar ponto</h2>
        <button class="ghost" onclick="closeScan()">Fechar</button>
      </div>
      <video id="scannerVideo" playsinline muted hidden></video>
      <form class="form" onsubmit="submitReading(event)">
        <label>
          Ponto da ronda
          <div class="inline">
            <select name="codigo_qr" id="qrInput" required ${activePoints.length ? "" : "disabled"}>
              <option value="">Escolha por onde vai registrar a ronda</option>
              ${activePoints.map((point) => `
                <option value="${escapeHtml(point.codigo_qr)}">
                  ${escapeHtml(point.nome_ponto)} - ${point.passagens_realizadas || 0}/${point.meta_passagens_turno || 1}
                </option>
              `).join("")}
            </select>
            <button type="button" class="secondary" onclick="startCameraScan()">Camera</button>
          </div>
        </label>
        <label>
          Foto obrigatoria do local
          <input name="foto" type="file" accept="image/*" capture="environment" required />
        </label>
        <label>
          Observacao
          <textarea name="observacao" rows="2" placeholder="Opcional"></textarea>
        </label>
        <label>
          Ocorrencia
          <textarea name="ocorrencia" rows="2" placeholder="Opcional"></textarea>
        </label>
        <button class="primary" type="submit">Salvar leitura</button>
      </form>
    </section>
  `;
}

function pointItem(point, doneIds) {
  const done = point.passagens_realizadas >= point.meta_passagens_turno;
  const status = point.status_ronda ? pointStatusLabel(point) : done ? "Realizado" : "Pendente";
  const help = pointHelpText(point);
  return html`
    <article class="point ${done ? "done" : ""}">
      <div>
        <strong>${escapeHtml(point.nome_ponto)}</strong>
        <span>${escapeHtml(point.codigo_qr)} - ${point.passagens_realizadas || 0}/${point.meta_passagens_turno || 1} passagens</span>
        <span>Carencia: ${point.carencia_minutos || 0} min</span>
        ${help ? `<span>${escapeHtml(help)}</span>` : ""}
      </div>
      <em>${escapeHtml(status)}</em>
    </article>
  `;
}

function pointStatusLabel(point) {
  if (point.status_ronda === "meta_atingida") return "Meta atingida";
  if (point.status_ronda === "bloqueado_carencia") return "Verificado recentemente";
  if (point.status_ronda === "disponivel") return "Disponivel";
  return "Aguardando turno";
}

function pointHelpText(point) {
  if (point.status_ronda !== "bloqueado_carencia" || !point.bloqueado_ate) return "";
  const remaining = minutesUntil(point.bloqueado_ate);
  return `Proxima leitura liberada as ${fmtTime(point.bloqueado_ate)}${remaining ? `, em cerca de ${remaining} min` : ""}.`;
}

function adminView() {
  return html`
    <section class="admin-grid">
      <div class="panel">
        <div class="panel-title"><h2>Funcionarios</h2></div>
        <form class="form compact" onsubmit="createEmployee(event)">
          <input name="name" placeholder="Nome" required />
          <input name="email" type="email" placeholder="E-mail" required />
          <input name="password" type="password" placeholder="Senha inicial" required minlength="6" />
          <input name="phone" placeholder="Telefone" />
          <input name="position" placeholder="Cargo" value="Operador de ronda" />
          <select name="role">
            <option value="employee">Funcionario</option>
            <option value="supervisor">Supervisor</option>
            <option value="admin">Administrador</option>
          </select>
          <button class="primary" type="submit">Cadastrar</button>
        </form>
        <div class="table-list">
          ${state.employees.map(employeeRow).join("")}
        </div>
        ${employeeDetails()}
      </div>

      <div class="panel">
        <div class="panel-title">
          <h2>Pontos QR</h2>
          <button class="ghost" onclick="printAllQrs()">Imprimir todos</button>
        </div>
        <form class="form compact" onsubmit="createPoint(event)">
          <label>Nome do ponto<input name="nome_ponto" placeholder="Ex: Portao Principal" required /></label>
          <label>Codigo QR<input name="codigo_qr" placeholder="Opcional, o sistema pode gerar" /></label>
          <label>Ordem na ronda<input name="ordem" type="number" min="0" value="0" /></label>
          <label>Meta de passagens por turno<input name="meta_passagens_turno" type="number" min="1" value="4" /></label>
          <label>Carencia entre leituras em minutos<input name="carencia_minutos" type="number" min="0" value="45" /></label>
          <label>Latitude<input name="latitude" type="number" step="0.000001" min="-90" max="90" placeholder="-22.512345" /></label>
          <label>Longitude<input name="longitude" type="number" step="0.000001" min="-180" max="180" placeholder="-44.123456" /></label>
          <label>Raio permitido em metros<input name="raio_permitido_metros" type="number" min="1" max="1000" placeholder="${state.adminConfig?.raio_padrao_metros || 20}" /></label>
          <button class="secondary" type="button" onclick="capturePointLocation(this)">Capturar localizacao atual</button>
          <label>Descricao<textarea name="descricao" rows="2" placeholder="Detalhes opcionais do local"></textarea></label>
          <button class="primary" type="submit">Cadastrar ponto</button>
        </form>
        <div class="table-list">
          ${state.points.map(pointRow).join("")}
        </div>
      </div>

      <div class="panel wide">
        <div class="panel-title"><h2>Empresa e SMTP</h2></div>
        ${configForm()}
      </div>
    </section>
  `;
}

function employeeRow(employee) {
  const selected = state.selectedEmployeeId === employee.id;
  return html`
    <article class="row clickable ${selected ? "selected" : ""}" onclick="selectEmployee(${employee.id})">
      <div>
        <strong>${escapeHtml(employee.name)}</strong>
        <span>${escapeHtml(employee.position)} - ${employee.is_active ? "Ativo" : "Inativo"}</span>
      </div>
      <div class="row-actions">
        <button class="danger-btn" onclick="event.stopPropagation(); removeEmployee(${employee.id})">Remover</button>
      </div>
    </article>
  `;
}

function employeeDetails() {
  const employee = state.employees.find((item) => item.id === state.selectedEmployeeId);
  if (!employee) {
    return `<div class="empty-detail">Clique em um funcionario para ver as informacoes.</div>`;
  }
  return html`
    <section class="detail-card">
      <div class="panel-title">
        <h2>${escapeHtml(employee.name)}</h2>
        <button class="ghost" onclick="selectEmployee(null)">Fechar</button>
      </div>
      <div class="detail-grid">
        <div><span>E-mail</span><strong>${escapeHtml(employee.user_email || "-")}</strong></div>
        <div><span>Perfil</span><strong>${escapeHtml(roleLabel(employee.user_role))}</strong></div>
        <div><span>Cargo</span><strong>${escapeHtml(employee.position || "-")}</strong></div>
        <div><span>Telefone</span><strong>${escapeHtml(employee.phone || "-")}</strong></div>
        <div><span>Status</span><strong>${employee.is_active ? "Ativo" : "Inativo"}</strong></div>
        <div><span>Cadastro</span><strong>${fmtDate(employee.created_at)}</strong></div>
      </div>
    </section>
  `;
}

function roleLabel(role) {
  return {
    admin: "Administrador",
    supervisor: "Supervisor",
    employee: "Funcionario",
  }[role] || "-";
}

function pointRow(point) {
  if (state.editingPointId === point.id) {
    return html`
      <article class="row editing-row">
        <form class="form compact point-edit-form" onsubmit="updatePoint(event, ${point.id})">
          <label>Nome do ponto<input name="nome_ponto" required value="${escapeHtml(point.nome_ponto)}" /></label>
          <label>Codigo QR<input name="codigo_qr" required value="${escapeHtml(point.codigo_qr)}" /></label>
          <label>Ordem na ronda<input name="ordem" type="number" min="0" value="${point.ordem || 0}" /></label>
          <label>Meta de passagens por turno<input name="meta_passagens_turno" type="number" min="1" max="50" value="${point.meta_passagens_turno || 4}" /></label>
          <label>Carencia entre leituras em minutos<input name="carencia_minutos" type="number" min="0" max="1440" value="${point.carencia_minutos || 45}" /></label>
          <label>Latitude<input name="latitude" type="number" step="0.000001" min="-90" max="90" value="${point.latitude ?? ""}" /></label>
          <label>Longitude<input name="longitude" type="number" step="0.000001" min="-180" max="180" value="${point.longitude ?? ""}" /></label>
          <label>Raio permitido em metros<input name="raio_permitido_metros" type="number" min="1" max="1000" value="${point.raio_permitido_metros ?? ""}" placeholder="${state.adminConfig?.raio_padrao_metros || 20}" /></label>
          <button class="secondary" type="button" onclick="capturePointLocation(this)">Capturar localizacao atual</button>
          <label>Descricao<textarea name="descricao" rows="2">${escapeHtml(point.descricao || "")}</textarea></label>
          <label class="check"><input name="ativo" type="checkbox" ${point.ativo ? "checked" : ""} /> Ponto ativo</label>
          <div class="row-actions form-actions">
            <button class="primary" type="submit">Salvar ponto</button>
            <button class="ghost" type="button" onclick="editPoint(null)">Cancelar</button>
          </div>
        </form>
      </article>
    `;
  }

  return html`
    <article class="row">
      <div>
        <strong>${escapeHtml(point.nome_ponto)}</strong>
        <span>${escapeHtml(point.codigo_qr)} · ${point.ativo ? "Ativo" : "Inativo"}</span>
        <span>Meta: ${point.meta_passagens_turno || 1} passagens por turno - Carencia: ${point.carencia_minutos || 0} min</span>
        <span>GPS: ${point.gps_inicializado ? `${fmtMeters(point.raio_permitido_metros || state.adminConfig?.raio_padrao_metros || 20)} de raio` : "Aguardando primeira leitura"}</span>
        <img class="qr-preview" src="/ronda/pontos/${point.id}/qr.svg" alt="QR ${escapeHtml(point.nome_ponto)}" />
      </div>
      <div class="row-actions">
        <button class="ghost" onclick="editPoint(${point.id})">Editar</button>
        <button class="ghost" onclick="printPointQr(${point.id})">Imprimir QR</button>
        <button class="danger-btn" onclick="removePoint(${point.id})">Remover</button>
      </div>
    </article>
  `;
}

function configForm() {
  const config = state.adminConfig || {};
  return html`
    <form class="form config-form" onsubmit="saveConfig(event)">
      <label>Nome empresa<input name="nome_empresa" required value="${escapeHtml(config.nome_empresa || "")}" /></label>
      <label>E-mail supervisor<input name="email_supervisor" type="email" required value="${escapeHtml(config.email_supervisor || "")}" /></label>
      <label>Cor principal<input name="cor_primaria" type="color" value="${escapeHtml(config.cor_primaria || "#1f6feb")}" /></label>
      <label>Tempo minimo entre leituras<input name="tempo_minimo_leituras_segundos" type="number" min="0" value="${config.tempo_minimo_leituras_segundos ?? 30}" /></label>
      <label>Raio GPS padrao em metros<input name="raio_padrao_metros" type="number" min="1" max="1000" value="${config.raio_padrao_metros ?? 20}" /></label>
      <label>Host SMTP<input name="smtp_host" value="${escapeHtml(config.smtp_host || "")}" /></label>
      <label>Porta SMTP<input name="smtp_porta" type="number" value="${config.smtp_porta || 587}" /></label>
      <label>E-mail remetente<input name="smtp_email_remetente" type="email" value="${escapeHtml(config.smtp_email_remetente || "")}" /></label>
      <label>Senha SMTP<input name="smtp_senha" type="password" placeholder="Manter atual se vazio" /></label>
      <label class="check"><input name="smtp_tls" type="checkbox" ${config.smtp_tls !== false ? "checked" : ""} /> Usar TLS</label>
      <button class="primary" type="submit">Salvar configuracoes</button>
    </form>
    <form class="form logo-form" onsubmit="uploadLogo(event)">
      <label>Logo da empresa<input name="logo" type="file" accept="image/*" required /></label>
      <button class="secondary" type="submit">Enviar logo</button>
    </form>
  `;
}

async function login(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const data = new FormData(formElement);
  try {
    const body = new URLSearchParams(data);
    const result = await api("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    state.token = result.access_token;
    state.user = result.user;
    localStorage.setItem("ronda_token", state.token);
    localStorage.setItem("ronda_user", JSON.stringify(state.user));
    await loadAll();
    setNotice("Login realizado.");
  } catch (error) {
    setError(error.message);
  }
}

async function startShift() {
  try {
    await api("/ronda/turnos/iniciar", { method: "POST" });
    await refresh();
    setNotice("Turno iniciado.");
  } catch (error) {
    setError(error.message);
  }
}

function openScan() {
  const panel = document.querySelector("#scanPanel");
  if (panel) panel.hidden = false;
}

function closeScan() {
  stopCameraScan();
  const panel = document.querySelector("#scanPanel");
  if (panel) panel.hidden = true;
}

async function submitReading(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  try {
    setNotice("Capturando localizacao GPS...");
    const position = await getCurrentGpsPosition();
    const data = new FormData(formElement);
    data.append("gps_latitude", position.coords.latitude);
    data.append("gps_longitude", position.coords.longitude);
    data.append("gps_precisao_metros", position.coords.accuracy);
    data.append("gps_data_hora", new Date(position.timestamp).toISOString());
    await api("/ronda/leituras", { method: "POST", body: data });
    formElement.reset();
    stopCameraScan();
    await refresh();
    setNotice("Leitura registrada com foto.");
  } catch (error) {
    await refresh();
    setError(gpsErrorMessage(error));
  }
}

async function finishShift(event) {
  const button = event?.currentTarget;
  const observacao_final = document.querySelector("#finalNote")?.value || "";
  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Finalizando...";
    }
    const result = await api("/ronda/turnos/finalizar", {
      method: "POST",
      body: JSON.stringify({ observacao_final }),
    });
    await refresh();
    setNotice(result.email_status || "Turno finalizado.");
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.textContent = "Finalizar Turno";
    }
    setError(error.message);
  }
}

async function logout() {
  try {
    if (state.shift?.turno) {
      await api("/ronda/logout", {
        method: "POST",
        body: JSON.stringify({ observacao_final: "Logout do funcionario." }),
      });
    }
  } catch {
    // O logout local continua mesmo se o encerramento remoto falhar.
  }
  clearSession();
  render();
}

async function installApp() {
  if (!state.installPrompt) {
    setNotice("No Android, abra o menu do navegador e toque em Adicionar a tela inicial.");
    return;
  }
  state.installPrompt.prompt();
  const choice = await state.installPrompt.userChoice;
  state.installPrompt = null;
  state.canInstall = false;
  render();
  if (choice.outcome === "accepted") {
    setNotice("Aplicativo instalado na tela inicial.");
  } else {
    setNotice("Instalacao cancelada. Voce pode instalar depois pelo menu do navegador.");
  }
}

function clearSession() {
  stopCameraScan();
  state.token = null;
  state.user = null;
  state.shift = null;
  localStorage.removeItem("ronda_token");
  localStorage.removeItem("ronda_user");
}

async function refresh() {
  await loadPublicConfig();
  await loadAll(true);
  render();
}

function switchTab(tab) {
  state.activeTab = tab;
  if (tab !== "admin") {
    state.printPoints = [];
    state.printTitle = "";
    state.printPreview = false;
  }
  render();
}

function selectEmployee(id) {
  state.selectedEmployeeId = id;
  render();
}

function editPoint(id) {
  state.editingPointId = id;
  render();
}

async function capturePointLocation(button) {
  const formElement = button.closest("form");
  try {
    button.disabled = true;
    button.textContent = "Capturando GPS...";
    const position = await getCurrentGpsPosition();
    formElement.latitude.value = position.coords.latitude.toFixed(6);
    formElement.longitude.value = position.coords.longitude.toFixed(6);
    setNotice(`Localizacao capturada. Precisao aproximada: ${fmtMeters(position.coords.accuracy)}.`);
  } catch (error) {
    setError(gpsErrorMessage(error));
  } finally {
    button.disabled = false;
    button.textContent = "Capturar localizacao atual";
  }
}

function printPointQr(id) {
  const point = state.points.find((item) => item.id === id);
  if (!point) return;
  prepareQrPrint([point], `QR Code - ${point.nome_ponto}`);
}

function printAllQrs() {
  if (!state.points.length) {
    setError("Nenhum ponto QR cadastrado para imprimir.");
    return;
  }
  prepareQrPrint(state.points, "QR Codes dos pontos de ronda");
}

function prepareQrPrint(points, title) {
  state.printPoints = points;
  state.printTitle = title;
  state.printPreview = true;
  state.error = "";
  state.notice = "Folha de QR Codes preparada. Se o navegador nao abrir a impressao, use Baixar folha HTML.";
  render();
  setTimeout(() => {
    document.querySelector(".print-sheet.preview")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 50);
}

function printNow() {
  window.print();
  setTimeout(() => {
    setNotice("Se a janela de impressao nao abriu, clique em Baixar folha HTML e imprima pelo Chrome ou Edge.");
  }, 600);
}

function downloadQrPrintSheet() {
  if (!state.printPoints.length) return;
  const content = buildQrPrintHtml(state.printPoints, state.printTitle);
  const blob = new Blob([content], { type: "text/html;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `qrcodes-ronda-${new Date().toISOString().slice(0, 10)}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function buildQrPrintHtml(points, title) {
  const cards = points
    .map((point) => {
      const qrUrl = `${window.location.origin}/ronda/pontos/${point.id}/qr.svg`;
      return `
        <article class="qr-card">
          <img src="${qrUrl}" alt="QR ${escapeHtml(point.nome_ponto)}" />
          <h2>${escapeHtml(point.nome_ponto)}</h2>
          <p>${escapeHtml(point.codigo_qr)}</p>
          <small>Meta: ${point.meta_passagens_turno || 1} passagens | Carencia: ${point.carencia_minutos || 0} min</small>
        </article>
      `;
    })
    .join("");

  return `<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(title || "QR Codes dos pontos de ronda")}</title>
    <style>
      * { box-sizing: border-box; }
      body { margin: 0; padding: 24px; font-family: Arial, sans-serif; color: #111827; }
      header { margin-bottom: 20px; border-bottom: 1px solid #d8e0ea; padding-bottom: 12px; }
      h1 { margin: 0 0 4px; font-size: 22px; }
      header p { margin: 0; color: #52627a; }
      .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
      .qr-card { break-inside: avoid; border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; text-align: center; }
      .qr-card img { width: 190px; height: 190px; object-fit: contain; }
      .qr-card h2 { margin: 12px 0 4px; font-size: 18px; }
      .qr-card p { margin: 0 0 8px; font-size: 13px; color: #475569; word-break: break-word; }
      .qr-card small { color: #64748b; }
      @media print { body { padding: 12mm; } }
    </style>
  </head>
  <body>
    <header>
      <h1>${escapeHtml(state.config.nome_empresa || "Ronda Eletronica")}</h1>
      <p>${escapeHtml(title || "QR Codes dos pontos de ronda")}</p>
    </header>
    <main class="grid">${cards}</main>
  </body>
</html>`;
}

function closePrintPreview() {
  state.printPoints = [];
  state.printTitle = "";
  state.printPreview = false;
  state.notice = "";
  render();
}

async function startCameraScan() {
  const video = document.querySelector("#scannerVideo");
  const input = document.querySelector("#qrInput");
  if (!("BarcodeDetector" in window)) {
    setError("Leitura automatica indisponivel neste navegador. Escolha o ponto na lista.");
    return;
  }
  try {
    const detector = new BarcodeDetector({ formats: ["qr_code"] });
    state.scanner.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    video.srcObject = state.scanner.stream;
    video.hidden = false;
    await video.play();
    state.scanner.running = true;
    const tick = async () => {
      if (!state.scanner.running) return;
      const codes = await detector.detect(video);
      if (codes.length) {
        const scannedCode = codes[0].rawValue;
        if ([...input.options].some((option) => option.value === scannedCode)) {
          input.value = scannedCode;
          setNotice("Ponto selecionado pela camera.");
        } else {
          setError("QR Code lido nao corresponde a um ponto ativo deste turno.");
        }
        stopCameraScan();
        return;
      }
      requestAnimationFrame(tick);
    };
    tick();
  } catch (error) {
    setError(error.message);
  }
}

function stopCameraScan() {
  state.scanner.running = false;
  if (state.scanner.stream) {
    state.scanner.stream.getTracks().forEach((track) => track.stop());
    state.scanner.stream = null;
  }
}

async function createEmployee(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  try {
    const form = Object.fromEntries(new FormData(formElement));
    await api("/employees", {
      method: "POST",
      body: JSON.stringify({ ...form, phone: form.phone || "", position: form.position || "Operador de ronda" }),
    });
    limparCacheFuncionarios();
    formElement.reset();
    await refresh();
    setNotice("Funcionario cadastrado.");
  } catch (error) {
    setError(error.message);
  }
}

async function toggleEmployee(id, active) {
  try {
    await api(`/employees/${id}/status?active=${active}`, { method: "PATCH" });
    limparCacheFuncionarios();
    if (!active && state.selectedEmployeeId === id) state.selectedEmployeeId = null;
    await refresh();
    setNotice("Status do funcionario atualizado.");
  } catch (error) {
    setError(error.message);
  }
}

async function removeEmployee(id) {
  if (!window.confirm("Remover este funcionario da lista operacional?")) return;
  try {
    await api(`/employees/${id}`, { method: "DELETE" });
    limparCacheFuncionarios();
    if (state.selectedEmployeeId === id) state.selectedEmployeeId = null;
    await refresh();
    setNotice("Funcionario removido da lista operacional.");
  } catch (error) {
    setError(error.message);
  }
}

async function createPoint(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  try {
    const form = Object.fromEntries(new FormData(formElement));
    if (!String(form.codigo_qr || "").trim()) {
      delete form.codigo_qr;
    }
    await api("/ronda/pontos", {
      method: "POST",
      body: JSON.stringify({
        ...form,
        ordem: Number(form.ordem || 0),
        meta_passagens_turno: Number(form.meta_passagens_turno || 4),
        carencia_minutos: Number(form.carencia_minutos || 45),
        latitude: numberOrNull(form.latitude),
        longitude: numberOrNull(form.longitude),
        raio_permitido_metros: numberOrNull(form.raio_permitido_metros),
      }),
    });
    formElement.reset();
    await refresh();
    setNotice("Ponto QR cadastrado.");
  } catch (error) {
    setError(error.message);
  }
}

async function togglePoint(id, active) {
  try {
    await api(`/ronda/pontos/${id}/status?ativo=${active}`, { method: "PATCH" });
    await refresh();
    setNotice("Status do ponto atualizado.");
  } catch (error) {
    setError(error.message);
  }
}

async function updatePoint(event, id) {
  event.preventDefault();
  const formElement = event.currentTarget;
  try {
    const form = Object.fromEntries(new FormData(formElement));
    await api(`/ronda/pontos/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        nome_ponto: form.nome_ponto,
        codigo_qr: form.codigo_qr,
        descricao: form.descricao || null,
        ordem: Number(form.ordem || 0),
        meta_passagens_turno: Number(form.meta_passagens_turno || 4),
        carencia_minutos: Number(form.carencia_minutos || 45),
        latitude: numberOrNull(form.latitude),
        longitude: numberOrNull(form.longitude),
        raio_permitido_metros: numberOrNull(form.raio_permitido_metros),
        ativo: formElement.ativo.checked,
      }),
    });
    state.editingPointId = null;
    await refresh();
    setNotice("Ponto atualizado.");
  } catch (error) {
    setError(error.message);
  }
}

async function removePoint(id) {
  if (!window.confirm("Remover este ponto da lista operacional?")) return;
  try {
    await api(`/ronda/pontos/${id}`, { method: "DELETE" });
    await refresh();
    setNotice("Ponto removido da lista operacional.");
  } catch (error) {
    setError(error.message);
  }
}

async function saveConfig(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  try {
    const data = Object.fromEntries(new FormData(formElement));
    await api("/ronda/config", {
      method: "PUT",
      body: JSON.stringify({
        ...data,
        smtp_porta: Number(data.smtp_porta || 587),
        tempo_minimo_leituras_segundos: Number(data.tempo_minimo_leituras_segundos || 0),
        raio_padrao_metros: Number(data.raio_padrao_metros || 20),
        smtp_tls: formElement.smtp_tls.checked,
      }),
    });
    await refresh();
    setNotice("Configuracoes salvas.");
  } catch (error) {
    setError(error.message);
  }
}

async function uploadLogo(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  try {
    const data = new FormData();
    data.append("file", formElement.logo.files[0]);
    await api("/ronda/config/logo", { method: "POST", body: data });
    formElement.reset();
    await refresh();
    setNotice("Logo enviada.");
  } catch (error) {
    setError(error.message);
  }
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/assets/service-worker.js").catch(() => {});
  });
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  state.installPrompt = event;
  state.canInstall = true;
  render();
});

window.addEventListener("appinstalled", () => {
  state.installPrompt = null;
  state.canInstall = false;
  setNotice("Aplicativo instalado na tela inicial.");
});

boot();
