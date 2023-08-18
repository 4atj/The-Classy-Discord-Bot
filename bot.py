from __future__ import annotations

__all__ = ("AspectRatio", "NumSteps", "Bot")

import os
import json
import dotenv
import aiohttp
from typing import Any, Final, Literal, TypeAlias

import discord
from discord import app_commands

AspectRatio: TypeAlias = Literal["16:9", "3:2", "5:4", "1:1", "4:5", "2:3", "9:16"]
default_aspect_ratio: Final = "3:2"

min_steps: Final = 5
max_steps: Final = 100
NumSteps: TypeAlias = app_commands.transformers.RangeTransformer(
    discord.enums.AppCommandOptionType.integer,
    min = min_steps,
    max = max_steps
) # type: ignore
default_steps: Final = 32

class Bot(discord.Client):
    class BotCommandTree(app_commands.CommandTree):
        def __init__(self, client: Any, *, fallback_to_global: bool = True) -> None:
            super().__init__(client, fallback_to_global = fallback_to_global)

            self.command(
                description = "Hello!"
            )( self.hello )

            self.command(
                description = "Turns your prompts into art"
            )( self.imagine )

        @app_commands.describe(
            prompt = "Provide a description of the image you want to create",
            negative_prompt = "Describe elements you want to avoid in the image",
            aspect_ratio = f"Choose your desired aspect ratio (default: {default_aspect_ratio})",
            num_steps = f"The more steps, the higher the quality (min: {min_steps}, max: {max_steps}, default: {default_steps})"
        )
        async def imagine(self,
            interaction: discord.Interaction,
            prompt: str,
            negative_prompt: str = "",
            aspect_ratio: AspectRatio = default_aspect_ratio,
            num_steps: NumSteps = 32
        ) -> None:
            
            await interaction.response.defer(thinking = True)

            aspect_ratio_numerator, aspect_ratio_denominator = map(int, aspect_ratio.split(":"))
            float_aspect_ratio = aspect_ratio_numerator / aspect_ratio_denominator
            
            try:
                async with aiohttp.ClientSession() as session:
                    response = await session.post(
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
                    content = await response.json()

                    os.environ["MAGE_REFRESH_TOKEN"] = content["refresh_token"]
                    dotenv.set_key(".env", "MAGE_REFRESH_TOKEN", os.environ["MAGE_REFRESH_TOKEN"])

                    response = await session.post(
                        url = "https://api.mage.space/api/v3/images/generate",
                        headers = {
                            "accept": "application/json",
                            "accept-language": "en-US,en;q=0.9",
                            "authorization": f"{content['token_type']} {content['access_token']}",
                            "cache-control": "no-cache",
                            "content-type": "application/json",
                            "pragma": "no-cache",
                            "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Google Chrome\";v=\"114\"",
                            "sec-ch-ua-mobile": "?0",
                            "sec-ch-ua-platform": "\"Linux\"",
                            "sec-fetch-dest": "empty",
                            "sec-fetch-mode": "cors",
                            "sec-fetch-site": "same-site",
                            "x-fjs-id": "5c0697a0c606ed84b53c310c7acb1a6b"
                        },
                        data = json.dumps({
                            "model": "sdxl",
                            "base_size": 1024,
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "clip_skip": False,
                            "num_inference_steps": num_steps,
                            "guidance_scale": 12,
                            "aspect_ratio": float_aspect_ratio,
                            "scheduler": "euler",
                            "scheduler_use_karras": False,
                            "strength": 0.8,
                            "preprocess_controlnet_image": True,
                            "image_guidance_scale": 1.5,
                            "refiner_strength": 0.25,
                            "use_refiner": True,
                            "easy_mode": True,
                            "is_public": True
                        })
                    )
                    content = await response.json()

                result, = content["results"]
                
                if result["is_nsfw"]:
                    interaction.client.loop.create_task(
                        interaction.followup.send(f"**NSFW content detected**")
                    )
                    return
                
                embed = discord.Embed(
                    title = fr"\> {prompt[:125]+'...' if len(prompt) > 128 else prompt} ({aspect_ratio})",
                    description = f"by {interaction.user.mention}"
                )
                embed.set_image(url = result["image_url"])
                interaction.client.loop.create_task(
                    interaction.followup.send(embed = embed)
                )

            except Exception as exception:
                await interaction.followup.send(f"**Something went wrong**")
                raise exception
        
        async def hello(self, interaction: discord.Interaction) -> None:
            await interaction.response.send_message('Hello')

    def __init__(self, *, intents: discord.Intents, **options: Any) -> None:
        super().__init__(intents = intents, **options)
        self.BotCommandTree(client = self)

    @classmethod
    def start_instance(cls) -> None:
        dotenv.load_dotenv(".env")

        intents = discord.Intents.default()
        intents.message_content = True

        bot = cls(intents = intents)
        bot.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    Bot.start_instance()