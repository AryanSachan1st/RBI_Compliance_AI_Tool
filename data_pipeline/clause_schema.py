from typing import Literal

from pydantic import BaseModel, Field


class SubSubItem(BaseModel):
    """Third nesting level, e.g. (i), (ii) inside a lettered sub-item. Rare but occurs
    in some RBI/IRDAI clauses (e.g. 3(a)(i))."""

    ref: str = Field(description="The sub-sub-item marker as written, e.g. 'i', 'ii'.")
    text: str = Field(
        description="Text of this sub-sub-item only, not including children."
    )


class SubItem(BaseModel):
    """Second nesting level, e.g. (a), (b), (c) inside a numbered clause."""

    ref: str = Field(description="The sub-item marker as written, e.g. 'a', 'b', 'f'.")
    text: str = Field(
        description="Text of this sub-item. If it has no further nested items, put the "
        "complete text here and leave sub_items empty."
    )
    sub_items: list[SubSubItem] = Field(
        default_factory=list,
        description="Further nested items like (i), (ii) if this sub-item breaks down further. "
        "Empty list if none.",
    )


class ClauseItem(BaseModel):
    item_type: Literal["clause", "table", "annexure_form", "chapter_heading"]
    chapter: str = Field(
        description="Chapter or Part name this item belongs to, e.g. 'Chapter II - Office of the Internal Ombudsman'. Use empty string if the document has no chapters."
    )
    clause_number: str = Field(
        description="The clause/paragraph number as written in the doc, e.g. '4' or '4.1'. Use empty string for tables/annexures/chapter headings that have no clause number."
    )
    heading: str = Field(
        description="Short heading/title of this clause if one exists, e.g. 'Definitions'. Empty string if none."
    )
    chapeau_text: str = Field(
        description="The clause's lead-in text BEFORE any lettered/numbered sub-items begin, "
        "e.g. 'In this Direction, unless the context otherwise requires -'. If the clause has "
        "NO sub-items at all, put the clause's complete text here and leave sub_items empty."
    )
    sub_items: list[SubItem] = Field(
        default_factory=list,
        description="Lettered/numbered sub-items like (a), (b), (c) belonging to this clause. "
        "Empty list if the clause has no sub-items (in that case chapeau_text holds everything).",
    )

    def full_text(self) -> str:
        """Reconstructs the flat text of this clause -- computed in code, not by the LLM,
        so there's a single source of truth (the structured fields) and no risk of the
        flat and structured versions disagreeing."""
        parts = [self.chapeau_text]
        for sub in self.sub_items:
            parts.append(f"({sub.ref}) {sub.text}")
            for subsub in sub.sub_items:
                parts.append(f"    ({subsub.ref}) {subsub.text}")
        return "\n".join(p for p in parts if p)


class ExtractedDocument(BaseModel):
    items: list[ClauseItem] = Field(
        description="All clauses, tables, and annexures found in the document, in document order."
    )
