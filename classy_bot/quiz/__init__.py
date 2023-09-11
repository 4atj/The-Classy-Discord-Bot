from __future__ import annotations

__all__ = (
    "Quiz",
    "MultiChoiceQuiz",
)

from dataclasses import dataclass


@dataclass(kw_only=True)
class Quiz:
    title: str
    prompt_header: str
    prompt_body: str


@dataclass(kw_only=True)
class MultiChoiceQuiz(Quiz):
    answer_header: str
    answer_body: str
    options: tuple[str, ...]
    answer: str