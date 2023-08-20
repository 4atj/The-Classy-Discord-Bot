from __future__ import annotations

import bisect
import datetime
from typing import Any, Optional, Union

import discord
from discord.emoji import Emoji
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.partial_emoji import PartialEmoji

class QuizOptionButton(discord.ui.Button):
    async def callback(self, interaction: Interaction) -> None:
        assert isinstance(self.view, QuizView)
        await self.view.answer_callback(interaction, self)

class QuizView(discord.ui.View):
    def __init__(self, *, interaction: discord.Interaction, quiz, timeout: float | None = 180) -> None:
        super().__init__(timeout = timeout)

        self.scoreboard: list[tuple[bool, datetime.timedelta, discord.User | discord.Member]] = []
        self.users_answered: set[discord.User | discord.Member] = set()
        self.interaction = interaction
        self.quiz = quiz

        self.embed = discord.Embed(
            title = f"Math Quiz (category: {quiz['category']})",
            color = discord.Color.blue()
        )
        self.embed.add_field(
            name = "**Problem**",
            value = quiz['problem'],
            inline = False
        ) 
        self.embed.add_field(
            name = "**Options**",
            value = "\n".join(
                f'**{option}) ** {label}'
                    for option, label in quiz["options"]
            ),
            inline = False
        )

        for option, _ in quiz["options"]:
            button = QuizOptionButton(label = option, custom_id = option)
            self.add_item(button)

    async def send(self) -> None:
        await self.interaction.response.send_message(embed = self.embed, view = self)

    async def on_timeout(self) -> None:
        assert self.embed.title is not None
        self.embed.title += " **\\*ENDED\\***"
        self.embed.add_field(
            name = "**Rationale**",
            value = self.quiz["rationale"],
            inline = False
        )
        await self.interaction.edit_original_response(embed = self.embed, view = None)

    async def answer_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        assert interaction.message is not None
        
        time_taken = interaction.created_at - interaction.message.created_at

        if interaction.user in self.users_answered:
            await interaction.response.defer()
            return
        
        self.users_answered.add(interaction.user)

        bisect.insort(
            self.scoreboard,
            (
                button.custom_id != self.quiz["correct"],
                time_taken,
                interaction.user
            )
        )

        scoreboard_content = []
        for index, (failure, time_taken, user) in enumerate(self.scoreboard, 1):
            minutes_taken = int(time_taken.total_seconds() / 60)
            formatted_time_taken = f"{minutes_taken:02d}:{time_taken.seconds % 60:02d}"
            scoreboard_content.append(
                f"**{[index,'_'][failure]}) {user.mention} {formatted_time_taken} {'✅❌'[failure]}**"
            )

        self.embed.description = "\n".join(scoreboard_content)

        await interaction.message.edit(embed = self.embed)
        await interaction.response.defer()