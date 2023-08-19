from __future__ import annotations

__all__ = ("ImageGenerator", "AspectRatio")

import sys
import json
import asyncio
from typing import Literal

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import aiohttp

AspectRatio: TypeAlias = Literal["16:9", "3:2", "5:4", "1:1", "4:5", "2:3", "9:16"]

class ImageGenerator:
    def __init__(self, refresh_token: str) -> None:
        self.session = aiohttp.ClientSession()
        self.refresh_token = refresh_token
        self.lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        response = await self.session.post(
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
                "refresh_token": self.refresh_token
            }
        )

        content = await response.json()
        access_token = content['token_type'] + " " + content['access_token']

        return access_token

    async def generate(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: AspectRatio = "1:1",
        num_steps: int = 30,
    ):
        
        if not (10 <= num_steps <= 100):
            raise ValueError(f"Expected num_steps to be in [10, 100] got {num_steps}.")
        
        aspect_ratio_numerator, aspect_ratio_denominator = map(int, aspect_ratio.split(":"))
        float_aspect_ratio = aspect_ratio_numerator / aspect_ratio_denominator

        access_token = await self.get_access_token()
        
        async with self.lock:
            response = await self.session.post(
                url = "https://api.mage.space/api/v3/images/generate",
                headers = {
                    "accept": "application/json",
                    "authorization": access_token,
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
                    "easy_mode": False,
                    "is_public": True
                })
            )
    
        content =  await response.json()
        result, = content["results"]

        return result
    
    def __del__(self):
        self.session.loop.create_task(
            self.session.close()
        )