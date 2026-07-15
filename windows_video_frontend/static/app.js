"use strict";

const body = document.body;
const viewport = document.getElementById("viewport");
const placeholder = document.getElementById("placeholder");
const statusBadge = document.getElementById("status");
const message = document.getElementById("message");
const serviceMessage = document.getElementById("service-message");
const keyboardPanel = document.getElementById("keyboard-panel");
const commandInput = document.getElementById("motion-command");
const commandMessage = document.getElementById("command-message");
let player = null;

function playerUrl() {
  const host = body.dataset.mediamtxHost || location.hostname;
  return `${location.protocol}//${host}:${body.dataset.mediamtxPort}/${body.dataset.streamPath}`;
}

function setVideoStatus(label, state, detail = "") {
  statusBadge.textContent = label;
  statusBadge.className = `status ${state}`;
  message.textContent = detail;
}

function describeService(status) {
  if (status.running) return ["运行中", "online"];
  if (status.local && !status.pi) return ["仅 Windows 运行", "partial"];
  if (!status.local && status.pi) return ["仅 Pi 运行", "partial"];
  return ["已停止", "offline"];
}

function updateServiceCard(name, status) {
  const card = document.querySelector(`[data-service="${name}"]`);
  if (!card) return;
  const [label, state] = describeService(status);
  const stateElement = card.querySelector(".service-state");
  stateElement.className = `service-state ${state}`;
  stateElement.querySelector("span:last-child").textContent = label;
}

async function refreshServices() {
  try {
    const response = await fetch("/api/services", {cache: "no-store"});
    const services = await response.json();
    if (!response.ok) throw new Error(services.error || "状态读取失败");
    Object.entries(services).forEach(([name, status]) => updateServiceCard(name, status));
  } catch (error) {
    serviceMessage.textContent = error.message;
  }
}

async function serviceAction(name, action) {
  const card = document.querySelector(`[data-service="${name}"]`);
  const buttons = card.querySelectorAll("button");
  buttons.forEach(button => { button.disabled = true; });
  serviceMessage.textContent = `${action === "start" ? "正在启动" : "正在停止"}${name === "control" ? "控制" : "视频"}服务…`;
  try {
    const response = await fetch(`/api/services/${name}/${action}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: "{}",
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "操作失败");
    updateServiceCard(name, result);
    serviceMessage.textContent = "操作完成";
  } catch (error) {
    serviceMessage.textContent = `操作失败：${error.message}`;
  } finally {
    buttons.forEach(button => { button.disabled = false; });
    window.setTimeout(refreshServices, 1000);
  }
}

function display(value, fallback = "--") {
  return value === null || value === undefined ? fallback : value;
}

async function refreshRobotStatus() {
  try {
    const response = await fetch("/api/robot-status", {cache: "no-store"});
    const data = await response.json();
    const telemetry = data.telemetry || {};
    const controller = data.controller || {};
    document.getElementById("telemetry-online").textContent = telemetry.online ? "在线" : "离线";
    document.getElementById("robot-mode").textContent = display(telemetry.mode, controller.mode);
    document.getElementById("ultrasonic").textContent = telemetry.us == null ? "无有效读数" : `${telemetry.us} cm`;
    document.getElementById("wheel-pwm").textContent = `${display(telemetry.lpwm)} / ${display(telemetry.rpwm)}`;
    document.getElementById("heading").textContent = `${display(telemetry.h)}°`;
    document.getElementById("position").textContent = `${display(telemetry.x)}, ${display(telemetry.y)} cm`;
    keyboardPanel.hidden = !(controller.online && controller.mode === "DISTANCE_MODE");
  } catch (_) {
    document.getElementById("telemetry-online").textContent = "离线";
  }
}

async function sendMotionCommand() {
  const text = commandInput.value.trim();
  if (!text) return;
  const button = document.getElementById("send-command");
  button.disabled = true;
  try {
    const response = await fetch("/api/motion-command", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({command: text}),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "发送失败");
    commandMessage.textContent = `已发送：${JSON.stringify(result.sent)}`;
    commandInput.value = "";
  } catch (error) {
    commandMessage.textContent = `发送失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

document.getElementById("send-command").addEventListener("click", sendMotionCommand);
commandInput.addEventListener("keydown", event => {
  if (event.key === "Enter") sendMotionCommand();
});

document.querySelectorAll(".service-card").forEach(card => {
  const name = card.dataset.service;
  card.querySelector(".service-start").addEventListener("click", () => {
    if (name !== "control" || window.confirm("确认车轮已架空或小车处于安全区域，并启动控制服务？")) {
      serviceAction(name, "start");
    }
  });
  card.querySelector(".service-stop").addEventListener("click", () => serviceAction(name, "stop"));
});

function startPlayback() {
  if (player) return;
  setVideoStatus("连接中", "connecting", "正在建立 WebRTC 连接…");
  player = document.createElement("iframe");
  player.title = "Robot WebRTC video";
  player.allow = "autoplay; fullscreen";
  player.src = playerUrl();
  player.addEventListener("load", () => {
    setVideoStatus("已连接", "online", `${body.dataset.width} × ${body.dataset.height} · ${body.dataset.fps} FPS`);
  }, {once: true});
  placeholder.hidden = true;
  viewport.appendChild(player);
}

function stopPlayback() {
  if (player) {
    player.remove();
    player = null;
  }
  placeholder.hidden = false;
  setVideoStatus("视频未连接", "offline", "播放器已停止，视频服务状态不受影响。");
}

document.getElementById("start").addEventListener("click", startPlayback);
document.getElementById("stop").addEventListener("click", stopPlayback);
document.getElementById("reconnect").addEventListener("click", () => {
  stopPlayback();
  window.setTimeout(startPlayback, 150);
});

refreshServices();
window.setInterval(refreshServices, 5000);
refreshRobotStatus();
window.setInterval(refreshRobotStatus, 500);
