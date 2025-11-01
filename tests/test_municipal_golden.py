import datetime as dt
import pytest

# Canonical scenario format:
# city, maker_profile, kitchen_profile, booking, expected_verdict, expected_reasons_subset
SCENARIOS = [
  # --- SAN FRANCISCO (12) ---
  {
    "name": "SF happy path — all permits, insurance, zoning notice, non-quiet hours",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T13:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW","reasons":[]}
  },
  {
    "name": "SF deny — missing §6.15 shared_kitchen permit",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["fire","ventilation"], "zoning":{"code":"M-1","notice_doc":False}},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["permit.shared_kitchen.missing"]}
  },
  {
    "name": "SF conditions — neighborhood notice missing",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"PDR-1-D","notice_doc":False}},
    "booking": {"start":"2025-11-05T09:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["zoning.notice.required"]}
  },
  {
    "name": "SF deny — quiet hours violation",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}},
    "booking": {"start":"2025-11-05T22:30:00-08:00","end":"2025-11-05T23:30:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["sound.quiet_hours"]}
  },
  {
    "name": "SF conditions — daily rental hour cap reached",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}, "hours_booked_today": 10},
    "booking": {"start":"2025-11-05T12:00:00-08:00","end":"2025-11-05T15:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["rental.limit.daily_cap_near"]}
  },
  {
    "name": "SF deny — insurance lacks additional insured phrase",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"Some Other Entity"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["insurance.additional_insured.mismatch"]}
  },
  {
    "name": "SF deny — scheduled health inspection overlap",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}, "inspection":{"start":"2025-11-05T11:00:00-08:00","end":"2025-11-05T12:00:00-08:00"}},
    "booking": {"start":"2025-11-05T10:30:00-08:00","end":"2025-11-05T12:30:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["calendar.inspection.conflict"]}
  },
  {
    "name": "SF conditions — ADA not accessible for ADA-required maker",
    "city": "san_francisco",
    "maker": {"requires_ada": True, "coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}, "ada_accessible": False},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["ada.accessibility.required"]}
  },
  {
    "name": "SF deny — ventilation cert missing",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire"], "zoning":{"code":"NC-3","notice_doc":True}},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["permit.ventilation.missing"]}
  },
  {
    "name": "SF conditions — grease interceptor service overdue",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}, "grease_overdue": True},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["grease.service.overdue"]}
  },
  {
    "name": "SF deny — fire permit missing",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}},
    "booking": {"start":"2025-11-05T10:00:00-08:00","end":"2025-11-05T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["permit.fire.missing"]}
  },
  {
    "name": "SF deny — quiet hours pre-dawn",
    "city": "san_francisco",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City and County of San Francisco"}},
    "kitchen": {"permits":["shared_kitchen","fire","ventilation"], "zoning":{"code":"NC-3","notice_doc":True}},
    "booking": {"start":"2025-11-05T05:30:00-08:00","end":"2025-11-05T07:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["sound.quiet_hours"]}
  },

  # --- PORTLAND (12) ---
  {
    "name": "PDX happy path — commissary permit + community notice + COI ok",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW","reasons":[]}
  },
  {
    "name": "PDX deny — missing community notification",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": False},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["community.notice.required"]}
  },
  {
    "name": "PDX conditions — lodging tax applied",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"baked_goods","fees_required": True},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["fees.lodging.assessed"]}
  },
  {
    "name": "PDX deny — COI missing aggregate limit",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["insurance.aggregate.min"]}
  },
  {
    "name": "PDX deny — inspection overlap",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "inspection":{"start":"2025-11-06T10:30:00-08:00","end":"2025-11-06T11:30:00-08:00"}},
    "booking": {"start":"2025-11-06T10:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["calendar.inspection.conflict"]}
  },
  {
    "name": "PDX conditions — ADA required, facility not accessible",
    "city": "portland",
    "maker": {"requires_ada": True, "coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True, "ada_accessible": False},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["ada.accessibility.required"]}
  },
  {
    "name": "PDX deny — ventilation cert missing",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["permit.ventilation.missing"]}
  },
  {
    "name": "PDX conditions — grease service overdue",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True, "grease_overdue": True},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["grease.service.overdue"]}
  },
  {
    "name": "PDX deny — quiet hours",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T22:15:00-08:00","end":"2025-11-06T23:15:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["sound.quiet_hours"]}
  },
  {
    "name": "PDX conditions — maintenance window buffer",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True, "maintenance":{"start":"2025-11-06T12:10:00-08:00","end":"2025-11-06T13:10:00-08:00"}},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["calendar.maintenance.buffer_required"]}
  },
  {
    "name": "PDX deny — fire permit missing",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","ventilation"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T09:00:00-08:00","end":"2025-11-06T11:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["permit.fire.missing"]}
  },
  {
    "name": "PDX deny — quiet hours pre-dawn",
    "city": "portland",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Portland and Multnomah County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"], "community_notice_doc": True},
    "booking": {"start":"2025-11-06T05:30:00-08:00","end":"2025-11-06T07:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["sound.quiet_hours"]}
  },

  # --- SEATTLE (12) ---
  {
    "name": "SEA happy path — TFE/commissary permits + COI + fees",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"]},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"ALLOW","reasons":[]}
  },
  {
    "name": "SEA deny — missing TFE",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["commissary","fire","ventilation"]},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["permit.tfe.missing"]}
  },
  {
    "name": "SEA conditions — lodging + B&O applied",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"]},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"baked_goods","fees_required": True},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["fees.lodging.assessed","fees.bo.assessed"]}
  },
  {
    "name": "SEA deny — quiet hours",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"]},
    "booking": {"start":"2025-11-07T22:30:00-08:00","end":"2025-11-07T23:30:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["sound.quiet_hours"]}
  },
  {
    "name": "SEA deny — additional insured phrase mismatch",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"Wrong String"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"]},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["insurance.additional_insured.mismatch"]}
  },
  {
    "name": "SEA conditions — seasonal restriction (outdoor cooking)",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"]},
    "booking": {"start":"2025-12-20T10:00:00-08:00","end":"2025-12-20T12:00:00-08:00","product_type":"outdoor_cooking"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["seasonal.restriction.notice"]}
  },
  {
    "name": "SEA deny — inspection failed auto-unlisted",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"], "inspection_result":"fail"},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["inspection.failed.unlisted"]}
  },
  {
    "name": "SEA conditions — grease overdue",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"], "grease_overdue": True},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["grease.service.overdue"]}
  },
  {
    "name": "SEA conditions — ADA requirement not met",
    "city": "seattle",
    "maker": {"requires_ada": True, "coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"], "ada_accessible": False},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"ALLOW_WITH_CONDITIONS","reasons":["ada.accessibility.required"]}
  },
  {
    "name": "SEA deny — maintenance overlap",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"], "maintenance":{"start":"2025-11-07T11:00:00-08:00","end":"2025-11-07T12:00:00-08:00"}},
    "booking": {"start":"2025-11-07T10:30:00-08:00","end":"2025-11-07T12:30:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["calendar.maintenance.conflict"]}
  },
  {
    "name": "SEA deny — commissary permit missing",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","fire","ventilation"]},
    "booking": {"start":"2025-11-07T10:00:00-08:00","end":"2025-11-07T12:00:00-08:00","product_type":"baked_goods"},
    "expect": {"verdict":"DENY","reasons":["permit.commissary.missing"]}
  },
  {
    "name": "SEA deny — quiet hours pre-dawn",
    "city": "seattle",
    "maker": {"coi":{"general":1_000_000,"aggregate":2_000_000,"ai":"City of Seattle and King County"}},
    "kitchen": {"permits":["TFE","commissary","fire","ventilation"]},
    "booking": {"start":"2025-11-07T06:30:00-08:00","end":"2025-11-07T08:00:00-08:00","product_type":"meal_prep"},
    "expect": {"verdict":"DENY","reasons":["sound.quiet_hours"]}
  },
]

@pytest.mark.parametrize("case", SCENARIOS, ids=[c["name"] for c in SCENARIOS])
def test_city_rules_golden(case):
    from apps.policy.evaluator import evaluate_booking

    verdict, reasons = evaluate_booking(
        city=case["city"],
        maker=case["maker"],
        kitchen=case["kitchen"],
        booking=case["booking"],
        now=dt.datetime(2025, 11, 5, 9, 0)
    )

    assert verdict == case["expect"]["verdict"]
    for r in case["expect"]["reasons"]:
        assert r in reasons
