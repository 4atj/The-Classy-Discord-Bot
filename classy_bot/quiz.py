from __future__ import annotations

import bisect
import datetime
from dataclasses import dataclass

import discord
from discord.interactions import Interaction


@dataclass(kw_only=True)
class Submission:
    user: discord.User | discord.Member
    answer: str
    success: bool
    time_taken: datetime.timedelta

    def __lt__(self, other: Submission) -> bool:
        return (self.success, -self.time_taken) < (other.success, -other.time_taken)


@dataclass(kw_only=True)
class Quiz:
    title: str
    prompt_header: str
    prompt_body: str
    answer_header: str
    answer_body: str
    options: tuple[str, ...]
    answer: str


class QuizEmbed(discord.Embed):
    def __init__(
        self,
        *,
        quiz: Quiz,
        color: discord.Color | int | None = None
    ) -> None:
        super().__init__(
            title=quiz.title,
            color=color
        )

        self.title: str
        self.quiz = quiz
        self.build_embed()

    def build_embed(self) -> None:
        self.add_field(
            name=f"**{self.quiz.prompt_header}**",
            value=self.quiz.prompt_body,
            inline=False
        )

    def update_leaderboard(self, leaderboard_content: list[str]) -> None:
        self.description = "\n".join(leaderboard_content)

    async def end_quiz(self) -> None:
        self.title += " **\\*ENDED\\***"
        self.add_field(
            name=f"**{self.quiz.answer_header}**",
            value=self.quiz.answer_body,
            inline=False
        )


class QuizOptionButton(discord.ui.Button):
    async def callback(self, interaction: Interaction) -> None:
        assert isinstance(self.view, QuizView)
        await self.view.on_answer(interaction, self)


class QuizView(discord.ui.View):
    def __init__(
        self,
        *,
        interaction: Interaction,
        quiz: Quiz,
        color: discord.Color | int | None = None,
        timeout: float = 60
    ) -> None:
        super().__init__(timeout=timeout)

        self.interaction = interaction
        self.quiz = quiz
        self.embed = QuizEmbed(
            quiz=quiz,
            color=color
        )
        self.submissions: list[Submission] = []

        self.build_view()

    def build_view(self) -> None:
        for option in self.quiz.options:
            button = QuizOptionButton(label=option)
            self.add_item(button)

    async def send(self) -> None:
        await self.interaction.response.send_message(embed=self.embed, view=self)

    async def add_submission(self, submission: Submission) -> None:
        if any(submission.user == s.user for s in self.submissions):
            raise ValueError("User has already submitted")

        bisect.insort(self.submissions, submission)

        leaderboard_content = []
        for rank, submission in enumerate(reversed(self.submissions), 1):
            minutes, seconds = divmod(int(submission.time_taken.total_seconds()), 60)
            time_taken_str = f"{minutes:02d}:{seconds:02d}"
            if submission.success:
                score_line = f"**{rank}) {submission.user.mention} {time_taken_str} ✅**"
            else:
                score_line = f"**_) {submission.user.mention} {time_taken_str} ❌**"
            leaderboard_content.append(score_line)
        self.embed.update_leaderboard(leaderboard_content)

    async def on_submission(self, submission: Submission) -> None:
        pass

    async def on_answer(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        message = interaction.message
        assert message is not None

        if any(interaction.user == subm.user for subm in self.submissions):
            await interaction.response.send_message(content="**You have already submitted an answer**", ephemeral=True)
            return

        submission = Submission(
            user=interaction.user,
            answer=button.label or "",
            success=button.label == self.quiz.answer,
            time_taken=interaction.created_at - message.created_at
        )

        await self.on_submission(submission)
        await self.add_submission(submission)

        await message.edit(embed=self.embed)
        await interaction.response.defer()
        await message.edit(embed = self.embed)

    async def on_timeout(self) -> None:
        await self.embed.end_quiz()
        await self.interaction.edit_original_response(embed=self.embed, view=None)
