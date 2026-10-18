import json
from pathlib import Path
from langchain_core.tools import tool

HRMS = Path(__file__).resolve().parent.parent / "data" / "hrms_mock.json"


@tool
def get_leave_balance(employee_id: str) -> dict:
    """Return remaining leave balances for an employee from the HRMS."""
    data = json.loads(HRMS.read_text())
    emp = data.get(employee_id)
    if not emp:
        return {"error": f"Employee {employee_id} not found"}
    return emp
