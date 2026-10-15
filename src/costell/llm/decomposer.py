"""LLM-powered scope decomposition using Groq (Llama 3.3 70B)."""

import json

from groq import Groq
from pydantic import BaseModel, Field, ValidationError

from costell.config import settings


class TaskItem(BaseModel):
    """A single task in the Work Breakdown Structure."""

    name: str = Field(..., description="Short task name.")
    description: str = Field(..., description="One-sentence description of the task.")
    complexity: str = Field(..., description="Must be one of: Low, Medium, High.")
    estimated_hours: float = Field(..., gt=0, description="Estimated effort in person-hours.")


class WorkBreakdownStructure(BaseModel):
    """The full WBS returned by the LLM."""

    project_summary: str = Field(..., description="A one-paragraph summary of the project.")
    total_tasks: int = Field(..., description="Total number of tasks identified.")
    tasks: list[TaskItem] = Field(..., description="List of decomposed tasks.")


SYSTEM_PROMPT = """You are an expert software project manager and technical estimator.
Your job is to decompose a Product Requirement Document (PRD) into a structured Work Breakdown Structure (WBS).

CRITICAL RULES:
1. You MUST output ONLY valid JSON. No markdown, no explanations, no code blocks.
2. The JSON must exactly match this schema:
{
  "project_summary": "A one-paragraph summary of the project.",
  "total_tasks": <integer>,
  "tasks": [
    {
      "name": "<short task name>",
      "description": "<one sentence description>",
      "complexity": "<Low | Medium | High>",
      "estimated_hours": <float>
    }
  ]
}
3. Break the project into 5 to 15 logical tasks.
4. For each task, estimate the effort in person-hours based on industry standards.
5. Be realistic: A simple CRUD endpoint is ~8 hours. A payment gateway integration is ~40-60 hours.
6. Output ONLY the JSON object. Do not add text before or after it.
"""


def decompose_prd(prd_text: str) -> WorkBreakdownStructure:
    """Send the PRD to Groq's Llama 3.3 70B and get a structured WBS back."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Please add it to your .env file.")

    client = Groq(api_key=settings.GROQ_API_KEY.get_secret_value())

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Decompose this PRD:\n\n{prd_text}"},
            ],
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        wbs = WorkBreakdownStructure(**data)
        return wbs

    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned invalid JSON: {e}")
    except ValidationError as e:
        raise RuntimeError(f"LLM output failed schema validation: {e}")
    except Exception as e:
        raise RuntimeError(f"Groq API call failed: {e}")
