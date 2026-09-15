
import random
import time
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
from PIL import Image

st.set_page_config(
    page_title="SIGNAL RESCUE — ARES-7",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# RETRO-FUTURIST CSS
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Mono:wght@400;700&display=swap');

    .stApp {
        background:
            radial-gradient(circle at 82% 12%, rgba(82,208,192,.09), transparent 25%),
            radial-gradient(circle at 12% 78%, rgba(217,154,82,.06), transparent 25%),
            #070d12;
        color: #fff2d0;
    }

    [data-testid="stSidebar"] {
        background: #111b20;
        border-right: 1px solid #33423e;
    }

    [data-testid="stHeader"] {
        background: rgba(7,13,18,.82);
    }

    .retro-title {
        font-family: "Space Mono", monospace;
        font-size: 42px;
        font-weight: 700;
        letter-spacing: 3px;
        color: #fff2d0;
        line-height: 1.0;
        margin-bottom: 0;
    }

    .retro-subtitle {
        font-family: "DM Mono", monospace;
        font-size: 12px;
        color: #b9c6be;
        letter-spacing: 1px;
    }

    .mission-card {
        background: #111b20;
        border: 1px solid #33423e;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }

    .section-label {
        color: #d99a52;
        font-family: "DM Mono", monospace;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    .analyzer {
        background: #0d161b;
        border: 1px solid #2d4944;
        border-left: 4px solid #52d0c0;
        border-radius: 6px;
        padding: 12px 14px;
        font-family: "DM Mono", monospace;
        color: #b9c6be;
        white-space: pre-wrap;
        font-size: 12px;
    }

    .bootbox {
        background: #0d161b;
        border: 1px solid #33423e;
        border-radius: 8px;
        padding: 16px;
        font-family: "DM Mono", monospace;
    }

    div.stButton > button {
        border-radius: 5px;
        border: 1px solid #52d0c0;
        background: #52d0c0;
        color: #071014;
        font-weight: 700;
    }

    div.stButton > button:hover {
        border-color: #fff2d0;
        background: #fff2d0;
        color: #071014;
    }

    .scorebox {
        background: #151f24;
        border: 1px solid #33423e;
        border-radius: 6px;
        padding: 8px 12px;
        font-family: "DM Mono", monospace;
    }

    .small-muted {
        color: #aebdb5;
        font-family: "DM Mono", monospace;
        font-size: 11px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CORE HELPERS
# ============================================================

def sine(t, amplitude=1.0, frequency=1.0, phase=0.0):
    return amplitude * np.sin(2 * np.pi * frequency * t + phase)


def energy(signal):
    return float(np.sum(np.abs(signal) ** 2))


def fft_components(signal, fs):
    spectrum = np.fft.fft(signal)
    freqs = np.fft.fftfreq(len(signal), d=1 / fs)
    mag = np.abs(spectrum) / len(signal)
    keep = (freqs >= 0) & (freqs <= 150)
    return freqs[keep], mag[keep]


def convolution(x, h):
    y = np.zeros(len(x) + len(h) - 1)
    for n in range(len(x)):
        for k in range(len(h)):
            y[n + k] += x[n] * h[k]
    return y


def numeric_error(answer, target, tolerance):
    a = np.asarray(answer, dtype=float)
    b = np.asarray(target, dtype=float)
    error = float(np.mean(np.abs(a - b)))
    return error, error <= tolerance


def component_score(actual, target, tolerance):
    return max(0.0, min(100.0, 100.0 * (1.0 - abs(actual - target) / tolerance)))


def delay_score(actual, target, frequency, tolerance=0.025):
    period = 1.0 / frequency
    wrapped = ((actual - target + period / 2) % period) - period / 2
    return component_score(abs(wrapped), 0.0, tolerance)


def score_mission(error, elapsed, hints, operations):
    if error <= 0:
        accuracy = 1000
    else:
        accuracy = min(1000, max(0, 1000 / (1 + error * 100)))
    speed = min(300, max(0, 300 - elapsed * 5))
    score = max(0, round(accuracy + speed - hints * 100 - max(0, operations - 1) * 25))
    return score


MISSION_NAMES = [
    "Establish Contact",
    "Align Transmission",
    "Restore Strength",
    "Corrupted Orientation",
    "The Mixer",
    "Corrupted Transmission",
    "Energy Crisis",
    "What's Inside?",
    "The Channel",
    "Unknown System",
    "System Failure",
    "Save ARES-7",
]

OPERATIONS = {1:1, 2:1, 3:1, 4:1, 5:2, 6:3, 7:2, 8:2, 9:1, 10:2, 11:2, 12:5}


# ============================================================
# RANDOM CAMPAIGN
# ============================================================

def new_campaign():
    missions = {}

    # 01
    amp = random.choice([0.75,1.0,1.25,1.5,1.75,2.0])
    freq = random.choice([3.,4.,5.,6.,7.,8.])
    phase = random.choice([-np.pi/2,-np.pi/4,0.,np.pi/4,np.pi/2])
    missions[1] = dict(amp=amp, freq=freq, phase=phase)

    # 02
    delay = random.choice([0.06,0.08,0.12,0.16,0.20])
    missions[2] = dict(freq=4.0, delay=delay)

    # 03
    weak = random.choice([0.35,0.4,0.45,0.5,0.55,0.6,0.65])
    target_amp = random.choice([0.9,1.0,1.1,1.2,1.3,1.4,1.5])
    missions[3] = dict(weak=weak, target_amp=target_amp, scale=target_amp/weak)

    # 04
    original = random.sample(range(1,9), random.choice([4,5,6]))
    missions[4] = dict(original=original, target=original[::-1])

    # 05
    missions[5] = dict(
        amp_a=random.choice([0.8,1.,1.2]),
        freq_a=random.choice([4.,5.,6.]),
        amp_b=random.choice([0.3,0.4,0.5,0.6,0.7]),
        freq_b=random.choice([15.,20.,25.]),
    )

    # 06
    missions[6] = dict(
        scale=random.choice([1.5,1.75,2.,2.25,2.5]),
        delay=random.choice([0.08,0.10,0.12,0.14,0.16,0.18,0.20]),
        reverse=1,
    )

    # 07
    amps = random.sample([0.8,1.0,1.2,1.5,1.8], 3)
    viable = [(i,a) for i,a in enumerate(amps,1) if a >= .75]
    correct = min(viable, key=lambda z:z[1])[0]
    missions[7] = dict(amps=amps, threshold=.75, correct=correct)

    # 08
    freqs = random.sample([8.,10.,12.,20.,40.,50.,60.,80.,100.,120.],3)
    fft_amps = random.sample([1.,0.8,0.6,0.5,0.4],3)
    missions[8] = dict(freqs=freqs, amps=fft_amps)

    # 09
    x = random.choice([[1,2,1],[1,1,2],[2,1,1],[1,2,2]])
    h = random.choice([[1,1],[1,2],[2,1],[1,-1]])
    y = convolution(np.array(x,dtype=float), np.array(h,dtype=float)).tolist()
    missions[9] = dict(x=x,h=h,target=y)

    # 10 / 11
    missions[10] = dict(pole=random.choice([-.5,-1.,-1.5,-2.,-2.5,-3.]), stable=1)
    missions[11] = dict(pole=random.choice([.5,1.,1.5,2.,2.5]), stable=0)

    # FINAL
    missions[12] = dict(
        scale=random.choice([1.5,1.75,2.,2.25]),
        delay=random.choice([.05,.08,.10,.12,.15]),
        reverse=1,
        freq=random.choice([8.,9.,10.,11.,12.]),
        stable=1,
    )

    return missions


# ============================================================
# SESSION STATE
# ============================================================

if "booted" not in st.session_state:
    st.session_state.booted = False
if "campaign_id" not in st.session_state:
    st.session_state.campaign_id = 1
if "missions" not in st.session_state:
    st.session_state.missions = new_campaign()
if "current" not in st.session_state:
    st.session_state.current = 1
if "score" not in st.session_state:
    st.session_state.score = 0
if "integrity" not in st.session_state:
    st.session_state.integrity = 100
if "completed" not in st.session_state:
    st.session_state.completed = set()
if "hints" not in st.session_state:
    st.session_state.hints = 0
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "mission_started" not in st.session_state:
    st.session_state.mission_started = time.time()
if "result" not in st.session_state:
    st.session_state.result = None


# ============================================================
# LOADING / BOOT
# ============================================================

if not st.session_state.booted:
    st.markdown(
        '<div class="bootbox"><div class="section-label">ARES-7 / COMMUNICATIONS RECOVERY UNIT</div>'
        '<div class="retro-title" style="margin-top:14px;">SIGNAL<br><span style="color:#52D0C0;">RESCUE</span></div>'
        '<div class="retro-subtitle" style="margin-top:14px;">DEEP-SPACE TELEMETRY RECOVERY SIMULATION</div></div>',
        unsafe_allow_html=True,
    )

    asset_path = Path(__file__).resolve().parent / "assets" / "retro_space_art.png"

    if asset_path.exists():
        with Image.open(asset_path) as img:
            st.image(img.copy(), use_container_width=True)
    else:
        st.warning("Retro visual feed unavailable — continuing without artwork.")

    if st.button("ENTER MISSION CONTROL", use_container_width=False):
        st.session_state.booted = True
        st.rerun()

    st.markdown(
        '<div class="small-muted">SIGNAL SYSTEMS ONLINE // SIGNALS & SYSTEMS TRAINING SIMULATION</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="retro-subtitle">ARES-7  //  COMMUNICATIONS RECOVERY CONSOLE</div>'
    '<div class="retro-title" style="font-size:32px;margin-top:4px;">SIGNAL <span style="color:#52D0C0;">RESCUE</span></div>',
    unsafe_allow_html=True,
)

top1, top2, top3 = st.columns([1.3,1,1])
with top1:
    st.markdown(
        f'<div class="scorebox">MISSION {st.session_state.current:02d} / 12</div>',
        unsafe_allow_html=True,
    )
with top2:
    st.markdown(
        f'<div class="scorebox">SCORE {st.session_state.score:04d}</div>',
        unsafe_allow_html=True,
    )
with top3:
    color = "#87DFA5" if st.session_state.integrity > 50 else "#F3B85B" if st.session_state.integrity > 20 else "#E97867"
    st.markdown(
        f'<div class="scorebox" style="color:{color};">INTEGRITY {st.session_state.integrity}%</div>',
        unsafe_allow_html=True,
    )

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### ARES-7 • CAMPAIGN")

    for idx, name in enumerate(MISSION_NAMES, 1):
        if idx in st.session_state.completed:
            label = f"✓ {idx:02d}  {name}"
        elif idx == st.session_state.current:
            label = f"▶ {idx:02d}  {name}"
        elif idx <= max(st.session_state.completed or {0}) + 1:
            label = f"○ {idx:02d}  {name}"
        else:
            label = f"🔒 {idx:02d}  {name}"

        enabled = idx <= max(st.session_state.completed or {0}) + 1
        if st.button(label, key=f"nav_{idx}_{st.session_state.campaign_id}", disabled=not enabled):
            st.session_state.current = idx
            st.session_state.result = None
            st.session_state.mission_started = time.time()
            st.rerun()

    st.divider()

    if st.button("RESET NEW CAMPAIGN", use_container_width=True):
        st.session_state.campaign_id += 1
        st.session_state.missions = new_campaign()
        st.session_state.current = 1
        st.session_state.score = 0
        st.session_state.integrity = 100
        st.session_state.completed = set()
        st.session_state.hints = 0
        st.session_state.attempts = 0
        st.session_state.result = None
        st.session_state.mission_started = time.time()
        st.rerun()

    st.markdown(
        '<div class="small-muted" style="margin-top:12px;">'
        'LIVE • RANDOMIZED • AUTO-SCORED</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# CURRENT MISSION
# ============================================================

mid = st.session_state.current
p = st.session_state.missions[mid]

briefing_data = {
    1: ("ESTABLISH CONTACT", "ARES-7's beacon has been detected. Reconstruct the signal parameters.",
        "Tune amplitude, frequency and phase until your generated signal matches the reference."),
    2: ("ALIGN THE TRANSMISSION", "The signal arrived late through the communication channel.",
        "Adjust the delay until the received waveform aligns with the reference."),
    3: ("RESTORE SIGNAL STRENGTH", "ARES-7's transmission is too weak to decode reliably.",
        "Scale the weak signal until its amplitude matches the recovery target."),
    4: ("CORRUPTED ORIENTATION", "The sampled telemetry arrived backwards in time.",
        "Reverse the received discrete-time sequence."),
    5: ("THE MIXER", "Two transmissions are riding on the same communication link.",
        "Recover the amplitudes of the two component signals used in the mixer."),
    6: ("CORRUPTED TRANSMISSION", "ARES-7 applied several transformations to the original signal.",
        "Identify the scale, time delay and reversal applied to the signal."),
    7: ("ENERGY CRISIS", "Power is limited. Choose the weakest signal that is still strong enough for reliable recovery.",
        "Select the lowest-energy signal whose amplitude is at least the mission threshold."),
    8: ("WHAT'S INSIDE?", "The waveform looks complicated, but hidden frequencies can be revealed with the FFT.",
        "Identify the three dominant frequencies hidden in the transmission."),
    9: ("THE CHANNEL", "The channel itself is altering the signal. Model it with discrete convolution.",
        "Recover the output y[n] = x[n] * h[n]."),
    10: ("UNKNOWN SYSTEM", "We have identified a first-order transfer function but its exact pole is unknown.",
        "Estimate the pole and determine whether the continuous-time system is stable."),
    11: ("SYSTEM FAILURE", "The spacecraft control system is amplifying disturbances instead of suppressing them.",
        "Estimate the pole and determine whether the system is stable."),
    12: ("SAVE ARES-7", "Final transmission recovery: combine signal operations with system-level reasoning.",
        "Recover scale, delay, reversal, frequency and stability."),
}

title, briefing, objective = briefing_data[mid]

# Only build Mission 07's threshold text when Mission 07 is actually active.
if mid == 7:
    objective = (
        f"Select the lowest-energy signal whose amplitude is at least "
        f"{p['threshold']:.2f}."
    )

st.markdown(
    f'<div class="mission-card">'
    f'<div class="section-label">MISSION {("FINAL" if mid==12 else f"{mid:02d}")}</div>'
    f'<h2 style="margin:5px 0 8px;color:#fff2d0;">{title}</h2>'
    f'<div style="color:#b9c6be;font-size:14px;">{briefing}</div>'
    f'<div style="margin-top:12px;color:#d99a52;font-family:DM Mono,monospace;font-size:11px;font-weight:700;">OBJECTIVE</div>'
    f'<div style="color:#fff2d0;">{objective}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ============================================================
# CONTROLS + ANSWERS
# ============================================================

a_col, g_col = st.columns([0.39,0.61], gap="large")

with a_col:
    st.markdown('<div class="section-label">LIVE ENGINEERING CONSOLE</div>', unsafe_allow_html=True)

    key = f"{st.session_state.campaign_id}_{mid}"

    # Deliberately imperfect defaults.
    if mid == 1:
        av = st.slider("Amplitude", 0.5, 2.25, 0.65 if p["amp"] > 1 else 1.75, 0.01, key=f"amp_{key}")
        fv = st.slider("Frequency (Hz)", 2.0, 9.0, 2.0 if p["freq"] > 3 else 6.0, 0.1, key=f"freq_{key}")
        pv = st.slider("Phase (rad)", -1.6, 1.6, 0.0 if abs(p["phase"]) > .1 else .6, 0.01, key=f"phase_{key}")
        answer = [av,fv,pv]
        match = float(np.mean([
            component_score(av,p["amp"],.25),
            component_score(fv,p["freq"],1.0),
            component_score(pv,p["phase"],.25),
        ]))
        analyzer = (
            f"A: {av:.2f} / target {p['amp']:.2f}\n"
            f"f: {fv:.2f} / target {p['freq']:.2f} Hz\n"
            f"phase: {pv:.2f} / target {p['phase']:.2f} rad"
        )

    elif mid == 2:
        dv = st.slider("Delay (s)", -0.25, 0.30, 0.0, 0.005, key=f"delay_{key}")
        answer = [dv]
        match = delay_score(dv,p["delay"],p["freq"])
        analyzer = f"Current delay = {dv:.3f} s\nTarget delay = {p['delay']:.3f} s\nAlignment error = {abs(dv-p['delay']):.3f} s"

    elif mid == 3:
        sv = st.slider("Scale K", 0.5, 4.0, 1.0, 0.01, key=f"scale_{key}")
        output = p["weak"] * sv
        answer = [sv]
        match = component_score(sv,p["scale"],.4)
        analyzer = f"Input amplitude = {p['weak']:.2f}\nOutput = A×K = {output:.2f}\nTarget amplitude = {p['target_amp']:.2f}\nRequired K = {p['scale']:.2f}"

    elif mid == 4:
        rv = st.radio("Orientation", ["FORWARD", "REVERSED"], index=0, key=f"rev_{key}")
        val = 1 if rv == "REVERSED" else 0
        answer = [val]
        match = 100.0 if val == 1 else 0.0
        analyzer = f"Current operation = {'x[-n]' if val else 'x[n]'}\nRequired operation = x[-n]"

    elif mid == 5:
        a1 = st.slider("Signal A amplitude", 0.2, 1.5, 0.5, 0.01, key=f"a1_{key}")
        a2 = st.slider("Signal B amplitude", 0.2, 1.0, 0.25, 0.01, key=f"a2_{key}")
        answer = [a1,a2]
        match = float(np.mean([
            component_score(a1,p["amp_a"],.25),
            component_score(a2,p["amp_b"],.20),
        ]))
        analyzer = f"y(t) = x₁(t) + x₂(t)\nA₁ = {a1:.2f} / {p['amp_a']:.2f}\nA₂ = {a2:.2f} / {p['amp_b']:.2f}"

    elif mid == 6:
        sc = st.slider("Scale", 1.0, 3.0, 1.0, 0.01, key=f"sc_{key}")
        dl = st.slider("Delay (s)", 0.0, 0.30, 0.0, 0.005, key=f"dl_{key}")
        rv = st.radio("Reversal", ["NO","YES"], index=0, key=f"r6_{key}")
        rev = 1 if rv=="YES" else 0
        answer = [sc,dl,rev]
        match = float(np.mean([
            component_score(sc,p["scale"],.4),
            component_score(dl,p["delay"],.05),
            100.0 if rev==1 else 0.0,
        ]))
        analyzer = f"K = {sc:.2f} / {p['scale']:.2f}\ndelay = {dl:.3f} / {p['delay']:.3f} s\nreversal = {'YES' if rev else 'NO'} / required YES"

    elif mid == 7:
        sel = st.radio(
            "Select signal",
            [1,2,3],
            format_func=lambda n: f"Signal {n}  •  amplitude {p['amps'][n-1]:.2f}",
            index=1 if p["correct"] != 2 else 2,
            key=f"sel_{key}",
        )
        idx = sel-1
        e = energy(sine(np.linspace(0,1,1000),p["amps"][idx],5,0))
        answer = [sel]
        match = 100.0 if sel==p["correct"] else 0.0
        analyzer = f"Selected signal = {sel}\nAmplitude = {p['amps'][idx]:.2f}\nEnergy Σ|x[n]|² ≈ {e:.0f}\nMinimum valid amplitude = {p['threshold']:.2f}"

    elif mid == 8:
        vals = []
        for i,f in enumerate(p["freqs"]):
            default = f + (15 if i != 1 else -12)
            default = max(5,min(130,default))
            vals.append(st.slider(f"Frequency guess {i+1} (Hz)",5,130,default,1,key=f"ff{i}_{key}"))
        answer = vals
        aa=np.sort(np.array(answer,dtype=float)); tt=np.sort(np.array(p["freqs"],dtype=float))
        match=float(np.mean([component_score(x,y,10.0) for x,y in zip(aa,tt)]))
        analyzer = f"Live peaks = {', '.join(f'{x:.0f}' for x in aa)} Hz\nTarget peaks = {', '.join(f'{x:.0f}' for x in tt)} Hz\nMethod = FFT → dominant magnitude peaks"

    elif mid == 9:
        answer=[]
        for i,target in enumerate(p["target"]):
            answer.append(st.slider(f"y[{i}]", -4.0, 8.0, 0.0, .1, key=f"y{i}_{key}"))
        match=float(np.mean([component_score(x,y,1.0) for x,y in zip(answer,p["target"])]))
        analyzer = f"x[n] = {p['x']}\nh[n] = {p['h']}\nLive y[n] = {[round(v,1) for v in answer]}\nCorrect y[n] = {p['target']}"

    elif mid in (10,11):
        start = -2.0 if p["pole"] > 0 else 2.0
        pole = st.slider("Estimated pole", -3.5, 3.5, start, .05, key=f"pole_{key}")
        stable = st.radio(
            "Stability",
            [0,1],
            index=0 if p["stable"] == 1 else 1,
            format_func=lambda x: "UNSTABLE" if x==0 else "STABLE",
            key=f"stable_{key}",
        )
        answer=[pole,stable]
        match=0.5*component_score(pole,p["pole"],.6)+0.5*(100 if stable==p["stable"] else 0)
        analyzer=f"Pole = {pole:.2f}\nResponse = {'decaying' if pole < 0 else 'growing'}\nClassification = {'STABLE' if stable else 'UNSTABLE'}\nTarget pole = {p['pole']:.2f}"

    else:
        sc = st.slider("Scale", 1.0, 3.0, 1.0, .01, key=f"fsc_{key}")
        dl = st.slider("Delay (s)", 0.0, .25, 0.0, .005, key=f"fdl_{key}")
        rv = st.radio("Reversal", ["NO","YES"], index=0, key=f"fr_{key}")
        rev = 1 if rv=="YES" else 0
        startf = p["freq"]+1.5 if p["freq"]<13 else p["freq"]-1.5
        fr = st.slider("Frequency (Hz)",6.0,14.0,startf,.1,key=f"ffinal_{key}")
        stable = st.radio("System", [0,1], index=0, format_func=lambda x:"UNSTABLE" if x==0 else "STABLE", key=f"fsys_{key}")
        answer=[sc,dl,rev,fr,stable]
        match=float(np.mean([
            component_score(sc,p["scale"],.4),
            component_score(dl,p["delay"],.05),
            100 if rev==p["reverse"] else 0,
            component_score(fr,p["freq"],1.0),
            100 if stable==p["stable"] else 0,
        ]))
        analyzer=f"K={sc:.2f} / {p['scale']:.2f}\ndelay={dl:.3f}s / {p['delay']:.3f}s\nreverse={'YES' if rev else 'NO'}\nf={fr:.2f}Hz / {p['freq']:.2f}Hz\nsystem={'STABLE' if stable else 'UNSTABLE'}"

    match_color = "#87DFA5" if match >= 95 else "#F3B85B" if match >= 60 else "#E97867"
    st.markdown(
        f'<div style="font-family:DM Mono,monospace;font-size:20px;font-weight:700;color:{match_color};margin:8px 0 12px;">LIVE MATCH {match:05.1f}%</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="analyzer">{analyzer}</div>',
        unsafe_allow_html=True,
    )

    col1,col2=st.columns(2)
    with col1:
        submit = st.button("SUBMIT RECOVERY", use_container_width=True)
    with col2:
        hint = st.button("HINT", use_container_width=True)

    if hint:
        hints = {
            1:"Compare height, spacing between cycles and horizontal shift.",
            2:"A positive delay moves the signal to the right.",
            3:"Use K = target amplitude / weak amplitude.",
            4:"Time reversal flips the sample order.",
            5:"The mixer is the sum of two signals.",
            6:"Treat scale, delay and reversal as separate operations.",
            7:"For equal duration/frequency, energy increases with amplitude².",
            8:"FFT reveals the strongest hidden frequency peaks.",
            9:"Compute each y[n] by summing overlapping products.",
            10:"A continuous-time LHP pole means a stable system.",
            11:"A RHP pole causes exponential growth.",
            12:"Solve amplitude, timing, orientation, frequency and stability separately.",
        }
        st.warning("💡 " + hints[mid])
        st.session_state.integrity=max(0,st.session_state.integrity-5)

    if submit and st.session_state.result is None:
        st.session_state.attempts += 1
        success=False
        error=999.0

        if mid==1:
            error=float(np.mean(np.abs(np.array(answer)-np.array([p["amp"],p["freq"],p["phase"]]))))
            success=error<=.05
        elif mid==2:
            diff=abs(((answer[0]-p["delay"]+1/(2*p["freq"]))%(1/p["freq"]))-1/(2*p["freq"]))
            error=diff
            success=diff<=.01
        elif mid==3:
            error=abs(answer[0]-p["scale"])
            success=error<=.05
        elif mid==4:
            error=0 if answer[0]==1 else 1
            success=answer[0]==1
        elif mid==5:
            error=float(np.mean(np.abs(np.array(answer)-np.array([p["amp_a"],p["amp_b"]]))))
            success=error<=.05
        elif mid==6:
            target=np.array([p["scale"],p["delay"],1])
            aa=np.array(answer,dtype=float)
            error=(abs(aa[0]-target[0])+4*abs(aa[1]-target[1])+abs(aa[2]-target[2]))/6
            success=error<=.035
        elif mid==7:
            error=0 if answer[0]==p["correct"] else 1
            success=answer[0]==p["correct"]
        elif mid==8:
            target=np.sort(np.array(p["freqs"],dtype=float))
            aa=np.sort(np.array(answer,dtype=float))
            error=float(np.mean(np.abs(aa-target)))
            success=error<=2.0
        elif mid==9:
            error=float(np.mean(np.abs(np.array(answer)-np.array(p["target"]))))
            success=error<=.10
        elif mid in (10,11):
            target_p=p["pole"]; target_s=p["stable"]
            error=abs(answer[0]-target_p)*.6+abs(answer[1]-target_s)*.4
            success=error<=.08
        else:
            target=np.array([p["scale"],p["delay"],1,p["freq"],1],dtype=float)
            aa=np.array(answer,dtype=float)
            error=abs(aa[0]-target[0])*.25+abs(aa[1]-target[1])*2+abs(aa[2]-target[2])*.25+abs(aa[3]-target[3])*.25+abs(aa[4]-target[4])*.25
            success=error<=.08

        if success:
            elapsed=time.time()-st.session_state.mission_started
            earned=score_mission(error,elapsed,0,OPERATIONS[mid])
            st.session_state.score += earned
            st.session_state.completed.add(mid)
            st.session_state.result=(True,earned,error,elapsed)
            st.rerun()
        else:
            st.session_state.integrity=max(0,st.session_state.integrity-10)
            st.session_state.status_message=f"Not yet — LIVE MATCH {match:.1f}%"

    if "status_message" in st.session_state and st.session_state.status_message:
        st.error(st.session_state.status_message)

with g_col:
    # ========================================================
    # LIVE GRAPH
    # ========================================================
    if mid == 1:
        t=np.linspace(0,1,1000)
        target=sine(t,p["amp"],p["freq"],p["phase"])
        live=sine(t,*answer)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=target,name="REFERENCE",line=dict(color="#52D0C0",width=3)))
        fig.add_trace(go.Scatter(x=t,y=live,name="LIVE CANDIDATE",line=dict(color="#D99A52",dash="dash")))
        title="ESTABLISH CONTACT — LIVE SIGNAL MATCH"

    elif mid == 2:
        t=np.linspace(0,1,1000)
        ref=sine(t,1,p["freq"],0)
        target=sine(t-p["delay"],1,p["freq"],0)
        live=sine(t-answer[0],1,p["freq"],0)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=ref,name="REFERENCE",line=dict(color="#AEBDB5")))
        fig.add_trace(go.Scatter(x=t,y=target,name="RECEIVED",line=dict(color="#52D0C0")))
        fig.add_trace(go.Scatter(x=t,y=live,name="LIVE SHIFT",line=dict(color="#D99A52",dash="dash")))
        title="ALIGN TRANSMISSION — LIVE DELAY"

    elif mid == 3:
        t=np.linspace(0,1,1000)
        weak=sine(t,p["weak"],5,0)
        target=sine(t,p["target_amp"],5,0)
        live=weak*answer[0]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=weak,name="WEAK INPUT",line=dict(color="#AEBDB5")))
        fig.add_trace(go.Scatter(x=t,y=target,name="TARGET",line=dict(color="#52D0C0")))
        fig.add_trace(go.Scatter(x=t,y=live,name="LIVE OUTPUT",line=dict(color="#D99A52",dash="dash")))
        title="RESTORE STRENGTH — LIVE SCALING"

    elif mid == 4:
        orig=np.array(p["original"])
        target=orig[::-1]
        live=target if answer[0]==1 else orig
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=list(range(len(orig))),y=target,mode="markers+lines",name="TARGET",line=dict(color="#52D0C0"),marker=dict(size=9)))
        fig.add_trace(go.Scatter(x=list(range(len(orig))),y=live,mode="markers+lines",name="LIVE",line=dict(color="#D99A52",dash="dash"),marker=dict(size=8)))
        title="TIME REVERSAL — LIVE ORIENTATION"

    elif mid == 5:
        t=np.linspace(0,1,1000)
        target=sine(t,p["amp_a"],p["freq_a"],0)+sine(t,p["amp_b"],p["freq_b"],0)
        live=sine(t,answer[0],p["freq_a"],0)+sine(t,answer[1],p["freq_b"],0)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=target,name="ACTUAL MIX",line=dict(color="#52D0C0",width=3)))
        fig.add_trace(go.Scatter(x=t,y=live,name="LIVE MIX",line=dict(color="#D99A52",dash="dash")))
        title="THE MIXER — LIVE COMBINATION"

    elif mid == 6:
        t=np.linspace(0,1,1000)
        original=sine(t,1,5,0)
        target=sine(t-p["delay"],p["scale"],5,0)[::-1]
        live=sine(t-answer[1],answer[0],5,0)
        if answer[2]: live=live[::-1]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=original,name="ORIGINAL",line=dict(color="#AEBDB5")))
        fig.add_trace(go.Scatter(x=t,y=target,name="CORRUPTED",line=dict(color="#52D0C0")))
        fig.add_trace(go.Scatter(x=t,y=live,name="LIVE RECOVERY",line=dict(color="#D99A52",dash="dash")))
        title="MULTI-STAGE CORRUPTION — LIVE"

    elif mid == 7:
        amps=p["amps"]
        ens=[energy(sine(np.linspace(0,1,1000),a,5,0)) for a in amps]
        fig=go.Figure(go.Bar(x=["SIGNAL 1","SIGNAL 2","SIGNAL 3"],y=ens,marker_color=["#AEBDB5","#52D0C0","#D99A52"]))
        title="ENERGY CRISIS — LIVE SELECTION"

    elif mid == 8:
        fs=500;t=np.arange(0,1,1/fs)
        target=sum(a*np.sin(2*np.pi*f*t) for f,a in zip(p["freqs"],p["amps"]))
        live=sum(a*np.sin(2*np.pi*f*t) for f,a in zip(answer,p["amps"]))
        f1,m1=fft_components(target,fs); f2,m2=fft_components(live,fs)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=f1,y=m1,name="TARGET FFT",line=dict(color="#52D0C0")))
        fig.add_trace(go.Scatter(x=f2,y=m2,name="LIVE FFT",line=dict(color="#D99A52",dash="dash")))
        title="FFT — LIVE FREQUENCY RECOVERY"

    elif mid == 9:
        target=np.array(p["target"],dtype=float)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=list(range(len(target))),y=target,mode="markers+lines",name="CORRECT y[n]",line=dict(color="#52D0C0"),marker=dict(size=10)))
        fig.add_trace(go.Scatter(x=list(range(len(answer))),y=answer,mode="markers+lines",name="LIVE y[n]",line=dict(color="#D99A52",dash="dash"),marker=dict(size=9)))
        title="CONVOLUTION — LIVE OUTPUT"

    elif mid in (10,11):
        t=np.linspace(0,4,500)
        response=np.exp(answer[0]*t)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=response,name="LIVE IMPULSE RESPONSE",line=dict(color="#52D0C0",width=3)))
        title="SYSTEM RESPONSE — LIVE POLE ANALYSIS"

    else:
        t=np.linspace(0,1,1000)
        original=np.sin(2*np.pi*p["freq"]*t)
        target=p["scale"]*np.sin(2*np.pi*p["freq"]*(t-p["delay"]))
        target=target[::-1]
        live=answer[0]*np.sin(2*np.pi*answer[3]*(t-answer[1]))
        if answer[2]: live=live[::-1]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=t,y=original,name="ORIGINAL",line=dict(color="#AEBDB5")))
        fig.add_trace(go.Scatter(x=t,y=target,name="CORRUPTED TELEMETRY",line=dict(color="#52D0C0",width=3)))
        fig.add_trace(go.Scatter(x=t,y=live,name="LIVE RECOVERY",line=dict(color="#D99A52",dash="dash")))
        title="FINAL ARES-7 TELEMETRY — LIVE RECOVERY"

    fig.update_layout(
        title=title,
        paper_bgcolor="#111B20",
        plot_bgcolor="#0B1318",
        font=dict(color="#FFF2D0"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20,r=20,t=55,b=20),
        height=520,
        xaxis=dict(gridcolor="rgba(174,189,181,.12)"),
        yaxis=dict(gridcolor="rgba(174,189,181,.12)"),
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# MISSION RESULT
# ============================================================

if st.session_state.result:
    ok, earned, error, elapsed = st.session_state.result

    st.success(f"MISSION COMPLETE • +{earned} POINTS • ERROR {error:.4f}")

    if mid == 12:
        st.markdown(
            f'<div class="mission-card">'
            f'<div class="retro-title" style="font-size:28px;">ARES-7 <span style="color:#52D0C0;">RECOVERED</span></div>'
            f'<div class="retro-subtitle" style="margin-top:8px;">SIGNAL RESCUE COMPLETE</div>'
            f'<div style="margin-top:12px;">Final score: <b>{st.session_state.score}</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        if st.button("NEXT MISSION →", use_container_width=False):
            st.session_state.current += 1
            st.session_state.result = None
            st.session_state.mission_started = time.time()
            st.rerun()

st.markdown(
    '<div class="small-muted" style="margin-top:14px;">'
    'SIGNAL RESCUE // INTERACTIVE SIGNALS & SYSTEMS TRAINING SIMULATION</div>',
    unsafe_allow_html=True,
)
