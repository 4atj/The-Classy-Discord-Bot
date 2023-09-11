from __future__ import annotations

__all__ = (
    "QuizEmbedBase",
    "MultiChoiceEmbedBase",
    "MultiChoiceEmbed",
)

from typing import Generic, TypeVar, Sequence
from abc import ABC, abstractmethod

import discord

from . import Quiz, MultiChoiceQuiz
from .submission import Submission, MultiChoiceSubmission


QuizT = TypeVar("QuizT", bound=Quiz)
SubmissionT = TypeVar("SubmissionT", bound=Submission)


class QuizEmbedBase(discord.Embed, ABC, Generic[QuizT, SubmissionT]):
    def __init__(
        self,
        *,
        quiz: QuizT,
        submissions: Sequence[SubmissionT],
        finished: bool,
        color: discord.Color | int | None = None,
    ) -> None:
        super().__init__(
            title=quiz.title,
            color=color
        )

        self.quiz = quiz
        self.submissions = submissions
        self.finished = finished

        self.build_embed()
        self.set_leaderboard()

        if finished:
            self.set_finished()

    def build_embed(self) -> None:
        self.add_field(
            name=f"**{self.quiz.prompt_header}**",
            value=self.quiz.prompt_body,
            inline=False
        )

    @abstractmethod
    def set_leaderboard(self) -> None:
        ...

    def set_finished(self) -> None:
        assert self.title is not None
        self.title += " **\\*ENDED\\***"


MultiChoiceQuizT = TypeVar("MultiChoiceQuizT", bound=MultiChoiceQuiz)
MutliChoiceSubmissionT = TypeVar("MutliChoiceSubmissionT", bound=MultiChoiceSubmission)


class MultiChoiceEmbedBase(QuizEmbedBase[MultiChoiceQuizT, MutliChoiceSubmissionT]):
    def set_leaderboard(self) -> None:
        leaderboard_content: list[str] = []

        for rank, submission in enumerate(reversed(self.submissions), 1):
            minutes, seconds = divmod(int(submission.time_taken.total_seconds()), 60)
            time_taken_str = f"{minutes:02d}:{seconds:02d}"
            if submission.success:
                score_line = f"**{rank}) {submission.user.mention} {time_taken_str} ✅**"
            else:
                score_line = f"**_) {submission.user.mention} {time_taken_str} ❌**"
            leaderboard_content.append(score_line)
    
        self.description = "\n".join(leaderboard_content)

    def set_finished(self) -> None:
        super().set_finished()
        self.add_field(
            name=f"**{self.quiz.answer_header}**",
            value=self.quiz.answer_body,
            inline=False
        )


class MultiChoiceEmbed(MultiChoiceEmbedBase[MultiChoiceQuiz, MultiChoiceSubmission]):
    pass