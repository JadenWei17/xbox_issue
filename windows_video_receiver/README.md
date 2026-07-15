# Windows video receiver service

该服务只运行 MediaMTX：监听 Pi 发来的 H.264/MPEG-TS/UDP 5600，并在
8889/8189 提供 WebRTC。它不启动 Flask 前端。

```powershell
cd D:\SWS3009B2\xbox_issue
conda activate robot
python -m windows_video_receiver.main
```

也可以运行：

```powershell
.\windows_video_receiver\start_receiver.ps1
```

看到 `stream is available and online, 1 track (H264)` 表示已经收到 Pi 视频。
停止本服务不会停止 Pi 控制服务或 Windows 前端。
