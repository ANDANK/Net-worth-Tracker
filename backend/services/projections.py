"""Projection engine for retirement and wealth modeling."""
from calculations.metrics import project_portfolio, fire_number, coast_fire
from models.schemas import ProjectionScenario, ProjectionResult


def run_projection(scenario: ProjectionScenario) -> ProjectionResult:
    years_to_retirement = scenario.target_age - scenario.current_age
    if years_to_retirement <= 0:
        years_to_retirement = 30

    nominal, real = project_portfolio(
        current_value=scenario.current_value,
        monthly_contribution=scenario.monthly_contribution,
        annual_return=scenario.annual_return / 100,
        inflation=scenario.inflation / 100,
        years=years_to_retirement,
    )

    years = list(range(scenario.current_age + 1, scenario.target_age + 1))

    fire_target = fire_number(scenario.monthly_contribution * 12 * 25)
    fire_age = None
    for i, val in enumerate(nominal):
        if val >= fire_target:
            fire_age = scenario.current_age + i + 1
            break

    coast_value = coast_fire(
        target=nominal[-1] if nominal else 0,
        current_age=scenario.current_age,
        retirement_age=scenario.target_age,
        annual_return=scenario.annual_return / 100,
    )

    return ProjectionResult(
        scenario_name=scenario.scenario_name,
        years=years,
        nominal_values=nominal,
        real_values=real,
        fire_age=fire_age,
        coast_fire_value=round(coast_value, 2),
        target_value=nominal[-1] if nominal else None,
    )


def save_projection(scenario: ProjectionScenario, result: ProjectionResult) -> None:
    from google_sheets.client import sheets_client
    row = [
        scenario.scenario_name,
        scenario.annual_return,
        scenario.inflation,
        scenario.monthly_contribution,
        scenario.target_age,
        result.target_value or 0,
    ]
    sheets_client.append_row("projections", row)
