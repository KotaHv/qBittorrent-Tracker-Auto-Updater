from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type Source = str
type Trackers = list[str]
type Sources = dict[Source, Trackers]


@dataclass(frozen=True)
class FetchSuccess:
    url: str
    trackers: Trackers


@dataclass(frozen=True)
class FetchFailure:
    url: str


type FetchResult = FetchSuccess | FetchFailure
type FetchResults = dict[Source, FetchResult]
type StrictFetchResults = dict[Source, FetchSuccess]


class TrackerState(BaseModel):
    """In-memory tracker state persisted to the state file."""

    model_config = ConfigDict(validate_assignment=True)

    schema_version: Literal[1] = 1
    sources: Sources = Field(default_factory=dict)
    last_committed: Trackers = Field(default_factory=list)
    updated_at: datetime | None = None
