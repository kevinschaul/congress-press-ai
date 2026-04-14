#!/usr/bin/env python3
"""
Inspect AI eval: compare model sentiment classifications against manual labels.

Run with:
    just eval

Or manually:
    OPENAI_BASE_URL=http://box.local:1112/v1 OPENAI_API_KEY=local \
        inspect eval scripts/eval_classify.py --model openai/gpt-oss-20b
"""

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, csv_dataset
from inspect_ai.scorer import Score, accuracy, mean, scorer
from inspect_ai.solver import generate, system_message

EVAL_CSV = str(Path(__file__).parent.parent / "data" / "eval" / "sentiment-eval.csv")

SYSTEM = "You are a political analyst classifying congressional press releases."
VALID = {"positive", "negative", "neutral", "mixed"}


@scorer(metrics=[accuracy(), mean()])
def sentiment_match():
    async def score(state, target):
        answer = state.output.completion.strip().lower().rstrip(".")
        if answer not in VALID:
            answer = "unknown"
        expected = target.text.strip().lower()
        return Score(
            value=1 if answer == expected else 0,
            answer=answer,
            explanation=f"predicted={answer}  expected={expected}",
        )
    return score


@task
def sentiment_classification():
    return Task(
        dataset=csv_dataset(
            EVAL_CSV,
            sample_fields=FieldSpec(
                input="input",
                target="sentiment",
                id="id",
                metadata=["url", "member", "party", "title"],
            ),
        ),
        solver=[system_message(SYSTEM), generate()],
        scorer=sentiment_match(),
    )
