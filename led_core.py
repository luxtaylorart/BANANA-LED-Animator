import random

TICKER_PATTERNS = ["Wave", "Sequence", "Together", "Alternate"]


def to_int(text, default, lowest, highest):
    try:
        number = int(text)
    except ValueError:
        number = default
    if number < lowest:
        number = lowest
    if number > highest:
        number = highest
    return number


def split_evenly(total, parts):
    sizes = []
    for i in range(parts):
        sizes.append(total // parts)
    sizes[parts - 1] = sizes[parts - 1] + total % parts
    return sizes


def starts_of(sizes):
    starts = []
    position = 0
    for size in sizes:
        starts.append(position)
        position = position + size
    return starts


def limit_to_600000(values):
    limited = []
    for value in values:
        if value > 600000:
            limited.append(600000)
        else:
            limited.append(value)
    return limited


def make_c_list(values, separator=", ", ending=""):
    text = ""
    for i in range(len(values)):
        if i > 0:
            text = text + separator
        text = text + str(values[i]) + ending
    return text


def c_bool(value):
    if value:
        return "true"
    return "false"


def strip_color(color):
    return "strip.Color(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"


def strip_color_list(colors, separator):
    texts = []
    for color in colors:
        texts.append(strip_color(color))
    return make_c_list(texts, separator)


def hex_color(color):
    number = color[0] * 65536 + color[1] * 256 + color[2]
    return "0x" + format(number, "06X") + "UL"


def hex_color_list(colors, separator):
    texts = []
    for color in colors:
        texts.append(hex_color(color))
    return make_c_list(texts, separator)


def hsv_to_rgb(hue):
    section = int(hue * 6.0)
    rising = hue * 6.0 - section
    falling = 1.0 - rising
    if section == 0:
        red = 1.0
        green = rising
        blue = 0.0
    elif section == 1:
        red = falling
        green = 1.0
        blue = 0.0
    elif section == 2:
        red = 0.0
        green = 1.0
        blue = rising
    elif section == 3:
        red = 0.0
        green = falling
        blue = 1.0
    elif section == 4:
        red = rising
        green = 0.0
        blue = 1.0
    else:
        red = 1.0
        green = 0.0
        blue = falling
    return (int(round(red * 255)), int(round(green * 255)), int(round(blue * 255)))


def blend(a, b, t):
    return int(round(a + (b - a) * t))


def build_gradient(stops, total_leds):
    segment_count = len(stops) - 1
    lengths = split_evenly(total_leds, segment_count)
    colors = []
    for s in range(segment_count):
        start = stops[s]
        end = stops[s + 1]
        length = lengths[s]
        if length <= 1:
            colors.append(end)
        else:
            for j in range(length):
                t = j / (length - 1)
                red = blend(start[0], end[0], t)
                green = blend(start[1], end[1], t)
                blue = blend(start[2], end[2], t)
                colors.append((red, green, blue))
    return colors[:total_leds]


def build_sections(colors, total_leds):
    lengths = split_evenly(total_leds, len(colors))
    pixel_colors = []
    for i in range(len(colors)):
        for j in range(lengths[i]):
            pixel_colors.append(colors[i])
    return pixel_colors


def apply_randomizer_slices(slices, intensity):
    percent = intensity * 25
    count = len(slices)
    last = count - 1
    new_slices = []
    for value in slices:
        new_slices.append(value)

    total_change = 0
    for i in range(last):
        max_change = int(round(slices[i] * (percent / 100.0)))
        if max_change > 0:
            change = random.randint(-max_change, max_change)
            if slices[i] + change < 0:
                change = -slices[i]
            new_slices[i] = slices[i] + change
            total_change = total_change + change

    new_slices[last] = slices[last] - total_change
    if new_slices[last] < 0:
        still_needed = -new_slices[last]
        new_slices[last] = 0
        i = 0
        while still_needed > 0 and i < last:
            take = min(still_needed, new_slices[i])
            new_slices[i] = new_slices[i] - take
            still_needed = still_needed - take
            i = i + 1
    return new_slices


def ticker_timing(pattern, num_colors, on_ms, off_ms, stagger_ms, step_ms):
    on_list = []
    off_list = []
    phase_list = []
    for c in range(num_colors):
        if pattern == "Sequence":
            on_list.append(step_ms)
            off_list.append(step_ms * (num_colors - 1))
            phase_list.append(c * step_ms)
        elif pattern == "Together":
            on_list.append(on_ms)
            off_list.append(off_ms)
            phase_list.append(0)
        elif pattern == "Alternate":
            on_list.append(on_ms)
            off_list.append(off_ms)
            phase_list.append((c % 2) * on_ms)
        else:
            on_list.append(on_ms)
            off_list.append(off_ms)
            phase_list.append(c * stagger_ms)
    return on_list, off_list, phase_list


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
    ease_on = params["ease_on"]
    ease_ms = params["ease_ms"]
    brightness = params["brightness"]

    color_array = strip_color_list(colors, ",\n  ")
    delay_array = make_c_list(delays, ", ", "UL")

    code = "#include <Adafruit_NeoPixel.h>\n"
    code += "#define LED_PIN " + str(pin) + "\n"
    code += "#define NUM_LEDS " + str(total) + "\n"
    code += "#define NUM_CHUNKS " + str(chunks) + "\n"
    code += "#define INPUT_PIN " + str(input_pin) + "\n"
    code += "Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);\n"
    code += "const int chunkStarts[NUM_CHUNKS] = {" + make_c_list(starts) + "};\n"
    code += "const int chunkLengths[NUM_CHUNKS] = {" + make_c_list(sizes) + "};\n"
    code += "const unsigned long chunkDelays[NUM_CHUNKS - 1] = {" + delay_array + "};\n"
    code += "uint32_t chunkColors[NUM_CHUNKS] = {\n"
    code += "  " + color_array + "\n"
    code += """};
unsigned long lastStep = 0;
int currentChunk = -1;
bool running = false;
"""
    code += "const bool EASE_ON = " + c_bool(ease_on) + ";\n"
    code += "const unsigned long EASE_MS = " + str(ease_ms) + "UL;\n"
    code += """
static inline uint8_t ur(uint32_t c) { return (uint8_t)(c >> 16); }
static inline uint8_t ug(uint32_t c) { return (uint8_t)(c >> 8); }
static inline uint8_t ub(uint32_t c) { return (uint8_t)(c); }

void easeRange(int st, int ln, uint32_t target) {
  if (!EASE_ON || EASE_MS == 0) {
    for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = st; i < st + ln; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
  strip.show();
}

void easeAll(uint32_t target) {
  if (!EASE_ON || EASE_MS == 0) {
    for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = 0; i < NUM_LEDS; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
  strip.show();
}

void resetSequence() {
  easeAll(0);
  currentChunk = -1;
  lastStep = millis();
  running = true;
}

void setup() {
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
"""
    if brightness < 255:
        code += "  strip.setBrightness(" + str(brightness) + ");\n"
    code += """  strip.show();
}

void loop() {
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
        code += "  if (!running) resetSequence();\n"
    code += """  if (!running) return;
  if (currentChunk == -1) {
"""
    code += "    if (now - lastStep >= " + str(pre) + "UL) {\n"
    code += """      currentChunk = 0;
      lastStep = now;
    }
  } else if (currentChunk < NUM_CHUNKS) {
    if (currentChunk == 0 || now - lastStep >= chunkDelays[currentChunk - 1]) {
      int st = chunkStarts[currentChunk];
      int ln = chunkLengths[currentChunk];
      easeRange(st, ln, chunkColors[currentChunk]);
      lastStep = now;
      currentChunk++;
    }
  } else {
"""
    if mode == "loop":
        code += "    if (now - lastStep >= " + str(post) + "UL) resetSequence();\n"
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
    ease_on = params["ease_on"]
    ease_ms = params["ease_ms"]
    brightness = params["brightness"]

    arr = hex_color_list(pixel_colors, ",\n  ")
    time_arr = make_c_list(slices, ", ", "UL")
    steps = len(slices)
    chase_steps = total - group + 1
    if chase_steps < 1:
        chase_steps = 1

    code = "#include <Adafruit_NeoPixel.h>\n"
    code += "#define LED_PIN " + str(pin) + "\n"
    code += "#define NUM_LEDS " + str(total) + "\n"
    code += "#define INPUT_PIN " + str(input_pin) + "\n"
    code += "#define STEPS " + str(steps) + "\n"
    code += """Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
const uint32_t pixelColors[NUM_LEDS] PROGMEM = {
"""
    code += "  " + arr + "\n"
    code += "};\n"
    code += "const unsigned long stepDelay[STEPS] = {" + time_arr + "};\n"
    code += """bool running = false;
unsigned long lastMs = 0;
int stepIdx = -1;
int head = 0;
"""
    code += "const bool EASE_ON = " + c_bool(ease_on) + ";\n"
    code += "const unsigned long EASE_MS = " + str(ease_ms) + "UL;\n"
    code += """
static inline uint8_t ur(uint32_t c) { return (uint8_t)(c >> 16); }
static inline uint8_t ug(uint32_t c) { return (uint8_t)(c >> 8); }
static inline uint8_t ub(uint32_t c) { return (uint8_t)(c); }

void easePixel(int i, uint32_t target) {
  if (!EASE_ON || EASE_MS == 0) {
    strip.setPixelColor(i, target);
    strip.show();
    return;
  }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
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
  }
  strip.setPixelColor(i, target);
  strip.show();
}

void allOff() {
  strip.clear();
  strip.show();
}

void allOffEase() {
  if (!EASE_ON || EASE_MS == 0) { allOff(); return; }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = 0; i < NUM_LEDS; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int remain = frames - f;
      int nr = cr + (0 - cr) / remain;
      int ng = cg + (0 - cg) / remain;
      int nb = cb + (0 - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  allOff();
}

void resetAnim() {
  allOffEase();
  running = true;
  lastMs = millis();
  stepIdx = -1;
  head = 0;
}

void setup() {
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
"""
    if brightness < 255:
        code += "  strip.setBrightness(" + str(brightness) + ");\n"
    code += """  strip.show();
  allOff();
}

void loop() {
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
        code += "  if (!running) resetAnim();\n"
    code += "  if (stepIdx == -1) {\n"
    code += "    if (now - lastMs >= " + str(pre) + "UL) {\n"
    code += """      stepIdx = 0;
      lastMs = now;
    }
    return;
  }
  if (stepIdx >= STEPS) {
"""
    if run_mode == "loop":
        code += "    if (now - lastMs >= " + str(post) + "UL) resetAnim();\n"
    if run_mode == "trigger_limit" and anim_mode == "Chase":
        code += "    if (pressed) resetAnim();\n"
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
        code += "  int onIdx = head + " + str(group) + " - 1;\n"
        code += """  int offIdx = head - 1;
  if (onIdx >= 0 && onIdx < NUM_LEDS) {
    if (EASE_ON && EASE_MS > 0) easePixel(onIdx, pgm_read_dword(&pixelColors[onIdx]));
    else { strip.setPixelColor(onIdx, pgm_read_dword(&pixelColors[onIdx])); strip.show(); }
  }
  if (offIdx >= 0 && offIdx < NUM_LEDS) {
    if (EASE_ON && EASE_MS > 0) easePixel(offIdx, 0);
    else { strip.setPixelColor(offIdx, 0); strip.show(); }
  }
  head++;
"""
        code += "  if (head > " + str(chase_steps) + ") head = " + str(chase_steps) + ";\n"
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
    ease_on = params["ease_on"]
    ease_ms = params["ease_ms"]
    brightness = params["brightness"]

    colors_arr = strip_color_list(colors, ", ")
    starts_arr = make_c_list(starts)
    lens_arr = make_c_list(lens)
    on_arr = make_c_list(on_by, ", ", "UL")
    off_arr = make_c_list(off_by, ", ", "UL")
    order_arr = make_c_list(custom_order)
    custom_len = len(custom_order)

    code = "#include <Adafruit_NeoPixel.h>\n"
    code += "#define LED_PIN " + str(pin) + "\n"
    code += "#define NUM_LEDS " + str(total) + "\n"
    code += "#define INPUT_PIN " + str(input_pin) + "\n"
    code += "#define NUM_SECTIONS " + str(sections) + "\n"
    code += "Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);\n"
    code += "const int sectionStarts[NUM_SECTIONS] = {" + starts_arr + "};\n"
    code += "const int sectionLengths[NUM_SECTIONS] = {" + lens_arr + "};\n"
    code += "const uint32_t sectionColors[NUM_SECTIONS] = {" + colors_arr + "};\n"
    code += "const int BLINK_MODE = " + str(blink_mode) + ";\n"
    code += "const unsigned long uniformOnMs = " + str(uniform_on) + "UL;\n"
    code += "const unsigned long uniformOffMs = " + str(uniform_off) + "UL;\n"
    code += "const unsigned long onMsBySection[NUM_SECTIONS] = {" + on_arr + "};\n"
    code += "const unsigned long offMsBySection[NUM_SECTIONS] = {" + off_arr + "};\n"
    code += "const int customOrderLen = " + str(custom_len) + ";\n"
    code += "const int customOrder[customOrderLen] = {" + order_arr + "};\n"
    code += """bool active = false;
unsigned long lastStep = 0;
int idx = 0;
bool onPhase = false;
"""
    code += "const bool EASE_ON = " + c_bool(ease_on) + ";\n"
    code += "const unsigned long EASE_MS = " + str(ease_ms) + "UL;\n"
    code += """
static inline uint8_t ur(uint32_t c) { return (uint8_t)(c >> 16); }
static inline uint8_t ug(uint32_t c) { return (uint8_t)(c >> 8); }
static inline uint8_t ub(uint32_t c) { return (uint8_t)(c); }

void easeRange(int st, int ln, uint32_t target) {
  if (!EASE_ON || EASE_MS == 0) {
    for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = st; i < st + ln; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  for (int i = st; i < st + ln; i++) strip.setPixelColor(i, target);
  strip.show();
}

void allOff() {
  strip.clear();
  strip.show();
}

void allOffEase() {
  if (!EASE_ON || EASE_MS == 0) { allOff(); return; }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = 0; i < NUM_LEDS; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int remain = frames - f;
      int nr = cr + (0 - cr) / remain;
      int ng = cg + (0 - cg) / remain;
      int nb = cb + (0 - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  allOff();
}

void renderTogether(bool on) {
  if (!on) { allOffEase(); return; }
  int frames = 1;
  unsigned long per = 0;
  if (EASE_ON && EASE_MS > 0) {
    frames = (int)(EASE_MS / 15UL);
    if (frames < 4) frames = 4;
    if (frames > 40) frames = 40;
    per = EASE_MS / (unsigned long)frames;
    if (per == 0) per = 1;
  }
  for (int f = 0; f < frames; f++) {
    int remain = frames - f;
    for (int s = 0; s < NUM_SECTIONS; s++) {
      uint32_t target = sectionColors[s];
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      for (int i = sectionStarts[s]; i < sectionStarts[s] + sectionLengths[s]; i++) {
        uint32_t cur = strip.getPixelColor(i);
        int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
        strip.setPixelColor(i, strip.Color((uint8_t)(cr + (tr - cr) / remain), (uint8_t)(cg + (tg - cg) / remain), (uint8_t)(cb + (tb - cb) / remain)));
      }
    }
    strip.show();
    if (per) delay(per);
  }
}

void renderSingle(int s, bool on) {
  if (!on) {
    int st = sectionStarts[s];
    int ln = sectionLengths[s];
    easeRange(st, ln, 0);
    return;
  }
  int st = sectionStarts[s];
  int ln = sectionLengths[s];
  easeRange(st, ln, sectionColors[s]);
}

int curSection = 0;

int pickSection() {
  if (BLINK_MODE == 2) return (int)random(NUM_SECTIONS);
  if (BLINK_MODE == 3) {
    int s = customOrder[idx % customOrderLen];
    if (s < 0) s = 0;
    if (s >= NUM_SECTIONS) s = NUM_SECTIONS - 1;
    return s;
  }
  return idx % NUM_SECTIONS;
}

void resetBlink() {
  idx = 0;
  onPhase = false;
  lastStep = millis();
  curSection = pickSection();
}

void setup() {
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
"""
    if brightness < 255:
        code += "  strip.setBrightness(" + str(brightness) + ");\n"
    code += """  strip.show();
  randomSeed(analogRead(0));
  allOff();
}

void loop() {
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
        code += "  if (!active) { active = true; resetBlink(); }\n"
    code += """  if (BLINK_MODE == 0) {
    unsigned long onMs = uniformOnMs;
    unsigned long offMs = uniformOffMs;
    if (!onPhase) {
      if (now - lastStep >= offMs) {
        onPhase = true;
        lastStep = now;
        renderTogether(true);
      }
    } else {
      if (now - lastStep >= onMs) {
        onPhase = false;
        lastStep = now;
        renderTogether(false);
      }
    }
    return;
  }
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
    consistent = params["rand_consistent_placement"]
    ease_on = params["ease_on"]
    ease_ms = params["ease_ms"]
    brightness = params["brightness"]

    solid_expr = strip_color(solid)
    subset_expr = strip_color_list(subset, ", ")

    code = "#include <Adafruit_NeoPixel.h>\n"
    code += "#define LED_PIN " + str(pin) + "\n"
    code += "#define NUM_LEDS " + str(total) + "\n"
    code += "#define INPUT_PIN " + str(input_pin) + "\n"
    code += "Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);\n"
    code += "const int CHUNK_SIZE = " + str(chunk_size) + ";\n"
    code += "const unsigned long BASE_ON_MS = " + str(base_on) + "UL;\n"
    code += "const unsigned long BASE_OFF_MS = " + str(base_off) + "UL;\n"
    code += "const bool FREQ_RAND = " + c_bool(freq_rand) + ";\n"
    code += "const unsigned long FREQ_RAND_MS = " + str(freq_rand_ms) + "UL;\n"
    code += "const bool RANDOM_PLACEMENT = " + c_bool(random_place) + ";\n"
    code += "const bool SIMUL = " + c_bool(simul) + ";\n"
    code += "const int MAX_SIMUL = " + str(max_simul) + ";\n"
    code += "const bool TIMING_JITTER = " + c_bool(timing_jitter) + ";\n"
    code += "const unsigned long JITTER_MS = " + str(jitter_ms) + "UL;\n"
    code += "const int COLOR_MODE = " + str(color_mode) + ";\n"
    code += "const uint32_t SOLID_COLOR = " + solid_expr + ";\n"
    code += "const int SUBSET_N = " + str(len(subset)) + ";\n"
    code += "const uint32_t SUBSET_COLORS[SUBSET_N] = {" + subset_expr + "};\n"
    code += "const bool CONSISTENT_PLACEMENT = " + c_bool(consistent) + ";\n"
    code += "const bool EASE_ON = " + c_bool(ease_on) + ";\n"
    code += "const unsigned long EASE_MS = " + str(ease_ms) + "UL;\n"
    code += """
static inline uint8_t ur(uint32_t c) { return (uint8_t)(c >> 16); }
static inline uint8_t ug(uint32_t c) { return (uint8_t)(c >> 8); }
static inline uint8_t ub(uint32_t c) { return (uint8_t)(c); }

void easeAllTo(uint32_t target) {
  if (!EASE_ON || EASE_MS == 0) {
    for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = 0; i < NUM_LEDS; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
  strip.show();
}

struct Slot {
  bool on;
  unsigned long nextMs;
  int start;
  int len;
  uint32_t color;
};
Slot slots[MAX_SIMUL];

bool active = false;

unsigned long randJitter(unsigned long v) {
  if (!TIMING_JITTER || JITTER_MS == 0) return v;
  long j = (long)random((long)JITTER_MS + 1L);
  if (random(2) == 0) j = -j;
  long out = (long)v + j;
  if (out < 0) out = 0;
  return (unsigned long)out;
}

unsigned long randFreq(unsigned long v) {
  if (!FREQ_RAND || FREQ_RAND_MS == 0) return v;
  long j = (long)random((long)FREQ_RAND_MS + 1L);
  if (random(2) == 0) j = -j;
  long out = (long)v + j;
  if (out < 0) out = 0;
  return (unsigned long)out;
}

uint32_t pickColor(int ledIndex) {
  if (COLOR_MODE == 0) return SOLID_COLOR;
  if (COLOR_MODE == 1) {
    if (CONSISTENT_PLACEMENT) {
      long band = (long)ledIndex * (long)SUBSET_N / (long)NUM_LEDS;
      if (band >= SUBSET_N) band = SUBSET_N - 1;
      return SUBSET_COLORS[band];
    }
    return SUBSET_COLORS[random(SUBSET_N)];
  }
  return SOLID_COLOR;
}

uint32_t randomConstrainedColor() {
  int total = (int)random(80, 181);
  int r = (int)random(0, total + 1);
  int g = (int)random(0, (total - r) + 1);
  int b = total - r - g;

  int a = (int)random(0, 6);
  int R=r, G=g, B=b;
  if (a == 0) { R=r; G=g; B=b; }
  else if (a == 1) { R=r; G=b; B=g; }
  else if (a == 2) { R=g; G=r; B=b; }
  else if (a == 3) { R=g; G=b; B=r; }
  else if (a == 4) { R=b; G=r; B=g; }
  else { R=b; G=g; B=r; }

  return strip.Color((uint8_t)R, (uint8_t)G, (uint8_t)B);
}

void computeChunk(int &st, int &ln) {
  ln = CHUNK_SIZE;
  if (ln > NUM_LEDS) ln = NUM_LEDS;
  if (!RANDOM_PLACEMENT) {
    int chunkCount = (NUM_LEDS + ln - 1) / ln;
    int k = random(chunkCount);
    st = k * ln;
    if (st + ln > NUM_LEDS) ln = NUM_LEDS - st;
    return;
  }
  int start = random(NUM_LEDS);
  st = start;
  if (st + ln > NUM_LEDS) st = NUM_LEDS - ln;
  if (st < 0) st = 0;
}

bool overlaps(int st, int ln, int otherSt, int otherLn) {
  int a0 = st;
  int a1 = st + ln - 1;
  int b0 = otherSt;
  int b1 = otherSt + otherLn - 1;
  if (a1 < b0) return false;
  if (b1 < a0) return false;
  return true;
}

void assignSlot(int k) {
  int st = 0;
  int ln = 0;
  bool placed = false;
  int limit = SIMUL ? MAX_SIMUL : 1;
  for (int attempt = 0; attempt < 16; attempt++) {
    computeChunk(st, ln);
    if (!SIMUL) { placed = true; break; }
    bool ok = true;
    for (int i = 0; i < limit; i++) {
      if (i == k) continue;
      if (slots[i].on) {
        if (overlaps(st, ln, slots[i].start, slots[i].len)) { ok = false; break; }
      }
    }
    if (ok) { placed = true; break; }
  }
  if (!placed) computeChunk(st, ln);
  slots[k].start = st;
  slots[k].len = ln;
}

void renderSlots() {
  strip.clear();
  int limit = SIMUL ? MAX_SIMUL : 1;
  for (int s = 0; s < limit; s++) {
    if (!slots[s].on) continue;
    int st = slots[s].start;
    int ln = slots[s].len;

    if (COLOR_MODE == 2 || (COLOR_MODE == 1 && !CONSISTENT_PLACEMENT)) {
      for (int i = st; i < st + ln; i++) strip.setPixelColor(i, slots[s].color);
    } else {
      for (int i = st; i < st + ln; i++) strip.setPixelColor(i, pickColor(i));
    }
  }
  strip.show();
}

void resetAll() {
  int limit = SIMUL ? MAX_SIMUL : 1;
  for (int i = 0; i < limit; i++) {
    slots[i].on = false;
    slots[i].nextMs = millis();
    slots[i].start = 0;
    slots[i].len = 0;
    slots[i].color = SOLID_COLOR;
    assignSlot(i);
  }
}

void setup() {
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
"""
    if brightness < 255:
        code += "  strip.setBrightness(" + str(brightness) + ");\n"
    code += """  strip.show();
  randomSeed(analogRead(0));
  easeAllTo(0);
  resetAll();
}

void loop() {
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
        code += "  if (!active) { active = true; resetAll(); }\n"
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
    ease_on = params["ease_on"]
    ease_ms = params["ease_ms"]
    brightness = params["brightness"]

    color_exprs = strip_color_list(colors, ", ")
    dur_exprs = make_c_list(durs, ", ", "UL")

    code = "#include <Adafruit_NeoPixel.h>\n"
    code += "#define LED_PIN " + str(pin) + "\n"
    code += "#define NUM_LEDS " + str(total) + "\n"
    code += "#define INPUT_PIN " + str(input_pin) + "\n"
    code += "#define STEPS " + str(steps) + "\n"
    code += "Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);\n"
    code += "const uint32_t stepColors[STEPS] = {" + color_exprs + "};\n"
    code += "const unsigned long stepDur[STEPS] = {" + dur_exprs + "};\n"
    code += "const bool CS_LOOP = " + c_bool(cs_loop) + ";\n"
    code += "const bool EASE_ON = " + c_bool(ease_on) + ";\n"
    code += "const unsigned long EASE_MS = " + str(ease_ms) + "UL;\n"
    code += """
static inline uint8_t ur(uint32_t c) { return (uint8_t)(c >> 16); }
static inline uint8_t ug(uint32_t c) { return (uint8_t)(c >> 8); }
static inline uint8_t ub(uint32_t c) { return (uint8_t)(c); }

void easeAllTo(uint32_t target) {
  if (!EASE_ON || EASE_MS == 0) {
    for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
    strip.show();
    return;
  }
  int frames = (int)(EASE_MS / 15UL);
  if (frames < 4) frames = 4;
  if (frames > 40) frames = 40;
  unsigned long per = EASE_MS / (unsigned long)frames;
  if (per == 0) per = 1;
  for (int f = 0; f < frames; f++) {
    for (int i = 0; i < NUM_LEDS; i++) {
      uint32_t cur = strip.getPixelColor(i);
      int cr = (int)ur(cur), cg = (int)ug(cur), cb = (int)ub(cur);
      int tr = (int)ur(target), tg = (int)ug(target), tb = (int)ub(target);
      int remain = frames - f;
      int nr = cr + (tr - cr) / remain;
      int ng = cg + (tg - cg) / remain;
      int nb = cb + (tb - cb) / remain;
      strip.setPixelColor(i, strip.Color((uint8_t)nr, (uint8_t)ng, (uint8_t)nb));
    }
    strip.show();
    delay(per);
  }
  for (int i = 0; i < NUM_LEDS; i++) strip.setPixelColor(i, target);
  strip.show();
}

void allOff() {
  strip.clear();
  strip.show();
}

void allOffEase() {
  easeAllTo(0);
}

bool running = false;
unsigned long lastMs = 0;
int idx = -1;

void resetSeq() {
  allOffEase();
  running = true;
  lastMs = millis();
  idx = -1;
}

void setup() {
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
"""
    if brightness < 255:
        code += "  strip.setBrightness(" + str(brightness) + ");\n"
    code += """  strip.show();
  allOff();
}

void loop() {
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
        code += "  if (!running) resetSeq();\n"
    code += "  if (idx == -1) {\n"
    code += "    if (now - lastMs >= " + str(pre) + "UL) {\n"
    code += """      idx = 0;
      lastMs = now;
      easeAllTo(stepColors[0]);
    }
    return;
  }
  if (idx >= STEPS) {
"""
    if run_mode == "loop":
        code += "    if (now - lastMs >= " + str(post) + "UL) resetSeq();\n"
    code += """    return;
  }
  if (now - lastMs < stepDur[idx]) return;
  lastMs = now;
  idx++;
  if (idx >= STEPS) {
"""
    if run_mode == "loop":
        code += "    return;\n"
    else:
        code += """    if (!CS_LOOP) return;
    idx = 0;
"""
    code += """  }
  easeAllTo(stepColors[idx]);
}"""
    return code.strip()


def gen_ticker_code(params):
    total = params["total_leds"]
    pin = params["data_pin"]
    input_pin = params["input_pin"]
    run_mode = params["run_mode"]
    chunk = params["ticker_chunk_size"]
    colors = params["ticker_colors"]
    n = len(colors)
    scroll = params["ticker_scroll"]
    reverse = params["ticker_reverse"]
    step_ms = params["ticker_step_ms"]
    step_leds = params["ticker_step_leds"]
    brightness = params["brightness"]
    if params["ease_on"]:
        ease_ms = params["ease_ms"]
    else:
        ease_ms = 0

    on_list = make_c_list(limit_to_600000(params["ticker_on_ms"]), ", ", "UL")
    off_list = make_c_list(limit_to_600000(params["ticker_off_ms"]), ", ", "UL")
    phase_list = make_c_list(limit_to_600000(params["ticker_phase_ms"]), ", ", "UL")
    color_arr = hex_color_list(colors, ", ")

    code = "#include <Adafruit_NeoPixel.h>\n"
    code += "#define LED_PIN " + str(pin) + "\n"
    code += "#define NUM_LEDS " + str(total) + "\n"
    code += "#define INPUT_PIN " + str(input_pin) + "\n"
    code += "#define CHUNK_SIZE " + str(chunk) + "\n"
    code += "#define NUM_COLORS " + str(n) + "\n"
    code += """#define PATTERN_LEN ((long)CHUNK_SIZE * NUM_COLORS)
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
"""
    code += "const uint32_t COLORS[NUM_COLORS] = {" + color_arr + "};\n"
    code += "const unsigned long ON_MS[NUM_COLORS] = {" + on_list + "};\n"
    code += "const unsigned long OFF_MS[NUM_COLORS] = {" + off_list + "};\n"
    code += "const unsigned long PHASE_MS[NUM_COLORS] = {" + phase_list + "};\n"
    code += "const bool SCROLL = " + c_bool(scroll) + ";\n"
    code += "const bool SCROLL_REVERSE = " + c_bool(reverse) + ";\n"
    code += "const unsigned long STEP_MS = " + str(step_ms) + "UL;\n"
    code += "const long STEP_LEDS = " + str(step_leds) + "L;\n"
    code += "const unsigned long EASE_MS = " + str(ease_ms) + "UL;\n"
    code += """const unsigned long EASE_DIV = EASE_MS ? EASE_MS : 1UL;

uint8_t level[NUM_COLORS];
long lastOffset = -1;
bool active = false;
bool stopping = false;
unsigned long startMs = 0;
unsigned long stopMs = 0;

uint8_t colorLevel(int c, unsigned long elapsed) {
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
}

uint32_t scaled(uint32_t c, uint8_t l) {
  if (l == 255) return c;
  if (l == 0) return 0;
  uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * l / 255);
  uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * l / 255);
  uint8_t b = (uint8_t)((c & 0xFF) * l / 255);
  return strip.Color(r, g, b);
}

void render(unsigned long elapsed, uint8_t master) {
  bool changed = false;
  for (int c = 0; c < NUM_COLORS; c++) {
    uint8_t l = (uint8_t)(((uint16_t)colorLevel(c, elapsed) * master) / 255);
    if (l != level[c]) { level[c] = l; changed = true; }
  }
  long offset = 0;
  if (SCROLL) offset = (long)(((elapsed / STEP_MS) % PATTERN_LEN) * STEP_LEDS % PATTERN_LEN);
  if (offset != lastOffset) { lastOffset = offset; changed = true; }
  if (!changed) return;
  for (int i = 0; i < NUM_LEDS; i++) {
    long p = SCROLL_REVERSE ? (long)i + offset : (long)i - offset;
    p %= PATTERN_LEN;
    if (p < 0) p += PATTERN_LEN;
    int c = (int)(p / CHUNK_SIZE);
    strip.setPixelColor(i, scaled(COLORS[c], level[c]));
  }
  strip.show();
}

void startTicker(unsigned long now) {
  active = true;
  stopping = false;
  startMs = now;
  lastOffset = -1;
}

void stopTicker(unsigned long now) {
  if (!active || stopping) return;
  stopping = true;
  stopMs = now;
}

void setup() {
  pinMode(INPUT_PIN, INPUT_PULLUP);
  strip.begin();
"""
    if brightness < 255:
        code += "  strip.setBrightness(" + str(brightness) + ");\n"
    code += """  strip.clear();
  strip.show();
}

void loop() {
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
        code += "  if (!active) startTicker(now);\n"
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
