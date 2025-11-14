from __future__ import annotations

from datetime import UTC, datetime

from prep.compliance.dol_reg_compliance_engine import DOLRegComplianceEngine


def test_dol_engine_initialization() -> None:
    engine = DOLRegComplianceEngine()
    assert engine.name == "DOL_Reg_Compliance_Engine"
    assert len(engine.rules) >= 5


def test_overtime_validation() -> None:
    engine = DOLRegComplianceEngine()
    data = {
        "employees": [
            {
                "id": "emp1",
                "hours_worked": 45,
                "hourly_rate": 20,
                "overtime_paid": 100,
            }
        ]
    }

    violations = engine.validate(data)
    overtime = [v for v in violations if v.rule_id == "dol_overtime_1"]
    assert len(overtime) == 1
    assert overtime[0].severity == "critical"
    assert all(v.timestamp.tzinfo == UTC for v in overtime)


def test_minimum_wage_validation() -> None:
    engine = DOLRegComplianceEngine()
    data = {
        "employees": [
            {
                "id": "emp1",
                "hourly_rate": 6.0,
            }
        ]
    }
    violations = engine.validate(data)
    minimum = [v for v in violations if v.rule_id == "dol_minimum_wage_1"]
    assert len(minimum) == 1
    assert minimum[0].severity == "critical"
    assert all(v.timestamp.tzinfo == UTC for v in minimum)


def test_child_labor_validation() -> None:
    engine = DOLRegComplianceEngine()
    data = {
        "employees": [
            {
                "id": "emp1",
                "age": 13,
            }
        ]
    }
    violations = engine.validate(data)
    child_labor = [v for v in violations if v.rule_id == "dol_child_labor_1"]
    assert len(child_labor) == 1
    assert child_labor[0].severity == "critical"
    assert all(v.timestamp.tzinfo == UTC for v in child_labor)


def test_record_keeping_validation() -> None:
    engine = DOLRegComplianceEngine()
    data = {
        "payroll_records": [
            {"id": "rec1", "created_date": "invalid-date"},
            {"id": "rec2", "created_date": None},
            {"id": "rec3", "created_date": datetime.now(UTC)},
        ]
    }

    violations = engine.validate(data)
    record = [v for v in violations if v.rule_id == "dol_record_keeping_1"]
    assert len(record) == 2
    assert all(v.timestamp.tzinfo == UTC for v in record)


def test_break_validation() -> None:
    engine = DOLRegComplianceEngine()
    data = {
        "employees": [
            {
                "id": "emp1",
                "hours_worked": 9,
                "breaks_taken": 0,
            }
        ]
    }

    violations = engine.validate(data)
    breaks = [v for v in violations if v.rule_id == "dol_break_1"]
    assert len(breaks) == 1
    assert all(v.timestamp.tzinfo == UTC for v in breaks)
