# FloatNote STT Diarization Server

This project runs a local speech-to-text server that:

- captures microphone audio
- captures system/speaker audio through VB-Cable
- transcribes speech with `faster-whisper`
- sends transcript messages over WebSocket
- extracts simple action items with spaCy

The main entry point is [stt_diarization_server2.py](/C:/Users/Tashvi/Coding/FloatNote/Floatnote_git/stt_diarization_server2.py).



## Requirements

- Windows
- Python 3.10
- VB-Cable installed
- a working microphone

Optional:

- Hugging Face access token for `pyannote.audio`
- FFmpeg / TorchCodec compatibility if you want pyannote audio decoding to work fully

## Audio Device Setup

Recommended setup on this machine:

- Microphone input: `Microphone Array`
- Windows or app speaker output: `CABLE Input (VB-Audio Virtual Cable)`
- Server loopback capture: `CABLE Output (VB-Audio Virtual Cable)`

Do not use `Stereo Mix` as your main mic if you want your voice separated from system audio.

## Create The Virtual Environment

```powershell
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run The Server

```powershell
.\venv\Scripts\python.exe -u .\stt_diarization_server2.py
```

The server starts on:

- WebSocket: `ws://127.0.0.1:8000/ws`

The server now also prints transcript lines to the terminal in this format:

```text
[TRANSCRIPT] speaker=S0 source=mic duration=0.6s text=Hello.
```

## Watch Live Transcript Output

Open a second PowerShell window and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\watch_ws.ps1
```

This connects to `ws://127.0.0.1:8000/ws` and prints JSON messages from the server.

## How To Test

1. Start the server.
2. Start the watcher script in another terminal.
3. Speak into your microphone.
4. Or play a YouTube video while system output is set to `CABLE Input`.
5. Check the watcher window for transcript messages.

## Optional Device Overrides

If device auto-selection picks the wrong input, set environment variables before starting the server:

```powershell
$env:FLOATNOTE_MIC_DEVICE="19"
$env:FLOATNOTE_LOOP_DEVICE="21"
.\venv\Scripts\python.exe -u .\stt_diarization_server2.py
```

Use the correct indexes for your machine.

## Output Message Shape

The WebSocket server sends JSON payloads like:

```json
{
  "text": "hello there",
  "source": "mic",
  "speaker": "S0",
  "actions": [],
  "duration": 0.6,
  "ts": 1710000000.123
}
```

## Known Limitations

- `pyannote.audio` is currently optional and may fall back to RMS-only source attribution.
- You may see a `torchcodec` warning in stderr. In the current setup that warning is non-fatal.
- The Hugging Face token is currently hardcoded in the server file. Moving it to an environment variable would be safer.
- Device names and indexes can vary across machines and driver setups.

## Troubleshooting

If the server starts but you see no transcript output:

- confirm the watcher is connected to `ws://127.0.0.1:8000/ws`
- confirm your mic is the active input device
- confirm speaker output is routed to `CABLE Input`
- confirm VB-Cable recording side appears as `CABLE Output`
- try forcing device indexes with `FLOATNOTE_MIC_DEVICE` and `FLOATNOTE_LOOP_DEVICE`

If Python cannot run from the venv:

- recreate the venv using the real `python.exe`
- reinstall dependencies from [requirements.txt](/C:/Users/Tashvi/Coding/FloatNote/Floatnote_git/requirements.txt)
