# Xbox robot services

## 本次更新

新增 Windows 网页前端启动入口。现在只需运行
`python -m windows_video_frontend.main`，即可通过页面按钮分别启动或停止控制服务和视频服务；原有 PowerShell 独立启动方式仍然保留。

项目已拆分为两个互不托管、互不导入的 Raspberry Pi 进程：

```text
xbox_issue/
├── pi_deploy/             # 整个目录的内容复制到 Raspberry Pi
│   ├── control_service/   # UDP、滤波、GPIO 急停、Arduino 串口
│   └── video_service/     # rpicam-vid、H.264、MPEG-TS/UDP
├── arduino/
├── windows_controller/
├── windows_video_receiver/ # 独立 MediaMTX UDP/WebRTC 接收服务
└── windows_video_frontend/ # 独立 Flask 浏览器前端
```

分别启动：

```bash
cd pi_deploy/control_service
python3 main.py
```

```bash
cd pi_deploy/video_service
python3 main.py
```

生产环境使用各目录中的 `robot-control.service` 和 `robot-video.service`。
两个 systemd 单元没有父子关系，可分别启动、停止、重启和查看日志。控制
服务具有更高调度和 OOM 优先级。视频只发送一条 640×480、30 FPS 的
H.264/MPEG-TS/UDP 流，不再发送 AI 预留副本，从进程隔离、资源调度和
网络负载三个方面降低并行运行对操控延迟的影响。

Raspberry Pi 部署用户为 `sws3009b2`，项目目录为
`/home/sws3009b2/robot`。两个服务共用 Pi 上已有的
`/home/sws3009b2/robot/.venv`；已有 `.vscode` 目录也会保留。

上传时把 `pi_deploy` 内的两个服务目录复制到 Pi：

```bash
scp -r pi_deploy/* sws3009b2@PI_IP:/home/sws3009b2/robot/
```

Windows 视频端分别启动：

```powershell
python -m windows_video_receiver.main
python -m windows_video_frontend.main
```

需要在两个 PowerShell 窗口中运行。前端不再管理 MediaMTX 子进程。
