import json

import httpx
from fastapi import HTTPException
from pydantic import Field

from .config import settings
from .schemas import Strict


class Selection(Strict):
    recipe_ids: list[str] = Field(min_length=21, max_length=21)


class CoachAnswer(Strict):
    answer: str = Field(min_length=2, max_length=6000)
    sources: list[str] = Field(default_factory=list, max_length=6)


def provider_config():
    cfg = settings()
    if cfg.ai_provider == "groq":
        return "Groq", cfg.groq_api_key, cfg.groq_model, "https://api.groq.com/openai/v1"
    return "NVIDIA", cfg.nvidia_api_key, cfg.nvidia_model, cfg.nvidia_base_url


def role_model(role):
    cfg = settings()
    return getattr(cfg, cfg.ai_provider + "_" + role + "_model", "") or None


def has_consent(profile):
    provider = settings().ai_provider
    return (
        profile.settings.coach_consent
        and (profile.settings.coach_consent_provider or "nvidia") == provider
    )


def configured():
    _, key, model, _ = provider_config()
    return bool(key and model)


def completion(system, context, schema, validate=None, *, max_tokens=1500, model=None):
    provider, key, default_model, base_url = provider_config()
    model = model or default_model
    if not key or not default_model:
        raise HTTPException(
            503,
            "La IA no está configurada. Puedes seguir usando el catálogo, tu plan y la lista de compras.",
        )
    headers = {"Authorization": f"Bearer {key}"}
    try:
        with httpx.Client(
            base_url=base_url, headers=headers, timeout=httpx.Timeout(35, connect=10)
        ) as client:
            models = client.get("/models")
            models.raise_for_status()
            if model not in {m.get("id") for m in models.json().get("data", [])}:
                raise HTTPException(
                    503, f"El modelo {provider} configurado no está disponible para esta cuenta."
                )
            validation_feedback = ""
            for attempt in range(2):
                result = client.post(
                    "/chat/completions",
                    json=dict(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": system
                                + " Devuelve exclusivamente JSON válido con este esquema: "
                                + json.dumps(schema.model_json_schema(), ensure_ascii=False),
                            },
                            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                            *(
                                [
                                    {
                                        "role": "system",
                                        "content": "Corrige el intento anterior. La validación encontró: "
                                        + validation_feedback
                                        + ". Devuelve una respuesta completa ajustada al esquema y evidencia; no inventes respaldo.",
                                    }
                                ]
                                if validation_feedback
                                else []
                            ),
                        ],
                        temperature=0.2,
                        **(
                            {
                                "max_completion_tokens": max_tokens,
                                **(
                                    {"reasoning_effort": "low"}
                                    if model.startswith("openai/gpt-oss")
                                    else {}
                                ),
                            }
                            if provider == "Groq"
                            else {"max_tokens": max_tokens}
                        ),
                        response_format={"type": "json_object"},
                        **(
                            {"chat_template_kwargs": {"enable_thinking": False}}
                            if model == "nvidia/nemotron-3.5-lightning-30b-a3b"
                            else {}
                        ),
                    ),
                )
                result.raise_for_status()
                try:
                    choice = result.json()["choices"][0]
                    if choice.get("finish_reason") == "length":
                        raise ValueError("Respuesta incompleta")
                    raw = choice["message"]["content"]
                    parsed = schema.model_validate_json(raw)
                    if validate:
                        validate(parsed)
                    return parsed
                except HTTPException as exc:
                    validation_feedback = str(exc.detail)[:600]
                    if attempt:
                        raise exc
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    validation_feedback = str(exc)[:600]
                    if attempt:
                        raise HTTPException(
                            502,
                            "La IA devolvió datos inválidos. No se guardaron cambios ni se consumió cuota.",
                        )
    except httpx.TimeoutException:
        raise HTTPException(503, "La IA tardó demasiado. Inténtalo de nuevo; no se consumió cuota.")
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(
            503, f"{provider} no está disponible o rechazó la solicitud. No se consumió cuota."
        )
