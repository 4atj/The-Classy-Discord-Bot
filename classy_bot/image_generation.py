from __future__ import annotations

__all__ = ("ImageGenerator", )

import json
import aiohttp

from . import utils


class ImageGenerationError(Exception):
    pass


class NSFWImageGenerationError(ImageGenerationError):
    pass


class ImageGenerator:
    def __init__(self) -> None:
        self.session = aiohttp.ClientSession()

    async def generate(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 50,
        guidance_scale: float = 12.0,
        scheduler: str = "KarrasDPM",
        refine: str = "expert_ensemble_refiner"
    ):
        response = await self.session.post(
            url = "https://zoo.replicate.dev/api/predictions",
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            },
            data = json.dumps({
                "prompt": prompt,
                "input": {
                    "num_inference_steps": num_inference_steps,
                    "width": width,
                    "height": height,
                    "refine": refine,
                    "guidance_scale": guidance_scale,
                    "scheduler": scheduler,
                    "negative_prompt": negative_prompt
                },
                "version": "98d6bab2dd21e4ffc4cc626420ab4f24b99ec60728c5d835ff9c3439396aca45",
                "source": "replicate",
                "model": "SDXL",
                "anon_id": utils.random_hex(16),
                "submission_id": utils.random_hex(16)
            })
        )

        content = json.loads(await response.text())

        while True:
            response = await self.session.get(
                url = "https://zoo.replicate.dev/api/predictions/" + content["id"],
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                }
            )

            content = json.loads(await response.text())

            match content["status"]:
                case "succeeded":
                    break

                case "failed":
                    if content["error"].startswith("NSFW"):
                        raise NSFWImageGenerationError
                    
                    raise ImageGenerationError

        return content["output"][0]
    
    def __del__(self):
        self.session.loop.create_task(
            self.session.close()
        )