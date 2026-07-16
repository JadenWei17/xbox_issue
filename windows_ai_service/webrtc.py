"""Small WHEP client used to receive the existing MediaMTX WebRTC stream."""

from __future__ import annotations

import asyncio
from urllib.parse import urljoin

import requests
from aiortc import RTCPeerConnection, RTCSessionDescription


async def _wait_for_ice(pc: RTCPeerConnection) -> None:
    if pc.iceGatheringState == "complete":
        return
    complete = asyncio.Event()

    @pc.on("icegatheringstatechange")
    def on_ice_gathering_state_change() -> None:
        if pc.iceGatheringState == "complete":
            complete.set()

    await asyncio.wait_for(complete.wait(), timeout=10)


async def connect(whep_url: str) -> tuple[RTCPeerConnection, object, str | None]:
    pc = RTCPeerConnection()
    track_ready: asyncio.Future[object] = asyncio.get_running_loop().create_future()

    @pc.on("track")
    def on_track(track: object) -> None:
        if getattr(track, "kind", None) == "video" and not track_ready.done():
            track_ready.set_result(track)

    pc.addTransceiver("video", direction="recvonly")
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await _wait_for_ice(pc)
    local = pc.localDescription
    if local is None:
        await pc.close()
        raise RuntimeError("WebRTC offer was not created")

    response = await asyncio.to_thread(
        requests.post,
        whep_url,
        data=local.sdp.encode("utf-8"),
        headers={"Content-Type": "application/sdp"},
        timeout=10,
    )
    if response.status_code not in (200, 201):
        await pc.close()
        raise RuntimeError(f"MediaMTX WHEP returned HTTP {response.status_code}: {response.text[:200]}")

    await pc.setRemoteDescription(RTCSessionDescription(sdp=response.text, type="answer"))
    track = await asyncio.wait_for(track_ready, timeout=10)
    location = response.headers.get("Location")
    session_url = urljoin(whep_url, location) if location else None
    return pc, track, session_url


async def disconnect(pc: RTCPeerConnection, session_url: str | None) -> None:
    await pc.close()
    if session_url:
        try:
            await asyncio.to_thread(requests.delete, session_url, timeout=3)
        except requests.RequestException:
            pass
