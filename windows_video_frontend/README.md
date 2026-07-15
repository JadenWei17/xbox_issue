# Windows robot frontend and service launcher

前端可作为统一入口，从一个 PowerShell 启动后由页面编排两个服务对：

- 控制：Pi `robot-control.service` + Windows `windows_controller`。
- 视频：Windows `windows_video_receiver` + Pi `robot-video.service`。

前端默认只监听 `127.0.0.1:8080`，不会向局域网暴露启停接口。

前端并不是唯一启动方式。下面的独立 PowerShell 命令始终保留：

```powershell
python -m windows_controller.main
python -m windows_video_receiver.main
```

Pi 端也仍可通过 SSH 分别运行 `control_service/main.py` 和
`video_service/main.py`，或直接使用 `systemctl start`。

## 一次性配置 Pi

首先安装仓库里的两个 systemd 单元：

```bash
sudo cp /home/sws3009b2/robot/control_service/robot-control.service /etc/systemd/system/
sudo cp /home/sws3009b2/robot/video_service/robot-video.service /etc/systemd/system/
sudo systemctl daemon-reload
```

不要在这里执行 `enable --now`，由网页按钮按需启动。

网页调用必须是无交互的。Windows 如果还没有 SSH 密钥，在 PowerShell 执行：

```powershell
ssh-keygen -t ed25519
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh sws3009b2@100.96.200.113 "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
ssh -o BatchMode=yes sws3009b2@100.96.200.113 "echo SSH_OK"
```

然后在 Pi 上创建最小 sudo 权限：

```bash
sudo visudo -f /etc/sudoers.d/robot-services
```

填入一行：

```text
sws3009b2 ALL=(root) NOPASSWD: /usr/bin/systemctl start robot-control.service, /usr/bin/systemctl stop robot-control.service, /usr/bin/systemctl start robot-video.service, /usr/bin/systemctl stop robot-video.service
```

保存后检查：

```bash
sudo visudo -cf /etc/sudoers.d/robot-services
```

## 日常启动

只需要一个 PowerShell：

```powershell
cd D:\SWS3009B2\xbox_issue
conda activate robot
pip install -r windows_video_frontend\requirements.txt
python -m windows_video_frontend.main
```

打开 `http://127.0.0.1:8080`，使用“启动控制”和“启动视频”按钮。启动
控制前页面会要求安全确认。Windows 子服务日志写入项目根目录
`runtime_logs/`。

状态栏通过 UDP 5010 接收 Pi 遥测，显示超声距离、Arduino 模式、PWM、
航向和位置。Windows 防火墙需要允许本机 UDP 5010 入站。手柄 D-pad 切换
到 `DISTANCE_MODE` 后，页面会显示命令输入框，格式与终端一致：

```text
w 2 50
s 1 20
a 1 90
d 2 45
```

速度仅保留两档：级别 1 对应 PWM 200，级别 2 对应 PWM 255；级别 3
会被 Windows、Pi 和 Arduino 三端共同拒绝。
