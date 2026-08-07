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


class DuplicateEmployerError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Employer {name!r} already exists.")


class DuplicateEmployeeError(Exception):
    def __init__(self, sin: str, employer_id: int) -> None:
        self.sin = sin
        self.employer_id = employer_id
        super().__init__(f"Employee with SIN {sin} already exists for employer {employer_id}.")


class EmployerNotFoundError(Exception):
    def __init__(self, employer_id: int) -> None:
        self.employer_id = employer_id
        super().__init__(f"Employer {employer_id} not found.")


class OnboardingEmployeeNotFoundError(Exception):
    def __init__(self, employer_id: int, employee_id: int) -> None:
        self.employer_id = employer_id
        self.employee_id = employee_id
        super().__init__(f"Employee {employee_id} not found for employer {employer_id}.")


class InactiveEmployerError(Exception):
    def __init__(self, employer_id: int) -> None:
        self.employer_id = employer_id
        super().__init__(f"Employer {employer_id} is inactive.")


class InactiveEmployeeError(Exception):
    def __init__(self, employee_id: int) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee {employee_id} is inactive.")


class EmployerNameLockedError(Exception):
    def __init__(self, employer_id: int) -> None:
        self.employer_id = employer_id
        super().__init__(
            f"Employer {employer_id} name cannot be changed after pay stubs have been submitted."
        )


class PayrollIdentityMismatchError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
