from __future__ import annotations

__all__ = (
    "Solution",
    "random_solution_from_db",
    "langs_from_db",
    "quiz_from_solution",
    "random_quiz_from_db"
)

import urllib
import urllib.parse
import random
import sqlite3
from dataclasses import dataclass

import discord
from discord import Interaction

from .quiz import MultiChoiceQuiz
from .quiz.submission import MultiChoiceSubmission
from .quiz.view import MultiChoiceView


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


def quiz_from_solution(*, solution: Solution, langs: list[str], n_choices: int) -> MultiChoiceQuiz:
    escaped_language = urllib.parse.quote(solution.language)

    options = random.sample(langs, k=n_choices)
    if solution.language in options:
        i = options.index(solution.language)
    else:
        i = random.randint(0, n_choices - 1)
        options[i] = solution.language

    return MultiChoiceQuiz(
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


def random_quiz_from_db(db_uri: str, *, n_choices: int) -> MultiChoiceQuiz:
    return quiz_from_solution(
        solution=random_solution_from_db(db_uri),
        langs=langs_from_db(db_uri),
        n_choices=n_choices
    )


class CodeguessrQuizView(MultiChoiceView):
    def __init__(
        self,
        *,
        interaction: Interaction,
        quiz: MultiChoiceQuiz,
        color: discord.Color | int | None = None,
        timeout: float = 60
    ) -> None:
        super().__init__(
            interaction=interaction,
            quiz=quiz,
            color=color,
            timeout=timeout
        )

        self.leaderboard_db_uri: str | None = None

    def use_leaderboard_db(self, db_uri: str):
        self.leaderboard_db_uri = db_uri

    async def on_submission(self, submission: MultiChoiceSubmission) -> None:
        db_uri = self.leaderboard_db_uri
        if not db_uri:
            return

        if submission.success:
            time_seconds = submission.time_taken.total_seconds()
            points = max(round(20 - time_seconds), 1)
        else:
            points = -20

        with sqlite3.connect(db_uri, uri=True) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS
                player_scores (discord_user_id INTEGER PRIMARY KEY, points INTEGER)
                """
            )
            conn.execute(
                """
                INSERT INTO player_scores (discord_user_id, points)
                VALUES (?, ?)
                ON CONFLICT (discord_user_id) DO
                UPDATE SET points = points + ?
                """,
                (submission.user.id, points, points)
            )


def leaderboard_top(n_players: int = 5, *, db_uri: str):
    with sqlite3.connect(db_uri, uri=True) as conn:
        return conn.execute(
            "SELECT discord_user_id, points FROM player_scores ORDER BY points DESC LIMIT ?",
            (n_players,)
        ).fetchall()
