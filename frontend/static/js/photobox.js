/**
 * Photobox — Frontend Camera Capture
 * Mengakses kamera, countdown, capture, kirim via Discord Webhook.
 */
(function () {
  'use strict';

  // ── DOM refs ──
  const $ = (id) => document.getElementById(id);

  const states = {
    loading: $('pbStateLoading'),
    camera: $('pbStateCamera'),
    countdown: $('pbStateCountdown'),
    preview: $('pbStatePreview'),
    sending: $('pbStateSending'),
    success: $('pbStateSuccess'),
    error: $('pbStateError'),
  };

  const video = $('pbVideo');
  const canvas = $('pbCanvas');
  const countdownNum = $('pbCountdownNum');
  const countdownLabel = $('pbCountdownLabel');
  const errorText = $('pbErrorText');

  const btnCapture = $('pbBtnCapture');
  const btnRetake = $('pbBtnRetake');
  const btnSend = $('pbBtnSend');
  const btnRetry = $('pbBtnRetry');

  // ── State ──
  let mediaStream = null;
  let capturedBlob = null;
  let isProcessing = false;

  // ── Webhook & Channel from URL ──
  const params = new URLSearchParams(window.location.search);
  const webhookId = params.get('whid');
  const webhookToken = params.get('whtoken');
  const channelId = params.get('channel');
  const WEBHOOK_URL = webhookId && webhookToken
    ? `https://discord.com/api/webhooks/${webhookId}/${webhookToken}`
    : null;

  // ── Utility: show only one state ──
  function showState(name) {
    Object.keys(states).forEach((key) => {
      states[key].classList.toggle('hidden', key !== name);
    });
  }

  // ── Utility: format filename ──
  function timestamp() {
    const d = new Date();
    return `photobox-${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}-${String(d.getHours()).padStart(2, '0')}${String(d.getMinutes()).padStart(2, '0')}${String(d.getSeconds()).padStart(2, '0')}`;
  }

  // ═══════════════════════════════════════════════
  // CAMERA
  // ═══════════════════════════════════════════════
  async function startCamera() {
    showState('loading');

    if (!WEBHOOK_URL) {
      showError('Link photobox gak valid — coba ulang dari Discord ya!');
      return;
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      });
      video.srcObject = mediaStream;
      await video.play();
      showState('camera');
    } catch (err) {
      console.error('[PHOTOBOX] Camera error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        showError('Izin kameranya diblokir! Coba izinin dulu di pengaturan browser.');
      } else if (err.name === 'NotFoundError') {
        showError('Kamera gak ketemu — pastiin perangkat lu punya kamera ya!');
      } else {
        showError('Gagal akses kamera: ' + err.message);
      }
    }
  }

  function stopCamera() {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }
  }

  // ═══════════════════════════════════════════════
  // CAPTURE with countdown
  // ═══════════════════════════════════════════════
  async function doCountdown() {
    if (isProcessing) return;
    isProcessing = true;

    showState('countdown');

    const steps = [
      { num: '3', label: 'siap-siap...', delay: 300 },
      { num: '2', label: 'senyum dulu! 😊', delay: 300 },
      { num: '1', label: 'siap-siap... 📸', delay: 300 },
      { num: '📸', label: 'CHEESE! ✨', delay: 500 },
    ];

    for (const step of steps) {
      countdownNum.textContent = step.num;
      countdownLabel.textContent = step.label;
      // Re-trigger animation
      countdownNum.style.animation = 'none';
      void countdownNum.offsetHeight;
      countdownNum.style.animation = 'countPop 0.6s ease-out';
      await sleep(step.delay);
    }

    // Capture frame
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    // Mirror the image (selfie mode)
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Reset transform
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    // Convert to blob
    capturedBlob = await new Promise((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.92)
    );

    isProcessing = false;
    showState('preview');
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // ═══════════════════════════════════════════════
  // SEND via Webhook
  // ═══════════════════════════════════════════════
  async function sendPhoto() {
    if (!capturedBlob || !WEBHOOK_URL) return;

    showState('sending');

    try {
      const formData = new FormData();
      formData.append('file', capturedBlob, `${timestamp()}.jpg`);

      // Optional: send with a cute message
      const messageContent = channelId
        ? `📸 **Ada yang foto!** <#${channelId}>`
        : '📸 **Ada yang foto nih!**';

      // Discord webhook payload as multipart/form-data
      const payload = new FormData();
      payload.append('file', capturedBlob, `${timestamp()}.jpg`);
      payload.append(
        'payload_json',
        JSON.stringify({
          content: '📸 **Photobox — hasil jepretan!**',
        })
      );

      const resp = await fetch(WEBHOOK_URL, {
        method: 'POST',
        body: payload,
      });

      if (!resp.ok) {
        const errBody = await resp.text().catch(() => '');
        throw new Error(`Discord webhook error ${resp.status}: ${errBody.slice(0, 100)}`);
      }

      showState('success');
      stopCamera();
    } catch (err) {
      console.error('[PHOTOBOX] Send error:', err);
      showError('Gagal kirim foto: ' + err.message);
    }
  }

  // ═══════════════════════════════════════════════
  // ERROR
  // ═══════════════════════════════════════════════
  function showError(msg) {
    errorText.textContent = msg;
    showState('error');
    isProcessing = false;
  }

  function resetAll() {
    capturedBlob = null;
    isProcessing = false;
    if (mediaStream) {
      // re-use existing stream if camera still available
      showState('camera');
    } else {
      startCamera();
    }
  }

  // ═══════════════════════════════════════════════
  // EVENT BINDINGS
  // ═══════════════════════════════════════════════
  btnCapture.addEventListener('click', doCountdown);
  btnRetake.addEventListener('click', () => {
    capturedBlob = null;
    showState('camera');
  });
  btnSend.addEventListener('click', sendPhoto);
  btnRetry.addEventListener('click', () => {
    stopCamera();
    startCamera();
  });

  // ═══════════════════════════════════════════════
  // INIT
  // ═══════════════════════════════════════════════
  startCamera();
})();
