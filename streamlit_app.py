import io
import random
import zipfile

import streamlit as st

import led_core


APP_TITLE = "Lux Taylor Art / B.A.N.A.N.A (Batch Arduino Nano Adafruit Neopixel Animator)"

WHITE = "#FFFFFF"
RED = "#FF0000"
BLUE = "#0000FF"

TICKER_DEFAULT_COLORS = ["#FF5000", "#FF0000", "#00FF00", "#0000FF", "#FFFFFF",
                         "#FF00FF", "#00FFFF", "#FFFF00", "#8000FF", "#FF0080"]

TICKER_DEFAULTS = {
    "Wave": {"on": 450, "off": 450, "stagger": 150, "step": 450},
    "Sequence": {"on": 300, "off": 300, "stagger": 0, "step": 300},
    "Together": {"on": 500, "off": 500, "stagger": 0, "step": 500},
    "Alternate": {"on": 500, "off": 500, "stagger": 0, "step": 500},
}


def hex_to_rgb(text):
    red = int(text[1:3], 16)
    green = int(text[3:5], 16)
    blue = int(text[5:7], 16)
    return (red, green, blue)


def numbered_labels(word, count):
    labels = []
    for i in range(count):
        labels.append(word + " " + str(i + 1))
    return labels


def color_grid(prefix, labels, defaults, cols=4):
    colors = []
    columns = st.columns(cols)
    for i in range(len(labels)):
        if i < len(defaults):
            default = defaults[i]
        else:
            default = defaults[len(defaults) - 1]
        with columns[i % cols]:
            picked = st.color_picker(labels[i], default, key=prefix + "_" + str(i))
        colors.append(hex_to_rgb(picked))
    return colors


def ms_grid(prefix, labels, default=500, cols=4):
    values = []
    columns = st.columns(cols)
    for i in range(len(labels)):
        with columns[i % cols]:
            value = st.number_input(labels[i], min_value=0, max_value=1000000,
                                    value=default, step=1, key=prefix + "_" + str(i))
        values.append(value)
    return values


st.set_page_config(page_title="Lux Taylor B.A.N.A.N.A", layout="wide")
st.title(APP_TITLE)
st.caption("Arduino Nano, WS2812B LEDs")
st.warning("NOTE: Must install the **Adafruit NeoPixel** library via the Library Manager in Arduino IDE")

st.sidebar.header("Settings")
total_leds = st.sidebar.number_input("Total number LEDs", min_value=1, max_value=2000, value=50, step=1)
data_pin = st.sidebar.number_input("Data Pin", min_value=0, max_value=50, value=6, step=1)
anim = st.sidebar.selectbox("Animation Type", ["Chunk", "Smooth", "Blink", "Random", "Color Sequence", "Ticker"])

st.sidebar.subheader("Run Mode")
if anim == "Blink" or anim == "Ticker":
    run_modes = ["Loop", "Trigger"]
else:
    run_modes = ["Loop", "Hold", "Trigger"]
rm = st.sidebar.selectbox("Run Mode", run_modes)

trigger_help = None
if anim == "Ticker":
    trigger_help = "Ticker: a limit switch runs it while held; each pushbutton press toggles it on or off."
trig = st.sidebar.selectbox("Trigger Type", ["limit switch", "pushbutton"], disabled=(rm != "Trigger"),
                            help=trigger_help)
input_pin = st.sidebar.number_input("Input Pin", min_value=0, max_value=50, value=2, step=1,
                                    disabled=(rm != "Trigger"))

uses_timing = anim in ["Chunk", "Smooth", "Color Sequence"]
pre = st.sidebar.number_input("Pre-light delay (ms)", min_value=0, max_value=600000, value=2000, step=1,
                              disabled=not uses_timing)
post = st.sidebar.number_input("Post-light hold (ms)", min_value=0, max_value=600000, value=2000, step=1,
                               disabled=not (uses_timing and rm == "Loop"))

if rm == "Loop":
    run_mode = "loop"
elif rm == "Hold":
    run_mode = "hold"
elif trig == "limit switch":
    run_mode = "trigger_limit"
else:
    run_mode = "trigger_push"

st.sidebar.subheader("Extra Settings")
ease_on = st.sidebar.checkbox("Animation Easing", value=False)
ease_ms = st.sidebar.number_input("Ease Duration (ms)", min_value=0, max_value=600000, value=250, step=1,
                                  disabled=not ease_on)
brightness = st.sidebar.slider("Brightness", min_value=1, max_value=255, value=255,
                               help="Scales every color. Lower brightness also lowers power draw.")

base_params = {
    "total_leds": total_leds,
    "data_pin": data_pin,
    "input_pin": input_pin,
    "run_mode": run_mode,
    "pre_delay": pre,
    "post_hold": post,
    "ease_on": ease_on,
    "ease_ms": ease_ms,
    "brightness": brightness,
}

est_ram = 3 * total_leds + 500
if est_ram > 1700:
    st.sidebar.warning(f"⚠ est RAM {est_ram} of 2048 bytes: too many LEDs for an Arduino Nano")
else:
    st.sidebar.info(f"est RAM: {est_ram} of 2048 bytes")

st.subheader(f"{anim} Settings")


def chunk_settings():
    n = st.number_input("Number of chunks", min_value=1, max_value=total_leds, value=min(5, total_leds), step=1)
    sizes = led_core.split_evenly(total_leds, n)
    starts = led_core.starts_of(sizes)

    if st.checkbox("Uniform RGB", value=True, key="chunk_rgb_uniform"):
        color = color_grid("chunk_rgb", ["RGB"], [WHITE])[0]
        rgb_values = [color] * n
    else:
        rgb_values = color_grid("chunk_rgb", numbered_labels("RGB", n), [WHITE])

    random_timing = False
    random_ms = 0
    if st.checkbox("Uniform timing", value=True, key="chunk_timing_uniform"):
        c1, c2, c3 = st.columns([2, 1, 1])
        delay = c1.number_input("milliseconds between chunks", min_value=0, max_value=1000000, value=500, step=1)
        random_timing = c2.checkbox("timing randomizer", value=False)
        random_ms = c3.number_input("± ms", min_value=0, max_value=1000000, value=300, step=1,
                                    disabled=not random_timing, key="chunk_rand_ms")
        delays = [delay] * (n - 1)
    else:
        delay_labels = []
        for i in range(n - 1):
            delay_labels.append(f"Delay {i + 1} (ms)")
        delays = ms_grid("chunk_delay", delay_labels)

    params = base_params.copy()
    params["num_chunks"] = n
    params["chunk_sizes"] = sizes
    params["chunk_starts"] = starts
    params["rgb_values"] = rgb_values
    params["delays"] = delays
    params["random_timing"] = random_timing
    params["random_ms"] = random_ms
    return params


def smooth_settings():
    c1, c2 = st.columns(2)
    mode = c1.selectbox("Type", ["Solid Color", "Gradient", "Sections", "Rainbow"])
    if mode == "Solid Color":
        color = color_grid("smooth_solid", ["RGB"], [WHITE])[0]
        pixel_colors = [color] * total_leds
    elif mode == "Gradient":
        k = c2.number_input("number of stops", min_value=2, max_value=8, value=2, step=1)
        stops = color_grid("smooth_stop", numbered_labels("Stop", k), [RED, BLUE, WHITE])
        pixel_colors = led_core.build_gradient(stops, total_leds)
    elif mode == "Sections":
        k = c2.number_input("number of sections", min_value=2, max_value=8, value=2, step=1)
        section_colors = color_grid("smooth_section", numbered_labels("Section", k), [WHITE])
        pixel_colors = led_core.build_sections(section_colors, total_leds)
    else:
        pixel_colors = []
        for i in range(total_leds):
            pixel_colors.append(led_core.hsv_to_rgb(i / total_leds))

    c1, c2 = st.columns(2)
    anim_mode = c1.selectbox("Animation Type", ["Fill", "Chase"])
    speed_ms = c2.number_input("Animation Speed, Millis", min_value=1, max_value=600000, value=100, step=1)

    chase_group = 5
    randomizer_on = False
    intensity = 1
    if anim_mode == "Chase":
        chase_group = st.number_input("Chase group size", min_value=1, max_value=total_leds,
                                      value=min(5, total_leds), step=1)
    else:
        c1, c2 = st.columns(2)
        randomizer_on = c1.checkbox("randomizer", value=False, key="smooth_rand")
        intensity = c2.selectbox("Intensity", list(range(1, 11)), disabled=not randomizer_on)

    if anim_mode == "Fill":
        steps = total_leds
    else:
        steps = total_leds - chase_group + 1

    params = base_params.copy()
    params["smooth_anim_mode"] = anim_mode
    params["smooth_chase_group"] = chase_group
    params["smooth_slices"] = [speed_ms] * steps
    params["pixel_colors"] = pixel_colors
    params["randomizer_on"] = randomizer_on
    params["intensity"] = intensity
    return params


def on_off_inputs():
    c1, c2 = st.columns(2)
    on_ms = c1.number_input("On (ms)", min_value=0, max_value=1000000, value=500, step=1, key="blink_on")
    off_ms = c2.number_input("Off (ms)", min_value=0, max_value=1000000, value=500, step=1, key="blink_off")
    return on_ms, off_ms


def per_section_inputs(sections):
    on_list = []
    off_list = []
    for s in range(sections):
        c1, c2 = st.columns(2)
        on_list.append(c1.number_input(f"S{s + 1} On", min_value=0, max_value=1000000, value=500, step=1,
                                       key=f"blink_on_{s}"))
        off_list.append(c2.number_input(f"S{s + 1} Off", min_value=0, max_value=1000000, value=500, step=1,
                                        key=f"blink_off_{s}"))
    return on_list, off_list


def blink_settings():
    sec = st.number_input("Number of sections", min_value=1, max_value=total_leds, value=1, step=1)
    lens = led_core.split_evenly(total_leds, sec)
    starts = led_core.starts_of(lens)

    if st.checkbox("uniform color", value=True, key="blink_uniform_color"):
        color = color_grid("blink_rgb", ["RGB"], [WHITE])[0]
        blink_colors = [color] * sec
    else:
        blink_colors = color_grid("blink_rgb", numbered_labels("RGB", sec), [WHITE])

    order_mode = "Together"
    if sec > 1:
        order_mode = st.selectbox("Order", ["Together", "Sequential", "Random", "Custom"])

    uniform_on = 500
    uniform_off = 500
    separate = False
    custom_order = [0]
    on_by = None
    off_by = None

    if order_mode == "Together" or order_mode == "Random":
        uniform_on, uniform_off = on_off_inputs()
    elif order_mode == "Sequential":
        separate = st.checkbox("separate timing", value=False)
        if separate:
            on_by, off_by = per_section_inputs(sec)
        else:
            uniform_on, uniform_off = on_off_inputs()
    else:
        typed = st.text_input("Custom order (comma-separated section numbers, starting at 1)", "1,1")
        custom_order = []
        for piece in typed.split(","):
            piece = piece.strip()
            if piece != "":
                custom_order.append(led_core.to_int(piece, 1, 1, sec) - 1)
        if len(custom_order) == 0:
            custom_order = [0]
        on_by, off_by = per_section_inputs(sec)

    if on_by is None:
        on_by = [uniform_on] * sec
        off_by = [uniform_off] * sec

    if order_mode == "Together":
        blink_mode = 0
    elif order_mode == "Sequential":
        blink_mode = 1
    elif order_mode == "Random":
        blink_mode = 2
    else:
        blink_mode = 3

    params = base_params.copy()
    params["blink_sections"] = sec
    params["blink_starts"] = starts
    params["blink_lens"] = lens
    params["blink_colors"] = blink_colors
    params["blink_mode"] = blink_mode
    params["blink_uniform_on"] = uniform_on
    params["blink_uniform_off"] = uniform_off
    params["blink_separate_timing"] = separate
    params["blink_on_by"] = on_by
    params["blink_off_by"] = off_by
    params["blink_custom_order"] = custom_order
    return params


def random_settings():
    c1, c2 = st.columns(2)
    chunk_size = c1.number_input("Size Of Random Chunk", min_value=1, max_value=total_leds,
                                 value=min(10, total_leds), step=1)
    random_place = c2.checkbox("random chunk placement", value=False)

    c1, c2 = st.columns(2)
    base_on = c1.number_input("Blink Frequency On (ms)", min_value=0, max_value=1000000, value=250, step=1)
    base_off = c2.number_input("Blink Frequency Off (ms)", min_value=0, max_value=1000000, value=0, step=1)

    c1, c2 = st.columns(2)
    freq_rand = c1.checkbox("Frequency Randomizer", value=False)
    freq_rand_ms = c2.number_input("Frequency randomizer ± ms", min_value=0, max_value=1000000, value=0, step=1,
                                   disabled=not freq_rand)

    c1, c2 = st.columns(2)
    simul = c1.checkbox("simultaneous", value=False)
    max_simul = c2.number_input("maximum simultaneous illumination", min_value=1, max_value=200, value=2, step=1,
                                disabled=not simul)

    c1, c2 = st.columns(2)
    timing_jitter = c1.checkbox("randomize timing", value=False, disabled=not simul,
                                help="Only applies when 'simultaneous' is on.")
    jitter_ms = c2.number_input("randomize timing ± ms", min_value=0, max_value=1000000, value=250, step=1,
                                disabled=not (simul and timing_jitter))

    color_choice = st.selectbox("Color", ["Solid", "Subset", "Random"])
    if color_choice == "Solid":
        color_mode = 0
        solid = color_grid("rand_solid", ["RGB"], [WHITE])[0]
        subset = [solid, solid]
        consistent = True
    elif color_choice == "Subset":
        color_mode = 1
        solid = (255, 255, 255)
        c1, c2 = st.columns(2)
        k = c1.selectbox("Number of Colors", list(range(2, 11)))
        consistent = c2.checkbox("consistent color placement", value=True)
        subset = color_grid("rand_subset", numbered_labels("RGB", k), [WHITE])
    else:
        color_mode = 2
        solid = (255, 255, 255)
        subset = [(255, 255, 255), (255, 255, 255)]
        consistent = False

    if not simul:
        max_simul = 1
        timing_jitter = False

    params = base_params.copy()
    params["rand_chunk_size"] = chunk_size
    params["rand_random_placement"] = random_place
    params["rand_on_ms"] = base_on
    params["rand_off_ms"] = base_off
    params["rand_freq_rand"] = freq_rand
    params["rand_freq_rand_ms"] = freq_rand_ms
    params["rand_simul"] = simul
    params["rand_max_simul"] = max_simul
    params["rand_timing_jitter"] = timing_jitter
    params["rand_jitter_ms"] = jitter_ms
    params["rand_color_mode"] = color_mode
    params["rand_solid_rgb"] = solid
    params["rand_subset_rgbs"] = subset
    params["rand_consistent_placement"] = consistent
    return params


def colorseq_settings():
    n = st.number_input("Number of Steps", min_value=1, max_value=50, value=3, step=1)
    colors = []
    durs = []
    for i in range(n):
        c1, c2 = st.columns(2)
        with c1:
            picked = st.color_picker(f"Step {i + 1} Color", RED, key=f"cs_color_{i}")
        colors.append(hex_to_rgb(picked))
        durs.append(c2.number_input(f"Step {i + 1} Duration (ms)", min_value=0, max_value=600000,
                                    value=500, step=1, key=f"cs_dur_{i}"))
    cs_loop = st.checkbox("loop", value=False, key="cs_loop", disabled=(rm == "Loop"),
                          help="Restarts the sequence immediately in Hold and Trigger modes. Loop run mode always repeats.")

    params = base_params.copy()
    params["cs_steps"] = n
    params["cs_colors"] = colors
    params["cs_durs"] = durs
    params["cs_loop"] = cs_loop
    return params


def ticker_pattern_timing(pattern, n):
    defaults = TICKER_DEFAULTS[pattern]
    name = pattern.lower()
    on = st.session_state.get(f"tk_{name}_on", defaults["on"])
    off = st.session_state.get(f"tk_{name}_off", defaults["off"])
    stagger = st.session_state.get(f"tk_{name}_stagger", defaults["stagger"])
    step = st.session_state.get(f"tk_{name}_step", defaults["step"])
    return led_core.ticker_timing(pattern, n, on, off, stagger, step)


def fill_per_color_from_pattern():
    if not st.session_state.get("tk_per_color"):
        return
    n = st.session_state.get("tk_num_colors", 3)
    pattern = st.session_state.get("tk_pattern", "Wave")
    on, off, phase = ticker_pattern_timing(pattern, n)
    for c in range(n):
        st.session_state[f"tk_pc_on_{c}"] = on[c]
        st.session_state[f"tk_pc_off_{c}"] = off[c]
        st.session_state[f"tk_pc_phase_{c}"] = phase[c]


def keep_hidden_ticker_settings():
    names = list(st.session_state.keys())
    for name in names:
        keep = False
        if name == "tk_pattern":
            keep = True
        if name.startswith("tk_pc_"):
            keep = True
        for pattern in led_core.TICKER_PATTERNS:
            if name.startswith("tk_" + pattern.lower() + "_"):
                keep = True
        if keep:
            st.session_state[name] = st.session_state[name]


def ms_input(container, label, key, default, min_value=0):
    if key not in st.session_state:
        st.session_state[key] = default
    return container.number_input(label, min_value=min_value, max_value=600000, step=1, key=key)


def ticker_settings():
    keep_hidden_ticker_settings()

    c1, c2 = st.columns(2)
    chunk = c1.number_input("Chunk size (LEDs)", min_value=1, max_value=total_leds, value=min(3, total_leds), step=1,
                            help="The strip is cut into chunks of this size; the last chunk is shorter if it doesn't divide evenly.")
    n = c2.selectbox("Number of colors", list(range(1, 11)), index=2, key="tk_num_colors")

    full_chunks = total_leds // chunk
    leftover = total_leds % chunk
    chunk_text = f"{full_chunks} chunk(s) of {chunk}"
    if leftover > 0:
        chunk_text = chunk_text + f" + 1 chunk of {leftover}"
    chunk_text = chunk_text + f" across {total_leds} LEDs"
    st.caption(chunk_text)

    colors = color_grid("tk_color", numbered_labels("Color", n), TICKER_DEFAULT_COLORS[:n], cols=5)

    st.markdown("##### Timing")
    per_color = st.checkbox("Per-color timing", value=False, key="tk_per_color", on_change=fill_per_color_from_pattern,
                            help="Set on, off and start delay separately for each color. Starts from the current pattern's values.")
    if not per_color:
        pattern = st.selectbox("Pattern", led_core.TICKER_PATTERNS, key="tk_pattern")
        name = pattern.lower()
        defaults = TICKER_DEFAULTS[pattern]
        if pattern == "Sequence":
            ms_input(st, "Step (ms each color is lit)", f"tk_{name}_step", defaults["on"], min_value=1)
            st.caption("One color at a time, in order.")
        elif pattern == "Wave":
            cols = st.columns(3)
            ms_input(cols[0], "On (ms)", f"tk_{name}_on", defaults["on"])
            ms_input(cols[1], "Off (ms)", f"tk_{name}_off", defaults["off"])
            ms_input(cols[2], "Stagger between colors (ms)", f"tk_{name}_stagger", defaults["stagger"])
            st.caption("Each color starts one stagger after the previous. Stagger ≥ On gives one color at a time; shorter overlaps.")
        else:
            cols = st.columns(2)
            ms_input(cols[0], "On (ms)", f"tk_{name}_on", defaults["on"])
            ms_input(cols[1], "Off (ms)", f"tk_{name}_off", defaults["off"])
            if pattern == "Together":
                st.caption("Every color flashes in unison.")
            else:
                st.caption("Odd and even colors blink opposite each other.")
        on, off, phase = ticker_pattern_timing(pattern, n)
    else:
        pattern = st.session_state.get("tk_pattern", "Wave")
        pattern_on, pattern_off, pattern_phase = ticker_pattern_timing(pattern, n)
        on = []
        off = []
        phase = []
        for c in range(n):
            cols = st.columns(3)
            on.append(ms_input(cols[0], f"Color {c + 1} On (ms)", f"tk_pc_on_{c}", pattern_on[c]))
            off.append(ms_input(cols[1], f"Color {c + 1} Off (ms)", f"tk_pc_off_{c}", pattern_off[c]))
            phase.append(ms_input(cols[2], f"Color {c + 1} Start delay (ms)", f"tk_pc_phase_{c}", pattern_phase[c]))

    st.markdown("##### Movement")
    movement = st.radio("Movement", ["Static", "Scroll"], horizontal=True, key="tk_movement", label_visibility="collapsed")
    scroll = False
    reverse = False
    step_ms = 100
    step_leds = 1
    if movement == "Scroll":
        scroll = True
        c1, c2, c3 = st.columns(3)
        direction = c1.selectbox("Direction", ["Forward", "Reverse"], key="tk_dir")
        if direction == "Reverse":
            reverse = True
        step_ms = c2.number_input("Step every (ms)", min_value=1, max_value=600000, value=100, step=1, key="tk_step_ms")
        step_leds = c3.number_input("Step size (LEDs)", min_value=1, max_value=chunk * n, value=1, step=1,
                                    key="tk_step_leds")

    params = base_params.copy()
    params["ticker_chunk_size"] = chunk
    params["ticker_colors"] = colors
    params["ticker_on_ms"] = on
    params["ticker_off_ms"] = off
    params["ticker_phase_ms"] = phase
    params["ticker_scroll"] = scroll
    params["ticker_reverse"] = reverse
    params["ticker_step_ms"] = step_ms
    params["ticker_step_leds"] = step_leds
    return params


def randomize_delays(delays, spread):
    new_delays = []
    for delay in delays:
        if delay > 0 and spread >= delay:
            limit = delay - 1
        else:
            limit = spread
        if limit > 0:
            change = random.randint(-limit, limit)
        else:
            change = 0
        new_delay = delay + change
        if new_delay < 0:
            new_delay = 0
        new_delays.append(new_delay)
    return new_delays


def make_sketch(anim, settings):
    params = settings.copy()
    if anim == "Chunk":
        if params["random_timing"]:
            params["delays"] = randomize_delays(params["delays"], params["random_ms"])
        return led_core.gen_chunk_code(params)
    elif anim == "Smooth":
        if params["smooth_anim_mode"] == "Fill" and params["randomizer_on"]:
            params["smooth_slices"] = led_core.apply_randomizer_slices(params["smooth_slices"], params["intensity"])
        return led_core.gen_smooth_code(params)
    elif anim == "Blink":
        return led_core.gen_blink_code(params)
    elif anim == "Random":
        return led_core.gen_random_code(params)
    elif anim == "Color Sequence":
        return led_core.gen_color_sequence_code(params)
    else:
        return led_core.gen_ticker_code(params)


def predictable_sketch(anim, settings):
    random.seed(0)
    sketch = make_sketch(anim, settings)
    random.seed()
    return sketch


if anim == "Chunk":
    settings = chunk_settings()
elif anim == "Smooth":
    settings = smooth_settings()
elif anim == "Blink":
    settings = blink_settings()
elif anim == "Random":
    settings = random_settings()
elif anim == "Color Sequence":
    settings = colorseq_settings()
else:
    settings = ticker_settings()

st.markdown("---")
current_preview = predictable_sketch(anim, settings)
if st.button("Generate Code", type="primary"):
    st.session_state.sketch = make_sketch(anim, settings)
    st.session_state.sketch_preview = current_preview

if "sketch" in st.session_state:
    sketch = st.session_state.sketch
    if st.session_state.sketch_preview != current_preview:
        st.info("Settings changed since this code was generated. Click **Generate Code** to refresh it.")

    tabs = st.tabs(["sketch.ino"])
    with tabs[0]:
        st.code(sketch, language="cpp")

    st.markdown("### Downloads")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download sketch.ino", data=sketch, file_name="banana_sketch.ino", mime="text/plain")
    with c2:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("banana_sketch/banana_sketch.ino", sketch)
        st.download_button("Download ZIP (ready-to-open sketch folder)", data=zip_buffer.getvalue(),
                           file_name="banana_sketch.zip", mime="application/zip")
