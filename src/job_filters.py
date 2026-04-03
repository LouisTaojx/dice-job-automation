from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class JobFilterDecision:
    should_skip: bool
    reason: str = ""


class DiceJobFilter:
    CLEARANCE_PATTERNS = (
        re.compile(r"\bclearance\b", re.IGNORECASE),
        re.compile(r"\bclearence\b", re.IGNORECASE),
        re.compile(r"\bsecret\s+clear(?:ance|ence)?\b", re.IGNORECASE),
        re.compile(r"\btop\s+secret\b", re.IGNORECASE),
        re.compile(r"\bpublic\s+trust\b", re.IGNORECASE),
        re.compile(r"\bts\s*/\s*sci\b", re.IGNORECASE),
        re.compile(r"\bsecurity\s+clear(?:ance|ence)?\b", re.IGNORECASE),
    )

    CITIZENSHIP_PATTERNS = (
        re.compile(
            r"\b(?:usc|u\.?s\.?\s*citizen(?:s)?|citizen(?:s)?|green\s*card(?:\s*holder(?:s)?)?|gc(?:\s*holder(?:s)?)?)\b"
            r"[^\n.]{0,30}\b(?:only|required|must|needed|need|needs)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:only|required|must|needed|need|needs|looking\s+for|seeking)\b[^\n.]{0,40}"
            r"\b(?:usc|u\.?s\.?\s*citizen(?:s)?|citizen(?:s)?|green\s*card(?:\s*holder(?:s)?)?|gc(?:\s*holder(?:s)?)?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:gc|green\s*card)\s*/\s*(?:usc|u\.?s\.?\s*citizen(?:s)?)\b", re.IGNORECASE),
        re.compile(r"\b(?:usc|u\.?s\.?\s*citizen(?:s)?)\s*/\s*(?:gc|green\s*card)\b", re.IGNORECASE),
        re.compile(r"\b(?:usc|u\.?s\.?\s*citizen(?:s)?|citizen(?:s)?)\s+only\b", re.IGNORECASE),
        re.compile(r"\b(?:gc|green\s*card(?:\s*holder(?:s)?)?)\s+only\b", re.IGNORECASE),
    )

    def evaluate_title_only(self, job_title: str) -> JobFilterDecision:
        combined_text = self._combine_text(job_title)
        return self._evaluate_hard_blockers(combined_text)

    def evaluate(self, job_title: str = "", page_title: str = "", page_text: str = "") -> JobFilterDecision:
        combined_text = self._combine_text(job_title, page_title, page_text)
        return self._evaluate_hard_blockers(combined_text)

    def _evaluate_hard_blockers(self, combined_text: str) -> JobFilterDecision:
        if self._matches_any(self.CLEARANCE_PATTERNS, combined_text):
            return JobFilterDecision(
                should_skip=True,
                reason="clearance requirement",
            )

        if self._matches_any(self.CITIZENSHIP_PATTERNS, combined_text):
            return JobFilterDecision(
                should_skip=True,
                reason="GC / USC requirement",
            )

        return JobFilterDecision(should_skip=False)

    def _matches_any(self, patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    def _combine_text(self, *parts: str) -> str:
        return "\n".join(part for part in parts if part)
