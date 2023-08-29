from __future__ import annotations

import urllib
import urllib.parse
import random
import sqlite3
from dataclasses import dataclass

from .quiz import Quiz


@dataclass(kw_only=True)
class Solution:
    # These data come from db (scraped from Rosetta Code)
    solution_id: int
    task_name: str
    task_url: str
    language: str
    code: str


def random_solution_from_db(db_uri: str) -> Solution:
    with sqlite3.connect(db_uri, uri=True) as conn:
        res = conn.execute(
            "SELECT id, task_name, lang, code"
            " FROM solutions"
            " ORDER BY random()"
            " LIMIT 1")
        solution_id, task_name, lang, code = res.fetchone()

    escaped_task_name = urllib.parse.quote(task_name)
    return Solution(
        solution_id=solution_id,
        task_name=task_name,
        task_url=f"https://rosettacode.org/wiki/{escaped_task_name}",
        language=lang,
        code=code
    )


def langs_from_db(db_uri: str) -> list[str]:
    with sqlite3.connect(db_uri, uri=True) as conn:
        res = conn.execute("SELECT DISTINCT(lang) FROM solutions")
        return [lang for (lang,) in res.fetchall()]


def quiz_from_solution(*, solution: Solution, langs: list[str], n_choices: int) -> Quiz:
    escaped_language = urllib.parse.quote(solution.language)

    options = random.sample(langs, k=n_choices)
    if solution.language in options:
        i = options.index(solution.language)
    else:
        i = random.randint(0, n_choices - 1)
        options[i] = solution.language

    return Quiz(
        title="CodeGuessr (discord edition)",
        prompt_header="What's this programming language?!",
        prompt_body=f"```\n{solution.code}\n```",
        answer_header="Answer",
        answer_body=
            f"It was of course **{solution.language}**! "
            f"This code is a solution to a Rosetta Code problem called "
            f"[{solution.task_name}]({solution.task_url}#{escaped_language}).",
        options=tuple(options),
        answer=solution.language
    )


def random_quiz_from_db(db_uri: str, *, n_choices: int) -> Quiz:
    return quiz_from_solution(
        solution=random_solution_from_db(db_uri),
        langs=langs_from_db(db_uri),
        n_choices=n_choices
    )