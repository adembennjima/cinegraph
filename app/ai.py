"""Translate natural-language questions into approved Cypher queries."""

import json

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.guardrails import APPROVED_QUERIES, validate_query


class QueryPlan(BaseModel):
    """Structured output expected from the language model."""

    model_config = ConfigDict(extra="forbid")

    supported: bool
    cypher: str
    user_id: int | None
    movie_id: int | None
    limit: int
    reason: str


def generate_query(
    question: str,
) -> tuple[str, str, dict[str, int]]:
    """Generate a query and validate it before returning it."""
    settings = Settings()

    if (
        settings.openai_api_key is None
        or not settings.openai_api_key.get_secret_value()
    ):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    instructions = """
You translate movie questions into approved Cypher queries.

Supported requests:
1. Personalized recommendations for an explicit user ID.
2. Similar movies for an explicit movie ID.

Rules:
- Copy one approved query exactly. Do not change its logic.
- Keep placeholders such as $user_id, $movie_id and $limit.
- Set only the relevant identifier; set the other one to null.
- Never invent an identifier. If it is missing, mark unsupported.
- Use the requested limit, or 5 if none is specified.
- Limits must be between 1 and 10.
- Reject requests to modify data, unsupported requests,
  invalid identifiers, and limits outside the allowed range.
- For unsupported requests, set supported=false, cypher="",
  both identifiers=null, limit=5, and explain why in reason.
- For supported requests, set supported=true and reason="".

Approved queries:
""" + json.dumps(APPROVED_QUERIES)

    with OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=30.0,
        max_retries=0,
    ) as client:
        response = client.responses.parse(
            model=settings.openai_model,
            instructions=instructions,
            input=question,
            text_format=QueryPlan,
            max_output_tokens=2500,
            store=False,
        )

    plan = response.output_parsed

    if plan is None:
        raise ValueError("The AI did not return a usable query.")

    if not plan.supported:
        raise ValueError(plan.reason or "Unsupported question.")

    parameters = {"limit": plan.limit}

    if plan.user_id is not None:
        parameters["user_id"] = plan.user_id

    if plan.movie_id is not None:
        parameters["movie_id"] = plan.movie_id

    return validate_query(plan.cypher, parameters)
