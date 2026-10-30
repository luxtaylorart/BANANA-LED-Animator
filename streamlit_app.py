import io
import random
import zipfile

import streamlit as st

from led_core import (
    APP_TITLE,
    to_int, hsv_to_rgb, build_gradient, build_sections, apply_randomizer_slices,
    gen_chunk_code, gen_smooth_code, gen_blink_code, gen_random_code, gen_color_sequence_code,
)

st.set_page_config(page_title="Lux Taylor B.A.N.A.N.A", layout="wide")
st.title(APP_TITLE)
st.caption("Arduino Nano, WS2812B LEDs")
st.warning("NOTE: Must install the **Adafruit NeoPixel** library via the Library Manager in Arduino IDE")


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def color_grid(prefix: str, labels, defaults, cols: int = 4):
    out = []
    columns = st.columns(cols)
    for i, label in enumerate(labels):
        d = defaults[i] if i < len(defaults) else defaults[-1]
        with columns[i % cols]:
            out.append(hex_to_rgb(st.color_picker(label, d, key=f"{prefix}_{i}")))
    return out


def ms_grid(prefix: str, labels, default: int = 500, cols: int = 4):
    out = []
    columns = st.columns(cols)
    for i, label in enumerate(labels):
        with columns[i % cols]:
            out.append(int(st.number_input(label, min_value=0, max_value=1_000_000,
                                           value=default, step=1, key=f"{prefix}_{i}")))
    return out


WHITE, RED, BLUE = "#FFFFFF", "#FF0000", "#0000FF"


st.sidebar.header("Settings")
total_leds = int(st.sidebar.number_input("Total number LEDs", min_value=1, max_value=2000, value=50, step=1))
data_pin = int(st.sidebar.number_input("Data Pin", min_value=0, max_value=50, value=6, step=1))
anim = st.sidebar.selectbox("Animation Type", ["Chunk", "Smooth", "Blink", "Random", "Color Sequence"])

st.sidebar.subheader("Run Mode")
run_modes = ["Loop", "Trigger"] if anim == "Blink" else ["Loop", "Hold", "Trigger"]
rm = st.sidebar.selectbox("Run Mode", run_modes)
trig = st.sidebar.selectbox("Trigger Type", ["limit switch", "pushbutton"], disabled=(rm != "Trigger"))
input_pin = int(st.sidebar.number_input("Input Pin", min_value=0, max_value=50, value=2, step=1,
                                        disabled=(rm != "Trigger")))
uses_timing = anim in ("Chunk", "Smooth", "Color Sequence")
pre = int(st.sidebar.number_input("Pre-light delay (ms)", min_value=0, max_value=600000, value=2000, step=1,
                                  disabled=not uses_timing))
post = int(st.sidebar.number_input("Post-light hold (ms)", min_value=0, max_value=600000, value=2000, step=1,
                                   disabled=not (uses_timing and rm == "Loop")))

if rm == "Loop":
    run_mode = "loop"
elif rm == "Hold":
    run_mode = "hold"
else:
    run_mode = "trigger_limit" if trig == "limit switch" else "trigger_push"

st.sidebar.subheader("Extra Settings")
ease_on = st.sidebar.checkbox("Animation Easing", value=False)
ease_ms = int(st.sidebar.number_input("Ease Duration (ms)", min_value=0, max_value=600000, value=250, step=1,
                                      disabled=not ease_on))

base_params = {
    "total_leds": total_leds,
    "data_pin": data_pin,
    "input_pin": input_pin,
    "run_mode": run_mode,
    "pre_delay": pre,
    "post_hold": post,
    "ease_on": ease_on,
    "ease_ms": ease_ms,
}


est_ram = 3 * total_leds + 500
if est_ram > 1700:
    st.sidebar.warning(f"⚠ est RAM {est_ram} of 2048 bytes: too many LEDs for an Arduino Nano")
else:
    st.sidebar.info(f"est RAM: {est_ram} of 2048 bytes")

st.subheader(f"{anim} Settings")


def chunk_settings():
    n = int(st.number_input("Number of chunks", min_value=1, max_value=total_leds, value=min(5, total_leds), step=1))
    sizes = [total_leds // n] * n
    sizes[-1] += total_leds % n
    starts, cur = [], 0
    for s in sizes:
        starts.append(cur)
        cur += s

    if st.checkbox("Uniform RGB", value=True, key="chunk_rgb_uniform"):
        rgb_values = color_grid("chunk_rgb", ["RGB"], [WHITE]) * n
    else:
        rgb_values = color_grid("chunk_rgb", [f"RGB {i+1}" for i in range(n)], [WHITE])

    uniform_timing = st.checkbox("Uniform timing", value=True, key="chunk_timing_uniform")
    if uniform_timing:
        c1, c2, c3 = st.columns([2, 1, 1])
        d0 = int(c1.number_input("milliseconds between chunks", min_value=0, max_value=1_000_000, value=500, step=1))
        rand_on = c2.checkbox("timing randomizer", value=False)
        rmax_in = int(c3.number_input("± ms", min_value=0, max_value=1_000_000, value=300, step=1,
                                      disabled=not rand_on, key="chunk_rand_ms"))
    else:
        delays_in = ms_grid("chunk_delay", [f"Delay {i+1} (ms)" for i in range(max(0, n - 1))])

    def make():
        if uniform_timing:
            delays = [d0] * max(0, n - 1)
            if rand_on and delays:
                rmax = rmax_in
                if d0 > 0 and rmax >= d0:
                    rmax = d0 - 1
                for i in range(len(delays)):
                    j = random.randint(-rmax, rmax) if rmax > 0 else 0
                    delays[i] = max(0, d0 + j)
        else:
            delays = delays_in
        return gen_chunk_code({**base_params, "num_chunks": n, "chunk_sizes": sizes, "chunk_starts": starts,
                               "rgb_values": rgb_values, "delays": delays})
    return make


def smooth_settings():
    c1, c2 = st.columns(2)
    mode = c1.selectbox("Type", ["Solid Color", "Gradient", "Sections", "Rainbow"])
    if mode == "Solid Color":
        c = color_grid("smooth_solid", ["RGB"], [WHITE])[0]
        pixel_colors = [c] * total_leds
    elif mode == "Gradient":
        k = int(c2.number_input("number of stops", min_value=2, max_value=8, value=2, step=1))
        stops = color_grid("smooth_stop", [f"Stop {i+1}" for i in range(k)], [RED, BLUE, WHITE])
        pixel_colors = build_gradient(stops, total_leds)
    elif mode == "Sections":
        k = int(c2.number_input("number of sections", min_value=2, max_value=8, value=2, step=1))
        cols = color_grid("smooth_section", [f"Section {i+1}" for i in range(k)], [WHITE])
        pixel_colors = build_sections(cols, total_leds)
    else:
        pixel_colors = [hsv_to_rgb(i / max(1, total_leds)) for i in range(total_leds)]

    c1, c2 = st.columns(2)
    anim_mode = c1.selectbox("Animation Type", ["Fill", "Chase"])
    speed_ms = int(c2.number_input("Animation Speed, Millis", min_value=1, max_value=600000, value=100, step=1))

    chase_group = 5
    rand_on, intensity = False, 1
    if anim_mode == "Chase":
        chase_group = int(st.number_input("Chase group size", min_value=1, max_value=max(1, total_leds),
                                          value=min(5, total_leds), step=1))
    else:
        c1, c2 = st.columns(2)
        rand_on = c1.checkbox("randomizer", value=False, key="smooth_rand")
        intensity = int(c2.selectbox("Intensity", list(range(1, 11)), disabled=not rand_on))

    def make():
        steps = total_leds if anim_mode == "Fill" else max(1, total_leds - chase_group + 1)
        slices = [speed_ms] * steps
        if anim_mode == "Fill" and rand_on:
            slices = apply_randomizer_slices(slices, intensity)
        return gen_smooth_code({**base_params, "smooth_anim_mode": anim_mode, "smooth_chase_group": chase_group,
                                "smooth_slices": slices, "pixel_colors": pixel_colors})
    return make


def blink_settings():
    sec = int(st.number_input("Number of sections", min_value=1, max_value=total_leds, value=1, step=1))
    lens = [total_leds // sec] * sec
    lens[-1] += total_leds % sec
    starts, cur = [], 0
    for L in lens:
        starts.append(cur)
        cur += L

    if st.checkbox("uniform color", value=True, key="blink_uniform_color"):
        blink_colors = color_grid("blink_rgb", ["RGB"], [WHITE]) * sec
    else:
        blink_colors = color_grid("blink_rgb", [f"RGB {i+1}" for i in range(sec)], [WHITE])

    order_mode = "Together"
    if sec > 1:
        order_mode = st.selectbox("Order", ["Together", "Sequential", "Random", "Custom"])

    uniform_on, uniform_off = 500, 500
    separate = False
    on_by = off_by = None
    custom_order = [0]

    def on_off_row():
        c1, c2 = st.columns(2)
        return (int(c1.number_input("On (ms)", min_value=0, max_value=1_000_000, value=500, step=1, key="blink_on")),
                int(c2.number_input("Off (ms)", min_value=0, max_value=1_000_000, value=500, step=1, key="blink_off")))

    def per_section_rows():
        ons, offs = [], []
        for s in range(sec):
            c1, c2 = st.columns(2)
            ons.append(int(c1.number_input(f"S{s+1} On", min_value=0, max_value=1_000_000, value=500, step=1, key=f"blink_on_{s}")))
            offs.append(int(c2.number_input(f"S{s+1} Off", min_value=0, max_value=1_000_000, value=500, step=1, key=f"blink_off_{s}")))
        return ons, offs

    if order_mode in ("Together", "Random"):
        uniform_on, uniform_off = on_off_row()
    elif order_mode == "Sequential":
        separate = st.checkbox("separate timing", value=False)
        if separate:
            on_by, off_by = per_section_rows()
        else:
            uniform_on, uniform_off = on_off_row()
    else:
        raw = st.text_input("Custom order (comma-separated section numbers, starting at 1)", "1,1")
        items = [x.strip() for x in raw.split(",") if x.strip()]
        custom_order = [to_int(it, 1, 1, sec) - 1 for it in items] or [0]
        on_by, off_by = per_section_rows()

    if on_by is None:
        on_by, off_by = [uniform_on] * sec, [uniform_off] * sec

    blink_mode = {"Together": 0, "Sequential": 1, "Random": 2, "Custom": 3}[order_mode]

    def make():
        return gen_blink_code({**base_params, "blink_sections": sec, "blink_starts": starts, "blink_lens": lens,
                               "blink_colors": blink_colors, "blink_mode": blink_mode,
                               "blink_uniform_on": uniform_on, "blink_uniform_off": uniform_off,
                               "blink_separate_timing": separate, "blink_on_by": on_by, "blink_off_by": off_by,
                               "blink_custom_order": custom_order})
    return make


def random_settings():
    c1, c2 = st.columns(2)
    chunk_size = int(c1.number_input("Size Of Random Chunk", min_value=1, max_value=total_leds,
                                     value=min(10, total_leds), step=1))
    random_place = c2.checkbox("random chunk placement", value=False)

    c1, c2 = st.columns(2)
    base_on = int(c1.number_input("Blink Frequency On (ms)", min_value=0, max_value=1_000_000, value=250, step=1))
    base_off = int(c2.number_input("Blink Frequency Off (ms)", min_value=0, max_value=1_000_000, value=0, step=1))

    c1, c2 = st.columns(2)
    freq_rand = c1.checkbox("Frequency Randomizer", value=False)
    freq_rand_ms = int(c2.number_input("Frequency randomizer ± ms", min_value=0, max_value=1_000_000, value=0, step=1,
                                       disabled=not freq_rand))

    c1, c2 = st.columns(2)
    simul = c1.checkbox("simultaneous", value=False)
    max_simul = int(c2.number_input("maximum simultaneous illumination", min_value=1, max_value=200, value=2, step=1,
                                    disabled=not simul))

    c1, c2 = st.columns(2)
    timing_jitter = c1.checkbox("randomize timing", value=False, disabled=not simul,
                                help="Only applies when 'simultaneous' is on.")
    jitter_ms = int(c2.number_input("randomize timing ± ms", min_value=0, max_value=1_000_000, value=250, step=1,
                                    disabled=not (simul and timing_jitter)))

    cm = st.selectbox("Color", ["Solid", "Subset", "Random"])
    if cm == "Solid":
        color_mode = 0
        solid = color_grid("rand_solid", ["RGB"], [WHITE])[0]
        subset = [solid, solid]
        consistent = True
    elif cm == "Subset":
        color_mode = 1
        solid = (255, 255, 255)
        c1, c2 = st.columns(2)
        k = int(c1.selectbox("Number of Colors", list(range(2, 11))))
        consistent = c2.checkbox("consistent color placement", value=True)
        subset = color_grid("rand_subset", [f"RGB {i+1}" for i in range(k)], [WHITE])
    else:
        color_mode = 2
        solid = (255, 255, 255)
        subset = [(255, 255, 255), (255, 255, 255)]
        consistent = False

    def make():
        return gen_random_code({**base_params, "rand_chunk_size": chunk_size, "rand_random_placement": random_place,
                                "rand_on_ms": base_on, "rand_off_ms": base_off,
                                "rand_freq_rand": freq_rand, "rand_freq_rand_ms": freq_rand_ms,
                                "rand_simul": simul, "rand_max_simul": max_simul if simul else 1,
                                "rand_timing_jitter": timing_jitter if simul else False, "rand_jitter_ms": jitter_ms,
                                "rand_color_mode": color_mode, "rand_solid_rgb": solid, "rand_subset_rgbs": subset,
                                "rand_consistent_placement": consistent})
    return make


def colorseq_settings():
    n = int(st.number_input("Number of Steps", min_value=1, max_value=50, value=3, step=1))
    colors, durs = [], []
    for i in range(n):
        c1, c2 = st.columns(2)
        with c1:
            colors.append(hex_to_rgb(st.color_picker(f"Step {i+1} Color", RED, key=f"cs_color_{i}")))
        durs.append(int(c2.number_input(f"Step {i+1} Duration (ms)", min_value=0, max_value=600000,
                                        value=500, step=1, key=f"cs_dur_{i}")))
    cs_loop = st.checkbox("loop", value=False, key="cs_loop", disabled=(rm == "Loop"),
                          help="Restarts the sequence immediately in Hold and Trigger modes. Loop run mode always repeats.")

    def make():
        return gen_color_sequence_code({**base_params, "cs_steps": n, "cs_colors": colors, "cs_durs": durs,
                                        "cs_loop": cs_loop})
    return make


builders = {
    "Chunk": chunk_settings,
    "Smooth": smooth_settings,
    "Blink": blink_settings,
    "Random": random_settings,
    "Color Sequence": colorseq_settings,
}
make_sketch = builders[anim]()


def settings_fingerprint():
    state = random.getstate()
    random.seed(0)
    try:
        return make_sketch()
    finally:
        random.setstate(state)


st.markdown("---")
current_fp = settings_fingerprint()
if st.button("Generate Code", type="primary"):
    st.session_state.sketch = make_sketch()
    st.session_state.sketch_fp = current_fp

sketch = st.session_state.get("sketch")
if sketch:
    if st.session_state.get("sketch_fp") != current_fp:
        st.info("Settings changed since this code was generated. Click **Generate Code** to refresh it.")

    tab1, = st.tabs(["sketch.ino"])
    with tab1:
        st.code(sketch, language="cpp")

    st.markdown("### Downloads")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download sketch.ino", data=sketch.encode("utf-8"),
                           file_name="banana_sketch.ino", mime="text/plain")
    with c2:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("banana_sketch/banana_sketch.ino", sketch)
        st.download_button("Download ZIP (ready-to-open sketch folder)", data=zip_buf.getvalue(),
                           file_name="banana_sketch.zip", mime="application/zip")
