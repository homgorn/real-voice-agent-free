# OpenAI Runtime Setup

VoiceAgent supports OpenAI-backed speech-to-text, turn generation, and text-to-speech.

## Required Environment Variables

```bash
VOICEAGENT_OPENAI_API_KEY=sk-...
VOICEAGENT_OPENAI_STT_MODEL=gpt-4o-transcribe
VOICEAGENT_OPENAI_LLM_MODEL=gpt-4.1-mini
VOICEAGENT_OPENAI_TTS_MODEL=gpt-4o-mini-tts
VOICEAGENT_OPENAI_TTS_RESPONSE_FORMAT=mp3
VOICEAGENT_RUNTIME_AUDIO_DIR=runtime_audio
```

## Runtime Behavior

- `input_text` skips STT and enters the turn pipeline directly
- `audio_ref` is treated as a local file path for transcription
- generated audio is written to `VOICEAGENT_RUNTIME_AUDIO_DIR`
- if `VOICEAGENT_OPENAI_API_KEY` is empty, VoiceAgent falls back to stub adapters

## Supported Flow

```text
caller input -> STT -> LLM -> tool inference / scheduling lookup -> TTS -> stored call turn
```

## Current Limitation

This is not a full realtime telephony media pipeline yet. It is the production-oriented backend runtime path for call-turn orchestration.

## Related Docs

- [../USAGE.md](../USAGE.md)
- [control-plane.md](control-plane.md)
- [scheduling-and-bookings.md](scheduling-and-bookings.md)
