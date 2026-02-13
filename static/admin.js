function bytesToSize(bytes) {
  if (!bytes && bytes !== 0) return "-";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, idx)).toFixed(2)} ${units[idx]}`;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json();
  if (!res.ok || data.code !== 200) {
    throw new Error(data.detail || data.message || "请求失败");
  }
  return data.data;
}

function userRowHtml(u) {
  return `
    <tr>
      <td>${u.id}</td>
      <td>${u.username}</td>
      <td>${u.nickname}</td>
      <td>${u.isActive ? "启用" : "禁用"}</td>
      <td>${u.isAdmin ? "是" : "否"}</td>
      <td>${new Date(u.createdAt).toLocaleString()}</td>
      <td>
        <button class="inline-btn" onclick="editUser('${u.id}')">编辑</button>
        <button class="inline-btn danger" onclick="removeUser('${u.id}')">删除</button>
      </td>
    </tr>
  `;
}

function fileRowHtml(f) {
  return `
    <tr>
      <td><input type="checkbox" class="file-check" value="${f.id}"></td>
      <td>${f.id}</td>
      <td>${f.username || f.userId}</td>
      <td>${f.fileName}</td>
      <td>${f.fileType}</td>
      <td>${bytesToSize(f.fileSize)}</td>
      <td>${f.status}</td>
      <td>${new Date(f.uploadTime).toLocaleString()}</td>
      <td>${f.remark || ""}</td>
      <td>
        <button class="inline-btn" onclick="editFileRemark('${f.id}', '${(f.remark || "").replace(/'/g, "\\'")}')">改备注</button>
        <button class="inline-btn danger" onclick="removeFile('${f.id}')">删除</button>
      </td>
    </tr>
  `;
}

async function loadStats() {
  const data = await api("/api/v1/admin/stats");
  document.getElementById("stat-total-users").textContent = data.totalUsers;
  document.getElementById("stat-total-files").textContent = data.totalFiles;
  document.getElementById("stat-storage").textContent = bytesToSize(data.totalStorageBytes);
  document.getElementById("stat-last7days").textContent = data.uploadsLast7Days;
}

async function loadSystemInfo() {
  const data = await api("/api/v1/system/info");
  const text = `版本 ${data.version} | AI模型 ${data.aiModel} | AI配置 ${data.aiConfigured ? "已配置" : "未配置"}`;
  document.getElementById("sys-meta").textContent = text;
}

async function loadUsers() {
  const keyword = document.getElementById("user-keyword").value.trim();
  const isActive = document.getElementById("user-active-filter").value;
  const params = new URLSearchParams({ page: "1", pageSize: "20" });
  if (keyword) params.set("keyword", keyword);
  if (isActive !== "") params.set("isActive", isActive);
  const data = await api(`/api/v1/admin/users?${params.toString()}`);
  document.getElementById("user-table-body").innerHTML = data.list.map(userRowHtml).join("");
}

async function sendAiMessage() {
  const prompt = document.getElementById("ai-prompt").value.trim();
  if (!prompt) {
    alert("请输入内容");
    return;
  }
  document.getElementById("ai-reply").textContent = "请求中...";
  const data = await api("/api/v1/ai/chat", {
    method: "POST",
    body: JSON.stringify({
      messages: [{ role: "user", content: prompt }],
    }),
  });
  document.getElementById("ai-reply").textContent = data.reply || "(空响应)";
}

async function loadFiles() {
  const keyword = document.getElementById("file-keyword").value.trim();
  const fileType = document.getElementById("file-type-filter").value;
  const statusFilter = document.getElementById("file-status-filter").value;
  const params = new URLSearchParams({ page: "1", pageSize: "30" });
  if (keyword) params.set("keyword", keyword);
  if (fileType) params.set("fileType", fileType);
  if (statusFilter) params.set("statusFilter", statusFilter);
  const data = await api(`/api/v1/admin/files?${params.toString()}`);
  document.getElementById("file-table-body").innerHTML = data.list.map(fileRowHtml).join("");
}

async function loadCleanupConfig() {
  const data = await api("/api/v1/admin/cleanup/config");
  document.getElementById("cleanup-config-text").textContent =
    `当前保留天数: ${data.retentionDays} 天；每日 ${String(data.scheduleHour).padStart(2, "0")}:${String(data.scheduleMinute).padStart(2, "0")} 自动清理`;
}

async function createUser() {
  const username = prompt("用户名（3-20位字母数字）:");
  if (!username) return;
  const password = prompt("密码（6-20位）:");
  if (!password) return;
  const nickname = prompt("昵称:");
  if (!nickname) return;
  await api("/api/v1/admin/users", {
    method: "POST",
    body: JSON.stringify({ username, password, nickname, is_active: true, is_admin: false }),
  });
  await Promise.all([loadUsers(), loadStats()]);
}

async function editUser(userId) {
  const nickname = prompt("新昵称（留空不改）:");
  const activeInput = prompt("是否启用？输入 true 或 false（留空不改）:");
  const adminInput = prompt("是否管理员？输入 true 或 false（留空不改）:");
  const resetPassword = prompt("重置密码（留空不改）:");
  const payload = {};
  if (nickname) payload.nickname = nickname;
  if (activeInput === "true" || activeInput === "false") payload.is_active = activeInput === "true";
  if (adminInput === "true" || adminInput === "false") payload.is_admin = adminInput === "true";
  if (resetPassword) payload.reset_password = resetPassword;
  if (!Object.keys(payload).length) return;
  await api(`/api/v1/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) });
  await loadUsers();
}

async function removeUser(userId) {
  if (!confirm("确认删除该用户及其所有文件？")) return;
  await api(`/api/v1/admin/users/${userId}`, { method: "DELETE" });
  await Promise.all([loadUsers(), loadFiles(), loadStats()]);
}

async function editFileRemark(fileId, currentRemark) {
  const remark = prompt("输入新备注:", currentRemark || "");
  if (remark === null) return;
  await api(`/api/v1/admin/files/${fileId}`, {
    method: "PATCH",
    body: JSON.stringify({ remark }),
  });
  await loadFiles();
}

async function removeFile(fileId) {
  if (!confirm("确认删除该文件？")) return;
  await api(`/api/v1/admin/files/${fileId}`, { method: "DELETE" });
  await Promise.all([loadFiles(), loadStats()]);
}

async function batchDeleteFiles() {
  const ids = Array.from(document.querySelectorAll(".file-check:checked")).map((el) => el.value);
  if (!ids.length) {
    alert("请先勾选文件");
    return;
  }
  if (!confirm(`确认删除 ${ids.length} 个文件？`)) return;
  await api("/api/v1/admin/files/batch-delete", {
    method: "POST",
    body: JSON.stringify({ fileIds: ids }),
  });
  await Promise.all([loadFiles(), loadStats()]);
}

async function runCleanup() {
  if (!confirm("确认立即执行清理任务？")) return;
  const data = await api("/api/v1/admin/cleanup/run", { method: "POST" });
  document.getElementById("cleanup-result-text").textContent =
    `清理完成：删除记录 ${data.deletedRecords}，删除物理文件 ${data.deletedPhysicalFiles}，失败 ${data.failedPhysicalDeletes}`;
  await Promise.all([loadFiles(), loadStats()]);
}

document.getElementById("btn-user-search").addEventListener("click", loadUsers);
document.getElementById("btn-user-create").addEventListener("click", createUser);
document.getElementById("btn-file-search").addEventListener("click", loadFiles);
document.getElementById("btn-file-batch-delete").addEventListener("click", batchDeleteFiles);
document.getElementById("btn-run-cleanup").addEventListener("click", runCleanup);
document.getElementById("btn-ai-send").addEventListener("click", sendAiMessage);
document.getElementById("file-check-all").addEventListener("change", (e) => {
  document.querySelectorAll(".file-check").forEach((el) => {
    el.checked = e.target.checked;
  });
});

window.editUser = editUser;
window.removeUser = removeUser;
window.editFileRemark = editFileRemark;
window.removeFile = removeFile;

Promise.all([loadSystemInfo(), loadStats(), loadUsers(), loadFiles(), loadCleanupConfig()]).catch((err) => {
  alert(err.message);
});
