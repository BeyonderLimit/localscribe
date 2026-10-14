# LocalScribe - Offline ASR Dictation Tool — Hardware-Adaptive TUI

This is a local-first, hardware-aware dictation application that benchmarks the client's machine, it recommends the best speech-recognition configuration, and continuously transcribes microphone input for as long as the user needs.

The key design principle is to maximize sustained transcription throughput, accuracy, and responsiveness, rather than simply selecting the largest model the hardware can load.

The application should work without an internet connection after its selected models have been downloaded. Audio processing and transcription remain on-device, and users can dictate meeting transcripts, long-form notes, or short snippets without a fixed session limit imposed by the application.

## 1. Proposed architecture

Terminal UI (TUI)

Live transcript · microphone meter · engine/model selection · performance controls

Hardware profiler & optimizer

CPU features · physical RAM · GPU/backend availability · benchmark · thermal/load-aware recommendations

Audio pipeline

Microphone → ring buffer → VAD → speech segments

Resource controller

Queue limits · inference scheduling · memory budgets · adaptive chunking

### Vosk

Streaming partial results and final utterances

### whisper.cpp

Chunked inference with configurable model and compute type

Local transcript store

Incremental saving · timestamps · recovery after interruption · export to TXT, SRT, or JSON

I'd use Python with Textual for the TUI, a dedicated audio-capture thread, a VAD such as Silero VAD or WebRTC VAD, and native speech engines behind a common adapter interface. The audio callback must never wait for inference or terminal rendering.

## 2. Engine selection: Vosk vs. whisper.cpp

Both engines should be selectable at runtime, but the optimizer should explain the trade-offs instead of assuming one engine is best on every machine.

OSCAR Hub | Service Catalog

## Vosk — continuous streaming

Low-latency option

- Good fit for live partial results and incremental dictation.
- Generally attractive for low-resource machines using a compact model.
- Offers streaming recognition APIs and offline models.
- Best when responsiveness and low resource consumption matter more than maximizing recognition accuracy across every accent or vocabulary.
  Reference: [Vosk official site](<https://alphacephei.com/vosk/>).



## whisper.cpp — accuracy and model flexibility

Quality-focused option

- Supports CPU inference, quantized models, and multiple hardware acceleration backends.
- Has real-time microphone examples and VAD integration.
- Offers multilingual transcription and English-specific model variants.
- Usually requires more careful tuning of chunk size, model size, and compute resources for responsive live dictation.
  Reference: [whisper.cpp source and documentation](<https://github.com/ggml-org/whisper.cpp>).

Important distinction: Vosk is naturally suited to streaming recognition. Whisper is typically run on bounded audio windows or speech segments. The application should hide these differences behind a common interface while preserving each engine's best operating mode. GitHub

+1

## 3. Hardware-aware model selection

At first launch, the program should inspect the machine, run a short representative benchmark, and propose a recommended configuration. Hardware specs provide an initial estimate; the benchmark determines whether the model actually keeps up with live speech.

The following are starting heuristics, not hard hardware guarantees.

| Available resources | Initial recommendation |
| --- | --- |
| 4 GB RAM or less | Vosk small model; minimize background overhead |
| 8 GB RAM, CPU only | Vosk small/medium or Whisper tiny/base |
| 16 GB RAM, modern CPU | Benchmark Whisper base/small against Vosk |
| 32 GB+ RAM or capable GPU | Benchmark Whisper small/medium and larger candidates |
| Strong supported GPU | Test GPU acceleration and compare sustained throughput with CPU |

For Whisper, the UI should expose model families such as `tiny`, `base`, `small`, `medium`, and `large`, with quantized variants wherever supported by the chosen backend. For Vosk, show only models actually available in the configured model catalog; its model names and language coverage differ.

The optimizer should measure:

- Real-time factor (RTF): inference time divided by audio duration. Below 1.0 means the engine processes audio faster than it arrives, on average.
- Peak and sustained RAM usage: reserve memory for the OS, audio buffers, and the terminal.
- Latency: how long speech takes to appear in the transcript.
- Backlog growth: whether incoming audio is accumulating faster than inference can process it.
- CPU/GPU load and thermal behavior: prevent an initially fast configuration from becoming unstable during long meetings.
- Accuracy proxy: compare candidate models on a short, user-approved local test recording where possible.

A larger model should not be recommended merely because it fits in RAM. It must also sustain the target transcription rate with headroom.

## 4. Interactive TUI configuration prototype

Here is the proposed configuration screen. You can change the hardware profile, engine, model, optimization priorities, and VAD settings to see how the recommendation logic should behave.

# Dictation setup

Illustrative settings preview · not a live hardware scan

### Hardware profile

System RAM4 4 GB or less

8 GB

16 GB

32 GB

64 GB or more

CPU classlow Low-power / older CPU

Modern desktop or laptop CPU

High-core-count workstation

Available accelerationnone CPU only / unknown GPU support

Apple Silicon / Metal

NVIDIA CUDA-capable GPU

Other supported accelerator

### Recognition settings

Speech engineauto Automatic — recommended for this profile

Vosk — streaming-first

whisper.cpp — model flexibility

Optimization priorityBalanced — good accuracy and sustained speed

speed Maximum throughput / minimum backlog

Favor transcription quality

Low CPU usage and background impact

Model selection Automatic — use hardware recommendation The actual model list should be filtered by engine and language. Manual selection takes precedence over automatic recommendations.

Maximum preferred partial-result latency### 500 ms

200 ms

1 s

2 s

A target for the UI and streaming pipeline; actual Whisper latency depends on inference speed and segment length.

Inference CPU threadsAutomatic (2 threads suggested)

2 2 threads

4 threads

6 threads

8 threads

[x]Enable voice activity detection (VAD)

## Proposed configuration

Engine

Vosk

Model suggestion

Small language model

Acceleration

CPU

Inference threads

2

VAD

Enabled

Priority

Throughput

 Review configuration

This is a recommendation preview, not a running speech-recognition engine. The production TUI should replace these example profiles with detected hardware capabilities and measured benchmark results.

## 5. Live dictation screen

The primary screen should remain simple enough to operate during a meeting without interrupting the user's workflow.

## LOCALSCRIBE

Offline dictation · Session 00:42:18

Listening

Microphone input

-12 dB

Engine

### Vosk

RTF

### 0.18×

Audio queue

### 0.2 s

### Transcript

Today we are reviewing the project milestones, discussing the current implementation, and identifying the remaining work for the next release.

We should prioritize reliable audio capture, make sure the transcript is saved continuously, and test performance on the lowest-spec client machines.

We also need to validate the model selection...

Illustrative mock data only — these are not actual microphone readings or transcription results.

Pause

Insert marker

Save / export

Useful keyboard shortcuts:

- `Space` — pause/resume capture.
- `Ctrl+S` — force-save the current transcript.
- `Ctrl+M` — insert a timestamped meeting marker.
- `Ctrl+E` — export the transcript.
- `Ctrl+,` — open engine and optimization settings.
- `Esc` — stop the current session safely.

The transcript should distinguish provisional partial text from finalized segments. For Whisper, repeated rolling-window output must be reconciled to avoid duplicated or disappearing words.

## 6. Keeping dictation running indefinitely

A genuinely long-running tool needs resource management and fault recovery, not just an open microphone loop.

1. Bounded audio capture. Use a preallocated ring buffer with a dedicated audio callback. The callback records samples and returns immediately; it never performs inference, disk writes, or terminal updates.
2. VAD-controlled inference. Detect speech boundaries, retain a short pre-roll and post-roll, and avoid processing prolonged silence unnecessarily. Include a maximum segment duration so continuous speech cannot create unbounded buffers.
3. Adaptive scheduling. Monitor queue depth and measured RTF. When processing falls behind, reduce overlapping Whisper windows, adjust segment length, or reduce thread contention. Don't silently drop spoken audio.
4. Memory-aware operation. Keep the selected model loaded where feasible, reuse audio buffers, limit transcript rendering frequency, and append finalized text to disk rather than retaining all raw audio indefinitely.
5. Checkpointing and recovery. Persist finalized text incrementally, use atomic checkpoints, and recover the last completed segment after an exception or restart.
6. Thermal and background awareness. Periodically reassess CPU load, memory pressure, and throughput. Recommend a smaller model or lower background priority when appropriate, but don't switch models mid-sentence or discard unprocessed audio.

One important design constraint: no software can guarantee zero transcription loss if inference cannot keep up with speech indefinitely on a given machine. If the backlog grows persistently, the tool should warn the user, preserve the audio in a bounded-to-disk spool when configured, and offer a lower-cost model. The application should never silently throw away speech just to maintain a latency target.

## 7. Model download and offline lifecycle

The model manager should have an explicit online setup phase and an offline operating phase.

- Show available models by engine, language, model size, approximate download size, and estimated memory requirements.
- Recommend a default using detected hardware and benchmark measurements.
- Allow a manual override, with compatibility warnings.
- Download to a temporary file, verify a trusted checksum where available, and install atomically only after verification.
- Store models in an application-owned directory and keep a manifest containing source, version, license, and checksum.
- Allow users to pre-download additional models before traveling or entering a restricted network.
- Never attempt network access as a fallback during offline dictation.

Useful references for implementing these parts are the [Vosk model catalog](<https://alphacephei.com/vosk/models>) and the [whisper.cpp model and acceleration documentation](<https://github.com/ggml-org/whisper.cpp>). Vosk's smaller models can be particularly useful on constrained systems, while whisper.cpp supports quantization and multiple acceleration backends. Alpha Cephei

+1

## 8. Suggested project structure

text
```
localscribe/
├── pyproject.toml
├── README.md
├── src/localscribe/
│   ├── app.py                 # Textual TUI and keyboard bindings
│   ├── config.py              # User settings and overrides
│   ├── hardware.py            # CPU, RAM, GPU/backend detection
│   ├── benchmark.py           # Throughput and memory tests
│   ├── optimizer.py           # Recommendations and adaptation
│   ├── audio/
│   │   ├── capture.py         # Microphone callback and ring buffer
│   │   ├── vad.py             # Voice activity detection
│   │   └── segments.py        # Speech boundaries and overlap
│   ├── engines/
│   │   ├── base.py            # Shared ASR interface
│   │   ├── vosk_engine.py
│   │   └── whisper_cpp.py
│   ├── models/
│   │   ├── catalog.py         # Supported models and metadata
│   │   └── manager.py         # Download, verify, install
│   ├── storage/
│   │   ├── transcript.py      # Incremental persistence
│   │   └── export.py          # TXT, SRT, JSON
│   └── monitoring.py          # Queue, RTF, load and memory
└── tests/
    ├── test_optimizer.py
    ├── test_audio_queue.py
    ├── test_transcript_recovery.py
    └── test_engine_adapters.py
```

