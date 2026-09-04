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

        # Aggregate specific-course-credit ranking is completely supported by
        # canonical curriculum facts. Use the deterministic path first so this
        # answer cannot become blank or gain unsupported extra course claims.
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

        # The recurring AIT-vs-DSBA AI/Data decision question is also fully
        # answerable from canonical evidence. Prefer this deterministic path
        # over free-form generation to avoid upstream failures and unsupported
        # recommendations in competition CSV output.
        if route.comparison and len(route.programs) >= 2:
            fallback = deterministic_ait_dsba_compare(
                question,
                self.evidence,
                route.programs,
            )
            if fallback is not None:
                return fallback

            try:
                result = super().ask(question, forced_program=forced_program)
                if not str(getattr(result, "answer", "") or "").strip():
                    return nonempty_error_result(question, "empty comparison answer")
                return result
            except Exception as exc:
                return nonempty_error_result(question, str(exc))

        try:
            result = super().ask(question, forced_program=forced_program)
            if not str(getattr(result, "answer", "") or "").strip():
                return nonempty_error_result(question, "empty answer")
            return result
        except Exception as exc:
            return nonempty_error_result(question, str(exc))
