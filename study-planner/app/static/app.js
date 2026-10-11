const state = { token: localStorage.getItem("mayak_token"), user: null, users: [], assignments: [], filter: "all", search: "", editId: null };
const $ = (selector) => document.querySelector(selector);
const loginView = $("#loginView");
const appView = $("#appView");
const dialog = $("#assignmentDialog");
let toastTimer;

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 3000);
}

function errorText(data) {
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).join("; ");
  return data?.detail || "Не удалось выполнить запрос. Попробуй еще раз.";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = "Bearer " + state.token;
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch (_) {
    throw new Error("Сервер недоступен. Запусти проект и обнови страницу.");
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) logout(false);
    throw new Error(errorText(data));
  }
  return data;
}

function logout(showMessage = false) {
  state.token = null;
  state.user = null;
  localStorage.removeItem("mayak_token");
  appView.hidden = true;
  loginView.hidden = false;
  if (showMessage) showToast("Ты вышел из аккаунта.");
}

async function login(username, password) {
  $("#loginError").textContent = "";
  const button = $("#loginForm button[type='submit']");
  button.disabled = true;
  try {
    const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    state.token = result.access_token;
    localStorage.setItem("mayak_token", state.token);
    await loadApp();
  } catch (error) {
    $("#loginError").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function loadApp() {
  try {
    const user = await api("/api/auth/me");
    state.user = user;
    appView.hidden = false;
    loginView.hidden = true;
    const isAdmin = user.role === "admin";
    $("#profileName").textContent = user.username;
    $("#profileRole").textContent = isAdmin ? "Администратор" : "Ученик";
    $("#profileAvatar").textContent = isAdmin ? "А" : user.username.slice(0, 1).toUpperCase();
    $("#welcomeTitle").textContent = (isAdmin ? "Добрый день" : "Привет") + ", " + user.username + "!";
    $("#welcomeText").textContent = isAdmin ? "Вот общий план учеников на ближайшее время." : "Вот твой план на ближайшее время.";
    $("#tasksTitle").firstChild.textContent = isAdmin ? "Все задачи " : "Мои задачи ";
    $("#ownerField").hidden = !isAdmin;
    $("#todayLabel").textContent = new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
    if (isAdmin) {
      state.users = await api("/api/users");
      renderOwnerOptions();
    }
    await refreshData();
  } catch (error) {
    logout(false);
    $("#loginError").textContent = error.message;
  }
}

function renderOwnerOptions() {
  const select = $("#ownerSelect");
  select.innerHTML = state.users.map((user) => '<option value="' + user.id + '">' + escapeHTML(user.username) + '</option>').join("");
}

async function refreshData() {
  const params = new URLSearchParams();
  if (state.filter !== "all") params.set("status", state.filter);
  if (state.search.trim()) params.set("q", state.search.trim());
  const suffix = params.size ? "?" + params.toString() : "";
  try {
    const results = await Promise.all([api("/api/dashboard"), api("/api/assignments" + suffix)]);
    state.assignments = results[1];
    renderStats(results[0]);
    renderAssignments();
  } catch (error) {
    $("#taskList").innerHTML = '<div class="empty-state">' + escapeHTML(error.message) + '</div>';
  }
}

function renderStats(stats) {
  $("#totalStat").textContent = stats.total;
  $("#dueStat").textContent = stats.due_soon;
  $("#overdueStat").textContent = stats.overdue;
  $("#doneStat").textContent = stats.done;
  const percent = stats.total ? Math.round((stats.done / stats.total) * 100) : 0;
  $("#progressPercent").textContent = percent + "%";
  $("#progressBar").style.width = percent + "%";
  $("#progressTitle").textContent = percent === 100 && stats.total ? "Все задачи выполнены!" : stats.done ? "Хороший темп!" : "Начни с одного шага";
  $("#progressText").textContent = stats.total ? "Выполнено " + stats.done + " из " + stats.total + " задач." : "Добавь первую задачу — и план станет понятнее.";
}

const statusLabels = { planned: "Запланировано", in_progress: "В работе", done: "Готово" };
const priorityLabels = { low: "Низкий", medium: "Обычный", high: "Высокий" };

function formatDueDate(value) {
  const date = new Date(value + "T00:00:00");
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(date);
}

function renderAssignments() {
  const list = $("#taskList");
  $("#taskCount").textContent = state.assignments.length;
  if (!state.assignments.length) {
    list.innerHTML = '<div class="empty-state"><span class="empty-icon">✦</span><strong>Здесь пока тихо</strong>Создай задачу — и маяк поможет держать курс.</div>';
    return;
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  list.innerHTML = state.assignments.map((task) => {
    const overdue = task.status !== "done" && new Date(task.due_date + "T00:00:00") < today;
    const owner = state.user.role === "admin" ? '<span class="owner-pill">' + escapeHTML(task.owner_username) + '</span>' : "";
    return '<article class="task-card" data-id="' + task.id + '"><span class="task-accent priority-' + task.priority + '"></span><div class="task-main"><div class="task-title-row"><strong class="task-title">' + escapeHTML(task.title) + '</strong></div>' + (task.description ? '<div class="task-description">' + escapeHTML(task.description) + '</div>' : '') + '<div class="task-meta"><span class="subject-pill">' + escapeHTML(task.subject) + '</span><span class="priority-pill priority-' + task.priority + '">' + priorityLabels[task.priority] + '</span>' + owner + '<span class="due-date ' + (overdue ? "overdue" : "") + '">' + (overdue ? "Просрочено · " : "До ") + formatDueDate(task.due_date) + '</span></div></div><div class="task-actions"><label class="sr-only" for="status-' + task.id + '">Статус задачи ' + escapeHTML(task.title) + '</label><select class="task-status" id="status-' + task.id + '" data-action="status"><option value="planned" ' + (task.status === "planned" ? "selected" : "") + '>Запланировано</option><option value="in_progress" ' + (task.status === "in_progress" ? "selected" : "") + '>В работе</option><option value="done" ' + (task.status === "done" ? "selected" : "") + '>Готово</option></select><button class="task-action" type="button" data-action="edit" aria-label="Изменить задачу" title="Изменить">✎</button><button class="task-action delete" type="button" data-action="delete" aria-label="Удалить задачу" title="Удалить">×</button></div></article>';
  }).join("");
}

function openAssignment(task = null) {
  state.editId = task ? task.id : null;
  const form = $("#assignmentForm");
  form.reset();
  $("#assignmentError").textContent = "";
  $("#dialogTitle").textContent = task ? "Изменить задачу" : "Новая задача";
  $("#saveAssignmentButton").textContent = task ? "Сохранить изменения" : "Сохранить задачу";
  form.elements.title.value = task?.title || "";
  form.elements.subject.value = task?.subject || "";
  form.elements.description.value = task?.description || "";
  form.elements.due_date.value = task?.due_date || new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  form.elements.priority.value = task?.priority || "medium";
  form.elements.status.value = task?.status || "planned";
  if (state.user.role === "admin" && task) form.elements.owner_id.value = String(task.owner_id);
  dialog.showModal();
  form.elements.title.focus();
}

async function saveAssignment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  data.due_date = String(data.due_date);
  if (state.user.role === "admin" && data.owner_id) data.owner_id = Number(data.owner_id);
  else delete data.owner_id;
  const button = $("#saveAssignmentButton");
  button.disabled = true;
  try {
    const editing = state.editId !== null;
    await api(editing ? "/api/assignments/" + state.editId : "/api/assignments", {
      method: editing ? "PATCH" : "POST",
      body: JSON.stringify(data),
    });
    dialog.close();
    showToast(editing ? "Изменения сохранены." : "Задача добавлена в план.");
    await refreshData();
  } catch (error) {
    $("#assignmentError").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

$("#loginForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  login(form.elements.username.value.trim(), form.elements.password.value);
});

document.querySelectorAll("[data-demo]").forEach((button) => button.addEventListener("click", () => {
  const form = $("#loginForm");
  form.elements.username.value = button.dataset.demo;
  form.elements.password.value = button.dataset.demo === "admin" ? "admin123" : "student123";
  form.elements.username.focus();
}));

$("#logoutButton").addEventListener("click", () => logout(true));
$("#newAssignmentButton").addEventListener("click", () => openAssignment());
$("#closeDialogButton").addEventListener("click", () => dialog.close());
$("#cancelDialogButton").addEventListener("click", () => dialog.close());
$("#assignmentForm").addEventListener("submit", saveAssignment);
$("#statusFilter").addEventListener("change", (event) => { state.filter = event.target.value; refreshData(); });
let searchTimer;
$("#searchInput").addEventListener("input", (event) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.search = event.target.value; refreshData(); }, 220);
});

$("#taskList").addEventListener("change", async (event) => {
  if (event.target.dataset.action !== "status") return;
  const card = event.target.closest("[data-id]");
  try {
    await api("/api/assignments/" + card.dataset.id, { method: "PATCH", body: JSON.stringify({ status: event.target.value }) });
    await refreshData();
    showToast("Статус задачи обновлен.");
  } catch (error) {
    showToast(error.message, true);
    await refreshData();
  }
});

$("#taskList").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const card = button.closest("[data-id]");
  const task = state.assignments.find((item) => String(item.id) === card.dataset.id);
  if (button.dataset.action === "edit") openAssignment(task);
  if (button.dataset.action === "delete" && window.confirm("Удалить задачу «" + task.title + "»?")) {
    try {
      await api("/api/assignments/" + task.id, { method: "DELETE" });
      await refreshData();
      showToast("Задача удалена.");
    } catch (error) {
      showToast(error.message, true);
    }
  }
});

dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
if (state.token) loadApp();
