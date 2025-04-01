from typing import Dict, List, TypeAlias, TypedDict


class DataSource(TypedDict):
    """A data source for a knowledge base."""

    id: str
    name: str


class KnowledgeBase(TypedDict):
    """A knowledge base."""

    name: str
    data_sources: List[DataSource]


KnowledgeBaseMapping: TypeAlias = Dict[str, KnowledgeBase]
