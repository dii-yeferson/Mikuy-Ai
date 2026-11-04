/* Mikuy · Feel: sonidos suaves sintetizados (Web Audio), vibración y animaciones de resorte.
 * Todos los sonidos se crean en el momento: sin archivos ni sonidos de terceros. Familia "cálida":
 * madera suave, seda y campanitas doradas, siempre a volumen bajo y sin ataques duros.
 * Respeta Ajustes → Sonidos / Vibración, el modo silencio del iPhone y "Reducir movimiento".
 */

type Kind =
  | "tap" | "select" | "open" | "close" | "toggleOn" | "toggleOff" | "success" | "celebrate"
  | "remove" | "check" | "uncheck" | "notify" | "warn" | "error" | "ai" | "listen" | "send";

const prefs = { sounds: true, haptics: true };
export function setFeelPrefs(p: Partial<typeof prefs>) {
  Object.assign(prefs, p);
}

let ctx: AudioContext | null = null;
let out: GainNode | null = null;
let verb: GainNode | null = null;

try {
  const nav = navigator as Navigator & { audioSession?: { type: string } };
  if (nav.audioSession) nav.audioSession.type = "ambient";
} catch {
  /* sin soporte */
}

function audio(): AudioContext | null {
  if (ctx) {
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    return ctx;
  }
  const AC = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AC) return null;
  try {
    ctx = new AC({ latencyHint: "interactive" });
    const soft = ctx.createBiquadFilter();
    soft.type = "lowpass";
    soft.frequency.value = 4200;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -22;
    comp.ratio.value = 4;
    out = ctx.createGain();
    out.gain.value = 0.4;
    out.connect(soft).connect(comp).connect(ctx.destination);
    const len = Math.floor(ctx.sampleRate * 0.8);
    const ir = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = ir.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3);
    }
    const conv = ctx.createConvolver();
    conv.buffer = ir;
    verb = ctx.createGain();
    verb.gain.value = 0.25;
    verb.connect(conv).connect(comp);
  } catch {
    ctx = null;
  }
  return ctx;
}
if (typeof window !== "undefined") {
  const unlock = () => {
    audio();
    window.removeEventListener("pointerdown", unlock, true);
  };
  window.addEventListener("pointerdown", unlock, true);
}

function tone(freq: number, o: { at?: number; dur?: number; gain?: number; to?: number; attack?: number; wet?: number; type?: OscillatorType } = {}) {
  const a = audio();
  if (!a || !out) return;
  const { at = 0, dur = 0.18, gain = 0.03, to, attack = 0.012, wet = 0, type = "sine" } = o;
  const t = a.currentTime + at;
  const osc = a.createOscillator();
  const g = a.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, t + Math.min(dur, 0.14));
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(gain, t + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  osc.connect(g).connect(out);
  if (wet && verb) {
    const s = a.createGain();
    s.gain.value = wet;
    g.connect(s).connect(verb);
  }
  osc.start(t);
  osc.stop(t + dur + 0.05);
}

let noise: AudioBuffer | null = null;
function breath(from: number, to: number, o: { at?: number; dur?: number; gain?: number; q?: number; wet?: number } = {}) {
  const a = audio();
  if (!a || !out) return;
  const { at = 0, dur = 0.14, gain = 0.016, q = 0.8, wet = 0.12 } = o;
  if (!noise) {
    noise = a.createBuffer(1, a.sampleRate * 0.5, a.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  const t = a.currentTime + at;
  const src = a.createBufferSource();
  const f = a.createBiquadFilter();
  const g = a.createGain();
  src.buffer = noise;
  f.type = "bandpass";
  f.Q.value = q;
  f.frequency.setValueAtTime(from, t);
  f.frequency.exponentialRampToValueAtTime(to, t + dur);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(gain, t + Math.min(0.03, dur / 3));
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(f).connect(g).connect(out);
  if (wet && verb) {
    const s = a.createGain();
    s.gain.value = wet;
    g.connect(s).connect(verb);
  }
  src.start(t);
  src.stop(t + dur + 0.05);
}

// Notas en Re mayor: D5 587 · F#5 740 · A5 880 · D6 1175 (campanitas doradas)
const bells = (fs: number[], o: { at?: number; gain?: number; dur?: number; step?: number } = {}) =>
  fs.forEach((f, i) => tone(f, { at: (o.at ?? 0) + i * (o.step ?? 0.07), gain: o.gain ?? 0.008, dur: o.dur ?? 0.6, attack: 0.03, wet: 0.5 }));

const SOUNDS: Record<Kind, () => void> = {
  tap: () => breath(260, 520, { dur: 0.09, gain: 0.016, wet: 0.04 }),
  select: () => breath(900, 1600, { dur: 0.1, gain: 0.012 }),
  open: () => breath(320, 950, { dur: 0.22, gain: 0.013, wet: 0.25 }),
  close: () => breath(950, 320, { dur: 0.18, gain: 0.01 }),
  toggleOn: () => { breath(500, 1300, { dur: 0.14, gain: 0.011 }); tone(587, { dur: 0.18, gain: 0.006, to: 880, attack: 0.03 }); },
  toggleOff: () => { breath(1300, 500, { dur: 0.14, gain: 0.01 }); tone(880, { dur: 0.18, gain: 0.005, to: 587, attack: 0.03 }); },
  check: () => { tone(880, { dur: 0.16, gain: 0.012, attack: 0.01, wet: 0.3 }); tone(1175, { at: 0.06, dur: 0.22, gain: 0.008, wet: 0.4 }); },
  uncheck: () => tone(740, { dur: 0.14, gain: 0.009, to: 587 }),
  success: () => { breath(450, 1700, { dur: 0.24, gain: 0.013, wet: 0.3 }); bells([587, 880], { at: 0.05, gain: 0.009 }); },
  celebrate: () => { breath(400, 2200, { dur: 0.42, gain: 0.015, wet: 0.35 }); bells([1175, 1480, 1760, 2349], { at: 0.08, gain: 0.004, step: 0.09 }); bells([587, 880], { at: 0.1, gain: 0.006, dur: 1.1 }); },
  remove: () => breath(1700, 280, { dur: 0.22, gain: 0.02, wet: 0.2 }),
  notify: () => bells([880, 1175], { gain: 0.01, step: 0.12 }),
  warn: () => bells([740, 587], { gain: 0.011, step: 0.14, dur: 0.5 }),
  error: () => { tone(220, { dur: 0.2, gain: 0.028, attack: 0.025 }); tone(196, { at: 0.16, dur: 0.24, gain: 0.028, attack: 0.025 }); },
  ai: () => { breath(700, 2200, { dur: 0.3, gain: 0.011, q: 0.6, wet: 0.45 }); bells([1175], { at: 0.12, gain: 0.005 }); },
  listen: () => { tone(587, { dur: 0.16, gain: 0.01, to: 880, attack: 0.02, wet: 0.3 }); },
  send: () => breath(400, 1500, { dur: 0.16, gain: 0.014, wet: 0.15 }),
};

const HAPTICS: Partial<Record<Kind, number | number[]>> = {
  tap: 8, select: 6, toggleOn: 10, toggleOff: 10, check: 12, uncheck: 6, success: [12, 60, 16],
  celebrate: [12, 50, 12, 50, 22], remove: 14, notify: [10, 40, 10], warn: [18, 60, 18], error: [28, 50, 28],
  ai: 6, listen: 10, send: 8,
};
const GAP: Partial<Record<Kind, number>> = { select: 80, tap: 100, close: 180 };
const last: Partial<Record<Kind, number>> = {};

export function feel(kind: Kind) {
  const now = performance.now();
  if (now - (last[kind] ?? 0) < (GAP[kind] ?? 110)) return;
  last[kind] = now;
  if (prefs.haptics && typeof navigator.vibrate === "function" && HAPTICS[kind]) {
    try {
      navigator.vibrate(HAPTICS[kind]!);
    } catch {
      /* sin vibración */
    }
  }
  if (prefs.sounds && document.visibilityState !== "hidden") {
    try {
      SOUNDS[kind]();
    } catch {
      /* sin audio */
    }
  }
}

export function pulse(el: Element | null, cls = "feel-pop") {
  if (!el || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  el.classList.remove(cls);
  void (el as HTMLElement).offsetWidth;
  el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), 650);
}
