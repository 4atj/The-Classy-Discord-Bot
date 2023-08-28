from __future__ import annotations

__all__ = ("ImagineStepsNumber", "Bot")

import os
import json
import random
from typing import Final

import dotenv
import discord
from discord import app_commands
from discord.ext import commands

from . import utils
from .quiz import QuizView, Quiz
from .image_generation import ImageGenerator, AspectRatio
from . import codeguessr

dotenv.load_dotenv(utils.resolve_relative_path(__file__, "../dotenv/.env"))

ImagineStepsNumber: Final = app_commands.transformers.RangeTransformer(
    discord.enums.AppCommandOptionType.integer,
    min=10,
    max=100
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

        quiz = random.choice(quizzes)
        del quizzes

        _, options = zip(*quiz["options"])
        answer = options[ord(quiz["correct"])-ord("A")]

        quiz = Quiz(
            title="Math Quiz",
            prompt_header="Problem",
            prompt_body=quiz["problem"],
            answer_header="Rationale",
            answer_body=quiz["rationale"],
            options=options,
            answer=answer
        )

        await QuizView(
            interaction=interaction,
            quiz=quiz,
            color=discord.Color.blue(),
            timeout=240
        ).send()

    @app_commands.command(
        description = "Guess the programming language"
    )
    async def codeguessr(self, interaction: discord.Interaction) -> None:
        db_rel_path = utils.resolve_relative_path(__file__, "../data/codeguessr.db")
        db_uri = f"file:{db_rel_path}?mode=ro"

        await QuizView(
            interaction=interaction,
            quiz=codeguessr.random_quiz_from_db(db_uri, n_choices = 5),
            color=discord.Color.dark_grey(),
            timeout=20
        ).send()


class Bot(commands.Bot):
    async def on_ready(self):
        await self.add_cog(Cog())
        await self.tree.sync()


if __name__ == "__main__":
    
    intents = discord.Intents.default()
    intents.message_content = True

    bot = Bot(command_prefix="\0", intents=intents)
    bot.run(os.environ['DISCORD_TOKEN'])