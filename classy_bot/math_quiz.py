from __future__ import annotations

__all__ = (
    "random_math_quiz_from_json",
)

from typing import TypedDict
import json
import random

from .quiz import MultiChoiceQuiz


class MathQuiz(TypedDict):
    problem: str
    category: str
    options: list[list[str]]
    correct: str
    rationale: str


def random_math_quiz_from_json(path: str) -> MultiChoiceQuiz:
    with open(path, "r") as file:
        quizzes = json.load(file)
    
    math_quiz = MathQuiz(**random.choice(quizzes))

    _, options = zip(*math_quiz["options"])
    answer = options[ord(math_quiz["correct"])-ord("A")]

    return MultiChoiceQuiz(
        title="Math Quiz",
        prompt_header="Problem",
        prompt_body=math_quiz["problem"],
        answer_header="Rationale",
        answer_body=math_quiz["rationale"],
        options=options,
        answer=answer
    )