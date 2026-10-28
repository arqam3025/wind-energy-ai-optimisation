import cvxpy as cp

MAX_POWER = 1000.0

cases = [
    ("A", 100.0, 300.0, 200.0, 100.0, 0.0),
    ("B", 500.0, 300.0, 250.0, 300.0, 200.0),
    ("C", 800.0, 300.0, 200.0, 300.0, 200.0),
]

for name, wind, charge_request, curtail_request, expected_charge, expected_curtail in cases:
    charge = cp.Variable(nonneg=True)
    curtail = cp.Variable(nonneg=True)

    charge_selector = cp.Variable(boolean=True)
    curtail_selector = cp.Variable(boolean=True)

    big_m = MAX_POWER + max(wind, MAX_POWER)

    remaining_wind = wind - charge

    constraints = [
        charge <= charge_request,
        charge <= wind,
        charge >= charge_request - big_m * charge_selector,
        charge >= wind - big_m * (1 - charge_selector),

        curtail <= curtail_request,
        curtail <= remaining_wind,
        curtail >= curtail_request - big_m * curtail_selector,
        curtail >= remaining_wind - big_m * (1 - curtail_selector),
    ]

    problem = cp.Problem(cp.Minimize(0), constraints)
    problem.solve(solver=cp.HIGHS)

    if problem.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(
            f"Test {name} failed: solver status {problem.status}"
        )

    actual_charge = float(charge.value)
    actual_curtail = float(curtail.value)

    passed = (
        abs(actual_charge - expected_charge) < 0.01
        and abs(actual_curtail - expected_curtail) < 0.01
    )

    print(
        f"Test {name}: "
        f"charge={actual_charge:.3f} kW, "
        f"curtail={actual_curtail:.3f} kW, "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        raise AssertionError(f"Test {name} produced incorrect dispatch")

print("ALL STEP 120 TESTS PASSED")
