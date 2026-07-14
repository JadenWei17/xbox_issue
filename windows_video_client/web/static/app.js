"use strict";

const body = document.body;
const viewport = document.getElementById("viewport");
const placeholder = document.getElementById("placeholder");
const statusBadge = document.getElementById("status");
const message = document.getElementById("message");
let player = null;

function playerUrl() {
  return `${location.protocol}//${location.hostname}:${body.dataset.mediamtxPort}/${body.dataset.streamPath}`;
}

function setStatus(label, state, detail = "") {
  statusBadge.textContent = label;
  statusBadge.className = `status ${state}`;
  message.textContent = detail;
}

async function notify(path) {
  try {
    await fetch(path, {method: "POST", keepalive: true});
  } catch (_) {
    // Logging must never prevent playback or page shutdown.
  }
}

function startPlayback() {
  if (player) return;
  setStatus("连接中", "connecting", "正在建立 WebRTC 连接……");
  player = document.createElement("iframe");
  player.title = "Robot WebRTC video";
  player.allow = "autoplay; fullscreen";
  player.src = playerUrl();
  player.addEventListener("load", () => {
    setStatus("已连接", "online", `${body.dataset.width} × ${body.dataset.height} · ${body.dataset.fps} FPS`);
    notify("/api/connect");
  }, {once: true});
  placeholder.hidden = true;
  viewport.appendChild(player);
}

function stopPlayback() {
  if (player) {
    player.remove();
    player = null;
    notify("/api/disconnect");
  }
  placeholder.hidden = false;
  setStatus("已停止", "offline", "播放器已停止；RTP 主视频流仍在运行。 ");
}

function reconnect() {
  stopPlayback();
  window.setTimeout(startPlayback, 150);
}

document.getElementById("start").addEventListener("click", startPlayback);
document.getElementById("stop").addEventListener("click", stopPlayback);
document.getElementById("reconnect").addEventListener("click", reconnect);
window.addEventListener("beforeunload", () => {
  if (player) navigator.sendBeacon("/api/disconnect");
});

fetch("/api/status")
  .then(response => response.json())
  .then(data => {
    if (!data.gateway) setStatus("服务异常", "offline", "WebRTC 网关尚未运行。 ");
  })
  .catch(() => setStatus("服务异常", "offline", "无法获取网页服务状态。 "));
