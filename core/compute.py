from typing import List, Dict


def compute_alternative_fuel_heat_percentage(fuels: List[Dict]) -> float:
	"""Calculate the proportional heat % from alternative fuels (100 - Fine Coal %).
	Based on calorific value contribution, not just mass proportion.
	"""
	total_heat = 0.0
	fine_coal_heat = 0.0
	
	for fuel in fuels:
		fuel_name = str(fuel.get("Fuel", "")).strip().lower()
		prop = fuel.get("prop", 0.0) or 0.0
		cv = fuel.get("cv", 0.0) or 0.0
		heat_contribution = prop * cv
		
		total_heat += heat_contribution
		
		# Check if this is Fine Coal (case insensitive)
		if "fine coal" in fuel_name or "finecoal" in fuel_name.replace(" ", ""):
			fine_coal_heat += heat_contribution
	
	if total_heat == 0:
		return 0.0
	
	# Alternative fuel heat % = 100 - Fine Coal heat %
	fine_coal_percentage = (fine_coal_heat / total_heat) * 100
	alternative_fuel_percentage = 100 - fine_coal_percentage
	
	return alternative_fuel_percentage


def compute_cv_total(fuels: List[Dict]) -> float:
	num = sum((f.get("prop", 0.0) or 0.0) * (f.get("cv", 0.0) or 0.0) for f in fuels)
	den = sum((f.get("prop", 0.0) or 0.0) for f in fuels) or 1.0
	return num / (den or 1.0)


def compute_total_fuel_tph(stec: float, clinker_tph: float, cv_total: float) -> float:
	cv = cv_total or 1.0
	return (stec * clinker_tph) / cv


def compute_total_ash_tph(fuels: List[Dict], total_fuel_tph: float) -> float:
	return sum(((f.get("ash", 0.0) or 0.0) / 100.0) * ((f.get("prop", 0.0) or 0.0) / 100.0) * total_fuel_tph for f in fuels)


def compute_ash_composition(fuels: List[Dict]) -> Dict[str, float]:
	"""Weighted by (prop% * ash%). Unknown oxides default to 0.
	Expected per fuel oxide keys: SiO2, Al2O3, Fe2O3, CaO, K2O, Na2O, LOI
	"""
	ox_keys = ["SiO2", "Al2O3", "Fe2O3", "CaO", "K2O", "Na2O", "LOI"]
	weights = [((f.get("ash", 0.0) or 0.0) / 100.0) * ((f.get("prop", 0.0) or 0.0) / 100.0) for f in fuels]
	total_w = sum(weights) or 1.0
	res = {}
	for ox in ox_keys:
		res[ox] = sum((weights[i] / total_w) * (fuels[i].get(ox, 0.0) or 0.0) for i in range(len(fuels)))
	return res


def calculate_all_stages(RM: Dict[str, Dict[str, float]], x_percent: Dict[str, float], 
                        dust: Dict[str, float], pSilo: float, pKiln: float, 
                        tonKF: float, clinker_tph: float, dust_ratio: float, 
                        ASH: Dict[str, float], FCaO_cl: float = 1.0):
	"""Calculate compositions for all stages: Raw Meal → Kiln Feed → Unignited → Clinker"""
	
	# Raw Meal composition
	def ox_rm(ox: str) -> float:
		return sum((x_percent.get(k, 0.0) or 0.0) * (RM[k].get(ox, 0.0) or 0.0) for k in x_percent) / 100.0
	
	rm = {}
	for ox in ["SiO2", "Al2O3", "Fe2O3", "CaO", "K2O", "Na2O", "LOI"]:
		rm[ox] = ox_rm(ox)
	
	# Kiln Feed composition
	if pSilo > 0:
		# Dust → Silo scenario
		kf = {}
		for ox in rm:
			kf[ox] = (1 - pSilo) * rm[ox] + pSilo * (dust.get(ox, 0.0) or 0.0)
	else:
		# Dust → Kiln scenario
		den = 1 + pKiln
		kf = {}
		for ox in rm:
			kf[ox] = (rm[ox] + pKiln * (dust.get(ox, 0.0) or 0.0)) / den
	
	# Unignited composition
	tonDustLoss = dust_ratio * clinker_tph
	totalAshTPH = ASH.get('total_ash_tph', 0.0) if ASH else 0.0  # Get from ASH dict or calculate
	D = tonKF - tonDustLoss + totalAshTPH
	
	u = {}
	for ox in rm:
		# Include ash contribution in unignited calculation
		ash_contrib = (ASH.get(ox, 0.0) or 0.0) * totalAshTPH if ASH else 0.0
		u[ox] = ((kf[ox] * tonKF) - ((dust.get(ox, 0.0) or 0.0) * tonDustLoss) + ash_contrib) / (D if D != 0 else 1.0)
	
	# Clinker composition (LOI-free)
	Z = 100 - u["LOI"]
	cl = {}
	for ox in rm:
		if ox == "LOI":
			cl[ox] = 0.0
		else:
			cl[ox] = (u[ox] / (Z if Z != 0 else 1.0)) * 100.0
	
	# Add Free Lime to clinker
	cl["FCaO"] = FCaO_cl
	
	return {
		"raw_meal": rm,
		"kiln_feed": kf,
		"unignited": u,
		"clinker": cl,
		"Z": Z,
		"tonDustLoss": tonDustLoss
	}


def compute_bogue(cl: Dict[str, float]) -> Dict[str, float]:
	CaO_eff = (cl.get("CaO", 0.0) or 0.0) - (cl.get("FCaO", 0.0) or 0.0)
	C3S = 4.07 * CaO_eff - 7.60 * (cl.get("SiO2", 0.0) or 0.0) - 6.72 * (cl.get("Al2O3", 0.0) or 0.0) - 1.43 * (cl.get("Fe2O3", 0.0) or 0.0)
	C4AF = 3.04 * (cl.get("Fe2O3", 0.0) or 0.0)
	C3A = 2.65 * (cl.get("Al2O3", 0.0) or 0.0) - 1.69 * (cl.get("Fe2O3", 0.0) or 0.0)
	C2S = 2.87 * (cl.get("SiO2", 0.0) or 0.0) - 0.7544 * C3S
	return {"C3S": C3S, "C2S": C2S, "C3A": C3A, "C4AF": C4AF}


def calculate_quality_moduli(composition: Dict[str, float]) -> Dict[str, float]:
	"""Calculate LSF, SM, AM, NaEq for any composition"""
	SiO2 = composition.get("SiO2", 0.0) or 0.0
	Al2O3 = composition.get("Al2O3", 0.0) or 0.0
	Fe2O3 = composition.get("Fe2O3", 0.0) or 0.0
	CaO = composition.get("CaO", 0.0) or 0.0
	K2O = composition.get("K2O", 0.0) or 0.0
	Na2O = composition.get("Na2O", 0.0) or 0.0
	
	# LSF
	denom = 2.8 * SiO2 + 1.18 * Al2O3 + 0.65 * Fe2O3
	LSF = (CaO / denom * 100) if denom != 0 else 0.0
	
	# SM
	SM = SiO2 / (Al2O3 + Fe2O3) if (Al2O3 + Fe2O3) != 0 else 0.0
	
	# AM
	AM = Al2O3 / Fe2O3 if Fe2O3 != 0 else 0.0
	
	# NaEq
	NaEq = Na2O + 0.658 * K2O
	
	return {
		"LSF": LSF,
		"SM": SM,
		"AM": AM,
		"NaEq": NaEq
	}
