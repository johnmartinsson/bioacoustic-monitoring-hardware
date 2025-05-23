### Reading guide for *Acoustics and Audio Technology* (M. Kleiner)

Below is a two-pass route through the book that zeroes-in on the specific questions you’ve been asking (gain staging, noise, converter resolution) while giving you just enough background in acoustics to put those ideas in context.

---

## Pass 1 — Targeted “need-to-know” tour (± 120 pp)

| Step                                                 | Pages / sections                                                                                                        | Why read them now                                                                                                                                                           |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1.   The dB toolbox**                              | **§2.4 Noise**, **§2.5 The Level Concept**, **§2.8 Reference Levels**, **§2.9 Addition of Level Contributions**         | All the arithmetic you need to convert mic specs (dBu, dBV, dB SPL) into the dBFS world of your DAW and to see how noise sums when you add channels or raise gain.          |
| **2.   What a microphone really delivers**           | **§12.2 Dynamic Range, Frequency Response, Noise, and Distortion**                                                      | Gives concrete EIN figures and explains *how* self-noise is specified—essential when you look at “–128 dBu” numbers and wonder how far above them you should record.        |
| **3.   The A/D bottleneck**                          | **§16.2 Sampling and Digitisation**, **§16.3 Quantisation**, **§16.4 Additional Problems in A/D and D/A Conversion**    | Clarifies why a 24-bit mantissa is the true precision even in 32-bit float, shows where dither lives, and spells out analogue front-end limits (aperture error, S/H noise). |
| **4.   Measuring SNR in practice**                   | **§17.11 Noise Level and Signal-to-Noise Ratio**, skim **§17.21 Frequency Response, Spectrogram, and Wavelet Analysis** | Bridges the theory to real-world metering and spectrum plots—the same ideas you replicated in the Python script.                                                            |
| **5.   Quick psychoacoustics checkpoint (optional)** | **§3.3 Psychoacoustic Dimensions**, **§3.5 Masking**                                                                    | A 10-page detour that explains why 40 dB of hiss is objectionable even when “technically” below programme peaks, and why dithering works.                                   |
| **6.   Wrap-up with worked problems**                | End-of-chapter problems for Ch. 2, Ch. 12, Ch. 16                                                                       | Reinforces the calculations you’ll do when deciding how much analogue gain to add.                                                                                          |

*Outcome:* after this pass you can read spec-sheets fluently, predict how many dB of headroom a take needs, and understand every metric printed by the script you just ran.

---

## Pass 2 — Building the wider picture (cherry-pick as interests grow)

| Theme                         | Suggested chapters / sections                                                          | What you’ll gain                                                                                                                                    |
| ----------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Room & spatial acoustics**  | Ch. 4, Ch. 5, Ch. 6                                                                    | How room modes, early reflections, and diffusion affect the *noise floor you actually hear* and where to place mics to keep wanted signal dominant. |
| **Noise-control engineering** | Ch. 7 (Absorbers … Diffusers), Ch. 10 (Sound Isolation)                                | Practical tactics to lower ambient noise so you *can* afford conservative gain without drowning in hiss.                                            |
| **Transducers in depth**      | Remaining parts of Ch. 12 (mic principles), Ch. 14 (Loudspeakers), Ch. 15 (Headphones) | A fuller engineering look at why some mics have lower self-noise, how loudspeakers interact with rooms, etc.                                        |
| **Listening tests & metrics** | §§17.24 – 17.34                                                                        | How to design AB-tests that prove (to clients or teammates) the benefit of proper gain staging versus “fix it in post”.                             |

---

## How to pace yourself

| Week   | Reading load                                                     | Hands-on exercise                                                                                                      |
| ------ | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **1**  | Steps 1 & 2 above (≈ 40 pp)                                      | Re-analyse three of your own takes at different gains; correlate noise-floor in dBFS with what you *hear* on phones.   |
| **2**  | Steps 3 & 4 (≈ 50 pp)                                            | Modify the Python script to compute **LUFS-I** with *pyloudnorm*; compare to RMS numbers.                              |
| **3**  | Step 5 plus selected problems (≈ 30 pp)                          | Record the same source with two different mics; use the book’s formulas to predict and then measure SNR in both files. |
| **4+** | Start cherry-picking Pass 2 topics that match upcoming projects. | e.g. Before a location shoot in a reverberant hall, read Ch. 4 §4.2 and Ch. 7 §7.3, then design absorber placement.    |

---

### Tips for efficient reading

1. **Keep the symbols list (p. xix) bookmarked**—it saves hunting when formulas appear.
2. **Alternate theory with practice.** After every 20-page chunk, open your DAW and verify at least one concept (e.g., measure crest factor, observe masking in a spectrogram).
3. **Use the “Web Added Value™” index (p. xxii)**: many figures are downloadable; printing a few key ones (ADC block diagram, weighting curves) and taping them near your desk helps retention.
4. **Solve at least two end-of-chapter problems per session**—they are intentionally short and almost all map directly to real recording scenarios.

---

#### TL;DR

*Read Chapter 2 sections on noise & levels, Chapter 12 section 12.2 on mic dynamic range, and Chapter 16 sections on sampling/quantisation **first**; they address your gain-staging questions head-on.  Then circle back for room acoustics and noise-control once you’re comfortable with the signal chain itself.* Enjoy the journey!
