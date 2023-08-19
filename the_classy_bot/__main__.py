from __future__ import annotations

__all__ = ("ImagineStepsNumber", "Bot")

import os
import json
import random
import bisect
import datetime
from typing import Final

import dotenv
import discord
from discord import app_commands
from discord.ext import commands

from . import utils
from .image_generation import ImageGenerator, AspectRatio

dotenv.load_dotenv(utils.resolve_relative_path(__file__, "../dotenv/.env"))


ImagineStepsNumber: Final = app_commands.transformers.RangeTransformer(
    discord.enums.AppCommandOptionType.integer,
    min = 10,
    max = 100
)

class Cog(commands.Cog):
    def __init__(self) -> None:
        super().__init__()
        self.image_generator = ImageGenerator(os.environ["MAGE_REFRESH_TOKEN"])
        
    @app_commands.command(
        description = "Hello!"
    )
    async def hello(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message('Hello')

    default_imagine_aspect_ratio: Final[AspectRatio] = "3:2"
    default_imagine_steps: Final = 30
    @app_commands.command(
        description = "Turns your prompts into art"
    )
    @app_commands.describe(
        prompt = "Provide a description of the image you want to create",
        negative_prompt = "Describe elements you want to avoid in the image",
        aspect_ratio = f"Choose your desired aspect ratio (default: {default_imagine_aspect_ratio})",
        num_steps = f"The more steps, the higher the quality (min: {ImagineStepsNumber.min_value}, max: {ImagineStepsNumber.max_value}, default: {default_imagine_steps})"
    )
    async def imagine(
        self,
        interaction: discord.Interaction,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: AspectRatio = default_imagine_aspect_ratio,
        num_steps: ImagineStepsNumber = default_imagine_steps # type: ignore
    ) -> None:
        
        await interaction.response.defer(thinking = True)

        
        try:
            image = await self.image_generator.generate(
                prompt = prompt,
                negative_prompt = negative_prompt,
                aspect_ratio = aspect_ratio,
                num_steps = num_steps
            )

            if image["is_nsfw"]:
                await interaction.followup.send(f"**NSFW content detected**")
                return
            
            embed = discord.Embed(
                title = f"\\> {prompt[:125]+'...' if len(prompt) > 128 else prompt} ({aspect_ratio})",
                description = f"by {interaction.user.mention}",
                color = discord.Color.yellow()
            )
            embed.set_image(url = image["image_url"])
            
            await interaction.followup.send(embed = embed)

        except Exception as exception:
            await interaction.followup.send(f"**Something went wrong**")
            raise exception

    @app_commands.command(
        description = "Solve a short math question"
    )
    async def math_quiz(self, interaction: discord.Interaction) -> None:
        with open(utils.resolve_relative_path(__file__, "../data/math_qa.json")) as f:
            quizzes = json.load(f)

        await self.quiz(interaction, quiz = random.choice(quizzes))  

    async def quiz(self, interaction: discord.Interaction, quiz, quiz_timeout: float = 300.0) -> None:
        embed = discord.Embed(
            title = f"Math Quiz (category: {quiz['category']})",
            color = discord.Color.blue()
        )

        embed.add_field(
            name = "**Problem**",
            value = quiz['problem'],
            inline = False
        ) 
        embed.add_field(
            name = "**Options**",
            value = "\n".join(
                f'**{option}) ** {label}'
                    for option, label in quiz["options"]
            ),
            inline = False
        )

        scoreboard: list[tuple[bool, datetime.timedelta, discord.User | discord.Member]] = []
        users_submitted: set[discord.User | discord.Member] = set()

        class OptionButton(discord.ui.Button):
            async def callback(self, button_interaction: discord.Interaction) -> None:
                assert button_interaction.message is not None
                
                time_taken = button_interaction.created_at - button_interaction.message.created_at

                if button_interaction.user in users_submitted:
                    await button_interaction.response.defer()
                    return
                
                users_submitted.add(button_interaction.user)

                bisect.insort(
                    scoreboard,
                    (
                        self.custom_id != quiz["correct"],
                        time_taken,
                        button_interaction.user
                    )
                )

                scoreboard_content = []
                for index, (failure, time_taken, user) in enumerate(scoreboard, 1):
                    minutes_taken = int(time_taken.total_seconds() / 60)
                    formatted_time_taken = f"{minutes_taken:02d}:{time_taken.seconds % 60:02d}"
                    scoreboard_content.append(
                        f"**{[index,'_'][failure]}) {user.mention} {formatted_time_taken} {'✅❌'[failure]}**"
                    )

                embed.description = "\n".join(scoreboard_content)

                await button_interaction.message.edit(embed = embed)
                await button_interaction.response.defer()

        view = discord.ui.View(timeout = quiz_timeout)

        for option, _ in quiz["options"]:
            button = OptionButton(label = option, custom_id = option)
            view.add_item(button)
        
        await interaction.response.send_message(embed = embed, view = view)

        async def view_on_timeout():
            assert embed.title is not None
            embed.title += " **\\*ENDED\\***"
            embed.add_field(
                name = "**Rationale**",
                value = quiz["rationale"],
                inline = False
            )
            await interaction.edit_original_response(embed = embed, view = None)
            
        view.on_timeout = view_on_timeout

class Bot(commands.Bot):
    async def on_ready(self):
        await self.add_cog(Cog())
        await self.tree.sync()


if __name__ == "__main__":
    
    intents = discord.Intents.default()
    intents.message_content = True

    bot = Bot(command_prefix = "\0", intents = intents)
    bot.run(os.environ['DISCORD_TOKEN'])