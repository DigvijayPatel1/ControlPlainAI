from app.services.budget_service import BudgetService


def test_budget_service_exists():
    assert BudgetService() is not None
