import streamlit as st
import pandas as pd
import json
from datetime import datetime
from .compute import calculate_all_stages, calculate_quality_moduli, compute_bogue, compute_cv_total, compute_total_fuel_tph

RAW_MIX_COLUMNS = [
	"Material","H2O","LOI","SiO2","Al2O3","Fe2O3","CaO","MgO","K2O","Na2O","SO3","Cl","HPP","min%","max%"
]

DEFAULT_RM = [
	["LS",7.50,43.00,1.07,1.24,0.55,53.28,0.26,0.04,0.03,0.05,0.01,48632,0,100],
	["CY",16.00,13.87,67.00,15.27,9.09,1.28,1.42,1.18,0.58,0.12,0.01,79130,0,100],
	["SS",11.36,2.45,84.11,6.40,4.21,0.56,0.09,0.22,0.01,0.01,0.00,106507,0,100],
	["CS",3.20,0.00,35.40,4.28,52.06,5.77,2.17,0.03,0.01,0.03,0.00,353510,0,100],
]

DEFAULT_DUST = {"H2O":0.0,"LOI":10.06,"SiO2":3.76,"Al2O3":2.23,"Fe2O3":45.90,"CaO":40.00,"MgO":0.54,"K2O":0.12,"Na2O":0.39,"SO3":0.02,"Cl":0.02}


def build_general_tab(general: dict, dust: dict):
	st.subheader("General")
	c1,c2,c3,c4,c5 = st.columns(5)
	stec = c1.number_input("STEC (kcal/kg)", value=float(general.get("stec", 800.0)), key="stec_input")
	clinker_tph = c2.number_input("Clinker Prod (TPH)", value=float(general.get("clinker_tph", 342.0)), key="clinker_tph_input")
	tonKF = c3.number_input("Kiln Feed (TPH)", value=float(general.get("tonKF", 533.0)), key="tonKF_input")
	dust_ratio = c4.number_input("Dust Ratio (%)", value=float(general.get("dust_ratio", 3.0)), key="dust_ratio_input")
	fcao = c5.number_input("Free Lime Clinker (%)", value=float(general.get("fcao", 1.0)), key="fcao_input")
	
	# H₂O Raw meal input field for Indeks Bahan calculation
	st.markdown("---")
	st.markdown("**💧 H₂O Raw meal Configuration**")
	col1, col2 = st.columns([1, 2])
	with col1:
		h2o_rawmeal = st.number_input(
			"H₂O Raw meal (%)", 
			value=float(general.get("h2o_rawmeal", 0.50)), 
			min_value=0.0, 
			max_value=100.0, 
			step=0.01,
			key="h2o_rawmeal_input",
			help="Moisture content value used in Indeks Bahan calculation formula"
		)
	with col2:
		st.info("ℹ️ **Usage**: This H₂O Raw meal value is used in the Indeks Bahan formula: Proporsi Dry [%] × (100 - H₂O Raw meal) ÷ (100 - H₂O Raw Mix)")

	# Simplified dust routing status display
	st.markdown("---")
	st.markdown("**🌪️ Dust Routing Status**")
	
	# Get current dust values from general state
	pSilo = general.get("pSilo", 10.0)
	pKiln = general.get("pKiln", 0.0)
	
	# Determine current scenario
	if pKiln > 0:
		current_scenario = "Dust → Kiln"
		active_percentage = pKiln
		scenario_desc = f"{active_percentage:.1f}% of Kiln Feed"
		scenario_icon = "🏭"
	else:
		current_scenario = "Dust → Silo"
		active_percentage = pSilo
		scenario_desc = f"{active_percentage:.1f}% of Dust"
		scenario_icon = "📦"
	
	# Display current routing in metrics
	col1, col2, col3 = st.columns(3)
	col1.metric("Active Scenario", current_scenario, delta=None)
	col2.metric("Routing Percentage", scenario_desc, delta=None)
	col3.metric("Control Method", "Sidebar Radio", delta=None)
	
	st.info(f"{scenario_icon} **{current_scenario}**: {scenario_desc}. Use the sidebar radio buttons to switch scenarios.")

	st.markdown("**Dust composition**")
	dust = dust or DEFAULT_DUST.copy()
	cols = st.columns(len(dust))
	for i,k in enumerate(dust):
		dust[k] = cols[i].number_input(k, value=float(dust[k]), key=f"dust_{k}_input")

	return {
		"stec": stec,
		"clinker_tph": clinker_tph,
		"tonKF": tonKF,
		"dust_ratio": dust_ratio,  # Return as percentage, not divided by 100
		"fcao": fcao,
		"pSilo": pSilo,  # Return as percentage, not divided by 100
		"pKiln": pKiln,  # Return as percentage, not divided by 100
		"h2o_rawmeal": h2o_rawmeal,  # User-entered H2O Raw meal value
	}, dust


def build_rawmix_tab(rm_df: pd.DataFrame):
	st.subheader("Raw Mix (dry basis)")
	if rm_df is None or rm_df.empty:
		rm_df = pd.DataFrame(DEFAULT_RM, columns=RAW_MIX_COLUMNS)
	rm_df = st.data_editor(rm_df, num_rows="dynamic", use_container_width=True, key="rm_data_editor")
	
	# Calculate and display moduli for each individual material (with caching)
	if not rm_df.empty and len(rm_df) > 0:
		# Only show moduli in expander to reduce initial load time
		with st.expander("🔍 View Individual Material Quality Moduli", expanded=False):
			st.caption("Quality moduli for each raw material individually")
			
			try:
				# Calculate moduli for each material
				moduli_data = []
				
				for _, row in rm_df.iterrows():
					material_name = str(row.get('Material', '')).strip()
					if not material_name:
						continue
					
					# Extract composition for this material
					composition = {
						"SiO2": float(row.get("SiO2", 0.0) or 0.0),
						"Al2O3": float(row.get("Al2O3", 0.0) or 0.0),
						"Fe2O3": float(row.get("Fe2O3", 0.0) or 0.0),
						"CaO": float(row.get("CaO", 0.0) or 0.0),
						"K2O": float(row.get("K2O", 0.0) or 0.0),
						"Na2O": float(row.get("Na2O", 0.0) or 0.0)
					}
					
					# Calculate moduli for this material
					moduli = calculate_quality_moduli(composition)
					
					# Add to data list
					moduli_data.append({
						"Material": material_name,
						"LSF": f"{moduli['LSF']:.2f}",
						"SM": f"{moduli['SM']:.2f}",
						"AM": f"{moduli['AM']:.2f}",
						"NaEq": f"{moduli['NaEq']:.3f}"
					})
				
				if moduli_data:
					# Display moduli table
					st.dataframe(pd.DataFrame(moduli_data), use_container_width=True)
					
					# Show additional info
					st.info("💡 These are the quality moduli for each individual raw material. The final raw mix moduli will depend on the optimized proportions of these materials.")
				
			except Exception as e:
				st.warning(f"⚠️ Could not calculate moduli: {str(e)}")
	
	return rm_df


def build_fuel_tab(fuel_rows: list):
	st.subheader("Fuels")
	st.caption("Fine Coal proportion is automatically calculated. Other fuel prop% can be 0 for unused fuels")
	
	# Initialize with defaults if empty
	if not fuel_rows:
		fuel_rows = [
			{"Fuel":"Fine Coal","prop":75.3,"cv":4800,"ash":14.0,"S":0.3,"SiO2":11.87,"Al2O3":9.03,"Fe2O3":51.37,"CaO":4.0,"K2O":0.20,"Na2O":0.30,"LOI":0.0},
			{"Fuel":"Sekam","prop":19.5,"cv":2500,"ash":25.0,"S":0.3,"SiO2":95.0,"Al2O3":0.17,"Fe2O3":0.35,"CaO":0.91,"K2O":0.11,"Na2O":0.43,"LOI":0.0},
			{"Fuel":"SBE","prop":1.2,"cv":1800,"ash":65.0,"S":0.5,"SiO2":64.0,"Al2O3":16.0,"Fe2O3":1.2,"CaO":1.2,"K2O":1.54,"Na2O":2.25,"LOI":0.0},
			{"Fuel":"Tankos","prop":4.0,"cv":3000,"ash":11.0,"S":0.2,"SiO2":40.0,"Al2O3":10.0,"Fe2O3":2.0,"CaO":10.0,"K2O":0.11,"Na2O":30.0,"LOI":0.0},
		]
	
	# Session state for managing fuel data and auto-calculation
	if "fuel_data_state" not in st.session_state:
		st.session_state.fuel_data_state = fuel_rows.copy()
	if "prev_fuel_hash" not in st.session_state:
		st.session_state.prev_fuel_hash = None
	
	# Control buttons
	col1, col2, col3 = st.columns([2, 2, 2])
	with col1:
		add_fuel = st.toggle("➕ New Fuel", key="add_new_fuel_toggle", help="Toggle to add a new fuel row")
	with col2:
		remove_mode = st.toggle("🗑️ Remove Mode", key="remove_mode_toggle", help="Enable to remove fuel rows")
	with col3:
		manual_calc = st.button("🔄 Recalculate Fine Coal", key="manual_calc_fine_coal", help="Manually trigger Fine Coal calculation")
	
	# Prepare fuel DataFrame
	cols = ["Fuel","prop","cv","ash","S","SiO2","Al2O3","Fe2O3","CaO","K2O","Na2O","LOI"]
	fuel_df = pd.DataFrame(fuel_rows, columns=cols)
	
	# Add new fuel if toggle is activated
	if add_fuel:
		new_fuel = {
			"Fuel": "New Fuel",
			"prop": 0.0,
			"cv": 4000,
			"ash": 15.0,
			"S": 0.5,
			"SiO2": 50.0,
			"Al2O3": 25.0,
			"Fe2O3": 15.0,
			"CaO": 5.0,
			"K2O": 2.0,
			"Na2O": 1.0,
			"LOI": 0.0
		}
		new_row = pd.DataFrame([new_fuel], columns=cols)
		fuel_df = pd.concat([fuel_df, new_row], ignore_index=True)
	
	# Display fuel editor with enhanced configuration
	edited_fuel_df = st.data_editor(
		fuel_df, 
		num_rows="dynamic" if remove_mode else "fixed",
		use_container_width=True, 
		key="fuel_data_editor",
		hide_index=False,
		column_config={
			"Fuel": st.column_config.TextColumn("Fuel Name", help="Name of the fuel", width="medium"),
			"prop": st.column_config.NumberColumn("Prop (%)", help="Proportion percentage (auto-calculated for Fine Coal)", format="%.1f", min_value=0.0, max_value=100.0),
			"cv": st.column_config.NumberColumn("CV (kcal/kg)", help="Calorific Value", format="%.0f", min_value=0),
			"ash": st.column_config.NumberColumn("Ash (%)", help="Ash content", format="%.1f", min_value=0.0, max_value=100.0),
			"S": st.column_config.NumberColumn("S (%)", help="Sulfur content", format="%.2f", min_value=0.0),
			"SiO2": st.column_config.NumberColumn("SiO2 (%)", help="Silicon Dioxide", format="%.2f", min_value=0.0, max_value=100.0),
			"Al2O3": st.column_config.NumberColumn("Al2O3 (%)", help="Aluminum Oxide", format="%.2f", min_value=0.0, max_value=100.0),
			"Fe2O3": st.column_config.NumberColumn("Fe2O3 (%)", help="Iron Oxide", format="%.2f", min_value=0.0, max_value=100.0),
			"CaO": st.column_config.NumberColumn("CaO (%)", help="Calcium Oxide", format="%.2f", min_value=0.0, max_value=100.0),
			"K2O": st.column_config.NumberColumn("K2O (%)", help="Potassium Oxide", format="%.2f", min_value=0.0, max_value=100.0),
			"Na2O": st.column_config.NumberColumn("Na2O (%)", help="Sodium Oxide", format="%.2f", min_value=0.0, max_value=100.0),
			"LOI": st.column_config.NumberColumn("LOI (%)", help="Loss on Ignition", format="%.2f", min_value=0.0, max_value=100.0)
		}
	)
	
	# Convert to dict format
	fuel_data = edited_fuel_df.to_dict(orient="records")
	
	# Create hash of current fuel data (excluding Fine Coal prop for change detection)
	fuel_hash_data = []
	for fuel in fuel_data:
		if not ("fine coal" in str(fuel.get("Fuel", "")).lower()):
			fuel_hash_data.append(str(fuel))
	current_hash = hash(str(fuel_hash_data))
	
	# Auto-calculate Fine Coal proportion when other fuels change or manual button pressed
	if (current_hash != st.session_state.prev_fuel_hash) or manual_calc:
		fuel_data = auto_calculate_fine_coal_proportion(fuel_data)
		st.session_state.prev_fuel_hash = current_hash
		if manual_calc:
			st.success("✅ Fine Coal proportion recalculated!")
	
	# Update session state
	st.session_state.fuel_data_state = fuel_data.copy()
	
	# Display current fuel proportions with enhanced styling
	st.subheader("Current Fuel Proportions")
	total_prop = sum(f.get("prop", 0) for f in fuel_data)
	
	# Calculate total fuel TPH using general parameters if available
	total_fuel_tph = 0.0
	try:
		if hasattr(st.session_state, 'state') and 'general' in st.session_state.state:
			g = st.session_state.state.get("general", {})
			stec = g.get("stec", 800.0)
			clinker_tph = g.get("clinker_tph", 342.0)
			
			# Calculate CV total from current fuel data
			cv_total = compute_cv_total(fuel_data)
			
			if cv_total > 0:
				total_fuel_tph = compute_total_fuel_tph(stec, clinker_tph, cv_total)
	except Exception:
		# If session state is not available, use default calculation
		pass
	
	prop_summary = []
	for fuel in fuel_data:
		fuel_name = fuel.get("Fuel", "Unknown")
		prop = fuel.get("prop", 0)
		cv = fuel.get("cv", 0)
		ash = fuel.get("ash", 0)
		
		# Calculate individual fuel tonnage
		fuel_tonnage_tph = (prop / 100.0) * total_fuel_tph if total_fuel_tph > 0 else 0.0
		
		# Status icons and styling
		if "fine coal" in fuel_name.lower():
			status_icon = "🔥"
			status_text = "Auto-calculated"
		elif prop > 0:
			status_icon = "🌱"
			status_text = "Active"
		else:
			status_icon = "⚪"
			status_text = "Inactive"
		
		prop_summary.append({
			"Status": status_icon,
			"Fuel": fuel_name,
			"Proportion (%)": f"{prop:.1f}%",
			"CV (kcal/kg)": f"{cv:.0f}",
			"Ash (%)": f"{ash:.1f}%",
			"Tonnage (TPH)": f"{fuel_tonnage_tph:.1f}",
			"Note": status_text
		})
	
	# Add summary row with totals
	if total_fuel_tph > 0:
		prop_summary.append({
			"Status": "📊",
			"Fuel": "TOTAL",
			"Proportion (%)": f"{total_prop:.1f}%",
			"CV (kcal/kg)": f"{compute_cv_total(fuel_data):.0f}" if fuel_data else "0",
			"Ash (%)": "-",
			"Tonnage (TPH)": f"{total_fuel_tph:.1f}",
			"Note": "Total Fuel"
		})
	
	st.dataframe(pd.DataFrame(prop_summary), use_container_width=True, hide_index=True)
	
	# Total proportion validation
	if abs(total_prop - 100) < 0.1:
		st.success(f"✅ Total: {total_prop:.1f}% (Balanced)")
	elif total_prop > 100:
		st.error(f"❌ Total: {total_prop:.1f}% (Exceeds 100% - Please reduce other fuels)")
	else:
		st.warning(f"⚠️ Total: {total_prop:.1f}% (Below 100% - Fine Coal will compensate)")
	
	# Additional fuel information
	with st.expander("🔍 Fuel Details & Tips", expanded=False):
		st.markdown("""
		**How Auto-Calculation Works:**
		- Fine Coal proportion = 100% - (sum of all other active fuels)
		- Changes to any fuel (except Fine Coal) trigger automatic recalculation
		- Fine Coal proportion cannot go below 0%
		
		**Tonnage Calculation:**
		- Total Fuel TPH = (STEC × Clinker TPH) ÷ CV Total
		- Individual Fuel TPH = Proportion [%] × Total Fuel TPH ÷ 100
		- CV Total = Weighted average of all fuel calorific values
		- Updates automatically when general parameters change
		
		**Adding New Fuels:**
		- Toggle "New Fuel" to add a row
		- Customize the fuel name and properties
		- Set proportion > 0 to activate the fuel
		
		**Removing Fuels:**
		- Enable "Remove Mode" to allow row deletion
		- Delete rows directly in the table
		- Fine Coal cannot be deleted (it's essential for auto-calculation)
		""")
		
		# Show current calculation parameters
		if total_fuel_tph > 0:
			st.info(f"📊 **Current Parameters**: Total Fuel = {total_fuel_tph:.1f} TPH | CV Total = {compute_cv_total(fuel_data):.0f} kcal/kg")
	
	return fuel_data


def auto_calculate_fine_coal_proportion(fuel_data: list) -> list:
	"""Automatically calculate Fine Coal proportion based on other fuels"""
	try:
		# Find Fine Coal and calculate other fuels total
		fine_coal_index = None
		other_fuels_total = 0.0
		
		for i, fuel in enumerate(fuel_data):
			fuel_name = str(fuel.get("Fuel", "")).strip().lower()
			prop = float(fuel.get("prop", 0) or 0)
			
			# Check if this is Fine Coal (case insensitive, flexible matching)
			if any(term in fuel_name for term in ["fine coal", "finecoal", "coal fine", "fine_coal"]):
				fine_coal_index = i
			else:
				# Sum all other fuel proportions
				other_fuels_total += prop
		
		# Calculate Fine Coal proportion to balance to 100%
		if fine_coal_index is not None:
			fine_coal_prop = max(0, min(100, 100 - other_fuels_total))
			fuel_data[fine_coal_index]["prop"] = fine_coal_prop
			
			# If other fuels exceed 100%, proportionally reduce them
			if other_fuels_total > 100:
				reduction_factor = 95 / other_fuels_total  # Leave 5% for Fine Coal minimum
				for i, fuel in enumerate(fuel_data):
					if i != fine_coal_index:
						fuel["prop"] = fuel.get("prop", 0) * reduction_factor
				# Recalculate Fine Coal after reduction
				new_other_total = sum(fuel.get("prop", 0) for i, fuel in enumerate(fuel_data) if i != fine_coal_index)
				fuel_data[fine_coal_index]["prop"] = max(5, 100 - new_other_total)
		
		return fuel_data
	
	except Exception as e:
		# Return original data if calculation fails
		st.warning(f"Auto-calculation failed: {str(e)}")
		return fuel_data


def build_constraints_tab(cons: dict):
	st.subheader("Constraints (Clinker basis)")
	c1,c2,c3,c4,c5 = st.columns(5)
	LSF_min = c1.number_input("LSF min", value=float(cons.get("LSF_min", 95.5)), key="LSF_min_input")
	LSF_max = c1.number_input("LSF max", value=float(cons.get("LSF_max", 96.5)), key="LSF_max_input")
	SM_min = c2.number_input("SM min", value=float(cons.get("SM_min", 2.28)), key="SM_min_input")
	SM_max = c2.number_input("SM max", value=float(cons.get("SM_max", 2.32)), key="SM_max_input")
	AM_min = c3.number_input("AM min", value=float(cons.get("AM_min", 1.55)), key="AM_min_input")
	AM_max = c3.number_input("AM max", value=float(cons.get("AM_max", 1.60)), key="AM_max_input")
	NaEq_max = c4.number_input("NaEq max (%)", value=float(cons.get("NaEq_max", 0.60)), key="NaEq_max_input")
	C3S_min = c5.number_input("C3S min (%)", value=float(cons.get("C3S_min", 58.0)), key="C3S_min_input")
	C3S_max = c5.number_input("C3S max (%)", value=float(cons.get("C3S_max", 65.0)), key="C3S_max_input")
	return {
		"LSF_min": LSF_min,
		"LSF_max": LSF_max,
		"SM_min": SM_min,
		"SM_max": SM_max,
		"AM_min": AM_min,
		"AM_max": AM_max,
		"NaEq_max": NaEq_max,
		"C3S_min": C3S_min,
		"C3S_max": C3S_max,
	}


def to_rm_dict(rm_df: pd.DataFrame) -> dict:
	RM = {}
	for _, r in rm_df.iterrows():
		name = str(r["Material"]).strip()
		if not name:
			continue
		RM[name] = {
			"SiO2": float(r.get("SiO2", 0.0) or 0.0),
			"Al2O3": float(r.get("Al2O3", 0.0) or 0.0),
			"Fe2O3": float(r.get("Fe2O3", 0.0) or 0.0),
			"CaO": float(r.get("CaO", 0.0) or 0.0),
			"K2O": float(r.get("K2O", 0.0) or 0.0),
			"Na2O": float(r.get("Na2O", 0.0) or 0.0),
			"LOI": float(r.get("LOI", 0.0) or 0.0),
		}
	return RM


def to_bounds_dict(rm_df: pd.DataFrame) -> dict:
	b = {}
	for _, r in rm_df.iterrows():
		name = str(r["Material"]).strip()
		if not name:
			continue
		b[name] = (float(r.get("min%", 0.0) or 0.0), float(r.get("max%", 100.0) or 100.0))
	return b


def to_costs_dict(rm_df: pd.DataFrame) -> dict:
	c = {}
	for _, r in rm_df.iterrows():
		name = str(r["Material"]).strip()
		if not name:
			continue
		c[name] = float(r.get("HPP", 0.0) or 0.0)
	return c


def render_results_tab(state: dict, results: dict):
	st.subheader("Results")
	if not results:
		st.info("Click Calculate or enable Auto-resolve.")
		return

	status = results.get("status")
	sol = results.get("solution", {})
	meta = results.get("meta", {})
	
	# Status info
	if status == 1:
		st.success("✅ Solver converged successfully!")
	else:
		st.error(f"❌ Solver failed with status: {status}")
		return
	
	# Solution summary
	st.subheader("Optimal Proportions")
	if sol:
		# Get user-entered H2O Raw meal value from general state
		rm_df = state.get('rm_df')
		tonKF = state.get('general', {}).get('tonKF', 533.0)
		h2o_rawmeal = state.get('general', {}).get('h2o_rawmeal', 0.50)  # Use user-entered value
		
		# Create a nice table
		prop_data = []
		total_cost = 0
		indeks_bahan_values = []  # Store Indeks Bahan values for normalization
		
		for material, percentage in sol.items():
			if percentage is not None:
				tph = (percentage/100) * tonKF
				
				# Find HPP and H2O from DataFrame
				hpp = 0
				h2o_material = 0.0
				if rm_df is not None:
					for _, row in rm_df.iterrows():
						if str(row.get('Material', '')).strip() == material:
							hpp = float(row.get('HPP', 0) or 0)
							h2o_material = float(row.get('H2O', 0.0) or 0.0)
							break
				
				# Calculate Indeks Bahan using the formula:
				# Indeks Bahan = Proporsi Dry [%] * (100-H2O Rawmeal)/(100-H2O Raw Mix)
				indeks_bahan = 0.0
				if (100 - h2o_material) > 0:  # Avoid division by zero
					indeks_bahan = percentage * (100 - h2o_rawmeal) / (100 - h2o_material)
				
				indeks_bahan_values.append(indeks_bahan)
				cost_per_hour = tph * hpp
				total_cost += cost_per_hour
				
				prop_data.append({
					"Material": material,
					"% Dry": f"{percentage:.2f}%",
					"Indeks Bahan (%)": f"{indeks_bahan:.2f}%",
					"TPH": f"{tph:.1f}",
					"HPP (Rp/t)": f"{hpp:,.0f}",
					"Cost (Rp/h)": f"{cost_per_hour:,.0f}"
				})
		
		# Calculate normalized % Wet (normalize Indeks Bahan values to sum to 100%)
		total_indeks_bahan = sum(indeks_bahan_values) if indeks_bahan_values else 0.0
		for i, data_row in enumerate(prop_data):
			if total_indeks_bahan > 0:
				percent_wet = (indeks_bahan_values[i] / total_indeks_bahan) * 100
			else:
				percent_wet = 0.0
			# Insert % Wet column after % Dry
			new_row = {}
			for key, value in data_row.items():
				new_row[key] = value
				if key == "% Dry":
					new_row["% Wet"] = f"{percent_wet:.2f}%"
			prop_data[i] = new_row
		
		# Add TOTAL row
		total_percentage = sum(sol.values()) if sol else 0
		total_indeks_bahan = sum(indeks_bahan_values) if indeks_bahan_values else 0.0
		
		prop_data.append({
			"Material": "TOTAL",
			"% Dry": f"{total_percentage:.2f}%",
			"% Wet": "100.00%",  # Normalized % Wet always sums to 100%
			"Indeks Bahan (%)": f"{total_indeks_bahan:.2f}%",
			"TPH": f"{tonKF:.1f}",
			"HPP (Rp/t)": "-",
			"Cost (Rp/h)": f"{total_cost:,.0f}"
		})
		
		if prop_data:
			st.dataframe(pd.DataFrame(prop_data), use_container_width=True)
			
			with st.expander("ℹ️ Calculation Formulas & Column Explanations", expanded=False):
				st.markdown("""
				**Column Explanations:**
				- **% Dry**: Optimized dry proportion from solver (sums to 100%)
				- **% Wet**: Normalized Indeks Bahan values (sums to 100%)
				- **Indeks Bahan**: Raw wet proportion accounting for moisture
				
				**Indeks Bahan Formula:**
				```
				Indeks Bahan = Proporsi Dry [%] × (100 - H₂O Raw meal) ÷ (100 - H₂O Raw Mix)
				```
				
				**% Wet Calculation:**
				```
				% Wet = (Indeks Bahan / Sum of all Indeks Bahan) × 100%
				```
				
				Where:
				- **Proporsi Dry [%]**: Optimized dry proportion from solver
				- **H₂O Raw meal**: User-entered value from General tab (default: 0.50%)
				- **H₂O Raw Mix**: Individual material moisture content
				
				💡 **% Wet** represents the normalized wet proportions for practical use.
				""")
				
				# Show current H2O values
				st.info(f"📊 **Current H₂O Raw meal**: {h2o_rawmeal:.2f}% (user-entered)")
			
			# Check if sum = 100
			total_percentage = sum(sol.values()) if sol else 0
			if abs(total_percentage - 100) < 0.01:
				st.success(f"✅ Total: {total_percentage:.2f}%")
			else:
				st.warning(f"⚠️ Total: {total_percentage:.2f}% (should be 100%)")
			
			st.info(f"💰 Total Cost: Rp {total_cost:,.0f}/hour")
	
	# Calculate compositions for all stages
	if sol and status == 1:
		# Calculate stages using our compute functions
		g = state.get("general", {})
		dust = state.get("dust", {})
		ash_comp = results.get("ash_comp", {})
		RM = state.get("rm_dict", {})
		
		if not RM or not ash_comp:
			st.warning("⚠️ Missing RM dictionary or ash composition for detailed analysis")
			return
		
		stages = calculate_all_stages(
			RM=RM,
			x_percent=sol,
			dust=dust,
			pSilo=g.get("pSilo", 10.0) / 100.0,  # Convert to decimal
			pKiln=g.get("pKiln", 0.0) / 100.0,   # Convert to decimal
			tonKF=g.get("tonKF", 533.0),
			clinker_tph=g.get("clinker_tph", 342.0),
			dust_ratio=g.get("dust_ratio", 3.0) / 100.0,  # Convert to decimal
			ASH=ash_comp,
			FCaO_cl=g.get("fcao", 1.0)
		)
		
		# Composition tables
		st.subheader("Composition Analysis")
		
		col1, col2, col3 = st.columns(3)
		
		# Raw Meal
		with col1:
			st.markdown("**Raw Meal Composition**")
			rm_data = []
			for ox, val in stages["raw_meal"].items():
				rm_data.append({"Oxide": ox, "%": f"{val:.2f}"})
			st.dataframe(pd.DataFrame(rm_data), use_container_width=True)
		
		# Kiln Feed
		with col2:
			st.markdown("**Kiln Feed Composition**")
			kf_data = []
			for ox, val in stages["kiln_feed"].items():
				kf_data.append({"Oxide": ox, "%": f"{val:.2f}"})
			st.dataframe(pd.DataFrame(kf_data), use_container_width=True)
		
		# Clinker
		with col3:
			st.markdown("**Clinker Composition**")
			cl_data = []
			for ox, val in stages["clinker"].items():
				if ox not in ["LOI", "FCaO"]:  # Exclude LOI and FCaO from main display
					cl_data.append({"Oxide": ox, "%": f"{val:.2f}"})
			st.dataframe(pd.DataFrame(cl_data), use_container_width=True)
		
		# Quality moduli with constraint checking
		st.subheader("Quality Moduli & Constraint Verification")
		
		rm_moduli = calculate_quality_moduli(stages["raw_meal"])
		kf_moduli = calculate_quality_moduli(stages["kiln_feed"])
		cl_moduli = calculate_quality_moduli(stages["clinker"])
		
		# Get constraints for comparison
		constraints = state.get("constraints", {})
		
		# Create quality verification table
		quality_data = []
		
		# LSF verification
		clsf = cl_moduli['LSF']
		lsf_min = constraints.get('LSF_min', 95.5)
		lsf_max = constraints.get('LSF_max', 96.5)
		lsf_status = "✅" if lsf_min <= clsf <= lsf_max else "❌"
		quality_data.append({
			"Parameter": "LSF",
			"Target": f"{lsf_min:.1f} - {lsf_max:.1f}",
			"Raw Meal": f"{rm_moduli['LSF']:.2f}",
			"Kiln Feed": f"{kf_moduli['LSF']:.2f}",
			"Clinker": f"{clsf:.2f}",
			"Status": lsf_status
		})
		
		# SM verification  
		csm = cl_moduli['SM']
		sm_min = constraints.get('SM_min', 2.28)
		sm_max = constraints.get('SM_max', 2.32)
		sm_status = "✅" if sm_min <= csm <= sm_max else "❌"
		quality_data.append({
			"Parameter": "SM",
			"Target": f"{sm_min:.2f} - {sm_max:.2f}",
			"Raw Meal": f"{rm_moduli['SM']:.2f}",
			"Kiln Feed": f"{kf_moduli['SM']:.2f}", 
			"Clinker": f"{csm:.2f}",
			"Status": sm_status
		})
		
		# AM verification
		cam = cl_moduli['AM']
		am_min = constraints.get('AM_min', 1.55)
		am_max = constraints.get('AM_max', 1.60)
		am_status = "✅" if am_min <= cam <= am_max else "❌"
		quality_data.append({
			"Parameter": "AM",
			"Target": f"{am_min:.2f} - {am_max:.2f}",
			"Raw Meal": f"{rm_moduli['AM']:.2f}",
			"Kiln Feed": f"{kf_moduli['AM']:.2f}",
			"Clinker": f"{cam:.2f}",
			"Status": am_status
		})
		
		# NaEq verification
		cnaeq = cl_moduli['NaEq']
		naeq_max = constraints.get('NaEq_max', 0.60)
		naeq_status = "✅" if cnaeq <= naeq_max else "❌"
		quality_data.append({
			"Parameter": "NaEq",
			"Target": f"≤ {naeq_max:.2f}",
			"Raw Meal": f"{rm_moduli['NaEq']:.3f}",
			"Kiln Feed": f"{kf_moduli['NaEq']:.3f}",
			"Clinker": f"{cnaeq:.3f}",
			"Status": naeq_status
		})
		
		st.dataframe(pd.DataFrame(quality_data), use_container_width=True)
		
		# Bogue calculation with C3S verification
		st.subheader("Bogue Phases (Clinker)")
		bogue = compute_bogue(stages["clinker"])
		
		# C3S verification
		c3s_actual = bogue.get('C3S', 0)
		c3s_min = constraints.get('C3S_min', 58.0)
		c3s_max = constraints.get('C3S_max', 65.0)
		c3s_status = "✅" if c3s_min <= c3s_actual <= c3s_max else "❌"
		
		bogue_data = []
		for phase, val in bogue.items():
			status_symbol = ""
			if phase == "C3S":
				status_symbol = f" {c3s_status} (Target: {c3s_min:.1f}-{c3s_max:.1f}%)"
			bogue_data.append({"Phase": phase, "%": f"{val:.2f}{status_symbol}"})
		st.dataframe(pd.DataFrame(bogue_data), use_container_width=True)
	
	# Meta information
	st.subheader("Process Information")
	
	# Calculate dust tonnages
	g = state.get("general", {})
	clinker_tph = g.get("clinker_tph", 342.0)
	tonKF = g.get("tonKF", 533.0)
	dust_ratio = g.get("dust_ratio", 3.0) / 100.0  # Convert to decimal
	pSilo = g.get("pSilo", 10.0) / 100.0  # Convert to decimal
	pKiln = g.get("pKiln", 0.0) / 100.0   # Convert to decimal
	
	# Calculate tonnages based on formulas
	ton_dust_loss = dust_ratio * clinker_tph  # Dust Ratio tonnage
	ton_dust_to_silo = 0.0
	ton_dust_to_kiln = 0.0
	
	if pSilo > 0:
		# Dust → Silo scenario
		ton_raw_meal = tonKF / (1 - pSilo) if (1 - pSilo) > 0 else tonKF  # Approximate raw meal tonnage
		ton_dust_to_silo = pSilo * ton_raw_meal
	else:
		# Dust → Kiln scenario
		ton_dust_to_kiln = pKiln * tonKF
	
	meta_info = {
		"Z (100-LOI)": f"{meta.get('Z', 0):.2f}",
		"LOI Unignited": f"{meta.get('LOI_u', 0):.2f}%", 
		"C3S Linear": f"{meta.get('C3S_lin', 0):.2f}",
		"Total Fuel TPH": f"{results.get('total_fuel_tph', 0):.1f}",
		"Total Ash TPH": f"{results.get('total_ash_tph', 0):.1f}",
		"CV Total": f"{results.get('cv_total', 0):.0f} kcal/kg",
		"Prop. Heat Alt. Fuel [%]": f"{results.get('alternative_fuel_heat_pct', 0):.1f}%",
		"Dust Loss TPH": f"{ton_dust_loss:.1f}",
		"Dust to Silo TPH": f"{ton_dust_to_silo:.1f}" if ton_dust_to_silo > 0 else "0.0",
		"Dust to Kiln TPH": f"{ton_dust_to_kiln:.1f}" if ton_dust_to_kiln > 0 else "0.0"
	}
	
	# Display in 3 columns, but with more rows to accommodate new metrics
	col1, col2, col3 = st.columns(3)
	metrics_list = list(meta_info.items())
	
	for i, (key, value) in enumerate(metrics_list):
		col = [col1, col2, col3][i % 3]
		col.metric(key, value)
	
	# Add dust scenario information
	st.subheader("Dust Management Details")
	dust_scenario = "Dust → Silo" if pSilo > 0 else "Dust → Kiln" if pKiln > 0 else "No Dust Recycling"
	
	dust_info_data = [
		{"Parameter": "Active Scenario", "Value": dust_scenario},
		{"Parameter": "Dust Ratio (%)", "Value": f"{dust_ratio * 100:.1f}%"},
		{"Parameter": "Dust Loss (TPH)", "Value": f"{ton_dust_loss:.1f}"},
	]
	
	if pSilo > 0:
		dust_info_data.extend([
			{"Parameter": "% Dust to Silo", "Value": f"{pSilo * 100:.1f}%"},
			{"Parameter": "Dust to Silo (TPH)", "Value": f"{ton_dust_to_silo:.1f}"},
			{"Parameter": "Est. Raw Meal (TPH)", "Value": f"{tonKF / (1 - pSilo) if (1 - pSilo) > 0 else tonKF:.1f}"}
		])
	elif pKiln > 0:
		dust_info_data.extend([
			{"Parameter": "% Dust to Kiln", "Value": f"{pKiln * 100:.1f}%"},
			{"Parameter": "Dust to Kiln (TPH)", "Value": f"{ton_dust_to_kiln:.1f}"},
			{"Parameter": "Total Feed to Kiln (TPH)", "Value": f"{tonKF + ton_dust_to_kiln:.1f}"}
		])
	
	st.dataframe(pd.DataFrame(dust_info_data), use_container_width=True)
	
	# Add fuel heat contribution details
	st.subheader("Fuel Heat Contribution Details")
	fuels = state.get("fuel_rows", [])
	if fuels:
		fuel_heat_data = []
		total_heat = 0.0
		fine_coal_heat = 0.0
		
		# Calculate individual fuel heat contributions
		for fuel in fuels:
			fuel_name = str(fuel.get("Fuel", "")).strip()
			prop = fuel.get("prop", 0.0) or 0.0
			cv = fuel.get("cv", 0.0) or 0.0
			heat_contribution = prop * cv
			total_heat += heat_contribution
			
			if "fine coal" in fuel_name.lower() or "finecoal" in fuel_name.lower().replace(" ", ""):
				fine_coal_heat += heat_contribution
			
			fuel_heat_data.append({
				"Fuel": fuel_name,
				"Proportion (%)": f"{prop:.1f}%",
				"CV (kcal/kg)": f"{cv:.0f}",
				"Heat Contribution": f"{heat_contribution:.0f}"
			})
		
		if total_heat > 0:
			# Calculate percentages
			fine_coal_pct = (fine_coal_heat / total_heat) * 100
			alternative_fuel_pct = 100 - fine_coal_pct
			
			# Add percentage column
			for i, row in enumerate(fuel_heat_data):
				fuel = fuels[i]
				heat_contrib = (fuel.get("prop", 0.0) or 0.0) * (fuel.get("cv", 0.0) or 0.0)
				heat_pct = (heat_contrib / total_heat) * 100 if total_heat > 0 else 0
				row["Heat %"] = f"{heat_pct:.1f}%"
			
			st.dataframe(pd.DataFrame(fuel_heat_data), use_container_width=True)
			
			# Summary
			col1, col2 = st.columns(2)
			with col1:
				st.metric("Fine Coal Heat %", f"{fine_coal_pct:.1f}%")
			with col2:
				st.metric("Alternative Fuel Heat %", f"{alternative_fuel_pct:.1f}%")
	else:
		st.info("💡 No fuel data available for heat contribution analysis.")


def build_project_management_sidebar():
	"""Build project management interface in sidebar"""
	st.sidebar.markdown("---")
	st.sidebar.markdown("**📁 Project Management**")
	
	from core.database import db
	
	# Get all projects
	projects = db.get_projects()
	
	# Current project selection
	if "current_project_id" not in st.session_state:
		if projects:
			st.session_state.current_project_id = projects[0]["id"]
		else:
			# Create default project
			project_id = db.create_project("Default Project", "Initial project setup")
			st.session_state.current_project_id = project_id
			projects = db.get_projects()
	
	# Project selector
	if projects:
		project_names = [f"{p['name']}" for p in projects]
		project_ids = [p["id"] for p in projects]
		
		current_idx = 0
		if st.session_state.current_project_id in project_ids:
			current_idx = project_ids.index(st.session_state.current_project_id)
		
		selected_name = st.sidebar.selectbox(
			"Select Project:",
			project_names,
			index=current_idx,
			key="project_selector"
		)
		
		selected_idx = project_names.index(selected_name)
		selected_project_id = project_ids[selected_idx]
		
		if selected_project_id != st.session_state.current_project_id:
			st.session_state.current_project_id = selected_project_id
			st.rerun()
	
	# Project management buttons
	col1, col2 = st.sidebar.columns(2)
	
	with col1:
		if st.button("➕ New", key="new_project_btn", help="Create new project", use_container_width=True):
			st.session_state.show_new_project_dialog = True
	
	with col2:
		if st.button("💾 Save", key="save_project_btn", help="Save current project", use_container_width=True):
			save_current_project()
			st.sidebar.success("✅ Project saved!")
	
	# New project dialog
	if st.session_state.get("show_new_project_dialog", False):
		with st.sidebar.expander("➕ New Project", expanded=True):
			new_name = st.text_input("Project Name:", key="new_project_name")
			new_desc = st.text_area("Description:", key="new_project_desc", height=60)
			
			col1, col2 = st.columns(2)
			with col1:
				if st.button("Create", key="create_project_confirm"):
					if new_name.strip():
						try:
							project_id = db.create_project(new_name.strip(), new_desc.strip())
							st.session_state.current_project_id = project_id
							st.session_state.show_new_project_dialog = False
							st.rerun()
						except Exception as e:
							st.error(f"Error creating project: {str(e)}")
					else:
						st.error("Project name is required")
			
			with col2:
				if st.button("Cancel", key="create_project_cancel"):
					st.session_state.show_new_project_dialog = False
					st.rerun()
	
	# Project actions
	if projects and len(projects) > 1:
		with st.sidebar.expander("🔧 Project Actions"):
			if st.button("🗂️ Import Project", key="import_project_btn"):
				st.session_state.show_import_dialog = True
			
			if st.button("📤 Export Project", key="export_project_btn"):
				export_current_project()
			
			if st.button("🗑️ Delete Project", key="delete_project_btn"):
				st.session_state.show_delete_dialog = True
	
	# Import dialog
	if st.session_state.get("show_import_dialog", False):
		with st.sidebar.expander("🗂️ Import Project", expanded=True):
			uploaded_file = st.file_uploader("Choose project file:", type=['json'], key="import_file")
			
			if uploaded_file is not None:
				try:
					import_data = json.loads(uploaded_file.read().decode('utf-8'))
					
					import_name = st.text_input("Import as:", value=f"Imported_{datetime.now().strftime('%Y%m%d_%H%M')}")
					
					col1, col2 = st.columns(2)
					with col1:
						if st.button("Import", key="import_confirm"):
							if import_name.strip():
								project_id = db.import_project(import_name.strip(), import_data)
								st.session_state.current_project_id = project_id
								st.session_state.show_import_dialog = False
								st.success("✅ Project imported!")
								st.rerun()
							else:
								st.error("Project name is required")
					
					with col2:
						if st.button("Cancel", key="import_cancel"):
							st.session_state.show_import_dialog = False
							st.rerun()
				
				except Exception as e:
					st.error(f"Error importing project: {str(e)}")
	
	# Delete confirmation dialog
	if st.session_state.get("show_delete_dialog", False):
		with st.sidebar.expander("🗑️ Delete Project", expanded=True):
			current_project = next((p for p in projects if p["id"] == st.session_state.current_project_id), None)
			if current_project:
				st.warning(f"Delete '{current_project['name']}'?")
				st.caption("This action cannot be undone.")
				
				col1, col2 = st.columns(2)
				with col1:
					if st.button("Delete", key="delete_confirm"):
						db.delete_project(st.session_state.current_project_id)
						
						# Switch to another project
						remaining_projects = [p for p in projects if p["id"] != st.session_state.current_project_id]
						if remaining_projects:
							st.session_state.current_project_id = remaining_projects[0]["id"]
						else:
							# Create a new default project
							project_id = db.create_project("Default Project", "New project")
							st.session_state.current_project_id = project_id
						
						st.session_state.show_delete_dialog = False
						st.success("✅ Project deleted!")
						st.rerun()
				
				with col2:
					if st.button("Cancel", key="delete_cancel"):
						st.session_state.show_delete_dialog = False
						st.rerun()


def save_current_project():
	"""Save current session state to database"""
	if "current_project_id" not in st.session_state or "state" not in st.session_state:
		return
	
	from core.database import db
	
	try:
		project_id = st.session_state.current_project_id
		state = st.session_state.state
		
		# Save all components
		db.save_general_params(project_id, state.get("general", {}))
		
		if "rm_df" in state and not state["rm_df"].empty:
			db.update_raw_materials(project_id, state["rm_df"])
		
		if "fuel_rows" in state:
			db.update_fuels(project_id, state["fuel_rows"])
		
		db.save_constraints(project_id, state.get("constraints", {}))
		db.save_dust_composition(project_id, state.get("dust", {}))
		
		# Save results if available
		if hasattr(st.session_state, 'results_cache') and st.session_state.results_cache:
			calc_time = st.session_state.get('last_solve_time', 0.0)
			db.save_result(project_id, st.session_state.results_cache, calc_time)
	
	except Exception as e:
		st.error(f"Error saving project: {str(e)}")


def export_current_project():
	"""Export current project as JSON file"""
	if "current_project_id" not in st.session_state:
		return
	
	from core.database import db
	
	try:
		project_id = st.session_state.current_project_id
		export_data = db.export_project(project_id)
		
		# Get project info
		projects = db.get_projects()
		current_project = next((p for p in projects if p["id"] == project_id), None)
		
		if current_project:
			filename = f"{current_project['name'].replace(' ', '_')}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
			
			st.sidebar.download_button(
				label="⬇️ Download Export",
				data=json.dumps(export_data, indent=2),
				file_name=filename,
				mime="application/json",
				key="download_export"
			)
			st.sidebar.success("✅ Export ready!")
	
	except Exception as e:
		st.sidebar.error(f"Export error: {str(e)}")


def load_project_data():
	"""Load project data from database into session state"""
	if "current_project_id" not in st.session_state:
		return
	
	from core.database import db
	
	try:
		project_id = st.session_state.current_project_id
		
		# Load all project components
		general_params = db.get_general_params(project_id)
		raw_materials_df = db.get_raw_materials(project_id)
		fuel_data = db.get_fuels(project_id)
		constraints = db.get_constraints(project_id)
		dust_composition = db.get_dust_composition(project_id)
		
		# Update session state
		st.session_state.state = {
			"general": general_params,
			"rm_df": raw_materials_df,
			"fuel_rows": fuel_data,
			"constraints": constraints,
			"dust": dust_composition,
		}
		
		# Clear cached results when switching projects
		st.session_state.results_cache = None
		st.session_state.last_state_hash = None
	
	except Exception as e:
		st.error(f"Error loading project data: {str(e)}")


def build_project_history_tab():
	"""Build project history tab showing results history"""
	st.subheader("📈 Project History")
	
	if "current_project_id" not in st.session_state:
		st.info("No project selected.")
		return
	
	from core.database import db
	
	try:
		project_id = st.session_state.current_project_id
		history = db.get_results_history(project_id, limit=20)
		
		if not history:
			st.info("No calculation history available for this project.")
			return
		
		# Display history summary
		st.markdown("**Recent Calculations:**")
		
		for i, result in enumerate(history):
			with st.expander(f"Calculation {i+1} - {result['created_at'][:19]} (Status: {'✅' if result['solver_status'] == 1 else '❌'})"):
				col1, col2, col3 = st.columns(3)
				
				with col1:
					st.metric("Solver Status", "Success" if result['solver_status'] == 1 else "Failed")
					st.metric("Calculation Time", f"{result['calculation_time']:.2f}s")
				
				with col2:
					if result['solution_data']:
						st.markdown("**Solution:**")
						for material, proportion in result['solution_data'].items():
							st.caption(f"{material}: {proportion:.2f}%")
				
				with col3:
					st.markdown("**Metadata:**")
					if result['meta_data']:
						for key, value in result['meta_data'].items():
							if key != 'objective_value':
								st.caption(f"{key}: {value}")
				
				# Load this result button
				if st.button(f"📋 Load Result {i+1}", key=f"load_result_{i}"):
					st.session_state.results_cache = {
						"status": result['solver_status'],
						"solution": result['solution_data'],
						"meta": result['meta_data']
					}
					st.success("✅ Result loaded into current session!")
					st.rerun()
	
	except Exception as e:
		st.error(f"Error loading project history: {str(e)}")
