# Robot control service

该进程只负责 UDP 手柄输入、输入滤波、GPIO 急停和 Arduino 串口，
不导入也不启动任何摄像头或视频模块。控制包超时 0.5 秒时会主动停车；进程
退出时也会发送最终停车命令。

超声波距离由 Arduino 采集并作为遥测发送到前端，仅用于显示，不参与急停、
减速或路径规划。Y 键/GPIO17 硬件急停仍保持最高优先级。

## 安装与启动

```bash
cd control_service
python3 -m venv ../.venv
. ../.venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Raspberry Pi 5 必须使用 `rpi-lgpio`。它与旧 `RPi.GPIO` 提供相同的
`import RPi.GPIO as GPIO` 接口，但两者不能同时安装。如果虚拟环境曾安装
旧包，先执行：

```bash
pip uninstall -y RPi.GPIO
pip install -r requirements.txt
```

配置位于 `config.py`。默认监听 UDP 5000，串口为 `/dev/ttyACM0`。
手动摇杆仍保持比例混控，但每侧非零输出通过
`MANUAL_MIN_MOTOR_SPEED = 155` 设置最低有效 PWM；死区和回中输出仍为 0。
Arduino 状态以非阻塞 UDP 发送到 Windows `100.67.201.122:5010`，仅用于
前端显示；丢包或前端未运行都不会阻塞控制回路。
硬件无关测试：

```bash
python3 -m unittest discover -s tests -v
```

## systemd

仓库内的 `robot-control.service` 已按项目目录
`/home/sws3009b2/robot`、运行用户 `sws3009b2` 配置：

```bash
sudo cp robot-control.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now robot-control.service
sudo systemctl status robot-control.service
journalctl -u robot-control.service -f
```

服务使用较高 CPU/OOM 优先级，确保视频负载升高时控制回路优先运行。
