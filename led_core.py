APP_TITLE = "Lux Taylor Art / B.A.N.A.N.A (Batch Arduino Nano Adafruit Neopixel Animator)"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def to_int(s, default, lo=None, hi=None):
    try:
        v = int(str(s).strip())
    except:
        v = default
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v

def parse_rgb(text):
    try:
        parts = [p.strip() for p in str(text).split(",")]
        if len(parts) != 3:
            return (255, 255, 255)
        r = to_int(parts[0], 255, 0, 255)
        g = to_int(parts[1], 255, 0, 255)
        b = to_int(parts[2], 255, 0, 255)
        return (r, g, b)
    except:
        return (255, 255, 255)

def hsv_to_rgb(h):
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = 0.0
    q = 1.0 - f
    t = f
    i = i % 6
    if i == 0: r, g, b = 1.0, t, p
    elif i == 1: r, g, b = q, 1.0, p
    elif i == 2: r, g, b = p, 1.0, t
    elif i == 3: r, g, b = p, q, 1.0
    elif i == 4: r, g, b = t, p, 1.0
    else: r, g, b = 1.0, p, q
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))

def lerp(a, b, t):
    return int(round(a + (b - a) * t))

def build_gradient(stops, total_leds):
    n = len(stops)
    if n < 2:
        c = stops[0] if stops else (255, 255, 255)
        return [c] * total_leds
    segs = n - 1
    base = total_leds // segs
    rem = total_leds % segs
    lengths = [base] * segs
    lengths[-1] += rem
    out = []
    for si in range(segs):
        c0 = stops[si]
        c1 = stops[si + 1]
        L = lengths[si]
        if L <= 1:
            out.append(c1)
            continue
        for j in range(L):
            t = j / (L - 1)
            out.append((lerp(c0[0], c1[0], t), lerp(c0[1], c1[1], t), lerp(c0[2], c1[2], t)))
    if len(out) < total_leds:
        out += [stops[-1]] * (total_leds - len(out))
    return out[:total_leds]

def build_sections(colors, total_leds):
    n = len(colors)
    if n < 1:
        return [(255, 255, 255)] * total_leds
    base = total_leds // n
    rem = total_leds % n
    lengths = [base] * n
    lengths[-1] += rem
    out = []
    for i, c in enumerate(colors):
        out += [c] * lengths[i]
    if len(out) < total_leds:
        out += [colors[-1]] * (total_leds - len(out))
    return out[:total_leds]

def make_time_slices(total_ms, steps):
    steps = max(1, steps)
    base = total_ms // steps
    rem = total_ms - base * steps
    arr = [base] * steps
    for i in range(rem):
        arr[i] += 1
    return arr

def apply_randomizer_slices(slices, intensity_1_to_10):
    k = to_int(intensity_1_to_10, 0, 0, 10)
    if k == 0:
        return slices[:]
    percent = k * 25
    out = slices[:]
    steps = len(out)
    deltas = [0] * steps
    import random
    for i in range(steps - 1):
        base = out[i]
        maxj = int(round(base * (percent / 100.0)))
        if maxj <= 0:
            continue
        d = random.randint(-maxj, maxj)
        if base + d < 0:
            d = -base
        deltas[i] = d
    s = sum(deltas[:-1])
    deltas[-1] = -s
    if out[-1] + deltas[-1] < 0:
        need = -(out[-1] + deltas[-1])
        deltas[-1] += need
        i = 0
        while need > 0 and i < steps - 1:
            take = min(need, max(0, deltas[i] + out[i]))
            deltas[i] -= take
            need -= take
            i += 1
    for i in range(steps):
        out[i] = max(0, out[i] + deltas[i])
    s2 = sum(out)
    if s2 != sum(slices):
        diff = sum(slices) - s2
        out[-1] = max(0, out[-1] + diff)
    return out

def gen_chunk_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    chunks = params["num_chunks"]
    input_pin = params["input_pin"]
    mode = params["run_mode"]
    pre = params["pre_delay"]
    post = params["post_hold"]
    sizes = params["chunk_sizes"]
    starts = params["chunk_starts"]
    colors = params["rgb_values"]
    delays = params["delays"]
    ease_on = params.get("ease_on", False)
    ease_ms = params.get("ease_ms", 0)

    color_array = ",\n  ".join([f"strip.Color({r},{g},{b})" for (r, g, b) in colors])
    delay_array = ", ".join([f"{d}UL" for d in delays])

    code = f"""#include <Adafruit_NeoPixel.h>
#define LED_PIN {pin}
#define NUM_LEDS {total}
#define NUM_CHUNKS {chunks}
#define INPUT_PIN {input_pin}
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const int chunkStarts[NUM_CHUNKS] = {{{", ".join(map(str, starts))}}};
const int chunkLengths[NUM_CHUNKS] = {{{", ".join(map(str, sizes))}}};
const unsigned long chunkDelays[NUM_CHUNKS - 1] = {{{delay_array}}};
uint32_t chunkColors[NUM_CHUNKS] = {{
  {color_array}
}};
unsigned long lastStep = 0;
int currentChunk = -1;
bool running = false;
const bool EASE_ON = {"true" if ease_on else "false"};
const unsigned long EASE_MS = {to_int(ease_ms, 0, 0, 600000)}UL;

static inline uint8_t ur(uint32_t c) {{ return (uint8_t)(c >> 16); }}
static inline uint8_t ug(uint32_t c) {{ return (uint8_t)(c >> 8); }}
static inline uint8_t ub(uint32_t c) {{ return (uint8_t)(c); }}

void easeRange(int st, int ln, uint32_t target) {{
  if (!EASE_ON || EASE_MS == 0) {{
    for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = st; i < st + ln; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
  strip.show();
}}

void easeAll(uint32_t target) {{
  if (!EASE_ON || EASE_MS == 0) {{
    for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = 0; i < NUM_LEDS; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
  strip.show();
}}

void resetSequence() {{
  easeAll(0);
  currentChunk = -1;
  lastStep = millis();
  running = true;
}}

void setup() {{
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
  strip.show();
}}

void loop() {{
  unsigned long now = millis();
"""
    if mode == "trigger_limit":
        code += """  bool pressed = digitalRead(INPUT_PIN) == LOW;
  if (!pressed) {
    if (running) easeAll(0);
    running = false;
    return;
  }
  if (!running) resetSequence();
"""
    elif mode == "trigger_push":
        code += """  static bool lastState = HIGH;
  bool currentState = digitalRead(INPUT_PIN);
  if (lastState == HIGH && currentState == LOW) resetSequence();
  lastState = currentState;
  if (!running) return;
"""
    else:
        code += """  if (!running) resetSequence();
"""
    code += f"""  if (!running) return;
  if (currentChunk == -1) {{
    if (now - lastStep >= {pre}UL) {{
      currentChunk = 0;
      lastStep = now;
    }}
  }} else if (currentChunk < NUM_CHUNKS) {{
    if (currentChunk == 0 || now - lastStep >= chunkDelays[currentChunk - 1]) {{
      int st = chunkStarts[currentChunk];
      int ln = chunkLengths[currentChunk];
      easeRange(st, ln, chunkColors[currentChunk]);
      lastStep = now;
      currentChunk++;
    }}
  }} else {{
"""
    if mode == "loop":
        code += f"""    if (now - lastStep >= {post}UL) resetSequence();
"""
    code += """  }
}"""
    return code.strip()

def gen_smooth_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    input_pin = params["input_pin"]
    run_mode = params["run_mode"]
    pre = params["pre_delay"]
    post = params["post_hold"]
    anim_mode = params["smooth_anim_mode"]
    group = params["smooth_chase_group"]
    slices = params["smooth_slices"]
    pixel_colors = params["pixel_colors"]
    ease_on = params.get("ease_on", False)
    ease_ms = params.get("ease_ms", 0)

    arr = ",\n  ".join([f"0x{(r << 16) | (g << 8) | b:06X}UL" for (r, g, b) in pixel_colors])
    time_arr = ", ".join([f"{d}UL" for d in slices])
    steps = len(slices)
    chase_steps = max(1, total - group + 1)

    code = f"""#include <Adafruit_NeoPixel.h>
#define LED_PIN {pin}
#define NUM_LEDS {total}
#define INPUT_PIN {input_pin}
#define STEPS {steps}
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const uint32_t pixelColors[NUM_LEDS] PROGMEM = {{
  {arr}
}};
const unsigned long stepDelay[STEPS] = {{{time_arr}}};
bool running = false;
unsigned long lastMs = 0;
int stepIdx = -1;
int head = 0;
const bool EASE_ON = {"true" if ease_on else "false"};
const unsigned long EASE_MS = {to_int(ease_ms, 0, 0, 600000)}UL;

static inline uint8_t ur(uint32_t c) {{ return (uint8_t)(c >> 16); }}
static inline uint8_t ug(uint32_t c) {{ return (uint8_t)(c >> 8); }}
static inline uint8_t ub(uint32_t c) {{ return (uint8_t)(c); }}

void easePixel(int i, uint32_t target) {{
  if (!EASE_ON || EASE_MS == 0) {{
    strip.setPixelColor(i, target);
    strip.show();
    return;
  }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    uint32_t cur = strip.getPixelColor(i);
    int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
    int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
    int remain = frames - f;
    int nr = cr + (tr - cr) / remain;
    int ng = cg + (tg - cg) / remain;
    int nb = cb + (tb - cb) / remain;
    strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    strip.show();
    delay(per);
  }}
  strip.setPixelColor(i, target);
  strip.show();
}}

void allOff() {{
  strip.clear();
  strip.show();
}}

void allOffEase() {{
  if (!EASE_ON || EASE_MS == 0) {{ allOff(); return; }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = 0; i < NUM_LEDS; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int remain = frames - f;
      int nr = cr + (0 - cr) / remain;
      int ng = cg + (0 - cg) / remain;
      int nb = cb + (0 - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  allOff();
}}

void resetAnim() {{
  allOffEase();
  running = true;
  lastMs = millis();
  stepIdx = -1;
  head = 0;
}}

void setup() {{
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
  strip.show();
  allOff();
}}

void loop() {{
  unsigned long now = millis();
"""
    if run_mode == "trigger_limit":
        code += """  bool pressed = (digitalRead(INPUT_PIN) == LOW);
  if (!pressed) { if (running) allOffEase(); running = false; stepIdx = -1; head = 0; return; }
  if (!running) resetAnim();
"""
    elif run_mode == "trigger_push":
        code += """  static bool lastState = HIGH;
  bool cur = digitalRead(INPUT_PIN);
  if (lastState == HIGH && cur == LOW) resetAnim();
  lastState = cur;
  if (!running) return;
"""
    else:
        code += """  if (!running) resetAnim();
"""
    code += f"""  if (stepIdx == -1) {{
    if (now - lastMs >= {pre}UL) {{
      stepIdx = 0;
      lastMs = now;
    }}
    return;
  }}
  if (stepIdx >= STEPS) {{
"""
    if run_mode == "loop":
        code += f"""    if (now - lastMs >= {post}UL) resetAnim();
"""
    if run_mode == "trigger_limit" and anim_mode == "Chase":
        code += f"""    if (pressed) resetAnim();
"""
    code += """    return;
  }
  if (now - lastMs < stepDelay[stepIdx]) return;
  lastMs = now;
"""
    if anim_mode == "Fill":
        code += """  if (head < NUM_LEDS) {
    if (EASE_ON && EASE_MS > 0) {
      easePixel(head, pgm_read_dword(&pixelColors[head]));
    } else {
      strip.setPixelColor(head, pgm_read_dword(&pixelColors[head]));
      strip.show();
    }
    head++;
  }
"""
    else:
        code += f"""  int onIdx = head + {group} - 1;
  int offIdx = head - 1;
  if (onIdx >= 0 && onIdx < NUM_LEDS) {{
    if (EASE_ON && EASE_MS > 0) easePixel(onIdx, pgm_read_dword(&pixelColors[onIdx]));
    else {{ strip.setPixelColor(onIdx, pgm_read_dword(&pixelColors[onIdx])); strip.show(); }}
  }}
  if (offIdx >= 0 && offIdx < NUM_LEDS) {{
    if (EASE_ON && EASE_MS > 0) easePixel(offIdx, 0);
    else {{ strip.setPixelColor(offIdx, 0); strip.show(); }}
  }}
  head++;
  if (head > {chase_steps}) head = {chase_steps};
"""
    code += """  stepIdx++;
}"""
    return code.strip()

def gen_blink_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    input_pin = params["input_pin"]
    run_mode = params["run_mode"]
    sections = params["blink_sections"]
    starts = params["blink_starts"]
    lens = params["blink_lens"]
    colors = params["blink_colors"]
    blink_mode = params["blink_mode"]
    uniform_on = params["blink_uniform_on"]
    uniform_off = params["blink_uniform_off"]
    separate = params["blink_separate_timing"]
    on_by = params["blink_on_by"]
    off_by = params["blink_off_by"]
    custom_order = params["blink_custom_order"]
    ease_on = params.get("ease_on", False)
    ease_ms = params.get("ease_ms", 0)

    colors_arr = ", ".join([f"strip.Color({r},{g},{b})" for (r, g, b) in colors])
    starts_arr = ", ".join(map(str, starts))
    lens_arr = ", ".join(map(str, lens))
    on_arr = ", ".join([f"{v}UL" for v in on_by])
    off_arr = ", ".join([f"{v}UL" for v in off_by])

    order_arr = ", ".join([str(max(0, min(sections - 1, x))) for x in custom_order])
    if len(custom_order) < 1:
        order_arr = "0"
        custom_len = 1
    else:
        custom_len = len(custom_order)

    code = f"""#include <Adafruit_NeoPixel.h>
#define LED_PIN {pin}
#define NUM_LEDS {total}
#define INPUT_PIN {input_pin}
#define NUM_SECTIONS {sections}
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const int sectionStarts[NUM_SECTIONS] = {{{starts_arr}}};
const int sectionLengths[NUM_SECTIONS] = {{{lens_arr}}};
const uint32_t sectionColors[NUM_SECTIONS] = {{{colors_arr}}};
const int BLINK_MODE = {blink_mode};
const unsigned long uniformOnMs = {uniform_on}UL;
const unsigned long uniformOffMs = {uniform_off}UL;
const unsigned long onMsBySection[NUM_SECTIONS] = {{{on_arr}}};
const unsigned long offMsBySection[NUM_SECTIONS] = {{{off_arr}}};
const int customOrderLen = {custom_len};
const int customOrder[customOrderLen] = {{{order_arr}}};
bool active = false;
unsigned long lastStep = 0;
int idx = 0;
bool onPhase = false;
const bool EASE_ON = {"true" if ease_on else "false"};
const unsigned long EASE_MS = {to_int(ease_ms, 0, 0, 600000)}UL;

static inline uint8_t ur(uint32_t c) {{ return (uint8_t)(c >> 16); }}
static inline uint8_t ug(uint32_t c) {{ return (uint8_t)(c >> 8); }}
static inline uint8_t ub(uint32_t c) {{ return (uint8_t)(c); }}

void easeRange(int st, int ln, uint32_t target) {{
  if (!EASE_ON || EASE_MS == 0) {{
    for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = st; i < st + ln; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
  strip.show();
}}

void allOff() {{
  strip.clear();
  strip.show();
}}

void allOffEase() {{
  if (!EASE_ON || EASE_MS == 0) {{ allOff(); return; }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = 0; i < NUM_LEDS; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int remain = frames - f;
      int nr = cr + (0 - cr) / remain;
      int ng = cg + (0 - cg) / remain;
      int nb = cb + (0 - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  allOff();
}}

void renderTogether(bool on) {{
  if (!on) {{ allOffEase(); return; }}
  int frames = 1;
  unsigned long per = 0;
  if (EASE_ON && EASE_MS > 0) {{
    frames = (int)(EASE_MS / 15UL);
    if (frames < 4) frames = 4;
    if (frames > 40) frames = 40;
    per = EASE_MS / (unsigned long)frames;
    if (per == 0) per = 1;
  }}
  for (int f = 0; f < frames; f++) {{
    int remain = frames - f;
    for (int s = 0; s < NUM_SECTIONS; s++) {{
      uint32_t target = sectionColors[s];
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      for (int i = sectionStarts[s]; i < sectionStarts[s] + sectionLengths[s]; i++) {{
        uint32_t cur = strip.getPixelColor(i);
        int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
        strip.setPixelColor(i, strip.Color((uint8_t)(cr + (tr - cr) / remain), (uint8_t)(cg + (tg - cg) / remain), (uint8_t)(cb + (tb - cb) / remain)));
      }}
    }}
    strip.show();
    if (per) delay(per);
  }}
}}

void renderSingle(int s, bool on) {{
  if (!on) {{
    int st = sectionStarts[s];
    int ln = sectionLengths[s];
    easeRange(st, ln, 0);
    return;
  }}
  int st = sectionStarts[s];
  int ln = sectionLengths[s];
  easeRange(st, ln, sectionColors[s]);
}}

int curSection = 0;

int pickSection() {{
  if (BLINK_MODE == 2) return (int)random(NUM_SECTIONS);
  if (BLINK_MODE == 3) {{
    int s = customOrder[idx % customOrderLen];
    if (s < 0) s = 0;
    if (s >= NUM_SECTIONS) s = NUM_SECTIONS - 1;
    return s;
  }}
  return idx % NUM_SECTIONS;
}}

void resetBlink() {{
  idx = 0;
  onPhase = false;
  lastStep = millis();
  curSection = pickSection();
}}

void setup() {{
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
  strip.show();
  randomSeed(analogRead(0));
  allOff();
}}

void loop() {{
  unsigned long now = millis();
"""
    if run_mode == "trigger_limit":
        code += """  bool pressed = (digitalRead(INPUT_PIN) == LOW);
  if (!pressed) { if (active) allOffEase(); active = false; return; }
  if (!active) { active = true; resetBlink(); }
"""
    elif run_mode == "trigger_push":
        code += """  static bool lastState = HIGH;
  bool cur = digitalRead(INPUT_PIN);
  if (lastState == HIGH && cur == LOW) { active = true; resetBlink(); }
  lastState = cur;
  if (!active) return;
"""
    else:
        code += """  if (!active) { active = true; resetBlink(); }
"""
    code += f"""  if (BLINK_MODE == 0) {{
    unsigned long onMs = uniformOnMs;
    unsigned long offMs = uniformOffMs;
    if (!onPhase) {{
      if (now - lastStep >= offMs) {{
        onPhase = true;
        lastStep = now;
        renderTogether(true);
      }}
    }} else {{
      if (now - lastStep >= onMs) {{
        onPhase = false;
        lastStep = now;
        renderTogether(false);
      }}
    }}
    return;
  }}
  unsigned long onMs = uniformOnMs;
  unsigned long offMs = uniformOffMs;
"""
    if separate or blink_mode == 3:
        code += """  onMs = onMsBySection[curSection];
  offMs = offMsBySection[curSection];
"""
    code += """  if (!onPhase) {
    if (now - lastStep >= offMs) {
      onPhase = true;
      lastStep = now;
      renderSingle(curSection, true);
    }
  } else {
    if (now - lastStep >= onMs) {
      onPhase = false;
      lastStep = now;
      renderSingle(curSection, false);
      idx++;
      curSection = pickSection();
    }
  }
}"""
    return code.strip()

def gen_random_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    input_pin = params["input_pin"]
    run_mode = params["run_mode"]
    chunk_size = params["rand_chunk_size"]
    random_place = params["rand_random_placement"]
    base_on = params["rand_on_ms"]
    base_off = params["rand_off_ms"]
    freq_rand = params["rand_freq_rand"]
    freq_rand_ms = params["rand_freq_rand_ms"]
    simul = params["rand_simul"]
    max_simul = params["rand_max_simul"]
    timing_jitter = params["rand_timing_jitter"]
    jitter_ms = params["rand_jitter_ms"]
    color_mode = params["rand_color_mode"]
    solid = params["rand_solid_rgb"]
    subset = params["rand_subset_rgbs"]
    subset_n = len(subset)
    consistent = params["rand_consistent_placement"]
    ease_on = params.get("ease_on", False)
    ease_ms = params.get("ease_ms", 0)

    solid_expr = f"strip.Color({solid[0]},{solid[1]},{solid[2]})"
    subset_expr = ", ".join([f"strip.Color({c[0]},{c[1]},{c[2]})" for c in subset]) if subset_n > 0 else solid_expr

    code = f"""#include <Adafruit_NeoPixel.h>
#define LED_PIN {pin}
#define NUM_LEDS {total}
#define INPUT_PIN {input_pin}
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const int CHUNK_SIZE = {chunk_size};
const unsigned long BASE_ON_MS = {base_on}UL;
const unsigned long BASE_OFF_MS = {base_off}UL;
const bool FREQ_RAND = {"true" if freq_rand else "false"};
const unsigned long FREQ_RAND_MS = {freq_rand_ms}UL;
const bool RANDOM_PLACEMENT = {"true" if random_place else "false"};
const bool SIMUL = {"true" if simul else "false"};
const int MAX_SIMUL = {max_simul};
const bool TIMING_JITTER = {"true" if timing_jitter else "false"};
const unsigned long JITTER_MS = {jitter_ms}UL;
const int COLOR_MODE = {color_mode};
const uint32_t SOLID_COLOR = {solid_expr};
const int SUBSET_N = {max(1, subset_n)};
const uint32_t SUBSET_COLORS[SUBSET_N] = {{{subset_expr}}};
const bool CONSISTENT_PLACEMENT = {"true" if consistent else "false"};
const bool EASE_ON = {"true" if ease_on else "false"};
const unsigned long EASE_MS = {to_int(ease_ms, 0, 0, 600000)}UL;

static inline uint8_t ur(uint32_t c) {{ return (uint8_t)(c >> 16); }}
static inline uint8_t ug(uint32_t c) {{ return (uint8_t)(c >> 8); }}
static inline uint8_t ub(uint32_t c) {{ return (uint8_t)(c); }}

void easeAllTo(uint32_t target) {{
  if (!EASE_ON || EASE_MS == 0) {{
    for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = 0; i < NUM_LEDS; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
  strip.show();
}}

struct Slot {{
  bool on;
  unsigned long nextMs;
  int start;
  int len;
  uint32_t color;
}};
Slot slots[MAX_SIMUL];

bool active = false;

unsigned long randJitter(unsigned long v) {{
  if (!TIMING_JITTER || JITTER_MS == 0) return v;
  long j = (long)random((long)JITTER_MS + 1L);
  if (random(2) == 0) j = -j;
  long out = (long)v + j;
  if (out < 0) out = 0;
  return (unsigned long)out;
}}

unsigned long randFreq(unsigned long v) {{
  if (!FREQ_RAND || FREQ_RAND_MS == 0) return v;
  long j = (long)random((long)FREQ_RAND_MS + 1L);
  if (random(2) == 0) j = -j;
  long out = (long)v + j;
  if (out < 0) out = 0;
  return (unsigned long)out;
}}

uint32_t pickColor(int ledIndex) {{
  if (COLOR_MODE == 0) return SOLID_COLOR;
  if (COLOR_MODE == 1) {{
    if (CONSISTENT_PLACEMENT) {{
      long band = (long)ledIndex * (long)SUBSET_N / (long)NUM_LEDS;
      if (band >= SUBSET_N) band = SUBSET_N - 1;
      return SUBSET_COLORS[band];
    }}
    return SUBSET_COLORS[random(SUBSET_N)];
  }}
  return SOLID_COLOR;
}}

uint32_t randomConstrainedColor() {{
  int total = (int)random(80, 181);
  int r = (int)random(0, total + 1);
  int g = (int)random(0, (total - r) + 1);
  int b = total - r - g;

  int a = (int)random(0, 6);
  int R=r, G=g, B=b;
  if (a == 0) {{ R=r; G=g; B=b; }}
  else if (a == 1) {{ R=r; G=b; B=g; }}
  else if (a == 2) {{ R=g; G=r; B=b; }}
  else if (a == 3) {{ R=g; G=b; B=r; }}
  else if (a == 4) {{ R=b; G=r; B=g; }}
  else {{ R=b; G=g; B=r; }}

  return strip.Color((uint8_t)R, (uint8_t)G, (uint8_t)B);
}}

void computeChunk(int &st, int &ln) {{
  ln = CHUNK_SIZE;
  if (ln > NUM_LEDS) ln = NUM_LEDS;
  if (!RANDOM_PLACEMENT) {{
    int chunkCount = (NUM_LEDS + ln - 1) / ln;
    int k = random(chunkCount);
    st = k * ln;
    if (st + ln > NUM_LEDS) ln = NUM_LEDS - st;
    return;
  }}
  int start = random(NUM_LEDS);
  st = start;
  if (st + ln > NUM_LEDS) st = NUM_LEDS - ln;
  if (st < 0) st = 0;
}}

bool overlaps(int st, int ln, int otherSt, int otherLn) {{
  int a0 = st;
  int a1 = st + ln - 1;
  int b0 = otherSt;
  int b1 = otherSt + otherLn - 1;
  if (a1 < b0) return false;
  if (b1 < a0) return false;
  return true;
}}

void assignSlot(int k) {{
  int st = 0;
  int ln = 0;
  bool placed = false;
  int limit = SIMUL ? MAX_SIMUL : 1;
  for (int attempt = 0; attempt < 16; attempt++) {{
    computeChunk(st, ln);
    if (!SIMUL) {{ placed = true; break; }}
    bool ok = true;
    for (int i = 0; i < limit; i++) {{
      if (i == k) continue;
      if (slots[i].on) {{
        if (overlaps(st, ln, slots[i].start, slots[i].len)) {{ ok = false; break; }}
      }}
    }}
    if (ok) {{ placed = true; break; }}
  }}
  if (!placed) computeChunk(st, ln);
  slots[k].start = st;
  slots[k].len = ln;
}}

void renderSlots() {{
  strip.clear();
  int limit = SIMUL ? MAX_SIMUL : 1;
  for (int s = 0; s < limit; s++) {{
    if (!slots[s].on) continue;
    int st = slots[s].start;
    int ln = slots[s].len;

    if (COLOR_MODE == 2 || (COLOR_MODE == 1 && !CONSISTENT_PLACEMENT)) {{
      for (int i = st; i < st + ln; i++) strip.setPixelColor(i, slots[s].color);
    }} else {{
      for (int i = st; i < st + ln; i++) strip.setPixelColor(i, pickColor(i));
    }}
  }}
  strip.show();
}}

void resetAll() {{
  int limit = SIMUL ? MAX_SIMUL : 1;
  for (int i = 0; i < limit; i++) {{
    slots[i].on = false;
    slots[i].nextMs = millis();
    slots[i].start = 0;
    slots[i].len = 0;
    slots[i].color = SOLID_COLOR;
    assignSlot(i);
  }}
}}

void setup() {{
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
  strip.show();
  randomSeed(analogRead(0));
  easeAllTo(0);
  resetAll();
}}

void loop() {{
  unsigned long now = millis();
"""
    if run_mode == "trigger_limit":
        code += """  bool pressed = (digitalRead(INPUT_PIN) == LOW);
  if (!pressed) { if (active) easeAllTo(0); active = false; return; }
  if (!active) { active = true; resetAll(); }
"""
    elif run_mode == "trigger_push":
        code += """  static bool lastState = HIGH;
  bool cur = digitalRead(INPUT_PIN);
  if (lastState == HIGH && cur == LOW) { active = true; resetAll(); }
  lastState = cur;
  if (!active) return;
"""
    else:
        code += """  if (!active) { active = true; resetAll(); }
"""
    code += """  int limit = SIMUL ? MAX_SIMUL : 1;
  bool changed = false;
  for (int s = 0; s < limit; s++) {
    if ((long)(now - slots[s].nextMs) < 0) continue;
    changed = true;
    if (!slots[s].on) {
      slots[s].on = true;
      if (COLOR_MODE == 2) slots[s].color = randomConstrainedColor();
      else if (COLOR_MODE == 1 && !CONSISTENT_PLACEMENT) slots[s].color = SUBSET_COLORS[random(SUBSET_N)];
      unsigned long t = randFreq(BASE_ON_MS);
      t = randJitter(t);
      slots[s].nextMs = now + t;
    } else {
      slots[s].on = false;
      unsigned long t = randFreq(BASE_OFF_MS);
      t = randJitter(t);
      slots[s].nextMs = now + t;
      assignSlot(s);
    }
  }
  if (changed) renderSlots();
}"""
    return code.strip()


def gen_color_sequence_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    input_pin = params["input_pin"]
    run_mode = params["run_mode"]
    pre = params["pre_delay"]
    post = params["post_hold"]
    steps = params["cs_steps"]
    colors = params["cs_colors"]
    durs = params["cs_durs"]
    cs_loop = params["cs_loop"]
    ease_on = params.get("ease_on", False)
    ease_ms = params.get("ease_ms", 0)

    color_exprs = ", ".join([f"strip.Color({c[0]},{c[1]},{c[2]})" for c in colors])
    dur_exprs = ", ".join([f"{to_int(d, 0, 0, 600000)}UL" for d in durs])

    code = f"""#include <Adafruit_NeoPixel.h>
#define LED_PIN {pin}
#define NUM_LEDS {total}
#define INPUT_PIN {input_pin}
#define STEPS {steps}
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const uint32_t stepColors[STEPS] = {{{color_exprs}}};
const unsigned long stepDur[STEPS] = {{{dur_exprs}}};
const bool CS_LOOP = {"true" if cs_loop else "false"};
const bool EASE_ON = {"true" if ease_on else "false"};
const unsigned long EASE_MS = {to_int(ease_ms, 0, 0, 600000)}UL;

static inline uint8_t ur(uint32_t c) {{ return (uint8_t)(c >> 16); }}
static inline uint8_t ug(uint32_t c) {{ return (uint8_t)(c >> 8); }}
static inline uint8_t ub(uint32_t c) {{ return (uint8_t)(c); }}

void easeAllTo(uint32_t target) {{
  if (!EASE_ON || EASE_MS == 0) {{
    for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }}
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {{
    for (int i = 0; i < NUM_LEDS; i++) {{
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }}
    strip.show();
    delay(per);
  }}
  for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
  strip.show();
}}

void allOff() {{
  strip.clear();
  strip.show();
}}

void allOffEase() {{
  easeAllTo(0);
}}

bool running = false;
unsigned long lastMs = 0;
int idx = -1;

void resetSeq() {{
  allOffEase();
  running = true;
  lastMs = millis();
  idx = -1;
}}

void setup() {{
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
  strip.show();
  allOff();
}}

void loop() {{
  unsigned long now = millis();
"""
    if run_mode == "trigger_limit":
        code += """  bool pressed = (digitalRead(INPUT_PIN) == LOW);
  if (!pressed) { if (running) allOffEase(); running = false; return; }
  if (!running) resetSeq();
"""
    elif run_mode == "trigger_push":
        code += """  static bool lastState = HIGH;
  bool cur = digitalRead(INPUT_PIN);
  if (lastState == HIGH && cur == LOW) resetSeq();
  lastState = cur;
  if (!running) return;
"""
    else:
        code += """  if (!running) resetSeq();
"""
    code += f"""  if (idx == -1) {{
    if (now - lastMs >= {pre}UL) {{
      idx = 0;
      lastMs = now;
      easeAllTo(stepColors[0]);
    }}
    return;
  }}
  if (idx >= STEPS) {{
"""
    if run_mode == "loop":
        code += f"""    if (now - lastMs >= {post}UL) resetSeq();
"""
    code += """    return;
  }
  if (now - lastMs < stepDur[idx]) return;
  lastMs = now;
  idx++;
  if (idx >= STEPS) {
"""
    if run_mode == "loop":
        code += """    return;
"""
    else:
        code += """    if (!CS_LOOP) return;
    idx = 0;
"""
    code += """  }
  easeAllTo(stepColors[idx]);
}"""
    return code.strip()


TICKER_PATTERNS = ["Wave", "Sequence", "Together", "Alternate"]


def ticker_timing(pattern, num_colors, on_ms, off_ms, stagger_ms, step_ms):
    n = max(1, num_colors)
    if pattern == "Sequence":
        on = [step_ms] * n
        off = [step_ms * (n - 1)] * n
        phase = [c * step_ms for c in range(n)]
    elif pattern == "Together":
        on, off, phase = [on_ms] * n, [off_ms] * n, [0] * n
    elif pattern == "Alternate":
        on, off = [on_ms] * n, [off_ms] * n
        phase = [(c % 2) * on_ms for c in range(n)]
    else:
        on, off = [on_ms] * n, [off_ms] * n
        phase = [c * stagger_ms for c in range(n)]
    return on, off, phase


def apply_brightness(code, brightness):
    b = to_int(brightness, 255, 1, 255)
    if b >= 255:
        return code
    return code.replace("  strip.begin();\n", f"  strip.begin();\n  strip.setBrightness({b});\n", 1)


def gen_ticker_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    input_pin = params["input_pin"]
    run_mode = params["run_mode"]
    chunk = max(1, min(total, params["ticker_chunk_size"]))
    colors = params["ticker_colors"]
    n = len(colors)
    on_ms = params["ticker_on_ms"]
    off_ms = params["ticker_off_ms"]
    phase_ms = params["ticker_phase_ms"]
    scroll = params.get("ticker_scroll", False)
    reverse = params.get("ticker_reverse", False)
    step_ms = max(1, to_int(params.get("ticker_step_ms", 100), 100, 1, 600000))
    step_leds = max(1, to_int(params.get("ticker_step_leds", 1), 1, 1, 100000))
    ease_on = params.get("ease_on", False)
    ease_ms = to_int(params.get("ease_ms", 0), 0, 0, 600000) if ease_on else 0

    def arr(vals):
        return ", ".join(f"{to_int(v, 0, 0, 600000)}UL" for v in vals)

    color_arr = ", ".join(f"0x{(r << 16) | (g << 8) | b:06X}UL" for (r, g, b) in colors)

    code = f"""#include <Adafruit_NeoPixel.h>
#define LED_PIN {pin}
#define NUM_LEDS {total}
#define INPUT_PIN {input_pin}
#define CHUNK_SIZE {chunk}
#define NUM_COLORS {n}
#define PATTERN_LEN ((long)CHUNK_SIZE * NUM_COLORS)
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const uint32_t COLORS[NUM_COLORS] = {{{color_arr}}};
const unsigned long ON_MS[NUM_COLORS] = {{{arr(on_ms)}}};
const unsigned long OFF_MS[NUM_COLORS] = {{{arr(off_ms)}}};
const unsigned long PHASE_MS[NUM_COLORS] = {{{arr(phase_ms)}}};
const bool SCROLL = {"true" if scroll else "false"};
const bool SCROLL_REVERSE = {"true" if reverse else "false"};
const unsigned long STEP_MS = {step_ms}UL;
const long STEP_LEDS = {step_leds}L;
const unsigned long EASE_MS = {ease_ms}UL;
const unsigned long EASE_DIV = EASE_MS ? EASE_MS : 1UL;

uint8_t level[NUM_COLORS];
long lastOffset = -1;
bool active = false;
bool stopping = false;
unsigned long startMs = 0;
unsigned long stopMs = 0;

uint8_t colorLevel(int c, unsigned long elapsed) {{
  unsigned long period = ON_MS[c] + OFF_MS[c];
  if (period == 0 || ON_MS[c] == 0) return 0;
  if (OFF_MS[c] == 0) return 255;
  unsigned long pos = (elapsed + period - (PHASE_MS[c] % period)) % period;
  if (EASE_MS == 0) return pos < ON_MS[c] ? 255 : 0;
  if (pos < ON_MS[c]) return pos >= EASE_MS ? 255 : (uint8_t)((pos * 255UL) / EASE_DIV);
  unsigned long peak = ON_MS[c] >= EASE_MS ? 255UL : (ON_MS[c] * 255UL) / EASE_DIV;
  unsigned long d = pos - ON_MS[c];
  if (d >= EASE_MS) return 0;
  return (uint8_t)(peak - (peak * d) / EASE_DIV);
}}

uint32_t scaled(uint32_t c, uint8_t l) {{
  if (l == 255) return c;
  if (l == 0) return 0;
  uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * l / 255);
  uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * l / 255);
  uint8_t b = (uint8_t)((c & 0xFF) * l / 255);
  return strip.Color(r, g, b);
}}

void render(unsigned long elapsed, uint8_t master) {{
  bool changed = false;
  for (int c = 0; c < NUM_COLORS; c++) {{
    uint8_t l = (uint8_t)(((uint16_t)colorLevel(c, elapsed) * master) / 255);
    if (l != level[c]) {{ level[c] = l; changed = true; }}
  }}
  long offset = 0;
  if (SCROLL) offset = (long)(((elapsed / STEP_MS) % PATTERN_LEN) * STEP_LEDS % PATTERN_LEN);
  if (offset != lastOffset) {{ lastOffset = offset; changed = true; }}
  if (!changed) return;
  for (int i = 0; i < NUM_LEDS; i++) {{
    long p = SCROLL_REVERSE ? (long)i + offset : (long)i - offset;
    p %= PATTERN_LEN;
    if (p < 0) p += PATTERN_LEN;
    int c = (int)(p / CHUNK_SIZE);
    strip.setPixelColor(i, scaled(COLORS[c], level[c]));
  }}
  strip.show();
}}

void startTicker(unsigned long now) {{
  active = true;
  stopping = false;
  startMs = now;
  lastOffset = -1;
}}

void stopTicker(unsigned long now) {{
  if (!active || stopping) return;
  stopping = true;
  stopMs = now;
}}

void setup() {{
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
  strip.clear();
  strip.show();
}}

void loop() {{
  unsigned long now = millis();
"""
    if run_mode == "trigger_limit":
        code += """  if (digitalRead(INPUT_PIN) == LOW) {
    if (!active || stopping) startTicker(now);
  } else {
    stopTicker(now);
  }
"""
    elif run_mode == "trigger_push":
        code += """  static int lastRaw = HIGH;
  static int stable = HIGH;
  static unsigned long lastChange = 0;
  int raw = digitalRead(INPUT_PIN);
  if (raw != lastRaw) { lastRaw = raw; lastChange = now; }
  if (now - lastChange >= 30UL && raw != stable) {
    stable = raw;
    if (stable == LOW) {
      if (active && !stopping) stopTicker(now);
      else startTicker(now);
    }
  }
"""
    else:
        code += """  if (!active) startTicker(now);
"""
    code += """  if (!active) return;
  uint8_t master = 255;
  if (stopping) {
    unsigned long d = now - stopMs;
    if (d >= EASE_MS) {
      active = false;
      stopping = false;
      for (int c = 0; c < NUM_COLORS; c++) level[c] = 0;
      strip.clear();
      strip.show();
      return;
    }
    master = (uint8_t)(255UL - (d * 255UL) / EASE_DIV);
  }
  render(now - startMs, master);
}"""
    return code.strip()
