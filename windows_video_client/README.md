# Windows video client

This directory contains the Windows-side receiver for the Raspberry Pi camera
stream and hosts the browser/WebRTC gateway. It is independent from
`windows_controller/`: the controller directory sends Xbox and keyboard
commands, while this directory only receives and displays video.

## Network configuration

Set `RTP_TARGET_IP` on the Raspberry Pi to this Windows computer's LAN or
Tailscale IPv4 address. The direct video/AI port is UDP 5004. A second RTP copy
for MediaMTX uses UDP 5600. Both use payload type 96.

Allow these inbound ports in Windows Firewall:

- UDP 5004: direct GStreamer/OpenCV/deep-learning input.
- UDP 5600: MediaMTX RTP input from the Raspberry Pi.
- TCP 8080: custom browser page.
- TCP 8889: MediaMTX WebRTC/WHEP signaling.
- UDP 8189: WebRTC media/ICE.

## GStreamer viewer

Install the 64-bit MSVC GStreamer Runtime and Development packages, including
Good, Bad, and Libav plugins. Then run in PowerShell:

```powershell
gst-launch-1.0 -v udpsrc port=5004 buffer-size=131072 `
  caps="application/x-rtp,media=video,encoding-name=H264,clock-rate=90000,payload=96" `
  ! rtpjitterbuffer latency=30 drop-on-latency=true `
  ! rtph264depay ! h264parse ! avdec_h264 max-threads=1 `
  ! queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream `
  ! d3d11videosink sync=false
```

## OpenCV / future deep-learning input

`opencv_rtp_receiver.py` demonstrates direct RTP input without using the web
page or taking browser screenshots. It requires an OpenCV build with GStreamer
support:

```powershell
python windows_video_client/opencv_rtp_receiver.py --port 5004 --payload-type 96
```

The GStreamer `appsink` retains at most one frame and drops old frames when
processing is slower than the camera. Insert future inference code at the
marked position without adding an unbounded Python queue.

## Windows browser and WebRTC service

Install Python dependencies from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r windows_video_client\requirements.txt
```

Download the Windows MediaMTX archive from its official release page and put
`mediamtx.exe` in a directory listed in `PATH`:

<https://github.com/bluenviron/mediamtx/releases>

Verify it:

```powershell
mediamtx.exe --version
```

Start the web and MediaMTX service from the project root:

```powershell
python -m windows_video_client.web.server
```

Or use:

```powershell
.\windows_video_client\start_web.ps1
```

Open the local viewer:

```text
http://127.0.0.1:8080
```

Another device in the LAN or tailnet can use the Windows LAN/Tailscale IP:

```text
http://WINDOWS_IP:8080
```

The Flask service starts and stops its own MediaMTX child process. Closing the
browser does not stop either Raspberry Pi RTP output. Stopping the Windows web
service does not affect Xbox control, GPIO E-STOP, Arduino serial, motors, or
the direct RTP stream on port 5004.

Configuration is in `video_config.py`. MediaMTX listens on `0.0.0.0:5600` by
default, while the page is served on `0.0.0.0:8080`.

## Startup order

1. Start MediaMTX/web on Windows.
2. Start the RTP video service on the Raspberry Pi.
3. Start robot control independently.
4. Open the Windows web page or direct GStreamer/OpenCV receiver.

MediaMTX may be started after the Raspberry Pi stream; RTP/UDP has no session
handshake, so it begins receiving new packets as soon as it binds port 5600.
