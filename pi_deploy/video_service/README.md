# Robot video service

视频链路只有一条：

```text
rpicam-vid → H.264 → MPEG-TS → UDP 5600 → Windows MediaMTX → WebRTC
```

不再创建原先供 AI/OpenCV 使用的 UDP 5004 输出，避免重复发送视频造成网络、
CPU 和内存压力。视频服务与控制服务仍是完全独立的进程。

## 配置

配置位于 `config.py`：

- 固定分辨率：640×480。
- `CAMERA_FPS`：独立帧率常量，当前为 30，需要调整帧率时只改这一项。
- `VIDEO_TARGET_IP`：Windows 电脑地址。
- `VIDEO_TARGET_PORT`：单一 UDP 目标端口，默认 5600。
- `VIDEO_BITRATE`：默认 1 Mbit/s，可用同名环境变量覆盖。

## 安装和启动

```bash
sudo apt update
sudo apt install -y rpicam-apps
cd /home/sws3009b2/robot/video_service
python3 -m venv ../.venv
. ../.venv/bin/activate
pip install -r requirements.txt
VIDEO_TARGET_IP=192.168.1.20 python3 main.py
```

实际执行的核心命令等价于：

```bash
rpicam-vid -t 0 -n --width 640 --height 480 --framerate 30 \
  --codec libav --low-latency --libav-format mpegts \
  -o udp://WINDOWS_IP:5600
```

Pi 5 必须保留 `--low-latency`。它会禁止 WebRTC 不支持的 H.264 B 帧，
同时减少编码等待时间。

## systemd

`robot-video.service` 已按用户 `sws3009b2` 和部署目录
`/home/sws3009b2/robot` 配置。先在服务文件中设置 Windows 地址，例如：

```ini
Environment=VIDEO_TARGET_IP=192.168.1.20
```

然后安装：

```bash
sudo cp robot-video.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now robot-video.service
journalctl -u robot-video.service -f
```
