import asyncio
import logging
import queue
import time

_missing: list[str] = []

try:
    import numpy as np
except ImportError:
    _missing.append("numpy>=1.24.0")

try:
    import sounddevice as sd
except ImportError:
    _missing.append("sounddevice>=0.4.0")

try:
    import edge_tts
except ImportError:
    _missing.append("edge-tts==7.2.8")

try:
    import pytchat
except ImportError:
    _missing.append("pytchat==0.5.5")

try:
    from PySide6.QtCore import QThread, Signal
except ImportError:
    _missing.append("PySide6>=6.11.0")

if _missing:
    import sys
    lines = "\n".join(f"  {p}" for p in _missing)
    sys.exit(f"Missing dependencies:\n{lines}\nRun: pip install -r requirements.txt")

_logger = logging.getLogger("worker")
_VOICES = [
    "th-TH-PremwadeeNeural",
    "th-TH-AcharaNeural",
    "th-TH-NiwatNeural",
]
_SAMPLE_RATE = 24_000


class TTSWorker(QThread):
    tray_notify    = Signal(str, str)
    status_changed = Signal(str)
    warn_error     = Signal(str)
    fatal_error    = Signal(str)

    def __init__(self, video_id: str, delay_per_char: float, max_delay: float) -> None:
        super().__init__()
        self.video_id       = video_id
        self.delay_per_char = delay_per_char
        self.max_delay      = max_delay
        self._running       = True
        self._q: queue.Queue[str] = queue.Queue(maxsize=50)
        self._loop: asyncio.AbstractEventLoop | None = None

    def stop(self) -> None:
        self._running = False
        sd.stop()

    async def _generate_pcm(self, text: str) -> bytes | None:
        for voice in _VOICES:
            try:
                chunks: list[bytes] = []
                async for chunk in edge_tts.Communicate(
                    text, voice, output_format="raw-24khz-16bit-mono-pcm"
                ).stream():
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
                return b"".join(chunks)
            except Exception as e:
                _logger.warning("Voice fail %s: %s", voice, e)
        return None

    async def _tts_loop(self) -> None:
        while self._running:
            try:
                text = self._q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            _logger.info("TTS: %s", text[:60])

            # Generate PCM in memory — previous utterance keeps playing while this generates
            pcm = await self._generate_pcm(text)
            if pcm is None:
                _logger.error("TTS generation failed — all voices exhausted")
                self.warn_error.emit("TTS generation failed — all voices exhausted")
                continue

            samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

            # Interrupt whatever is playing and start this utterance
            try:
                sd.stop()
                sd.play(samples, samplerate=_SAMPLE_RATE)
            except Exception as e:
                _logger.error("Audio playback error: %s", e)
                self.warn_error.emit(f"Audio playback error: {e}")
                continue

            self.tray_notify.emit("Now speaking", text[:80])

            # Wait for natural end or next item arriving in queue
            while self._running:
                try:
                    active = sd.get_stream().active
                except Exception:
                    active = False
                if not active or not self._q.empty():
                    break
                await asyncio.sleep(0.05)

    async def _chat_loop(self) -> None:
        _logger.info("=== SESSION START ===")
        attempts = 0
        while self._running:
            chat = None
            last_msg = time.time()
            try:
                if not self.video_id:
                    _logger.warning("No YouTube video ID configured")
                    self.status_changed.emit("No video ID")
                    self.fatal_error.emit("No YouTube video ID configured")
                    self._running = False
                    break

                attempts += 1
                self.status_changed.emit(f"Connecting... ({attempts}/3)")
                _logger.info("Connecting: %s (attempt %d/3)", self.video_id, attempts)
                chat = pytchat.create(video_id=self.video_id)
                attempts = 0  # reset on successful connect
                self.status_changed.emit("Live")
                _logger.info("Connected to chat")
                self.tray_notify.emit("tdibam_t2s", "Connected to YouTube chat")

                while chat.is_alive() and self._running:
                    items = list(chat.get().sync_items())
                    if items:
                        last_msg = time.time()
                    for c in items:
                        msg = f"{c.author.name} พูดว่า {c.message}".strip()
                        try:
                            self._q.put_nowait(msg)
                        except queue.Full:
                            _logger.warning("Queue full — message dropped")
                    if time.time() - last_msg > 60:
                        _logger.info("No messages for 60s — reconnecting")
                        break
                    await asyncio.sleep(0.5)

            except Exception as e:
                _logger.error("Connection error (attempt %d/3): %s", attempts, e)
                self.status_changed.emit("Error")
                if attempts >= 3:
                    _logger.error("Failed to connect after 3 attempts — ending session")
                    self.fatal_error.emit(f"Could not connect after 3 attempts: {e}")
                    self._running = False
                    break
                self.warn_error.emit(str(e))
            finally:
                if chat:
                    try:
                        chat.terminate()
                    except Exception:
                        pass

            if self._running:
                _logger.info("Restarting in 5s...")
                self.status_changed.emit("Reconnecting...")
                await asyncio.sleep(5)

        _logger.info("=== SESSION END ===")
        self.status_changed.emit("Stopped")

    async def _main(self) -> None:
        await asyncio.gather(self._chat_loop(), self._tts_loop())

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._loop.close()
            self._loop = None
