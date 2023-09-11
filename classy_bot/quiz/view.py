from __future__ import annotations

__all__ = (
    "QuizItemBase",
    "QuizViewBase",
    "MultiChoiceButtonBase",
    "MultiChoiceButton",
    "MultiChoiceViewBase",
    "MultiChoiceView"
)
    
from typing import Generic, TypeVar, Any
import bisect
from abc import ABC, abstractmethod

import discord
from discord.interactions import Interaction

from . import Quiz, MultiChoiceQuiz
from .embed import QuizEmbedBase, MultiChoiceEmbedBase, MultiChoiceEmbed
from .submission import Submission, MultiChoiceSubmission 


QuizT = TypeVar("QuizT", bound=Quiz)
SubmissionT = TypeVar("SubmissionT", bound=Submission)
QuizItemT = TypeVar("QuizItemT", bound="QuizItemBase[Any]")
QuizViewT = TypeVar("QuizViewT", bound="QuizViewBase[Any, Any, Any]")


class QuizItemBase(discord.ui.Item[QuizViewT]):
    pass


class QuizViewBase(Generic[QuizT, SubmissionT, QuizItemT], discord.ui.View, ABC):
    def __init__(
        self,
        *,
        interaction: Interaction,
        quiz: QuizT,
        color: discord.Color | int | None = None,
        timeout: float = 60
    ) -> None:
        super().__init__(timeout=timeout)

        self.interaction = interaction
        self.quiz = quiz
        self.color = color
        self.submissions: list[SubmissionT] = []

        self.build_view()

    @abstractmethod
    def build_view(self) -> None:
        ...

    @abstractmethod
    def build_embed(self) -> QuizEmbedBase[QuizT, SubmissionT]:
        ...

    @abstractmethod
    async def build_submission(self, interaction: discord.Interaction, button: QuizItemT) -> SubmissionT:
        ...

    async def send(self) -> None:
        self.embed = self.build_embed()
        await self.interaction.response.send_message(embed=self.embed, view=self)

    async def add_submission(self, submission: SubmissionT) -> None:
        if any(submission.user == s.user for s in self.submissions):
            raise ValueError("User has already submitted")

        bisect.insort(self.submissions, submission)

    async def on_submission(self, submission: SubmissionT) -> None:
        pass

    async def on_answer(self, interaction: discord.Interaction, button: QuizItemT) -> None:
        message = interaction.message
        assert message is not None

        if any(interaction.user == subm.user for subm in self.submissions):
            await interaction.response.send_message(content="**You have already submitted an answer**", ephemeral=True)
            return

        submission = await self.build_submission(interaction, button)
        await self.add_submission(submission)
        await self.on_submission(submission)

        await interaction.response.defer()
        await message.edit(embed=self.build_embed())

    async def on_timeout(self) -> None:
        await self.interaction.edit_original_response(embed=self.build_embed(), view=None)


MultiChoiceQuizT = TypeVar("MultiChoiceQuizT", bound=MultiChoiceQuiz)
MultiChoiceSubmissionT = TypeVar("MultiChoiceSubmissionT", bound=MultiChoiceSubmission)
MultiChoiceButtonT = TypeVar("MultiChoiceButtonT", bound="MultiChoiceButtonBase[Any]")
MultiChoiceViewT = TypeVar("MultiChoiceViewT", bound="MultiChoiceViewBase[Any, Any, Any]")


class MultiChoiceButtonBase(QuizItemBase[MultiChoiceViewT], discord.ui.Button[MultiChoiceViewT]):
    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        await self.view.on_answer(interaction, self)


class MultiChoiceButton(MultiChoiceButtonBase["MultiChoiceView"]):
    pass
    

class MultiChoiceViewBase(QuizViewBase[MultiChoiceQuizT, MultiChoiceSubmissionT, MultiChoiceButtonT]):
    @abstractmethod
    def build_embed(self) -> MultiChoiceEmbedBase[MultiChoiceQuizT, MultiChoiceSubmissionT]:
        ...


class MultiChoiceView(MultiChoiceViewBase[MultiChoiceQuiz, MultiChoiceSubmission, MultiChoiceButton]):
    def build_embed(self) -> MultiChoiceEmbed:
        return MultiChoiceEmbed(
            quiz=self.quiz,
            submissions=self.submissions,
            finished=self.is_finished(),
            color=self.color
        )

    def build_view(self) -> None:
        for option in self.quiz.options:
            button = MultiChoiceButton(label=option)
            self.add_item(button)

    async def build_submission(self, interaction: discord.Interaction, button: MultiChoiceButton) -> MultiChoiceSubmission:
        message = interaction.message
        assert message is not None

        return MultiChoiceSubmission(
            user=interaction.user,
            answer=button.label or "",
            success=button.label == self.quiz.answer,
            time_taken=interaction.created_at - message.created_at
        )
