from __future__ import annotations

from .batch_fallback import (
    deterministic_ait_dsba_compare,
    deterministic_structure_ranking,
    nonempty_error_result,
)
from .hard_policy import is_all_program_question
from .policy_pipeline import ALL_PROGRAMS, PolicyCompetitionPipeline
from .router import route_question


class ResilientCompetitionPipeline(PolicyCompetitionPipeline):
    """Competition pipeline with deterministic fallbacks for batch-critical cases."""

    def ask(self, question: str, forced_program: str | None = None):
        question = (question or "").strip()

        # Aggregate specific-course-credit ranking is fully supported by
        # canonical evidence and should never depend on an upstream LLM call.
        if is_all_program_question(question):
            ranked = deterministic_structure_ranking(
                question,
                self.evidence,
                ALL_PROGRAMS.copy(),
            )
            if ranked is not None:
                return ranked

        route = route_question(
            question,
            self.catalog,
            forced_program=forced_program,
        )

        # The AIT-vs-DSBA AI/Data decision case has a deterministic evidence-only
        # fallback. Try the normal ThaiLLM compare path first, but never return an
        # empty row if the upstream endpoint fails.
        if route.comparison and len(route.programs) >= 2:
            try:
                return super().ask(question, forced_program=forced_program)
            except Exception as exc:
                fallback = deterministic_ait_dsba_compare(
                    question,
                    self.evidence,
                    route.programs,
                )
                if fallback is not None:
                    fallback.debug = {
                        **(fallback.debug or {}),
                        "upstream_error": str(exc),
                    }
                    return fallback
                return nonempty_error_result(question, str(exc))

        try:
            return super().ask(question, forced_program=forced_program)
        except Exception as exc:
            return nonempty_error_result(question, str(exc))
