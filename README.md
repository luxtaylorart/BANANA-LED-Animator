# B.A.N.A.N.A — Batch Arduino Nano Adafruit Neopixel Animator

**Lux Taylor Art.** A browser tool that writes ready-to-upload Arduino sketches for addressable LED strips (WS2812B / NeoPixel), with no hand-coding needed.

## How to use

1. In the sidebar, set your **total LED count**, the **data pin**, and the **animation type**.
2. Pick a **run mode**:
   - **Loop:** repeats forever, waiting the post-light hold time between runs.
   - **Hold:** plays once and stays on.
   - **Trigger:** starts from a limit switch (runs while held) or a pushbutton (starts on press). Wire the switch between the input pin and GND; the sketch uses the internal pull-up.
3. Adjust the settings for your animation, then click **Generate Code**.
4. Download the `.ino` file, or the ZIP, which unpacks into a sketch folder ready to open in the Arduino IDE. Upload it to your board.

**Required:** install the **Adafruit NeoPixel** library from the Arduino IDE Library Manager.

## Animation types

| Type | What it does |
|---|---|
| **Chunk** | Splits the strip into chunks that light one after another |
| **Smooth** | Fills or chases LED by LED, in a solid color, gradient, color sections, or rainbow |
| **Blink** | Blinks sections together, in sequence, at random, or in a custom order |
| **Random** | Random chunks flash on and off, optionally several at once, in solid, chosen, or random colors |
| **Color Sequence** | Steps the whole strip through a list of colors |

**Animation Easing** (under Extra Settings) fades between states instead of switching instantly.

## Notes

- Built for the Arduino Nano (ATmega328P, 2 KB RAM). **Smooth** stores a color for every LED in RAM, so on a Nano keep it under about 200 LEDs.
- Every WS2812B LED draws up to about 60 mA at full white. Power long strips from a separate 5 V supply, not from the Nano.

## Run locally

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

`led_core.py` contains all of the code generation. `streamlit_app.py` contains only the interface.

## License

B.A.N.A.N.A is © 2026 Lux Taylor and released under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) (see `LICENSE`). You may use, modify and share it for noncommercial purposes, as long as you keep the copyright notice. Selling, bundling into a paid product, or hosting it commercially requires permission.

**Generated code is yours.** Arduino sketches produced by this tool may be used for any purpose, including commercial projects, with no attribution required.
