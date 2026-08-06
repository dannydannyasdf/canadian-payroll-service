from datetime import date


class DuplicatePayPeriodError(Exception):
    """Raised when the same pay period is submitted more than once for an employee."""

    def __init__(
        self,
        *,
        employee_sin: str,
        period_start: date,
        period_end: date,
    ) -> None:
        self.employee_sin = employee_sin
        self.period_start = period_start
        self.period_end = period_end
        super().__init__(
            f"Pay period {period_start} to {period_end} was already submitted "
            f"for employee SIN {employee_sin}. Duplicate submissions would inflate YTD totals."
        )
