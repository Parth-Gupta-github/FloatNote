

import asyncio
import collections
import os
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# faster-whisper: pip install faster-whisper
from faster_whisper import WhisperModel

# webrtcvad: pip install webrtcvad
import webrtcvad

# pyannote (optional — used async only for enrichment)
try:
    from pyannote.audio import Pipeline
    from huggingface_hub import login as hf_login
    _PYANNOTE_AVAILABLE = True
except ImportError:
    _PYANNOTE_AVAILABLE = False

# Fix: keep the import package-relative so module execution resolves correctly.
from ..utils.nlp_processor import process_text

_ORIGINAL_INPUT_STREAM = sd.InputStream

# ── CONFIG ────────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16_000          # Hz — webrtcvad only supports 8k/16k/32k/48k
BLOCKSIZE    = 320            # samples per callback → 20ms frames (webrtcvad)
VAD_MODE     = 3              # 0 = least aggressive, 3 = most aggressive
# Speech / silence timing
SPEECH_PAD_MS      = 300      # ms of trailing silence before we consider speech ended
MAX_SPEECH_S       = 8        # hard cap on one segment (seconds)
MIN_SPEECH_MS      = 250      # ignore segments shorter than this
# Whisper
WHISPER_MODEL      = "base"   # "tiny" is ~2x faster, "small" is more accurate
WHISPER_DEVICE     = "cpu"    # "cuda" if you have a GPU
WHISPER_COMPUTE    = "int8"   # int8 quantisation — halves CPU time
BEAM_SIZE          = 1        # greedy decoding → lowest latency
# Ring-buffer: how much history each source keeps
RING_SECONDS = 4
RING_SIZE    = SAMPLE_RATE * RING_SECONDS

HF_TOKEN     = "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"
MAX_CLIENTS  = 3

# ── MODELS ───────────────────────────────────────────────────────────────────
print("Loading faster-whisper …")
asr = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
print("faster-whisper loaded.")

vad = webrtcvad.Vad(VAD_MODE)

diarize_pipeline = None
if _PYANNOTE_AVAILABLE:
    try:
        hf_login(HF_TOKEN)
        # Fix: newer pyannote versions expect auth to come from `hf_login`.
        diarize_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
        print("pyannote loaded.")
    except Exception as e:
        print(f"pyannote unavailable ({e}) — using RMS fast-path only.")

# ── GLOBALS ───────────────────────────────────────────────────────────────────
_loop: Optional[asyncio.AbstractEventLoop] = None
# Per-source sample queues (filled from audio callbacks)
_q_mic  = asyncio.Queue(maxsize=500)
_q_loop = asyncio.Queue(maxsize=500)
# Per-source rolling ring-buffers
_ring_mic  = collections.deque(maxlen=RING_SIZE)
_ring_loop = collections.deque(maxlen=RING_SIZE)
# Connected WebSocket clients
_clients: set[WebSocket] = set()
# Last known speaker identity from pyannote (updated async in background)
_last_speaker_info: dict = {}
_loopback_only_mode = False

# ── HELPERS ───────────────────────────────────────────────────────────────────

def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0

def quick_source(mic_chunk: np.ndarray, loop_chunk: np.ndarray) -> str:
    """RMS heuristic: which source is louder in this segment?"""
    return "mic" if rms(mic_chunk) >= rms(loop_chunk) else "system"

def is_speech_frame(frame_bytes: bytes) -> bool:
    """Ask webrtcvad whether a 20ms PCM-16 frame is speech."""
    try:
        return vad.is_speech(frame_bytes, SAMPLE_RATE)
    except Exception:
        return False

def float_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float32 [-1, 1] to int16 PCM bytes for webrtcvad."""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()

def _system_frame_active(frame: np.ndarray) -> bool:
    # Fix: give loopback-only mode a simple RMS fallback when VAD misses system audio speech.
    return rms(frame) >= 0.008

# ── AUDIO CALLBACKS (called from sounddevice thread) ──────────────────────────

def _cb_mic(indata, frames, t, status):
    if status:
        print(f"MIC: {status}")
    if _loop is None:
        return
    data = indata[:, 0].copy()
    if not _q_mic.full():
        _loop.call_soon_threadsafe(_q_mic.put_nowait, data)

def _cb_loop(indata, frames, t, status):
    if status:
        print(f"LOOP: {status}")
    if _loop is None:
        return
    data = indata[:, 0].copy()
    if _loopback_only_mode and not _q_mic.full():
        _loop.call_soon_threadsafe(_q_mic.put_nowait, np.zeros_like(data))
    if not _q_loop.full():
        _loop.call_soon_threadsafe(_q_loop.put_nowait, data)

# ── DEVICE DISCOVERY ─────────────────────────────────────────────────────────

def _device_name(index: int) -> str:
    try:
        return sd.query_devices(index)["name"]
    except Exception:
        return f"<unavailable:{index}>"

def _device_info(index: int) -> dict:
    return sd.query_devices(index)

def _device_default_samplerate(index: int) -> int:
    try:
        return int(float(_device_info(index)["default_samplerate"]))
    except Exception:
        return SAMPLE_RATE

def _hostapi_name(index: int) -> str:
    try:
        info = _device_info(index)
        hostapi_index = int(info["hostapi"])
        return str(sd.query_hostapis(hostapi_index)["name"])
    except Exception:
        return ""

def _device_input_channels(index: int) -> int:
    try:
        return int(_device_info(index)["max_input_channels"])
    except Exception:
        return 1

def _device_output_channels(index: int) -> int:
    try:
        return int(_device_info(index)["max_output_channels"])
    except Exception:
        return 0

def _is_loopback_device(index: int) -> bool:
    name = _device_name(index).lower()
    return any(token in name for token in ("pc speaker", "stereo mix", "loopback", "cable output", "vb-audio"))

def _is_wasapi_output_device(index: int) -> bool:
    try:
        info = _device_info(index)
    except Exception:
        return False
    return _device_output_channels(index) > 0 and "wasapi" in _hostapi_name(index).lower()

def _default_wasapi_output() -> Optional[int]:
    # Fix: on Windows, capture YouTube/system audio from the active WASAPI output via loopback.
    try:
        for hostapi in sd.query_hostapis():
            if "wasapi" in str(hostapi["name"]).lower():
                default_output = hostapi.get("default_output_device", -1)
                if isinstance(default_output, int) and default_output >= 0:
                    return default_output
    except Exception:
        return None
    return None

def _default_wasapi_input() -> Optional[int]:
    # Fix: pair the mic with the WASAPI host when loopback capture uses WASAPI output.
    try:
        for hostapi in sd.query_hostapis():
            if "wasapi" in str(hostapi["name"]).lower():
                default_input = hostapi.get("default_input_device", -1)
                if isinstance(default_input, int) and default_input >= 0:
                    return default_input
    except Exception:
        return None
    return None

class _NullInputStream:
    # Fix: allow startup to continue in mic-only mode when loopback capture is unavailable.
    def start(self):
        return self

    def stop(self):
        return self

    def close(self):
        return self

def _resample_for_pipeline(indata: np.ndarray, samplerate: int) -> np.ndarray:
    # Fix: convert native device rates like 48 kHz down to the 16 kHz pipeline rate.
    if samplerate == SAMPLE_RATE:
        return indata

    if len(indata) == 0:
        return indata

    target_len = max(1, round(len(indata) * SAMPLE_RATE / samplerate))
    src_positions = np.linspace(0, len(indata) - 1, num=len(indata), dtype=np.float32)
    dst_positions = np.linspace(0, len(indata) - 1, num=target_len, dtype=np.float32)

    if indata.ndim == 1:
        return np.interp(dst_positions, src_positions, indata).astype(np.float32)

    channels = [
        np.interp(dst_positions, src_positions, indata[:, ch]).astype(np.float32)
        for ch in range(indata.shape[1])
    ]
    return np.stack(channels, axis=1)

def _wrap_input_callback(callback, samplerate: int):
    # Fix: adapt incoming stream frames to the pipeline sample rate before queueing them.
    if samplerate == SAMPLE_RATE:
        return callback

    def _wrapped(indata, frames, t, status):
        resampled = _resample_for_pipeline(indata, samplerate)
        callback(resampled, len(resampled), t, status)

    return _wrapped

def _open_input_stream(device: int, callback, preferred_channels: int = 1) -> sd.InputStream:
    # Fix: probe a few valid channel/rate combinations before opening the stream.
    is_wasapi_loopback = _is_wasapi_output_device(device)
    max_channels = max(1, _device_output_channels(device) if is_wasapi_loopback else _device_input_channels(device))
    native_samplerate = _device_default_samplerate(device)
    channel_options = []
    for channels in (preferred_channels, min(2, max_channels), 1):
        if 1 <= channels <= max_channels and channels not in channel_options:
            channel_options.append(channels)

    samplerates = []
    for samplerate in (native_samplerate, SAMPLE_RATE, 48_000, 44_100):
        if samplerate not in samplerates:
            samplerates.append(samplerate)

    if is_wasapi_loopback:
        # Fix: use the exact WASAPI loopback stream pattern that works on this machine.
        stream_callback = _wrap_input_callback(callback, native_samplerate)
        for channels in channel_options:
            try:
                return _ORIGINAL_INPUT_STREAM(
                    samplerate=native_samplerate,
                    channels=channels,
                    dtype="float32",
                    blocksize=512,
                    device=device,
                    callback=stream_callback,
                    extra_settings=sd.WasapiSettings(loopback=True),
                )
            except Exception:
                continue

    for samplerate in samplerates:
        for channels in channel_options:
            try:
                if "pc speaker" in _device_name(device).lower():
                    return _ORIGINAL_INPUT_STREAM(
                        samplerate=native_samplerate,
                        channels=max(2, channels),
                        dtype="float32",
                        blocksize=512,
                        device=device,
                        callback=_wrap_input_callback(callback, native_samplerate),
                    )
                extra_settings = None
                stream_callback = _wrap_input_callback(callback, samplerate)
                stream_blocksize = max(1, round(BLOCKSIZE * samplerate / SAMPLE_RATE))
                sd.check_input_settings(device=device, samplerate=samplerate, channels=channels, dtype="float32", extra_settings=extra_settings)
                return _ORIGINAL_INPUT_STREAM(
                    samplerate=samplerate,
                    channels=channels,
                    dtype="float32",
                    blocksize=stream_blocksize,
                    device=device,
                    callback=stream_callback,
                    latency="low",
                    extra_settings=extra_settings,
                )
            except Exception:
                continue

    raise RuntimeError(f"Unable to open input device #{device} ({_device_name(device)})")

def _patched_input_stream(*args, **kwargs):
    # Fix: let the existing startup code retry safer formats for input devices automatically.
    if args:
        return _ORIGINAL_INPUT_STREAM(*args, **kwargs)

    device = kwargs.get("device")
    callback = kwargs.get("callback")
    if device is None or callback is None:
        return _ORIGINAL_INPUT_STREAM(*args, **kwargs)

    if _loopback_only_mode and callback is _cb_mic:
        return _NullInputStream()

    preferred_channels = int(kwargs.get("channels", 1))
    try:
        return _open_input_stream(device, callback, preferred_channels=preferred_channels)
    except Exception:
        if _is_loopback_device(device):
            print(f"Loopback device #{device} could not be opened â€” continuing with mic only.")
            return _NullInputStream()
        raise

# Fix: route later `sd.InputStream(...)` calls through the compatibility wrapper above.
sd.InputStream = _patched_input_stream

def _env_device(name: str) -> Optional[int]:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print(f"Ignoring invalid {name}={raw!r}; expected device index.")
        return None

def find_loopback() -> Optional[int]:
    forced = _env_device("FLOATNOTE_LOOP_DEVICE")
    if forced is not None:
        return forced

    # Fix: prefer the Realtek speaker-capture input that actually opens on this machine.
    preferred_tokens = ("pc speaker", "cable output", "vb-audio", "stereo mix", "loopback")
    candidates = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] <= 0:
            continue
        n = d["name"].lower()
        for priority, token in enumerate(preferred_tokens):
            if token in n:
                candidates.append((priority, i))
                break
    if candidates:
        candidates.sort()
        return candidates[0][1]
    return None

def default_input() -> int:
    forced = _env_device("FLOATNOTE_MIC_DEVICE")
    if forced is not None:
        return forced

    wasapi_input = _default_wasapi_input()
    if wasapi_input is not None:
        return wasapi_input

    preferred_tokens = ("microphone", "mic input", "microphone array", "headset mic")
    excluded_tokens = ("stereo mix", "loopback", "cable output", "vb-audio")

    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] <= 0:
            continue
        name = d["name"].lower()
        if any(token in name for token in excluded_tokens):
            continue
        if any(token in name for token in preferred_tokens):
            return i

    dev = sd.default.device
    if hasattr(dev, "__len__") and not isinstance(dev, (str, bytes)):
        try:
            return int(dev[0])
        except Exception:
            pass
    return int(dev)

# ── VAD-DRIVEN SPEECH SEGMENTER ───────────────────────────────────────────────

async def vad_segmenter():
    """
    Reads 20ms frames from both queues, runs VAD, and yields complete speech
    segments as (mic_audio, loop_audio, duration_s) tuples via an asyncio.Queue.
    Uses a state machine:
      SILENCE → accumulating background
      SPEECH  → accumulating utterance
    Emits when speech ends (SPEECH_PAD_MS silence) or MAX_SPEECH_S hit.
    """
    frame_samples  = int(SAMPLE_RATE * 0.02)  # 20ms = 320 samples @ 16kHz
    pad_frames     = int(SPEECH_PAD_MS / 20)  # silence frames before emit
    max_frames     = int(MAX_SPEECH_S * 50)   # 50 frames/s

    speech_mic:  list[np.ndarray] = []
    speech_loop: list[np.ndarray] = []
    silence_count = 0
    in_speech     = False

    # Temporary per-frame buffers
    buf_mic  = np.zeros(0, dtype=np.float32)
    buf_loop = np.zeros(0, dtype=np.float32)

    while True:
        # Drain both queues into per-source buffers
        try:
            chunk = await asyncio.wait_for(_q_mic.get(), timeout=0.05)
            buf_mic = np.concatenate([buf_mic, chunk])
            _ring_mic.extend(chunk)
        except asyncio.TimeoutError:
            pass

        try:
            chunk = await asyncio.wait_for(_q_loop.get(), timeout=0.001)
            buf_loop = np.concatenate([buf_loop, chunk])
            _ring_loop.extend(chunk)
        except asyncio.TimeoutError:
            # Pad loop with silence if no data
            if len(buf_mic) > 0:
                buf_loop = np.concatenate([buf_loop, np.zeros(len(buf_mic), dtype=np.float32)])

        # Process complete 20ms frames
        while len(buf_mic) >= frame_samples and len(buf_loop) >= frame_samples:
            frm_mic  = buf_mic[:frame_samples]
            frm_loop = buf_loop[:frame_samples]
            buf_mic  = buf_mic[frame_samples:]
            buf_loop = buf_loop[frame_samples:]

            # Fix: in loopback-only mode, drive VAD from system audio instead of averaging it with silence.
            mixed_frame = frm_loop if _loopback_only_mode else (frm_mic + frm_loop) / 2.0
            pcm16       = float_to_pcm16(mixed_frame)
            is_speech   = is_speech_frame(pcm16)
            if _loopback_only_mode:
                is_speech = is_speech or _system_frame_active(frm_loop)

            if is_speech:
                in_speech     = True
                silence_count = 0
                speech_mic.append(frm_mic)
                speech_loop.append(frm_loop)
            elif in_speech:
                silence_count += 1
                speech_mic.append(frm_mic)   # keep trailing silence for context
                speech_loop.append(frm_loop)
                if silence_count >= pad_frames or len(speech_mic) >= max_frames:
                    await _emit_segment(speech_mic, speech_loop)
                    speech_mic.clear()
                    speech_loop.clear()
                    silence_count = 0
                    in_speech     = False
            # else: silence while not in speech — discard frame

async def _emit_segment(mic_frames: list, loop_frames: list):
    """Transcribe + attribute one VAD-delimited speech segment."""
    if not mic_frames:
        return

    mic_np  = np.concatenate(mic_frames,  dtype=np.float32)
    loop_np = np.concatenate(loop_frames, dtype=np.float32)

    duration_ms = len(mic_np) / SAMPLE_RATE * 1000
    if duration_ms < MIN_SPEECH_MS:
        return

    # Fix: keep system-audio chunks at full strength in loopback-only mode.
    mixed = loop_np.copy() if _loopback_only_mode else (mic_np + loop_np) / 2.0
    mixed -= mixed.mean()  # remove DC offset

    print(
        f"[CHUNK] frames={len(mic_frames)} duration={round(duration_ms / 1000, 2)}s "
        f"loop_rms={rms(loop_np):.4f} mic_rms={rms(mic_np):.4f} loopback_only={_loopback_only_mode}"
    )

    # Run ASR + source attribution concurrently
    loop = asyncio.get_running_loop()
    asr_task = loop.run_in_executor(None, _transcribe, mixed)
    src_task = loop.run_in_executor(None, quick_source, mic_np, loop_np)

    text, source = await asyncio.gather(asr_task, src_task)
    text = text.strip()
    if len(text) < 2:
        print("[CHUNK] dropped: transcription was empty or too short")
        return

    speaker = _last_speaker_info.get("label", "S0")
    # Fix: `process_text` currently accepts only the transcript text.
    processed = process_text(text)

    payload = {
        "text":     text,
        "source":   source,
        "speaker":  speaker,
        "actions":  processed.get("actions", []),
        "duration": round(duration_ms / 1000, 2),
        "ts":       round(time.time(), 3),
    }

    print(
        f"[TRANSCRIPT] speaker={speaker} source={source} "
        f"duration={payload['duration']}s text={text}"
    )

    # Fan out to all connected clients
    dead: set[WebSocket] = set()
    for ws in list(_clients):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)

    # Kick off async pyannote enrichment for the NEXT segment
    # (fire-and-forget — doesn't block the current emit)
    if diarize_pipeline is not None:
        asyncio.create_task(_async_diarize(mixed, mic_np, loop_np))

def _transcribe(audio: np.ndarray) -> str:
    """
    Run faster-whisper on an audio array.
    Returns the concatenated transcript text.
    """
    segments, _ = asr.transcribe(
        audio,
        beam_size=BEAM_SIZE,
        language="en",           # set to None for auto-detect (slower)
        vad_filter=True,         # faster-whisper's built-in VAD (extra guard)
        vad_parameters=dict(min_silence_duration_ms=200),
        word_timestamps=False,
    )
    return " ".join(s.text for s in segments)

async def _async_diarize(mixed: np.ndarray, mic: np.ndarray, loop: np.ndarray):
    """
    Run pyannote diarization in the background.
    Updates _last_speaker_info so the NEXT segment gets accurate labels.
    Does NOT block the current transcript emit.
    """
    if diarize_pipeline is None:
        return
    ev_loop = asyncio.get_running_loop()
    try:
        speakers = await ev_loop.run_in_executor(None, _run_diarize, mixed, mic, loop)
        if speakers:
            # Pick the dominant speaker by duration
            from collections import Counter
            counts = Counter(s["speaker"] for s in speakers)
            dominant = counts.most_common(1)[0][0]
            _last_speaker_info["label"] = dominant
    except Exception as e:
        print(f"async diarize error: {e}")

def _run_diarize(mixed: np.ndarray, mic: np.ndarray, loop: np.ndarray) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, mixed, SAMPLE_RATE)
        path = f.name
    try:
        diar = diarize_pipeline(path)
    except Exception as e:
        print(f"pyannote error: {e}")
        return []
    segments = []
    for turn, _, label in diar.itertracks(yield_label=True):
        s = int(max(0, round(turn.start * SAMPLE_RATE)))
        e = int(min(len(mixed), round(turn.end   * SAMPLE_RATE)))
        seg_mic  = mic[s:e]  if e > s else mic[s:]
        seg_loop = loop[s:e] if e > s else loop[s:]
        segments.append({
            "start":   round(turn.start, 2),
            "end":     round(turn.end,   2),
            "speaker": label,
            "source":  quick_source(seg_mic, seg_loop),
        })
    return segments

# ── LIFESPAN ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop, _loopback_only_mode
    _loop = asyncio.get_running_loop()

    mic_dev  = default_input()
    loop_dev = find_loopback()

    print(f"Mic device  : #{mic_dev}  {_device_name(mic_dev)}")
    if loop_dev is not None:
        print(f"Loop device : #{loop_dev} {_device_name(loop_dev)}")
    else:
        print("No loopback found — mic only.")

    streams = []
    loopback_only_candidate = loop_dev is not None and "pc speaker" in _device_name(loop_dev).lower()
    if loopback_only_candidate:
        # Fix: Realtek PC Speaker capture conflicts with the mic on this machine, so use system-audio-only mode.
        _loopback_only_mode = True
        print("Using loopback-only mode for system audio capture.")

    mic_stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=BLOCKSIZE,
        device=mic_dev,
        callback=_cb_mic,
        latency="low",       # ← request low-latency scheduling from PortAudio
    )
    mic_stream.start()
    streams.append(mic_stream)

    if loop_dev is not None:
        loop_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCKSIZE,
            device=loop_dev,
            callback=_cb_loop,
            latency="low",
        )
        loop_stream.start()
        streams.append(loop_stream)

    asyncio.create_task(vad_segmenter())
    print("STT engine running — ws://0.0.0.0:8000/ws")

    try:
        yield
    finally:
        _loopback_only_mode = False
        for s in streams:
            s.stop()
            s.close()

# ── FASTAPI + WEBSOCKET ───────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    if len(_clients) >= MAX_CLIENTS:
        await ws.close(code=1008, reason="Too many clients")
        return
    _clients.add(ws)
    print(f"WS connected  — total={len(_clients)}")
    try:
        # Keep alive: echo any client pings
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
        print(f"WS disconnected — total={len(_clients)}")

# ── ENTRY POINT ───────────────────────────────────────────────────────────────

def run():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

if __name__ == "__main__":
    run()
