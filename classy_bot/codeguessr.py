from __future__ import annotations

import urllib
import urllib.parse
import sqlite3
import bisect
import datetime
import random
from dataclasses import dataclass

import discord
from discord.interactions import Interaction


@dataclass
class Solution:
    # These data come from db (scraped from Rosetta Code)
    solution_id: int
    task_name: str
    task_url: str
    language: str
    code: str


class OptionButton(discord.ui.Button):
    async def callback(self, interaction: Interaction) -> None:
        assert isinstance(self.view, View)
        await self.view.answer_callback(interaction, self)


class View(discord.ui.View):
    def __init__(
            self,
            *,
            interaction: discord.Interaction,
            answer: Solution,
            langs: list[str],
            timeout: float | None = 20
    ) -> None:
        super().__init__(timeout=timeout)

        self.scoreboard: list[tuple[bool, datetime.timedelta, discord.User | discord.Member]] = []
        self.users_answered: set[discord.User | discord.Member] = set()
        self.interaction = interaction
        self.answer = answer

        n_choices = 5

        options = random.choices(langs, k=n_choices)
        if answer.language in options:
            i = options.index(answer.language)
        else:
            i = random.randint(0, n_choices - 1)
            options[i] = answer.language

        self.embed = discord.Embed(title="CodeGuessr (discord edition)")

        self.embed.add_field(
            name="**What's this programming language?!**",
            value=f"```\n{answer.code}\n```",
            inline=False,
        )

        for option in options:
            button = OptionButton(label=option)
            self.add_item(button)

    async def send(self) -> None:
        await self.interaction.response.send_message(embed=self.embed, view=self)

    async def on_timeout(self) -> None:
        assert self.embed.title is not None
        self.embed.title += " **\\*ENDED\\***"
        escaped_language = urllib.parse.quote(self.answer.language)
        self.embed.add_field(
            name="**Answer**",
            value=(
                f"It was of course **{self.answer.language}**! "
                f"This code is a solution to a Rosetta Code problem called "
                f"[{self.answer.task_name}]({self.answer.task_url}#{escaped_language})."
            ),
        )
        await self.interaction.edit_original_response(embed=self.embed, view=None)

    async def answer_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        assert interaction.message is not None

        time_taken = interaction.created_at - interaction.message.created_at

        if interaction.user in self.users_answered:
            await interaction.response.defer()
            return

        self.users_answered.add(interaction.user)

        bisect.insort(
            self.scoreboard,
            (button.label != self.answer.language, time_taken, interaction.user),
        )

        scoreboard_content = []
        for rank, (wrong, time_taken, user) in enumerate(self.scoreboard, 1):
            minutes, seconds = divmod(int(time_taken.total_seconds()), 60)
            time_taken_str = f"{minutes:02d}:{seconds:02d}"
            if not wrong:
                score_line = f"**{rank}) {user.mention} {time_taken_str} ✅**"
            else:
                score_line = f"**_) {user.mention} {time_taken_str} ❌**"
            scoreboard_content.append(score_line)

        self.embed.description = "\n".join(scoreboard_content)

        await interaction.message.edit(embed=self.embed)
        await interaction.response.defer()


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
