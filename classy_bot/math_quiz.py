from __future__ import annotations

__all__ = (
    "random_math_quiz_from_json",
)

import json
import random

from .quiz import MultiChoiceQuiz


def random_math_quiz_from_json(path: str) -> MultiChoiceQuiz:
    with open(path, "r") as file:
        quizzes = json.load(file)

    math_quiz = random.choice(quizzes)
    math_quiz["options"] = tuple(f"{key}) {value}" for key, value in math_quiz["options"])
    math_quiz["correct"] = math_quiz["options"][ord(math_quiz["correct"])-ord("A")]

    return MultiChoiceQuiz(
        title="Math Quiz",
        prompt_header="Problem",
        prompt_body=math_quiz["problem"],
        answer_header="Rationale",
        answer_body=math_quiz["rationale"],
        options=math_quiz["options"],
        answer=math_quiz["correct"]
    )