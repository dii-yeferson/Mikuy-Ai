from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from . import coach_insights
from .coach_app_context import app_reply, records_reply
from .coach_pipeline import run_coach
from .coach_plans import linked, propose
from .coach_response import DISCLAIMER, checked_citations
from .config import settings
from .conversations import owned, resolve
from .db import get_db
from .models import Conversation, Entry, Message, Plan, Profile, utcnow
from .nvidia import configured, has_consent, provider_config
from .safety import check_question, contains, validate_answer
from .schemas import CoachIn, normalize
from .security import current_user
from .services import lock_user, profile_for, quota
from .shopping_service import shopping_response

router = APIRouter(prefix="/coach", tags=["Coach"])


def present(r, db=None):
    return dict(
        proposal=linked(db, r) if db is not None else None,
        insight=coach_insights.linked(db, r) if db is not None else None,
        id=r.id,
        conversation_id=r.conversation_id,
        question=r.question,
        answer=r.answer,
        sources=r.sources or [],
        mode=r.mode or "ia",
        date=r.created_at.isoformat(),
    )


@router.get("")
def history(conversation_id: str | None = None, user=Depends(current_user), db=Depends(get_db)):
    if conversation_id:
        owned(db, user, conversation_id)
    query = (
        select(Message)
        .join(Conversation)
        .where(Message.user_id == user.id, Conversation.delete_after.is_(None))
    )
    if conversation_id:
        query = query.where(Message.conversation_id == conversation_id)
    return [present(r, db) for r in db.scalars(query.order_by(Message.created_at))]


@router.get("/status")
def status(user=Depends(current_user), db=Depends(get_db)):
    p = profile_for(db, user)
    return dict(
        provider=provider_config()[0],
        ai=configured(),
        disclaimer=DISCLAIMER,
        consent=has_consent(p),
        intro_seen=p.settings.coach_intro_seen,
    )


class ConsentIn(BaseModel):
    consent: bool


@router.put("/consent")
def consent(data: ConsentIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    p = profile_for(db, user)
    p.settings.coach_consent = data.consent
    p.settings.coach_consent_provider = settings().ai_provider
    p.settings.coach_intro_seen = True
    row = db.get(Profile, user.id)
    row.data = p.model_dump(mode="json")
    db.commit()
    return dict(
        provider=provider_config()[0],
        ai=configured(),
        consent=data.consent,
        intro_seen=True,
        disclaimer=DISCLAIMER,
    )


def _check(result, profile, cards, question):
    validate_answer(result.answer, profile)
    checked_citations(result, cards)
    first = normalize(result.answer.split("\n")[0])
    if first.startswith(("considerando tu perfil", "esto dicen las fuentes")):
        raise ValueError("La respuesta debe contestar la pregunta antes de listar evidencia")
    foods = [f for f in ("pollo", "mango", "arroz", "gaseosa", "sal") if contains(question, f)]
    if foods and not any(contains(first, food) for food in foods):
        raise ValueError("La respuesta no aborda el alimento consultado")
    if foods and cards and not result.sources and not result.answer.rstrip().endswith("?"):
        raise ValueError("La orientación nutricional debe citar su respaldo")


@router.post("", status_code=201)
def ask(data: CoachIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    conversation = resolve(db, user, data.conversation_id, data.question)
    conversation.updated_at = utcnow()
    if conversation.title == "Nuevo chat":
        conversation.title = data.question[:100]
    redirect = check_question(data.question)
    if redirect:
        row = Message(
            user_id=user.id,
            conversation_id=conversation.id,
            question=data.question,
            answer=redirect,
            sources=[],
            mode="seguridad",
        )
        db.add(row)
        db.commit()
        return present(row)
    quota(db, user, "coach")
    profile = profile_for(db, user)
    proposal_question = data.question
    last = db.scalar(
        select(Message)
        .where(Message.user_id == user.id, Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    recent = list(
        db.scalars(
            select(Message)
            .where(Message.user_id == user.id, Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(20)
        )
    )
    guard = coach_insights.clinical_guard(data.question, profile, recent)
    insight = None if guard else coach_insights.handle(db, user, profile, data.question, recent)
    if guard or insight:
        row = Message(
            user_id=user.id,
            conversation_id=conversation.id,
            question=data.question,
            answer=guard or insight["answer"],
            sources=[] if guard else insight["sources"],
            mode="seguridad" if guard else "calculo",
        )
        db.add(row)
        db.flush()
        if insight:
            db.add(
                Entry(
                    user_id=user.id,
                    kind="coach_insight",
                    data={
                        "message_id": row.id,
                        "view": insight["view"],
                        "private": insight["private"],
                    },
                )
            )
        quota(db, user, "coach", consume=True)
        db.commit()
        return present(row, db)
    if (
        last
        and last.answer.startswith(("¿Cuántos soles", "¿Qué comidas"))
        and len(data.question) < 80
    ):
        proposal_question = last.question + ". " + data.question
    proposal = propose(proposal_question, profile, data.consent or has_consent(profile))
    if proposal:
        row = Message(
            user_id=user.id,
            conversation_id=conversation.id,
            question=data.question,
            answer=proposal["answer"],
            sources=[],
            mode="catalogo",
        )
        db.add(row)
        db.flush()
        if proposal["doc"]:
            db.add(
                Entry(
                    user_id=user.id,
                    kind="coach_proposal",
                    data={**proposal["doc"], "message_id": row.id},
                )
            )
        quota(db, user, "coach", consume=True)
        db.commit()
        return present(row, db)
    plan = db.scalar(
        select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at.desc()).limit(1)
    )
    previous = list(
        reversed(
            list(
                db.scalars(
                    select(Message)
                    .where(Message.user_id == user.id, Message.conversation_id == conversation.id)
                    .order_by(Message.created_at.desc())
                    .limit(6)
                )
            )
        )
    )
    shopping = shopping_response(db, plan) if plan else None
    result = app_reply(data.question, profile, plan, shopping, user, previous)
    if not result:
        result = records_reply(db, user, data.question)
    if not result:
        context = dict(
            budget=profile.budget,
            shopping=shopping,
            plan={
                "start_date": plan.data["start_date"],
                "cost": plan.data["cost"],
                "meals": [
                    {k: m[k] for k in ("name", "day", "meal", "nutrition") if k in m}
                    for m in plan.data["meals"]
                ],
            }
            if plan
            else None,
            guide="Menú: /menu; Compras: /compras; Diario: /plan; Progreso: /progreso; Comunidad: /social; Ajustes: /ajustes",
            memories=profile.settings.coach_memories,
        )
        result = run_coach(
            data.question,
            profile,
            plan,
            previous,
            data.consent or has_consent(profile),
            app_context=context,
        )
    answer, sources, mode = result.answer, result.sources, result.mode
    row = Message(
        user_id=user.id,
        conversation_id=conversation.id,
        question=data.question,
        answer=answer,
        sources=sources,
        mode=mode,
    )
    db.add(row)
    quota(db, user, "coach", consume=True)
    db.commit()
    return present(row)
