from __future__ import annotations

__all__ = ("ImagineInferenceSteps", "Bot")

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
from .image_generation import ImageGenerator, NSFWImageGenerationError
from . import codeguessr


dotenv.load_dotenv(utils.resolve_relative_path(__file__, "../dotenv/.env"))


ImagineInferenceSteps: Final = app_commands.transformers.RangeTransformer(
    discord.enums.AppCommandOptionType.integer,
    min = 5,
    max = 500
)


class Cog(commands.Cog):
    def __init__(self) -> None:
        super().__init__()
        self.image_generator = ImageGenerator()
        
    @app_commands.command(
        description="Hello!"
    )
    async def hello(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message('Hello')

    default_imagine_inference_steps: Final = 50
    @app_commands.command(
        description="Turns your prompts into art"
    )
    @app_commands.describe(
        prompt="Provide a description of the image you want to create",
        negative_prompt="Describe elements you want to avoid in the image",
        inference_steps=
            "The more steps, the higher the quality "
            f"(min: {ImagineInferenceSteps.min_value}, "
            f"max: {ImagineInferenceSteps.max_value}, "
            f"default: {default_imagine_inference_steps})"
    )
    async def imagine(
        self,
        interaction: discord.Interaction,
        prompt: str,
        negative_prompt: str = "",
        inference_steps: ImagineInferenceSteps = default_imagine_inference_steps # type: ignore
    ) -> None:
        
        await interaction.response.defer(thinking = True)

        try:
            image_url = await self.image_generator.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=1216,
                height=832,
                num_inference_steps=inference_steps
            )
            
            embed = discord.Embed(
                title=f"\\> {prompt[:125]+'...' if len(prompt) > 128 else prompt}",
                description=f"by {interaction.user.mention}",
                color=discord.Color.yellow()
            )
            embed.set_image(url=image_url)
            
            await interaction.followup.send(embed=embed)

        except NSFWImageGenerationError:
            await interaction.followup.send("**NSFW content detected**")

        except Exception as exception:
            await interaction.followup.send("**Something went wrong**")
            raise exception

    @app_commands.command(
        description="Solve a short math question"
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
        description="Guess the programming language"
    )
    async def codeguessr(self, interaction: discord.Interaction) -> None:
        db_rel_path = utils.resolve_relative_path(__file__, "../data/codeguessr.db")
        db_uri = f"file:{db_rel_path}?mode=ro"

        await QuizView(
            interaction=interaction,
            quiz=codeguessr.random_quiz_from_db(db_uri, n_choices = 5),
            color=discord.Color.dark_grey(),
            timeout=60
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