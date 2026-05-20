/**
 * welcome.js — Hidden Hamlet Welcome Settings Form Logic v3.7
 * Features: style toggle (embed/banner), color picker sync, live preview,
 *           drag & drop upload, banner preview, form submit
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── Elements ──
  const toggleEmbed = document.getElementById("toggleEmbed");
  const embedPanel = document.getElementById("embedPanel");
  const toggleEnabled = document.getElementById("toggleEnabled");
  const statusBanner = document.getElementById("statusBanner");
  const statusText = document.getElementById("statusText");
  const colorPicker = document.getElementById("embed_color");
  const colorHexInput = document.getElementById("embed_color_text");
  const embedTitleInput = document.getElementById("embed_title");
  const embedPreviewTitle = document.getElementById("embedPreviewTitle");
  const embedPreviewBar = document.getElementById("embedPreviewBar");
  const welcomeForm = document.getElementById("welcomeForm");
  const btnSave = document.getElementById("btnSave");
  const toast = document.getElementById("toast");

  // Style selector elements (NEW v3.7)
  const styleSelector = document.getElementById("styleSelector");
  const embedSettingsCard = document.getElementById("embedSettingsCard");
  const bannerSettingsCard = document.getElementById("bannerSettingsCard");

  // Banner elements (NEW v3.7)
  const bannerTextInput = document.getElementById("banner_text");
  const bannerSubtextInput = document.getElementById("banner_subtext");
  const bannerFontColorPicker = document.getElementById("banner_font_color");
  const bannerFontColorHex = document.getElementById("banner_font_color_text");
  const toggleAvatarRing = document.getElementById("toggleAvatarRing");
  const koyaBannerTitle = document.getElementById("koyaBannerTitle");
  const koyaBannerName = document.getElementById("koyaBannerName");
  const koyaBannerSub = document.getElementById("koyaBannerSub");
  const koyaAvatarRing = document.getElementById("koyaAvatarRing");
  const koyaBannerBg = document.getElementById("koyaBannerBg");
  const bannerBgUrlInput = document.getElementById("banner_bg_url");

  // Banner upload elements (NEW v3.7)
  const bannerUploadZone = document.getElementById("bannerUploadZone");
  const bannerFileInput = document.getElementById("bannerFileInput");
  const bannerUploadPreview = document.getElementById("bannerUploadPreview");
  const bannerUploadPreviewImg = document.getElementById(
    "bannerUploadPreviewImg",
  );
  const bannerUploadRemove = document.getElementById("bannerUploadRemove");

  // Embed upload elements
  const uploadZone = document.getElementById("uploadZone");
  const fileInput = document.getElementById("fileInput");
  const uploadPreview = document.getElementById("uploadPreview");
  const uploadPreviewImg = document.getElementById("uploadPreviewImg");
  const uploadRemove = document.getElementById("uploadRemove");

  // ── 1. Style Selector Toggle (NEW v3.7) ──
  function setActiveStyle(style) {
    // Update radio buttons
    document
      .querySelectorAll('.style-option input[name="style"]')
      .forEach((radio) => {
        radio.checked = radio.value === style;
      });

    // Update visual active state
    document.querySelectorAll(".style-option").forEach((opt) => {
      opt.classList.toggle("active", opt.dataset.style === style);
    });

    // Show/hide settings cards
    if (embedSettingsCard) {
      embedSettingsCard.classList.toggle("visible", style === "embed");
    }
    if (bannerSettingsCard) {
      bannerSettingsCard.classList.toggle("visible", style === "banner");
    }

    console.log(`[WELCOME] 🎨 Style switched to: ${style}`);
  }

  if (styleSelector) {
    document.querySelectorAll(".style-option").forEach((option) => {
      option.addEventListener("click", () => {
        const style = option.dataset.style;
        setActiveStyle(style);
      });
    });

    // Init: set initial active style
    const initialStyleRadio = document.querySelector(
      '.style-option input[name="style"]:checked',
    );
    if (initialStyleRadio) {
      setActiveStyle(initialStyleRadio.value);
    } else {
      setActiveStyle("embed");
    }
  }

  // ── 2. Embed Panel Toggle ──
  if (toggleEmbed && embedPanel) {
    toggleEmbed.addEventListener("change", function () {
      embedPanel.classList.toggle("open", this.checked);
    });
  }

  // ── 3. Status Banner Toggle ──
  if (toggleEnabled && statusBanner && statusText) {
    toggleEnabled.addEventListener("change", function () {
      if (this.checked) {
        statusBanner.className = "status-banner active";
        statusText.innerHTML = "Modul Welcome sedang <strong>aktif</strong>.";
      } else {
        statusBanner.className = "status-banner inactive";
        statusText.innerHTML =
          "Modul Welcome sedang <strong>nonaktif</strong>.";
      }
    });
  }

  // ── 4. Color Picker Sync (Embed) ──
  function applyEmbedColor(hex) {
    document.documentElement.style.setProperty("--welcome-accent", hex);
    if (document.activeElement !== colorPicker && colorPicker) {
      colorPicker.value = hex;
    }
    if (document.activeElement !== colorHexInput && colorHexInput) {
      colorHexInput.value = hex;
    }
    if (embedPreviewBar) {
      embedPreviewBar.style.background = hex;
    }
  }

  if (colorPicker) {
    colorPicker.addEventListener("input", function () {
      applyEmbedColor(this.value);
    });
  }

  if (colorHexInput) {
    colorHexInput.addEventListener("input", function () {
      const v = this.value.startsWith("#") ? this.value : "#" + this.value;
      if (/^#[0-9A-Fa-f]{6}$/.test(v)) {
        applyEmbedColor(v);
      }
    });
  }

  // ── 5. Banner Font Color Sync (NEW v3.7) ──
  function applyBannerColor(hex) {
    document.documentElement.style.setProperty("--banner-font-color", hex);
    if (
      document.activeElement !== bannerFontColorPicker &&
      bannerFontColorPicker
    ) {
      bannerFontColorPicker.value = hex;
    }
    if (document.activeElement !== bannerFontColorHex && bannerFontColorHex) {
      bannerFontColorHex.value = hex;
    }
  }

  if (bannerFontColorPicker) {
    bannerFontColorPicker.addEventListener("input", function () {
      applyBannerColor(this.value);
    });
  }

  if (bannerFontColorHex) {
    bannerFontColorHex.addEventListener("input", function () {
      const v = this.value.startsWith("#") ? this.value : "#" + this.value;
      if (/^#[0-9A-Fa-f]{6}$/.test(v)) {
        applyBannerColor(v);
      }
    });
  }

  // ── 6. Live Preview Title (Embed) ──
  if (embedTitleInput && embedPreviewTitle) {
    embedTitleInput.addEventListener("input", function () {
      embedPreviewTitle.textContent = this.value.trim() || "👋 Selamat Datang!";
    });
  }

  // ── 7. Banner Text Live Preview (NEW v3.7) ──
  if (bannerTextInput && koyaBannerTitle) {
    bannerTextInput.addEventListener("input", function () {
      koyaBannerTitle.textContent = (
        this.value.trim() || "WELCOME"
      ).toUpperCase();
    });
  }

  if (bannerSubtextInput && koyaBannerSub) {
    bannerSubtextInput.addEventListener("input", function () {
      const val = this.value.trim() || "Member ke-171 • Hidden Hamlet";
      koyaBannerSub.textContent = val
        .replace("{count}", "171")
        .replace("{server}", "Hidden Hamlet");
    });
  }

  // ── 8. Avatar Ring Toggle (NEW v3.7) ──
  if (toggleAvatarRing && koyaAvatarRing) {
    toggleAvatarRing.addEventListener("change", function () {
      koyaAvatarRing.classList.toggle("hidden", !this.checked);
    });
  }

  // ── 9. Banner Background Preview (NEW v3.7) ──
  function updateBannerBgPreview(url) {
    if (koyaBannerBg && url) {
      koyaBannerBg.style.backgroundImage = `url(${url})`;
      koyaBannerBg.classList.remove("no-image");
    } else if (koyaBannerBg) {
      koyaBannerBg.style.backgroundImage = "";
      koyaBannerBg.classList.add("no-image");
    }
  }

  if (bannerBgUrlInput) {
    bannerBgUrlInput.addEventListener("input", function () {
      updateBannerBgPreview(this.value.trim());
    });
  }

  // ── 10. Drag & Drop Upload (Embed) ──
  setupUploadZone(
    uploadZone,
    fileInput,
    uploadPreview,
    uploadPreviewImg,
    uploadRemove,
    (base64) => {
      // For embed: update banner preview with base64
      console.log("[WELCOME] 📤 Embed file selected (base64 preview)");
    },
  );

  // ── 11. Drag & Drop Upload (Banner) (NEW v3.7) ──
  setupUploadZone(
    bannerUploadZone,
    bannerFileInput,
    bannerUploadPreview,
    bannerUploadPreviewImg,
    bannerUploadRemove,
    (base64) => {
      // For banner: update background preview
      updateBannerBgPreview(base64);
      console.log("[WELCOME] 📤 Banner file selected (base64 preview)");
    },
  );

  // ── Upload Zone Setup Helper ──
  function setupUploadZone(
    zone,
    input,
    preview,
    previewImg,
    removeBtn,
    onPreview,
  ) {
    if (!zone || !input) return;

    // Prevent default drag behaviors
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, preventDefaults, false);
      document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    // Highlight drop zone on drag
    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, highlight, false);
    });

    ["dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
      zone.classList.add("dragover");
    }

    function unhighlight() {
      zone.classList.remove("dragover");
    }

    // Handle dropped files
    zone.addEventListener("drop", handleDrop, false);

    function handleDrop(e) {
      const dt = e.dataTransfer;
      const files = dt.files;
      handleFiles(files);
    }

    // Handle file input change
    input.addEventListener("change", function () {
      handleFiles(this.files);
    });

    function handleFiles(files) {
      if (files.length > 0) {
        const file = files[0];
        if (!file.type.startsWith("image/")) {
          showToast("File harus berupa gambar (PNG, JPG, GIF).", "error");
          return;
        }
        if (file.size > 5 * 1024 * 1024) {
          showToast("Ukuran file maksimal 5MB.", "error");
          return;
        }
        previewFile(file);
      }
    }

    function previewFile(file) {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onloadend = function () {
        const base64 = reader.result;

        // Show preview in upload zone
        if (previewImg) {
          previewImg.src = base64;
        }
        if (preview) {
          preview.classList.add("active");
        }
        zone.classList.add("has-file");

        // Callback
        if (onPreview) onPreview(base64);

        console.log(
          "[WELCOME] 📤 File selected (base64 preview only — upload to hosting for Discord)",
        );
      };
    }

    // Remove uploaded file
    if (removeBtn) {
      removeBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();

        if (preview) {
          preview.classList.remove("active");
        }
        if (previewImg) {
          previewImg.src = "";
        }
        if (input) {
          input.value = "";
        }
        zone.classList.remove("has-file");

        // Reset preview
        if (onPreview) onPreview(null);
      });
    }
  }

  // ── 12. Toast Notification ──
  function showToast(msg, type = "success") {
    if (!toast) return;
    document.getElementById("toastMsg").textContent = msg;
    document.getElementById("toastIcon").textContent =
      type === "success" ? "✅" : "❌";
    toast.className = `toast ${type}`;
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => toast.classList.remove("show"), 4000);
  }

  // ── 13. Form Submit ──
  if (welcomeForm) {
    welcomeForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      // Sync hex inputs ke color pickers sebelum submit
      if (colorHexInput && colorPicker) {
        const hexVal = colorHexInput.value;
        if (/^#?[0-9A-Fa-f]{6}$/.test(hexVal)) {
          colorPicker.value = hexVal.startsWith("#") ? hexVal : "#" + hexVal;
        }
      }
      if (bannerFontColorHex && bannerFontColorPicker) {
        const hexVal = bannerFontColorHex.value;
        if (/^#?[0-9A-Fa-f]{6}$/.test(hexVal)) {
          bannerFontColorPicker.value = hexVal.startsWith("#")
            ? hexVal
            : "#" + hexVal;
        }
      }

      // Validate channel
      const channelSelect = document.getElementById("channel_id");
      if (channelSelect && !channelSelect.value) {
        showToast("Pilih channel tujuan terlebih dahulu.", "error");
        return;
      }

      // Validate message text
      const messageText = document.getElementById("message_text");
      if (messageText && !messageText.value.trim()) {
        showToast("Teks pesan tidak boleh kosong.", "error");
        return;
      }

      const guildId = document.querySelector('input[name="guild_id"]')?.value;
      if (!guildId) {
        showToast("Guild ID tidak ditemukan.", "error");
        return;
      }

      // Loading state
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.classList.add("loading");
      }

      try {
        const res = await fetch(`/dashboard/${guildId}/welcome/save`, {
          method: "POST",
          body: new FormData(this),
        });
        const result = await res.json();

        showToast(
          result.message || (res.ok ? "✅ Tersimpan!" : "❌ Gagal menyimpan."),
          res.ok && result.success ? "success" : "error",
        );
      } catch (err) {
        console.error("[WELCOME SAVE]", err);
        showToast("❌ Kesalahan jaringan. Periksa koneksi.", "error");
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.classList.remove("loading");
        }
      }
    });
  }

  console.log(
    "[WELCOME] ✅ Welcome JS v3.7 loaded — Dual Style (Embed + Banner)",
  );
});
