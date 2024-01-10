---
language:
- en
tags:
- JETS
- LightSpeech
- MB-MelGAN
- Text-to-Speech
datasets:
- CMUArctic
- Hi-Fi
pipeline_tag: text-to-speech
---

# TTS Models

Here you can find models compatible with [Balacoon software](https://balacoon.com).
There are several model types to be aware of:

* `*_jets_cpu.addon` - JETS models for synthesis on CPU, compatible with
  [balacoon_tts](https://gemfury.com/balacoon/python:balacoon-tts) python package.
  A tutorial on how to use it can be found [here](https://balacoon.com/use/tts/package).
  Those are high-end models, producing 24khz audio.
* `*_light_cpu.addon` - Light models for lightning-fast synthesis on-device.
  Usage is the same as of JETS models, but the naturalness of synthesized audio is compromised
  in favor of speed. Models produce 16khz audio.
* `*_jets_gpu.addon` - JETS models for synthesis on GPU, compatible with
  [balacoon/tts_server](https://hub.docker.com/r/balacoon/tts_server) docker image.
  A tutorial on how to use it can be found [here](https://balacoon.com/use/tts/service).
  Exactly the same as jets_cpu models, but repacked for GPU.

You can check the interactive demo
[balacoon/tts](https://huggingface.co/spaces/balacoon/tts) space.

# List of available models

- en-US locale
  - [CMUArtic databases](http://festvox.org/cmu_arctic/)
    - <mark>en_us_cmuartic_jets_cpu.addon</mark>
    - <mark>en_us_cmuartic_jets_gpu.addon</mark>
  - [Hi-Fi audiobooks dataset](https://arxiv.org/abs/2104.01497)
    - <mark>en_us_hifi_jets_cpu.addon</mark>
    - <mark>en_us_hifi92_light_cpu.addon</mark> - trained only on "92" speaker
- uk locale
  - [Ukrainian TTS datasets](https://github.com/egorsmkv/ukrainian-tts-datasets)
    - <mark>uk_ltm_jets_cpu.addon</mark>
    - <mark>uk_ltm_jets_gpu.addon</mark>
    - <mark>uk_tetiana_light_cpu.addon</mark> - trained only on "Tetiana" speaker