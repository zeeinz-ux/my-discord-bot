/**
 * dashboard.js — Hidden Hamlet Dashboard Logic
 * Updated: Soft Refresh (No Page Reload)
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── 1. Soft Auto-refresh (Fetch API, No Reload) ──
  const REFRESH_INTERVAL = 20000; // 20 detik (Safe limit)
  // Pastikan di HTML lu ada: <body data-guild-id="1290376615439892591">
  const guildId = document.body.dataset.guildId || "1290376615439892591";

  async function updateDashboard() {
    try {
      // Fetch data status dari backend (tanpa reload halaman)
      const response = await fetch(`/api/music/status?guild_id=${guildId}`);
      if (!response.ok) throw new Error("Gagal ambil data");

      const data = await response.json();

      // Update UI jika ada elemen yang sesuai
      // Sesuaikan ID selector ini dengan ID di file HTML lu
      const titleEl = document.querySelector("#now-playing");
      const queueEl = document.querySelector("#queue-count");

      if (data.connected) {
        if (titleEl)
          titleEl.textContent = data.current || "Lagu tidak diketahui";
        if (queueEl) queueEl.textContent = data.queue_count || 0;
      } else {
        if (titleEl) titleEl.textContent = "Bot tidak terhubung ke voice";
      }

      console.log("[DASHBOARD] ✅ Status diperbarui (No Reload)");
    } catch (err) {
      console.error("[DASHBOARD] ❌ Gagal update status:", err);
    }
  }

  // Set interval untuk refresh data secara background
  setInterval(updateDashboard, REFRESH_INTERVAL);

  // ── 2. Artwork fallback on error ──
  document.querySelectorAll(".p-art").forEach((img) => {
    img.addEventListener("error", function () {
      const fallback = this.dataset.fallback;
      if (fallback && this.src !== fallback) {
        this.src = fallback;
      }
    });
  });

  // ── 3. Animate progress bars ──
  document.querySelectorAll(".bar-fill").forEach((bar) => {
    const progress = bar.dataset.progress || 0;
    requestAnimationFrame(() => {
      bar.style.setProperty("--progress", progress + "%");
    });
  });

  console.log(
    "[DASHBOARD] ✅ Dashboard JS initialized. Auto-refresh setiap 20s (Background Mode)",
  );
});
