from __future__ import annotations

__all__ = (
    "Submission",
    "MultiChoiceSubmission",
)

from dataclasses import dataclass
import datetime

import discord


@dataclass(kw_only=True)
class Submission:
    user: discord.User | discord.Member
    time_taken: datetime.timedelta

    def __lt__(self, other: Submission) -> bool:
        return self.time_taken > other.time_taken


@dataclass(kw_only=True)
class MultiChoiceSubmission(Submission):
    success: bool
    answer: str

    def __lt__(self, other: Submission) -> bool:
        if not isinstance(other, MultiChoiceSubmission):
            raise NotImplementedError
        return (self.success, -self.time_taken) < (other.success, -other.time_taken)
        