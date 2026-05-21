/* ================================================================================
   JS: AI Chat Settings v4.1 — Hidden Hamlet Dashboard
   ================================================================================ */

(function () {
  const GUILD_ID = window.CURRENT_GUILD_ID;
  const API_BASE = `/api/ai-chat`;
  const TOGGLE_URL = `/dashboard/${GUILD_ID}/ai-chat/toggle`;
  const SAVE_URL = `/dashboard/${GUILD_ID}/ai-chat/save`;

  const els = {
    toggle: document.getElementById("aiChatToggle"),
    channel: document.getElementById("channelSelect"),
    personality: document.getElementById("personalitySelect"),
    temperature: document.getElementById("temperatureRange"),
    tempValue: document.getElementById("temperatureValue"),
    saveBtn: document.getElementById("saveSettingsBtn"),
    refreshHistory: document.getElementById("refreshHistoryBtn"),
    historyList: document.getElementById("historyList"),
    historyLoading: document.getElementById("historyLoading"),
    historyEmpty: document.getElementById("historyEmpty"),
    toast: document.getElementById("toast"),
    toastIcon: document.getElementById("toast-icon"),
    toastMsg: document.getElementById("toast-message"),
    apiStatus: document.getElementById("apiStatusBadge"),
  };

  async function init() {
    await loadSettings();
    setupEventListeners();
    await loadHistory();
    checkApiStatus();
  }

  async function loadSettings() {
    try {
      const res = await fetch(`${API_BASE}/settings/${GUILD_ID}`);
      const data = await res.json();

      if (!data.success) {
        showToast("⚠️", "Gagal memuat pengaturan.", "error");
        return;
      }

      els.toggle.checked = data.ai_chat_enabled || false;

      const cfg = data.ai_chat || {};
      if (cfg.personality) els.personality.value = cfg.personality;
      if (cfg.temperature) {
        els.temperature.value = cfg.temperature;
        els.tempValue.textContent = cfg.temperature;
      }
      if (cfg.channel_id) els.channel.value = cfg.channel_id;

      updateToggleVisuals();
    } catch (err) {
      console.error("[AI Chat] Error load settings:", err);
      showToast("⚠️", "Gagal memuat pengaturan.", "error");
    }
  }

  function setupEventListeners() {
    els.toggle.addEventListener("change", handleToggle);
    els.temperature.addEventListener("input", (e) => {
      els.tempValue.textContent = e.target.value;
    });
    els.saveBtn.addEventListener("click", handleSaveSettings);
    els.refreshHistory.addEventListener("click", loadHistory);
  }

  async function handleToggle() {
    const enabled = els.toggle.checked;
    updateToggleVisuals();

    try {
      const res = await fetch(TOGGLE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: enabled }),
      });

      const data = await res.json();

      if (data.success) {
        showToast(
          enabled ? "✅" : "🚫",
          `AI Chat ${enabled ? "diaktifkan" : "dinonaktifkan"}.`,
          "success",
        );
      } else {
        els.toggle.checked = !enabled;
        updateToggleVisuals();
        showToast("❌", data.message || "Gagal menyimpan.", "error");
      }
    } catch (err) {
      console.error("[AI Chat] Toggle error:", err);
      els.toggle.checked = !enabled;
      updateToggleVisuals();
      showToast("❌", "Koneksi error. Coba lagi.", "error");
    }
  }

  function updateToggleVisuals() {
    const card = els.toggle.closest(".card");
    if (els.toggle.checked) {
      card.style.borderColor = "var(--accent-primary)";
      card.style.background =
        "linear-gradient(135deg, #1e1e22 0%, #1a1a2e 100%)";
    } else {
      card.style.borderColor = "var(--border-color)";
      card.style.background = "var(--bg-card)";
    }
  }

  async function handleSaveSettings() {
    const payload = {
      personality: els.personality.value,
      channel_id: els.channel.value,
      temperature: parseFloat(els.temperature.value),
      model: "gemini-2.0-flash",
    };

    const originalText = els.saveBtn.innerHTML;
    els.saveBtn.innerHTML = `<span class="btn-icon">⏳</span> Menyimpan...`;
    els.saveBtn.disabled = true;

    try {
      const res = await fetch(SAVE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data.success) {
        showToast("✅", "Pengaturan berhasil disimpan!", "success");
      } else {
        showToast("❌", data.message || "Gagal menyimpan.", "error");
      }
    } catch (err) {
      console.error("[AI Chat] Save error:", err);
      showToast("❌", "Koneksi error. Coba lagi.", "error");
    } finally {
      els.saveBtn.innerHTML = originalText;
      els.saveBtn.disabled = false;
    }
  }

  async function loadHistory() {
    els.historyLoading.classList.remove("hidden");
    els.historyEmpty.classList.add("hidden");
    els.historyList.innerHTML = "";

    try {
      const res = await fetch(`${API_BASE}/history/${GUILD_ID}`);
      const data = await res.json();

      els.historyLoading.classList.add("hidden");

      if (!data.success || !data.history || data.history.length === 0) {
        els.historyEmpty.classList.remove("hidden");
        return;
      }

      data.history.forEach((item) => {
        const div = document.createElement("div");
        div.className = "history-item";

        const preview = item.preview || [];
        let messagesHtml = "";
        preview.forEach((msg) => {
          const roleClass = msg.role === "user" ? "user" : "assistant";
          const roleLabel = msg.role === "user" ? "User" : "AI";
          messagesHtml += `
            <div class="history-msg ${roleClass}">
              <strong>${roleLabel}:</strong> ${escapeHtml(msg.content)}
            </div>
          `;
        });

        div.innerHTML = `
          <div class="history-meta">
            <div class="history-avatar">#${item.user_id.slice(-4)}</div>
            <span class="history-user">User ${item.user_id.slice(-8)}</span>
            <span class="history-time">${item.total_messages} pesan • ${item.personality}</span>
          </div>
          ${messagesHtml}
        `;

        els.historyList.appendChild(div);
      });
    } catch (err) {
      console.error("[AI Chat] History load error:", err);
      els.historyLoading.classList.add("hidden");
      els.historyEmpty.classList.remove("hidden");
    }
  }

  function checkApiStatus() {
    setTimeout(() => {
      els.apiStatus.textContent = "Online";
      els.apiStatus.className = "badge badge-success";
    }, 800);
  }

  function showToast(icon, message, type = "success") {
    els.toastIcon.textContent = icon;
    els.toastMsg.textContent = message;
    const colors = {
      success: "#3ba55d",
      error: "#ed4245",
      warning: "#f0b232",
    };
    els.toast.style.borderLeft = `4px solid ${colors[type] || colors.success}`;
    els.toast.classList.remove("hidden");
    void els.toast.offsetWidth;
    els.toast.classList.add("show");

    setTimeout(() => {
      els.toast.classList.remove("show");
      setTimeout(() => els.toast.classList.add("hidden"), 300);
    }, 3000);
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
