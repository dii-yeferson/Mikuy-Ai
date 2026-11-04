import { ArrowUp, History, Mic, Plus, Sparkles, Square, Trash2, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/Chrome";
import Cover from "../components/Cover";
import { useRecipe } from "../components/RecipeSheet";
import Sheet from "../components/Sheet";
import { api, ApiError, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Card, ChatMessage, Plan, Subscription } from "../lib/types";

const SUGGESTIONS = [
  "Cambia el almuerzo de hoy por algo con pollo",
  "Hazme el menú más barato",
  "¿Cuántas calorías debo comer?",
  "No me gusta el hígado",
  "Mi presupuesto es 150 soles a la semana",
  "¿Cómo preparo un lomo saltado?",
];

type SR = { lang: string; interimResults: boolean; continuous: boolean; start: () => void; stop: () => void; onresult: ((e: any) => void) | null; onend: (() => void) | null; onerror: ((e: any) => void) | null };

export default function Assistant() {
  const { me, setMe, setPlan, toast, openPremium } = useStore();
  const { openRecipe } = useRecipe();
  const nav = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [cid, setCid] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [history, setHistory] = useState<{ id: string; title: string; updated_at: string }[] | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const rec = useRef<SR | null>(null);
  const bars = useRef<HTMLDivElement>(null);
  const stopWave = useRef<() => void>(() => {});

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);
  useEffect(() => () => { rec.current?.stop(); stopWave.current(); }, []);

  async function send(raw?: string) {
    const value = (raw ?? text).trim();
    if (!value || busy) return;
    feel("send");
    setText("");
    setBusy(true);
    const tmp: ChatMessage = { id: `u${Date.now()}`, role: "user", content: value, cards: [] };
    setMessages((m) => [...m, tmp, { id: "typing", role: "assistant", content: "", cards: [], pending: true }]);
    try {
      const r = await api.post<{ conversation_id: string; message: ChatMessage; plan: Plan | null; subscription: Subscription }>("/api/assistant/message", { text: value, conversation_id: cid });
      setCid(r.conversation_id);
      setMessages((m) => [...m.filter((x) => x.id !== "typing"), r.message]);
      if (r.plan) setPlan(r.plan);
      if (me) setMe({ ...me, subscription: r.subscription });
      feel("ai");
      if (me?.profile.voice_reply) speak(r.message.content);
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== "typing"));
      if (e instanceof ApiError && e.status === 402) openPremium();
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  function speak(t: string) {
    if (!("speechSynthesis" in window)) return;
    const u = new SpeechSynthesisUtterance(t.replace(/[*_#⚠️]/g, ""));
    u.lang = "es-PE";
    const voice = speechSynthesis.getVoices().find((v) => v.lang.startsWith("es"));
    if (voice) u.voice = voice;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }

  async function startWave() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ctx = new AudioContext();
      const an = ctx.createAnalyser();
      an.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(an);
      const data = new Uint8Array(an.frequencyBinCount);
      let raf = 0;
      const loop = () => {
        an.getByteFrequencyData(data);
        const els = bars.current?.children;
        if (els) for (let i = 0; i < els.length; i++) (els[i] as HTMLElement).style.height = `${10 + (data[i + 2] / 255) * 90}%`;
        raf = requestAnimationFrame(loop);
      };
      loop();
      stopWave.current = () => { cancelAnimationFrame(raf); stream.getTracks().forEach((t) => t.stop()); ctx.close(); };
    } catch {
      /* solo es la animación: el dictado sigue funcionando */
    }
  }

  function toggleMic() {
    if (listening) {
      rec.current?.stop();
      return;
    }
    if (!me?.subscription.premium) {
      toast("Hablar con Mikuy AI por voz es parte de Premium.", "info");
      openPremium();
      return;
    }
    const Ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Ctor) {
      toast("Tu navegador no permite dictado. Prueba en Chrome o Safari.", "error");
      return;
    }
    const r: SR = new Ctor();
    r.lang = "es-PE";
    r.interimResults = true;
    r.continuous = false;
    let finalText = "";
    r.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalText += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      setText((finalText + interim).trim());
    };
    r.onerror = (e: any) => {
      if (e.error === "not-allowed") toast("Permite el micrófono para hablar con Mikuy.", "error");
    };
    r.onend = () => {
      setListening(false);
      stopWave.current();
      if (finalText.trim()) send(finalText);
    };
    rec.current = r;
    feel("listen");
    setListening(true);
    startWave();
    r.start();
  }

  async function openHistory() {
    setShowHistory(true);
    const r = await api.get<{ items: { id: string; title: string; updated_at: string }[] }>("/api/assistant/conversations");
    setHistory(r.items);
  }
  async function loadConversation(id: string) {
    const r = await api.get<{ id: string; messages: ChatMessage[] }>(`/api/assistant/conversations/${id}`);
    setCid(r.id);
    setMessages(r.messages);
    setShowHistory(false);
  }
  async function removeConversation(id: string) {
    feel("remove");
    await api.del(`/api/assistant/conversations/${id}`);
    setHistory((h) => h?.filter((c) => c.id !== id) ?? null);
    if (id === cid) { setCid(null); setMessages([]); }
  }

  const limits = me?.subscription.limits;
  return (
    <>
      <TopBar
        sub={limits ? `${Math.max(0, limits.ai_per_day - limits.ai_used_today)} mensajes gratis hoy` : "Premium · sin límites"}
        title={<span className="row" style={{ gap: 8 }}><Sparkles className="gold" /> Mikuy AI</span>}
        right={
          <>
            <button className="icon-btn" aria-label="Nueva conversación" onClick={() => { feel("tap"); setCid(null); setMessages([]); }}><Plus size={18} /></button>
            <button className="icon-btn" aria-label="Historial" onClick={openHistory}><History size={18} /></button>
          </>
        }
      />
      <div className="chat">
        {messages.length === 0 && (
          <div className="stack stagger" style={{ paddingTop: 10 }}>
            <div className="center">
              <img src="/icons/logo-mark.webp" alt="" style={{ width: 84, animation: "float 5s ease-in-out infinite" }} />
              <h2 style={{ margin: "8px 0 4px", fontWeight: 1000 }}>¿Qué cocinamos?</h2>
              <p className="muted" style={{ margin: 0 }}>Cambio tu menú, ajusto el presupuesto, te doy recetas y cuido tu meta. Escríbeme o háblame.</p>
            </div>
            <div className="suggest">
              {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            {m.pending ? (
              <span className="typing"><i /><i /><i /></span>
            ) : (
              <>
                {m.content}
                {m.role === "assistant" && (
                  <button className="tiny muted" style={{ display: "inline-flex", marginLeft: 8, verticalAlign: "middle" }} aria-label="Escuchar" onClick={() => speak(m.content)}><Volume2 size={14} /></button>
                )}
                {m.cards.map((c, i) => <CardView key={i} card={c} onRecipe={(id) => openRecipe(id)} onNav={nav} />)}
              </>
            )}
          </div>
        ))}
        <div ref={bottom} />
      </div>

      <div className="composer glass">
        <button className={`mic ${listening ? "live" : ""}`} aria-label={listening ? "Detener" : "Hablar"} onClick={toggleMic}>
          {listening ? <Square size={18} fill="currentColor" /> : <Mic size={20} />}
        </button>
        {listening && !text ? (
          <div className="wave" ref={bars}>{Array.from({ length: 22 }, (_, i) => <i key={i} />)}</div>
        ) : (
          <textarea
            rows={1}
            placeholder={listening ? "Escuchando…" : "Escribe a Mikuy…"}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
        )}
        <button className="send" aria-label="Enviar" disabled={!text.trim() || busy} onClick={() => send()}><ArrowUp size={22} /></button>
      </div>

      <Sheet open={showHistory} onClose={() => setShowHistory(false)} title="Conversaciones">
        <div className="list">
          {history?.length ? history.map((c) => (
            <div key={c.id} className="list-row">
              <button className="grow" style={{ textAlign: "left" }} onClick={() => loadConversation(c.id)}>
                <div className="bold ellipsis">{c.title}</div>
                <div className="tiny muted">{new Date(c.updated_at + "Z").toLocaleString("es-PE", { dateStyle: "medium", timeStyle: "short" })}</div>
              </button>
              <button className="icon-btn" aria-label="Borrar" onClick={() => removeConversation(c.id)}><Trash2 size={16} /></button>
            </div>
          )) : <div className="list-row muted">{history ? "Aún no hay conversaciones." : "Cargando…"}</div>}
        </div>
      </Sheet>
    </>
  );
}

function CardView({ card, onRecipe, onNav }: { card: Card; onRecipe: (id: string) => void; onNav: (p: string) => void }) {
  if (card.type === "swap") {
    return (
      <button className="ai-card" onClick={() => onRecipe(card.to.id)}>
        <Cover recipe={card.to} />
        <div className="grow">
          <div className="tiny gold bold">{card.meal.toUpperCase()} · {card.day}</div>
          <div className="bold">{card.to.name}</div>
          <div className="tiny muted">antes: {card.from.name}</div>
        </div>
      </button>
    );
  }
  if (card.type === "recipe") {
    return (
      <button className="ai-card" onClick={() => onRecipe(card.recipe.id)}>
        <Cover recipe={card.recipe} />
        <div className="grow">
          <div className="bold">{card.recipe.name}</div>
          <div className="tiny muted">{card.recipe.kcal} kcal · {card.recipe.minutes} min · {soles(card.recipe.cost)}</div>
        </div>
      </button>
    );
  }
  if (card.type === "savings") {
    return (
      <button className="ai-card" onClick={() => onNav("/plan")}>
        <span style={{ fontSize: 28 }}>💰</span>
        <div className="grow">
          <div className="bold">Ahorras {soles(card.before - card.after)}</div>
          <div className="tiny muted">{soles(card.before)} → {soles(card.after)} esta semana</div>
        </div>
      </button>
    );
  }
  if (card.type === "shopping") {
    return (
      <button className="ai-card" onClick={() => onNav("/compras")}>
        <span style={{ fontSize: 28 }}>🛒</span>
        <div className="grow">
          <div className="bold">Lista de compras · {soles(card.total)}</div>
          <div className="tiny muted">{card.count} productos · falta {soles(card.pending)}</div>
        </div>
      </button>
    );
  }
  if (card.type === "plan") {
    return (
      <button className="ai-card" onClick={() => onNav("/plan")}>
        <span style={{ fontSize: 28 }}>📅</span>
        <div className="grow bold">Ver mi menú nuevo</div>
      </button>
    );
  }
  if (card.type === "profile") {
    return <div className="ai-card"><span style={{ fontSize: 24 }}>✅</span><div className="small">Preferencias actualizadas</div></div>;
  }
  return null;
}
