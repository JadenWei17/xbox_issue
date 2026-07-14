# Raspberry Pi camera and RTP publisher

The Raspberry Pi only captures and publishes video. Browser/WebRTC and future
deep-learning programs run on Windows in `../windows_video_client/`.

```text
Pi camera -> H.264 -> RTP/UDP 5004 -> Windows GStreamer / AI
                   `-> RTP/UDP 5600 -> Windows MediaMTX -> WebRTC browser
```

Both outputs come from one libcamera capture and one H.264 encoder. Each branch
has a bounded two-buffer leaky queue, so a slow Windows receiver cannot build
an unlimited backlog or block robot control. Video does not import the Xbox,
GPIO E-STOP, Arduino serial, or motor-control modules.

## Configuration

Edit `video/video_config.py` or set matching environment variables:

- `RTP_TARGET_IP`: Windows LAN or Tailscale IPv4 address.
- `RTP_TARGET_PORT`: direct low-latency/AI stream, default UDP 5004.
- `WEBRTC_TARGET_IP`: Windows address for MediaMTX; defaults to
  `RTP_TARGET_IP`.
- `WEBRTC_TARGET_PORT`: MediaMTX input, default UDP 5600.
- `CAMERA_WIDTH` / `CAMERA_HEIGHT`: default 1280x720.
- `CAMERA_FPS`: default 30.
- `VIDEO_BITRATE`: default 2,000,000 bit/s.
- `GOP_SIZE`: default 15 frames.
- `RTP_PAYLOAD_TYPE`: default 96.

Ports 5004 and 5600 are intentionally different. A single unicast UDP port
must not be shared by MediaMTX and the direct inference receiver.

## Raspberry Pi dependencies

```bash
sudo apt update
sudo apt install -y rpicam-apps gstreamer1.0-tools \
  gstreamer1.0-libcamera gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

Verify the camera and encoder:

```bash
rpicam-hello --list-cameras
gst-inspect-1.0 libcamerasrc
gst-inspect-1.0 v4l2h264enc
```

The service prefers `v4l2h264enc`. If unavailable, it logs a warning and uses
the low-latency `x264enc` fallback.

## Run

From the project root:

```bash
cd raspberry_pi
RTP_TARGET_IP=100.67.201.122 python3 -m video.rtp_streamer
```

Replace the example address with the Windows LAN or Tailscale IP. To use
different Windows addresses for direct RTP and WebRTC:

```bash
RTP_TARGET_IP=192.168.1.20 \
WEBRTC_TARGET_IP=100.67.201.122 \
python3 -m video.rtp_streamer
```

Start the existing control process separately:

```bash
python3 main.py
```

Or supervise control and video as independent child processes:

```bash
RTP_TARGET_IP=100.67.201.122 python3 service_manager.py --with-control
```

The supervisor no longer starts a web service. Web/MediaMTX runs on Windows.
A video crash does not terminate control; Ctrl+C stops supervisor-owned
children cleanly.

Background video scripts:

```bash
chmod +x scripts/*.sh
RTP_TARGET_IP=100.67.201.122 ./scripts/start_video.sh
./scripts/stop_video.sh
```

## Troubleshooting

- Camera busy: stop other Picamera2, rpicam, or GStreamer camera processes.
- No packets on Windows: verify both devices can ping each other, the selected
  LAN/Tailscale IP is correct, and Windows Firewall allows UDP 5004 and 5600.
- Increasing delay: keep receiver queues leaky and small; lower bitrate or
  resolution if Wi-Fi/Tailscale bandwidth is insufficient.
- Tailscale DERP relay: video can work but latency and bandwidth may be worse
  than a direct Tailscale connection.
- Web works but video is blank: confirm Windows MediaMTX is listening on 5600
  and sender/receiver both use RTP payload type 96.

Hardware camera, encoder controls, and end-to-end UDP behavior must be verified
on the target Raspberry Pi.
