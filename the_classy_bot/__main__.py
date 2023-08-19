from __future__ import annotations

__all__ = ("ImagineAspectRatio", "ImagineStepsNumber", "Bot")

import sys
from typing import Final, Literal

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import os
import json
import random
import bisect
import datetime

import dotenv
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


file_path: Final = os.path.dirname(os.path.abspath(__file__))

dotenv.load_dotenv(os.path.join(file_path, "../dotenv/.env"))

ImagineAspectRatio: TypeAlias = Literal["16:9", "3:2", "5:4", "1:1", "4:5", "2:3", "9:16"]
ImagineStepsNumber: Final = app_commands.transformers.RangeTransformer(
    discord.enums.AppCommandOptionType.integer,
    min = 5,
    max = 100
)

class Bot(commands.Bot):
    class Cog(commands.Cog):
        @app_commands.command(
            description = "Hello!"
        )
        async def hello(self, interaction: discord.Interaction) -> None:
            await interaction.response.send_message('Hello')

        default_imagine_aspect_ratio: Final[ImagineAspectRatio] = "3:2"
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
        async def imagine(self,
            interaction: discord.Interaction,
            prompt: str,
            negative_prompt: str = "",
            aspect_ratio: ImagineAspectRatio = default_imagine_aspect_ratio,
            num_steps: ImagineStepsNumber = default_imagine_steps # type: ignore
        ) -> None:
            
            await interaction.response.defer(thinking = True)

            aspect_ratio_numerator, aspect_ratio_denominator = map(int, aspect_ratio.split(":"))
            float_aspect_ratio = aspect_ratio_numerator / aspect_ratio_denominator
            
            try:
                async with aiohttp.ClientSession() as session:
                    token_response = await session.post(
                        url = "https://securetoken.googleapis.com/v1/token",   
                        headers = {
                            "accept": "*/*",
                            "content-type": "application/x-www-form-urlencoded",
                        },
                        params = {
                            "key": "AIzaSyAzUV2NNUOlLTL04jwmUw9oLhjteuv6Qr4"
                        },
                        data = {
                            "grant_type": "refresh_token",
                            "refresh_token": os.environ["MAGE_REFRESH_TOKEN"]
                        }
                    )
                    token_content = await token_response.json()

                    os.environ["MAGE_REFRESH_TOKEN"] = token_content["refresh_token"]
                    dotenv.set_key(
                        dotenv_path = os.path.join(file_path, "../dotenv/.env"),
                        key_to_set = "MAGE_REFRESH_TOKEN",
                        value_to_set = os.environ["MAGE_REFRESH_TOKEN"]
                    )

                    generate_response = await session.post(
                        url = "https://api.mage.space/api/v3/images/generate",
                        headers = {
                            "accept": "application/json",
                            "authorization": f"{token_content['token_type']} {token_content['access_token']}",
                            "content-type": "application/json",
                        },
                        data = json.dumps({
                            "model": "sdxl",
                            "base_size": 1024,
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "clip_skip": False,
                            "num_inference_steps": num_steps,
                            "guidance_scale": 12.5,
                            "aspect_ratio": float_aspect_ratio,
                            "scheduler": "euler",
                            "scheduler_use_karras": False,
                            "strength": 0.8,
                            "preprocess_controlnet_image": True,
                            "image_guidance_scale": 1.5,
                            "refiner_strength": 0.2,
                            "use_refiner": True,
                            "easy_mode": True,
                            "is_public": True
                        })
                    )
                    generate_content = await generate_response.json()

                result, = generate_content["results"]
                
                if result["is_nsfw"]:
                    await interaction.followup.send(f"**NSFW content detected**")
                    return
                
                embed = discord.Embed(
                    title = f"\\> {prompt[:125]+'...' if len(prompt) > 128 else prompt} ({aspect_ratio})",
                    description = f"by {interaction.user.mention}",
                    color = discord.Color.yellow()
                )
                embed.set_image(url = result["image_url"])
                
                await interaction.followup.send(embed = embed)

            except Exception as exception:
                await interaction.followup.send(f"**Something went wrong**")
                raise exception

        math_quiz_timeout: Final = 300.0
        @app_commands.command(
            description = "Solve a short math question"
        )
        async def math_quiz(self, interaction: discord.Interaction) -> None:
            with open(os.path.join(file_path, "../data/math_qa.json")) as f:
                quizzes = json.load(f)
                quiz = random.choice(quizzes)
                del quizzes

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

            view = discord.ui.View(timeout = self.math_quiz_timeout)

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

    async def on_ready(self):
        await self.add_cog(self.Cog())
        await self.tree.sync()

if __name__ == "__main__":
    
    intents = discord.Intents.default()
    intents.message_content = True

    bot = Bot(command_prefix = "\0", intents = intents)
    bot.run(os.environ['DISCORD_TOKEN'])