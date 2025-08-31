import pulp


def solve_rawmix(
	RM,
	DUST,
	ASH,
	costs,
	bounds,
	pSilo,
	pKiln,
	tonKF,
	clinkerTPH,
	dust_ratio,
	totalAshTPH,
	LSF_min, LSF_max,
	SM_min, SM_max,
	AM_min, AM_max,
	NaEq_max,
	C3S_min, C3S_max,
	FCaO_cl=1.0,
	epsilon=1e-3,
	objective_mode="feasibility",
):
	# 1) constants
	tonDustLoss = dust_ratio * clinkerTPH
	D = tonKF - tonDustLoss + totalAshTPH

	# 2) model
	m = pulp.LpProblem("RawMix_ClinkerQuality", pulp.LpMinimize)

	# 3) decision vars
	x = {k: pulp.LpVariable(k, lowBound=bounds[k][0], upBound=bounds[k][1]) for k in bounds}

	# 4) sum to 100
	m += pulp.lpSum(x.values()) == 100, "Sum100"

	# 5) raw meal oxides
	def ox_rm(ox):
		return pulp.lpSum(x[k] * RM[k][ox] for k in x) / 100.0

	Si_RM, Al_RM = ox_rm("SiO2"), ox_rm("Al2O3")
	Fe_RM, Ca_RM = ox_rm("Fe2O3"), ox_rm("CaO")
	K_RM, Na_RM = ox_rm("K2O"), ox_rm("Na2O")
	LOI_RM = ox_rm("LOI")

	# 6) kiln feed
	if pSilo > 0:
		Si_KF = (1 - pSilo) * Si_RM + pSilo * DUST["SiO2"]
		Al_KF = (1 - pSilo) * Al_RM + pSilo * DUST["Al2O3"]
		Fe_KF = (1 - pSilo) * Fe_RM + pSilo * DUST["Fe2O3"]
		Ca_KF = (1 - pSilo) * Ca_RM + pSilo * DUST["CaO"]
		K_KF = (1 - pSilo) * K_RM + pSilo * DUST["K2O"]
		Na_KF = (1 - pSilo) * Na_RM + pSilo * DUST["Na2O"]
		LOI_KF = (1 - pSilo) * LOI_RM + pSilo * DUST["LOI"]
	else:
		denom = 1 + pKiln
		Si_KF = (Si_RM + pKiln * DUST["SiO2"]) / denom
		Al_KF = (Al_RM + pKiln * DUST["Al2O3"]) / denom
		Fe_KF = (Fe_RM + pKiln * DUST["Fe2O3"]) / denom
		Ca_KF = (Ca_RM + pKiln * DUST["CaO"]) / denom
		K_KF = (K_RM + pKiln * DUST["K2O"]) / denom
		Na_KF = (Na_RM + pKiln * DUST["Na2O"]) / denom
		LOI_KF = (LOI_RM + pKiln * DUST["LOI"]) / denom

	# 7) unignited
	def ox_u(Ox_KF, name):
		return ((Ox_KF * tonKF) - (DUST[name] * tonDustLoss) + (ASH[name] * totalAshTPH)) / D

	Si_u, Al_u, Fe_u, Ca_u = (
		ox_u(Si_KF, "SiO2"),
		ox_u(Al_KF, "Al2O3"),
		ox_u(Fe_KF, "Fe2O3"),
		ox_u(Ca_KF, "CaO"),
	)
	K_u, Na_u = ox_u(K_KF, "K2O"), ox_u(Na_KF, "Na2O")
	LOI_u = ((LOI_KF * tonKF) - (DUST["LOI"] * tonDustLoss) + (ASH["LOI"] * totalAshTPH)) / D
	Z = 100 - LOI_u
	Ca_u_eff = Ca_u - FCaO_cl * (Z / 100.0)
	C3S_lin = 4.07 * Ca_u_eff - 7.60 * Si_u - 6.72 * Al_u - 1.43 * Fe_u

	# 8) constraints
	m += Ca_u >= (LSF_min / 100.0) * (2.8 * Si_u + 1.18 * Al_u + 0.65 * Fe_u)
	m += Ca_u <= (LSF_max / 100.0) * (2.8 * Si_u + 1.18 * Al_u + 0.65 * Fe_u)

	m += Si_u >= SM_min * (Al_u + Fe_u)
	m += Si_u <= SM_max * (Al_u + Fe_u)

	m += Al_u >= AM_min * Fe_u
	m += Al_u <= AM_max * Fe_u

	m += (Na_u + 0.658 * K_u) <= NaEq_max * (Z / 100.0)

	m += C3S_lin >= C3S_min * (Z / 100.0)
	m += C3S_lin <= C3S_max * (Z / 100.0)

	# 9) objective
	if objective_mode == "cost":
		m += pulp.lpSum(x[k] * costs[k] for k in x)
	else:
		m += epsilon * pulp.lpSum(x[k] * costs[k] for k in x)

	# 10) solve
	status = m.solve(pulp.PULP_CBC_CMD(msg=False))
	sol = {k: x[k].value() for k in x}
	return status, sol, {
		"C3S_lin": C3S_lin.value(),
		"Z": Z.value(),
		"LOI_u": LOI_u.value(),
	}
