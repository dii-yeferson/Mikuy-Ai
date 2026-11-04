import { useRef, useState, type FormEvent } from "react";
import {
  Heart,
  ThumbsUp,
  PartyPopper,
  MessageCircle,
  ChevronDown,
  Send,
  X,
} from "lucide-react";
import { api, body } from "../api";
import { useResource } from "../hooks";
import { ErrorBox, Loading } from "./ui";

type Reaction = "like" | "heart" | "celebrate";
type Reactions = {
  my_reaction: Reaction | null;
  reactions: Record<Reaction, number>;
};
type Post = Reactions & { id: string; comments: number };
type Comment = {
  id: string;
  text: string;
  name: string;
  date: string;
  parent_id: string | null;
  can_delete: boolean;
};
const choices = [
  { kind: "like", label: "Me gusta", icon: ThumbsUp },
  { kind: "heart", label: "Me encanta", icon: Heart },
  { kind: "celebrate", label: "Celebrar", icon: PartyPopper },
] as const;

export function SocialDiscussion({
  post,
  onPatch,
}: {
  post: Post;
  onPatch: (patch: Partial<Post>) => void;
}) {
  const [open, setOpen] = useState(false),
    [picker, setPicker] = useState(false),
    [text, setText] = useState(""),
    [reply, setReply] = useState<Comment | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  const lock = useRef(false);
  const url = "/community/posts/" + post.id;
  const data = useResource<Comment[]>(open ? url + "/comments" : null);
  const selected =
    choices.find((c) => c.kind === post.my_reaction) || choices[0];
  const SelectedIcon = selected.icon;
  const count = Object.values(post.reactions).reduce((a, b) => a + b, 0);
  async function change(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const react = (kind: Reaction) =>
    change(async () => {
      onPatch(
        await api<Reactions>(
          url + "/reaction",
          body("PUT", { kind: post.my_reaction === kind ? null : kind }),
        ),
      );
      setPicker(false);
    });
  const refreshComments = async () => {
    const comments = await api<Comment[]>(url + "/comments");
    data.setData(comments);
    onPatch({ comments: comments.length });
  };
  function send(e?: FormEvent) {
    e?.preventDefault();
    if (!text.trim()) return;
    void change(async () => {
      await api(
        url + "/comments",
        body("POST", { text: text.trim(), parent_id: reply?.id ?? null }),
      );
      setText("");
      setReply(null);
      await refreshComments();
    });
  }
  const renderComment = (c: Comment, nested = false) => (
    <div
      key={c.id}
      className={"social-comment-row" + (nested ? " is-reply" : "")}
    >
      <span className="social-avatar" aria-hidden="true">
        {c.name.slice(0, 1).toUpperCase()}
      </span>
      <div className="social-comment-body">
        <div className="social-comment-bubble">
          <strong>{c.name}</strong>
          <p>{c.text}</p>
        </div>
        <div className="social-comment-meta">
          <time dateTime={c.date}>
            {new Date(c.date).toLocaleDateString("es-PE", {
              day: "numeric",
              month: "short",
            })}
          </time>
          <button
            disabled={busy}
            onClick={() => {
              setReply(c);
              input.current?.focus();
            }}
          >
            Responder
          </button>
          {c.can_delete && (
            <button
              disabled={busy}
              onClick={() =>
                change(async () => {
                  await api("/community/comments/" + c.id, body("DELETE"));
                  if (reply?.id === c.id) setReply(null);
                  await refreshComments();
                })
              }
            >
              Eliminar comentario
            </button>
          )}
        </div>
      </div>
    </div>
  );
  const ids = new Set(data.data?.map((c) => c.id));
  return (
    <div className="social-discussion">
      <div className="social-counts">
        <span>
          {count > 0 ? (
            <>
              <Heart size={13} /> {count}{" "}
              {count === 1 ? "reacción" : "reacciones"}
            </>
          ) : (
            "Sé el primero en reaccionar"
          )}
        </span>
        <button
          aria-label={
            "Comentarios (" + (data.data?.length ?? post.comments) + ")"
          }
          onClick={() => setOpen(!open)}
        >
          {data.data?.length ?? post.comments} comentarios
        </button>
      </div>
      <div className="social-feed-actions">
        <div className="social-reaction-control">
          <button
            aria-label={selected.label}
            aria-pressed={!!post.my_reaction}
            disabled={busy}
            onClick={() => react(selected.kind)}
          >
            <SelectedIcon size={18} />
            <span>{selected.label}</span>
          </button>
          <button
            aria-label="Elegir reacción"
            aria-expanded={picker}
            onClick={() => setPicker(!picker)}
          >
            <ChevronDown size={14} />
          </button>
          {picker && (
            <div
              className="social-reaction-picker"
              role="group"
              aria-label="Reacciones"
            >
              {choices.map(({ kind, label, icon: Icon }) => (
                <button
                  key={kind}
                  title={label}
                  aria-label={label}
                  aria-pressed={post.my_reaction === kind}
                  disabled={busy}
                  onClick={() => react(kind)}
                >
                  <Icon size={20} />
                  <small>{label}</small>
                </button>
              ))}
              <button
                aria-label="Cerrar reacciones"
                onClick={() => setPicker(false)}
              >
                <X size={14} />
              </button>
            </div>
          )}
        </div>
        <button
          onClick={() => {
            setOpen(true);
            setTimeout(() => input.current?.focus(), 0);
          }}
        >
          <MessageCircle size={18} />
          Comentar
        </button>
      </div>
      {open && (
        <div className="social-comment-thread">
          {data.loading && <Loading />}
          {data.data
            ?.filter((c) => !c.parent_id || !ids.has(c.parent_id))
            .map((c) => (
              <div key={c.id}>
                {renderComment(c)}
                {data.data
                  ?.filter((r) => r.parent_id === c.id)
                  .map((r) => renderComment(r, true))}
              </div>
            ))}
          {reply && (
            <div className="social-replying">
              Respondiendo a {reply.name}
              <button
                aria-label="Cancelar respuesta"
                onClick={() => setReply(null)}
              >
                <X size={14} />
              </button>
            </div>
          )}
          <form className="social-inline-composer" onSubmit={send}>
            <textarea
              ref={input}
              rows={1}
              aria-label={reply ? "Escribir respuesta" : "Escribir comentario"}
              placeholder={
                reply ? "Escribe tu respuesta…" : "Escribe un comentario…"
              }
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
              required
              disabled={busy}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <button
              type="submit"
              aria-label={reply ? "Enviar respuesta" : "Enviar comentario"}
              disabled={busy || !text.trim()}
            >
              <Send size={18} />
            </button>
          </form>
          <button
            className="social-close-comments"
            onClick={() => setOpen(false)}
          >
            Ocultar comentarios
          </button>
        </div>
      )}
      <ErrorBox error={error || data.error} />
    </div>
  );
}
