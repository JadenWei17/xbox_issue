# Raspberry Pi deployment package

这个目录包含所有需要传到 Raspberry Pi 的程序文件：

```text
pi_deploy/
├── control_service/
└── video_service/
```

将本目录的内容上传到 Pi 的 `/home/sws3009b2/robot`：

```bash
scp -r pi_deploy/* sws3009b2@PI_IP:/home/sws3009b2/robot/
```

上传后 Pi 上的结构为：

```text
/home/sws3009b2/robot/
├── .venv/                 # Pi 上现有的共享 Python 虚拟环境
├── .vscode/               # Pi 上现有的 VS Code 配置
├── control_service/
└── video_service/
```

两个 systemd 单元都使用 `/home/sws3009b2/robot/.venv/bin/python`，不会在
服务目录内重复创建虚拟环境。上传命令中的 `pi_deploy/*` 不包含目标端的
删除操作，因此 Pi 上已有的 `.venv` 和 `.vscode` 会原样保留。

首次部署或依赖变化后安装控制依赖：

```bash
cd /home/sws3009b2/robot
. .venv/bin/activate
pip install -r control_service/requirements.txt
```

Pi 5 上如果旧版 `RPi.GPIO` 已经存在，需要先删除冲突包：

```bash
pip uninstall -y RPi.GPIO
pip install -r control_service/requirements.txt
```

Arduino 固件在项目根目录的 `arduino/`，应从开发电脑烧录，不需要复制到 Pi。
Windows 端目录也不应复制到 Pi。
