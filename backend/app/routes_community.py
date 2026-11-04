from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import delete, func, select

from .db import get_db
from .models import CommunityGroup, Entry, GroupMember, PostComment, PostReaction, Profile, User
from .schemas import Strict
from .security import current_user
from .services import lock_user, profile_for

router = APIRouter(prefix="/community", tags=["Comunidad"])


class GroupIn(Strict):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)


class PostIn(Strict):
    text: str = Field(min_length=1, max_length=2000)
    group_id: str | None = Field(default=None, max_length=36)


class CommentIn(Strict):
    text: str = Field(min_length=1, max_length=2000)
    parent_id: str | None = Field(default=None, max_length=36)


class ReactionIn(Strict):
    kind: Literal["like", "heart", "celebrate"] | None = None


def public_required(db, user):
    if not profile_for(db, user).settings.public_profile:
        raise HTTPException(
            403, "Activa tu perfil público para participar. Tus datos de salud siguen privados."
        )


def get_group(db, id):
    group = db.get(CommunityGroup, id)
    if not group:
        raise HTTPException(404, "No se encontró la comunidad.")
    return group


def get_post(db, id):
    row = db.get(Entry, id)
    p = db.get(Profile, row.user_id) if row else None
    if (
        not row
        or row.kind != "publicacion"
        or not p
        or not p.data.get("settings", {}).get("public_profile")
    ):
        raise HTTPException(404, "No se encontró la publicación.")
    return row


def member_required(db, user, group_id):
    if group_id and not db.get(GroupMember, (group_id, user.id)):
        raise HTTPException(403, "Únete a esta comunidad para participar.")


def group_data(db, g, user):
    return dict(
        id=g.id,
        name=g.name,
        description=g.description,
        owner_id=g.owner_id,
        joined=bool(db.get(GroupMember, (g.id, user.id))),
        members=db.scalar(
            select(func.count()).select_from(GroupMember).where(GroupMember.group_id == g.id)
        ),
    )


def reaction_data(db, post, user):
    rows = list(db.scalars(select(PostReaction).where(PostReaction.post_id == post.id)))
    return dict(
        reactions={k: sum(r.kind == k for r in rows) for k in ("like", "heart", "celebrate")},
        my_reaction=next((r.kind for r in rows if r.user_id == user.id), None),
    )


@router.get("")
def community(group_id: str | None = None, user=Depends(current_user), db=Depends(get_db)):
    if group_id:
        get_group(db, group_id)
    people = [
        dict(id=u.id, name=u.name, description=p.data.get("settings", {}).get("description", ""))
        for u, p in db.execute(select(User, Profile).join(Profile, User.id == Profile.user_id))
        if p.data.get("settings", {}).get("public_profile")
    ]
    public_ids = [p["id"] for p in people]
    query = select(Entry).where(Entry.kind == "publicacion", Entry.user_id.in_(public_ids))
    if group_id:
        query = query.where(Entry.group_id == group_id)
    posts = []
    for row in db.scalars(query.order_by(Entry.created_at.desc()).limit(50)):
        posts.append(
            dict(
                id=row.id,
                user_id=row.user_id,
                text=row.data["text"],
                date=row.created_at.isoformat(),
                group_id=row.group_id,
                comments=db.scalar(
                    select(func.count())
                    .select_from(PostComment)
                    .where(PostComment.post_id == row.id, PostComment.user_id.in_(public_ids))
                ),
                **reaction_data(db, row, user),
            )
        )
    groups = [
        group_data(db, g, user)
        for g in db.scalars(
            select(CommunityGroup).order_by(CommunityGroup.created_at.desc()).limit(100)
        )
    ]
    return dict(people=people, posts=posts, groups=groups)


@router.post("/groups", status_code=201)
def create_group(data: GroupIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    public_required(db, user)
    if (
        db.scalar(
            select(func.count())
            .select_from(CommunityGroup)
            .where(CommunityGroup.owner_id == user.id)
        )
        >= 20
    ):
        raise HTTPException(422, "Puedes administrar hasta 20 comunidades.")
    g = CommunityGroup(owner_id=user.id, **data.model_dump())
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user.id))
    db.commit()
    return group_data(db, g, user)


@router.put("/groups/{id}")
def edit_group(id: str, data: GroupIn, user=Depends(current_user), db=Depends(get_db)):
    g = get_group(db, id)
    if g.owner_id != user.id:
        raise HTTPException(403, "Solo el creador puede editar esta comunidad.")
    g.name = data.name
    g.description = data.description
    db.commit()
    return group_data(db, g, user)


@router.delete("/groups/{id}", status_code=204)
def delete_group(id: str, user=Depends(current_user), db=Depends(get_db)):
    g = get_group(db, id)
    if g.owner_id != user.id:
        raise HTTPException(403, "Solo el creador puede eliminar esta comunidad.")
    db.delete(g)
    db.commit()


@router.put("/groups/{id}/membership")
def join_group(id: str, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    public_required(db, user)
    g = get_group(db, id)
    if not db.get(GroupMember, (id, user.id)):
        db.add(GroupMember(group_id=id, user_id=user.id))
    db.commit()
    return group_data(db, g, user)


@router.delete("/groups/{id}/membership", status_code=204)
def leave_group(id: str, user=Depends(current_user), db=Depends(get_db)):
    g = get_group(db, id)
    if g.owner_id == user.id:
        raise HTTPException(422, "Eres el creador; puedes eliminar la comunidad desde sus ajustes.")
    db.execute(
        delete(GroupMember).where(GroupMember.group_id == id, GroupMember.user_id == user.id)
    )
    db.commit()


@router.post("/posts", status_code=201)
def publish(data: PostIn, user=Depends(current_user), db=Depends(get_db)):
    public_required(db, user)
    if data.group_id:
        get_group(db, data.group_id)
        member_required(db, user, data.group_id)
    row = Entry(
        user_id=user.id, kind="publicacion", group_id=data.group_id, data={"text": data.text}
    )
    db.add(row)
    db.commit()
    return dict(id=row.id, text=data.text)


@router.delete("/posts/{id}", status_code=204)
def delete_post(id: str, user=Depends(current_user), db=Depends(get_db)):
    row = get_post(db, id)
    owner = get_group(db, row.group_id).owner_id if row.group_id else None
    if user.id not in (row.user_id, owner):
        raise HTTPException(
            403, "Solo el autor o el creador del grupo puede eliminar esta publicación."
        )
    db.delete(row)
    db.commit()


@router.put("/posts/{id}/reaction")
def react(id: str, data: ReactionIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    public_required(db, user)
    post = get_post(db, id)
    member_required(db, user, post.group_id)
    row = db.get(PostReaction, (id, user.id))
    if data.kind is None:
        if row:
            db.delete(row)
    elif row:
        row.kind = data.kind
    else:
        db.add(PostReaction(post_id=id, user_id=user.id, kind=data.kind))
    db.commit()
    return reaction_data(db, post, user)


@router.get("/posts/{id}/comments")
def comments(id: str, user=Depends(current_user), db=Depends(get_db)):
    post = get_post(db, id)
    owner = get_group(db, post.group_id).owner_id if post.group_id else None
    return [
        dict(
            id=c.id,
            parent_id=c.parent_id,
            text=c.text,
            user_id=u.id,
            name=u.name,
            date=c.created_at.isoformat(),
            can_delete=user.id in (c.user_id, owner),
        )
        for c, u, p in db.execute(
            select(PostComment, User, Profile)
            .join(User, User.id == PostComment.user_id)
            .join(Profile, Profile.user_id == User.id)
            .where(PostComment.post_id == id)
            .order_by(PostComment.created_at)
            .limit(100)
        )
        if p.data.get("settings", {}).get("public_profile")
    ]


@router.post("/posts/{id}/comments", status_code=201)
def comment(id: str, data: CommentIn, user=Depends(current_user), db=Depends(get_db)):
    public_required(db, user)
    post = get_post(db, id)
    member_required(db, user, post.group_id)
    if data.parent_id:
        parent = db.get(PostComment, data.parent_id)
        p = db.get(Profile, parent.user_id) if parent else None
        if (
            not parent
            or parent.post_id != id
            or not p
            or not p.data.get("settings", {}).get("public_profile")
        ):
            raise HTTPException(404, "No se encontró el comentario al que respondes.")
        # Keep one readable reply level, including replies to replies.
        parent_id = parent.parent_id or parent.id
    else:
        parent_id = None
    c = PostComment(post_id=id, user_id=user.id, text=data.text, parent_id=parent_id)
    db.add(c)
    db.commit()
    return dict(id=c.id, text=c.text)


@router.delete("/comments/{id}", status_code=204)
def delete_comment(id: str, user=Depends(current_user), db=Depends(get_db)):
    c = db.get(PostComment, id)
    if not c:
        raise HTTPException(404, "No se encontró el comentario.")
    post = get_post(db, c.post_id)
    owner = get_group(db, post.group_id).owner_id if post.group_id else None
    if user.id not in (c.user_id, owner):
        raise HTTPException(403, "No puedes eliminar este comentario.")
    db.delete(c)
    db.commit()
