from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from ..db import get_db
from ..models import Conversation, Message, utcnow
from ..security import current_user
from ..services import assistant, premium, profiles
from ..services import plans as plan_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    conversation_id: str | None = None


def own(db, user_id: str, conversation_id: str) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if not conv or conv.user_id != user_id:
        raise HTTPException(404, "Conversación no encontrada.")
    return conv


def msg_payload(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "cards": m.cards or [], "created_at": m.created_at.isoformat()}


@router.get("/status")
def status():
    return {"ai": assistant.ai_configured()}


@router.get("/conversations")
def conversations(user=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))
    return {"items": [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in rows]}


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, user=Depends(current_user), db=Depends(get_db)):
    conv = own(db, user.id, conversation_id)
    msgs = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.id))
    return {"id": conv.id, "title": conv.title, "messages": [msg_payload(m) for m in msgs]}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user=Depends(current_user), db=Depends(get_db)):
    conv = own(db, user.id, conversation_id)
    db.delete(conv)
    db.commit()
    return {"ok": True}


@router.delete("/conversations")
def delete_all(user=Depends(current_user), db=Depends(get_db)):
    db.execute(delete(Conversation).where(Conversation.user_id == user.id))
    db.commit()
    return {"ok": True}


@router.post("/message")
def message(body: MessageIn, user=Depends(current_user), db=Depends(get_db)):
    premium.consume(db, user.id, "ai")
    if body.conversation_id:
        conv = own(db, user.id, body.conversation_id)
    else:
        conv = Conversation(user_id=user.id, title=body.text.strip()[:60])
        db.add(conv)
        db.flush()
    history = [
        {"role": m.role, "content": m.content[:600]}
        for m in db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.desc()).limit(8))
    ][::-1]
    db.add(Message(conversation_id=conv.id, role="user", content=body.text.strip(), cards=[]))
    profile = profiles.load(db, user.id)
    profile["name"] = user.name
    result = assistant.respond(db, user, profile, body.text.strip(), history)
    answer = Message(conversation_id=conv.id, role="assistant", content=result["reply"], cards=result["cards"])
    db.add(answer)
    conv.updated_at = utcnow()
    db.flush()
    plan = None
    if result["plan_changed"]:
        fresh = profiles.load(db, user.id)
        plan = plan_service.payload(plan_service.current(db, user.id), fresh)
    out = {
        "conversation_id": conv.id,
        "message": msg_payload(answer),
        "plan": plan,
        "source": result["source"],
        "subscription": premium.status(db, user.id),
    }
    db.commit()
    return out
