import streamlit as st
import pandas as pd
import json
from pathlib import Path
import hashlib
import time
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from core.model import solve_rawmix
from core.compute import (
	compute_cv_total,
	compute_total_fuel_tph,
	compute_total_ash_tph,
	compute_ash_composition,
	compute_bogue,
	compute_alternative_fuel_heat_percentage,
)
from core.ui import (
	build_general_tab,
	build_rawmix_tab,
	build_fuel_tab,
	build_constraints_tab,
	render_results_tab,
	build_project_management_sidebar,
	load_project_data,
	save_current_project,
	build_project_history_tab,
	to_rm_dict,
	to_bounds_dict,
	to_costs_dict,
)

st.set_page_config(page_title="Raw Mix Design Optimizer", layout="wide")

# Dark Mode CSS
def apply_dark_mode():
	"""Apply dark mode styling"""
	dark_css = """
	<style>
	/* Dark mode variables */
	:root {
		--bg-color: #0e1117;
		--secondary-bg: #262730;
		--text-color: #fafafa;
		--border-color: #4a4a4a;
		--accent-color: #ff4b4b;
	}
	
	/* Main container */
	.stApp {
		background-color: var(--bg-color) !important;
		color: var(--text-color) !important;
	}
	
	/* Sidebar */
	.css-1d391kg {
		background-color: var(--secondary-bg) !important;
	}
	
	/* Input widgets */
	.stTextInput > div > div > input {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border: 1px solid var(--border-color) !important;
	}
	
	.stNumberInput > div > div > input {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border: 1px solid var(--border-color) !important;
	}
	
	.stSelectbox > div > div > div {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border: 1px solid var(--border-color) !important;
	}
	
	/* Buttons */
	.stButton > button {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border: 1px solid var(--border-color) !important;
	}
	
	.stButton > button:hover {
		background-color: var(--accent-color) !important;
		color: white !important;
	}
	
	/* Tabs */
	.stTabs [data-baseweb="tab-list"] {
		background-color: var(--secondary-bg) !important;
	}
	
	.stTabs [data-baseweb="tab"] {
		color: var(--text-color) !important;
		background-color: var(--secondary-bg) !important;
	}
	
	.stTabs [aria-selected="true"] {
		background-color: var(--accent-color) !important;
		color: white !important;
	}
	
	/* DataFrames */
	.stDataFrame {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
	}
	
	/* Data Editor */
	.stDataEditor {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
	}
	
	/* Data Editor cells */
	[data-testid="stDataEditor"] .ag-theme-streamlit {
		--ag-background-color: var(--secondary-bg) !important;
		--ag-foreground-color: var(--text-color) !important;
		--ag-border-color: var(--border-color) !important;
		--ag-header-background-color: var(--bg-color) !important;
		--ag-header-foreground-color: var(--text-color) !important;
		--ag-odd-row-background-color: rgba(255,255,255,0.05) !important;
	}
	
	/* Metrics */
	.metric-container {
		background-color: var(--secondary-bg) !important;
		border: 1px solid var(--border-color) !important;
		border-radius: 0.5rem;
		padding: 1rem;
	}
	
	/* Info boxes */
	.stInfo {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border-left: 4px solid #00d4aa !important;
	}
	
	.stSuccess {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border-left: 4px solid #00d4aa !important;
	}
	
	.stWarning {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border-left: 4px solid #ffaa00 !important;
	}
	
	.stError {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
		border-left: 4px solid #ff4b4b !important;
	}
	
	/* Headers */
	h1, h2, h3, h4, h5, h6 {
		color: var(--text-color) !important;
	}
	
	/* Expander */
	.streamlit-expanderHeader {
		background-color: var(--secondary-bg) !important;
		color: var(--text-color) !important;
	}
	
	.streamlit-expanderContent {
		background-color: var(--bg-color) !important;
		color: var(--text-color) !important;
	}
	
	/* Toggle switch */
	.stCheckbox {
		color: var(--text-color) !important;
	}
	
	/* Captions */
	.caption {
		color: #888888 !important;
	}
	
	/* Download buttons */
	.stDownloadButton > button {
		background-color: var(--accent-color) !important;
		color: white !important;
		border: none !important;
	}
	
	/* Markdown text */
	.stMarkdown {
		color: var(--text-color) !important;
	}
	
	/* Progress bars */
	.stProgress > div > div {
		background-color: var(--accent-color) !important;
	}
	
	/* Sidebar elements */
	.css-1lcbmhc {
		background-color: var(--secondary-bg) !important;
	}
	
	/* Column containers */
	.element-container {
		color: var(--text-color) !important;
	}
	</style>
	"""
	return dark_css

def apply_light_mode():
	"""Apply light mode styling (default Streamlit theme)"""
	light_css = """
	<style>
	/* Reset to default light theme */
	.stApp {
		background-color: #ffffff !important;
		color: #262730 !important;
	}
	</style>
	"""
	return light_css
st.title("Raw Mix Design Optimizer")
st.caption("Σ% = 100 with clinker-basis constraints (LSF, SM, AM, NaEq, C3S)")

# Project Management Section in Sidebar
build_project_management_sidebar()

# Dark Mode Toggle in Sidebar
with st.sidebar:
	st.markdown("### 🎨 Theme")
	dark_mode = st.toggle("🌙 Dark Mode", value=False, key="dark_mode_toggle", help="Toggle between light and dark themes")
	
	# Apply theme
	if dark_mode:
		st.markdown(apply_dark_mode(), unsafe_allow_html=True)
		st.markdown("**Current Theme:** 🌙 Dark")
	else:
		st.markdown(apply_light_mode(), unsafe_allow_html=True)
		st.markdown("**Current Theme:** ☀️ Light")
	
	st.markdown("---")

# Export Functions
def create_excel_report(state, results):
	"""Create comprehensive Excel report"""
	try:
		output = io.BytesIO()
		
		with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
			# Summary sheet
			summary_data = []
			if results and results.get("status") == 1:
				sol = results.get("solution", {})
				g = state.get("general", {})
				rm_df = state.get('rm_df')
				
				# Calculate H2O_Rawmeal (weighted average) for Indeks Bahan calculation
				h2o_rawmeal = 0.0
				if rm_df is not None and not rm_df.empty:
					for material, percentage in sol.items():
						if percentage is not None:
							for _, row in rm_df.iterrows():
								if str(row.get('Material', '')).strip() == material:
									h2o_material = float(row.get('H2O', 0.0) or 0.0)
									h2o_rawmeal += (percentage / 100.0) * h2o_material
									break
				
				# Add solution data with Indeks Bahan calculation
				indeks_bahan_values = []  # Store for % Wet normalization
				
				# First pass: calculate all Indeks Bahan values
				for material, percentage in sol.items():
					if percentage is not None:
						tph = (percentage/100) * g.get('tonKF', 533.0)
						# Find HPP and H2O for cost and Indeks Bahan calculation
						hpp = 0
						h2o_material = 0.0
						if rm_df is not None and not rm_df.empty:
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
						
						indeks_bahan_values.append((material, percentage, indeks_bahan, tph, hpp))
				
				# Calculate total Indeks Bahan for % Wet normalization
				total_indeks_bahan = sum(item[2] for item in indeks_bahan_values)
				
				# Second pass: create summary data with % Wet column
				for material, percentage, indeks_bahan, tph, hpp in indeks_bahan_values:
					# Calculate % Wet (normalized Indeks Bahan)
					percent_wet = (indeks_bahan / total_indeks_bahan * 100) if total_indeks_bahan > 0 else 0.0
					
					cost_per_hour = tph * hpp
					summary_data.append({
						'Material': material,
						'% Dry': f"{percentage:.2f}",
						'% Wet': f"{percent_wet:.2f}",
						'Indeks Bahan (%)': f"{indeks_bahan:.2f}",
						'TPH': f"{tph:.1f}",
						'HPP (Rp/t)': f"{hpp:,.0f}",
						'Cost (Rp/h)': f"{cost_per_hour:,.0f}"
					})
				
				# Add TOTAL row to Excel export
				if summary_data:
					total_percentage = sum(float(row['% Dry']) for row in summary_data)
					total_cost = sum(float(row['Cost (Rp/h)'].replace(',', '')) for row in summary_data)
					total_indeks = sum(float(row['Indeks Bahan (%)']) for row in summary_data)
					total_tph = g.get('tonKF', 533.0)
					
					summary_data.append({
						'Material': 'TOTAL',
						'% Dry': f"{total_percentage:.2f}",
						'% Wet': "100.00",  # Normalized % Wet always sums to 100%
						'Indeks Bahan (%)': f"{total_indeks:.2f}",
						'TPH': f"{total_tph:.1f}",
						'HPP (Rp/t)': '-',
						'Cost (Rp/h)': f"{total_cost:,.0f}"
					})
			
			if summary_data:
				pd.DataFrame(summary_data).to_excel(writer, sheet_name='Optimal_Proportions', index=False)
				
				# Add metadata sheet
				metadata = [
					{'Property': 'Report Generated', 'Value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
					{'Property': 'Application', 'Value': 'Raw Mix Design Optimizer'},
					{'Property': 'Optimization Status', 'Value': 'Success' if results.get('status') == 1 else 'Failed'},
					{'Property': 'Total Materials', 'Value': len(summary_data)},
					{'Property': 'Total Cost (Rp/h)', 'Value': f"{sum(float(row['Cost (Rp/h)'].replace(',', '')) for row in summary_data):,.0f}"}
				]
				pd.DataFrame(metadata).to_excel(writer, sheet_name='Report_Info', index=False)
			
			# Results Tab - Composition Analysis
			if results and results.get("status") == 1:
				try:
					from core.compute import calculate_all_stages, calculate_quality_moduli, compute_bogue
					
					if sol and state.get("rm_dict"):
						g = state.get("general", {})
						dust = state.get("dust", {})
						ash_comp = results.get("ash_comp", {})
						RM = state.get("rm_dict", {})
						
						# Calculate all stages
						stages = calculate_all_stages(
							RM=RM,
							x_percent=sol,
							dust=dust,
							pSilo=g.get("pSilo", 10.0) / 100.0,
							pKiln=g.get("pKiln", 0.0) / 100.0,
							tonKF=g.get("tonKF", 533.0),
							clinker_tph=g.get("clinker_tph", 342.0),
							dust_ratio=g.get("dust_ratio", 3.0) / 100.0,
							ASH=ash_comp,
							FCaO_cl=g.get("fcao", 1.0)
						)
						
						# Composition Analysis Sheet
						composition_data = []
						oxides = ['H2O', 'LOI', 'SiO2', 'Al2O3', 'Fe2O3', 'CaO', 'MgO', 'K2O', 'Na2O', 'SO3', 'Cl']
						
						for oxide in oxides:
							raw_meal_val = stages["raw_meal"].get(oxide, 0)
							kiln_feed_val = stages["kiln_feed"].get(oxide, 0)
							unignited_val = stages["unignited"].get(oxide, 0)
							clinker_val = stages["clinker"].get(oxide, 0)
							
							composition_data.append({
								'Oxide': oxide,
								'Raw Meal (%)': f"{raw_meal_val:.2f}",
								'Kiln Feed (%)': f"{kiln_feed_val:.2f}",
								'Unignited (%)': f"{unignited_val:.2f}",
								'Clinker (%)': f"{clinker_val:.2f}"
							})
						
						pd.DataFrame(composition_data).to_excel(writer, sheet_name='Composition_Analysis', index=False)
						
						# Quality Moduli Sheet
						rm_moduli = calculate_quality_moduli(stages["raw_meal"])
						kf_moduli = calculate_quality_moduli(stages["kiln_feed"])
						un_moduli = calculate_quality_moduli(stages["unignited"])
						cl_moduli = calculate_quality_moduli(stages["clinker"])
						
						moduli_data = [
							{
								'Stage': 'Raw Meal',
								'LSF': f"{rm_moduli['LSF']:.2f}",
								'SM': f"{rm_moduli['SM']:.3f}",
								'AM': f"{rm_moduli['AM']:.3f}",
								'NaEq (%)': f"{rm_moduli['NaEq']:.3f}"
							},
							{
								'Stage': 'Kiln Feed',
								'LSF': f"{kf_moduli['LSF']:.2f}",
								'SM': f"{kf_moduli['SM']:.3f}",
								'AM': f"{kf_moduli['AM']:.3f}",
								'NaEq (%)': f"{kf_moduli['NaEq']:.3f}"
							},
							{
								'Stage': 'Unignited',
								'LSF': f"{un_moduli['LSF']:.2f}",
								'SM': f"{un_moduli['SM']:.3f}",
								'AM': f"{un_moduli['AM']:.3f}",
								'NaEq (%)': f"{un_moduli['NaEq']:.3f}"
							},
							{
								'Stage': 'Clinker',
								'LSF': f"{cl_moduli['LSF']:.2f}",
								'SM': f"{cl_moduli['SM']:.3f}",
								'AM': f"{cl_moduli['AM']:.3f}",
								'NaEq (%)': f"{cl_moduli['NaEq']:.3f}"
							}
						]
						
						pd.DataFrame(moduli_data).to_excel(writer, sheet_name='Quality_Moduli', index=False)
						
						# Bogue Phases Sheet
						bogue = compute_bogue(stages["clinker"], FCaO=g.get("fcao", 1.0))
						bogue_data = [
							{'Phase': 'C3S', 'Percentage (%)': f"{bogue['C3S']:.2f}"},
							{'Phase': 'C2S', 'Percentage (%)': f"{bogue['C2S']:.2f}"},
							{'Phase': 'C3A', 'Percentage (%)': f"{bogue['C3A']:.2f}"},
							{'Phase': 'C4AF', 'Percentage (%)': f"{bogue['C4AF']:.2f}"}
						]
						
						pd.DataFrame(bogue_data).to_excel(writer, sheet_name='Bogue_Phases', index=False)
						
						# Process Information Sheet
						dust_tph = g.get('dust_ratio', 3.0) / 100.0 * g.get('clinker_tph', 342.0)
						total_fuel_tph = results.get('total_fuel_tph', 0)
						total_ash_tph = results.get('total_ash_tph', 0)
						alternative_fuel_heat_pct = results.get('alternative_fuel_heat_pct', 0)
						cv_total = results.get('cv_total', 0)
						
						# Calculate dust scenarios
						pSilo = g.get('pSilo', 0.0) / 100.0
						pKiln = g.get('pKiln', 0.0) / 100.0
						tonKF = g.get('tonKF', 533.0)
						
						dust_to_silo_tph = 0
						dust_to_kiln_tph = 0
						
						if pSilo > 0:
							# Estimate raw meal TPH from kiln feed
							estimated_rm_tph = tonKF / (1 - pSilo)
							dust_to_silo_tph = pSilo * estimated_rm_tph
						elif pKiln > 0:
							dust_to_kiln_tph = pKiln * tonKF
						
						process_info_data = [
							{'Parameter': 'STEC', 'Value': f"{g.get('stec', 0):.1f}", 'Unit': 'kcal/kg'},
							{'Parameter': 'Clinker Production', 'Value': f"{g.get('clinker_tph', 0):.1f}", 'Unit': 'TPH'},
							{'Parameter': 'Kiln Feed', 'Value': f"{tonKF:.1f}", 'Unit': 'TPH'},
							{'Parameter': 'Dust Ratio', 'Value': f"{g.get('dust_ratio', 0):.1f}", 'Unit': '%'},
							{'Parameter': 'Dust Loss', 'Value': f"{dust_tph:.1f}", 'Unit': 'TPH'},
							{'Parameter': 'Dust to Silo', 'Value': f"{g.get('pSilo', 0):.1f}", 'Unit': '%'},
							{'Parameter': 'Dust to Silo TPH', 'Value': f"{dust_to_silo_tph:.1f}", 'Unit': 'TPH'},
							{'Parameter': 'Dust to Kiln', 'Value': f"{g.get('pKiln', 0):.1f}", 'Unit': '%'},
							{'Parameter': 'Dust to Kiln TPH', 'Value': f"{dust_to_kiln_tph:.1f}", 'Unit': 'TPH'},
							{'Parameter': 'Free Lime Clinker', 'Value': f"{g.get('fcao', 0):.1f}", 'Unit': '%'},
							{'Parameter': 'Total Fuel', 'Value': f"{total_fuel_tph:.1f}", 'Unit': 'TPH'},
							{'Parameter': 'Total Ash', 'Value': f"{total_ash_tph:.1f}", 'Unit': 'TPH'},
							{'Parameter': 'CV Total', 'Value': f"{cv_total:.0f}", 'Unit': 'kcal/kg'},
							{'Parameter': 'Fine Coal Heat', 'Value': f"{100 - alternative_fuel_heat_pct:.1f}", 'Unit': '%'},
							{'Parameter': 'Alternative Fuel Heat', 'Value': f"{alternative_fuel_heat_pct:.1f}", 'Unit': '%'}
						]
						
						pd.DataFrame(process_info_data).to_excel(writer, sheet_name='Process_Information', index=False)
					
				except Exception as e:
					print(f"Warning: Could not generate detailed results: {str(e)}")
			
			# Input parameters sheet
			params_data = []
			g = state.get("general", {})
			for key, value in g.items():
				if key not in ["manual_dust_control"]:
					params_data.append({'Parameter': key, 'Value': str(value)})
			
			if params_data:
				pd.DataFrame(params_data).to_excel(writer, sheet_name='Input_Parameters', index=False)
			
			# Raw materials sheet
			rm_df = state.get('rm_df')
			if rm_df is not None and not rm_df.empty:
				rm_df.to_excel(writer, sheet_name='Raw_Materials', index=False)
			
			# Fuel data sheet
			fuel_rows = state.get('fuel_rows', [])
			if fuel_rows:
				pd.DataFrame(fuel_rows).to_excel(writer, sheet_name='Fuel_Data', index=False)
			
			# Constraints sheet
			constraints = state.get('constraints', {})
			if constraints:
				constraints_data = [{'Constraint': k, 'Value': v} for k, v in constraints.items()]
				pd.DataFrame(constraints_data).to_excel(writer, sheet_name='Constraints', index=False)
		
		output.seek(0)
		return output.getvalue()
	
	except Exception as e:
		st.error(f"Error creating Excel report: {str(e)}")
		return None

def create_pdf_report(state, results):
	"""Create comprehensive PDF report"""
	try:
		buffer = io.BytesIO()
		doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
		styles = getSampleStyleSheet()
		story = []
		
		# Title
		title_style = ParagraphStyle(
			'CustomTitle',
			parent=styles['Heading1'],
			fontSize=18,
			alignment=1  # Center alignment
		)
		story.append(Paragraph("Raw Mix Design Optimization Report", title_style))
		story.append(Spacer(1, 20))
		
		# Timestamp and status
		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		story.append(Paragraph(f"Generated: {timestamp}", styles['Normal']))
		if results and results.get("status") == 1:
			story.append(Paragraph("Status: ✅ Optimization Successful", styles['Normal']))
		else:
			story.append(Paragraph("Status: ❌ Optimization Failed", styles['Normal']))
		story.append(Spacer(1, 20))
		
		if results and results.get("status") == 1:
			sol = results.get("solution", {})
			g = state.get("general", {})
			
			# Optimal Proportions
			story.append(Paragraph("Optimal Raw Mix Proportions", styles['Heading2']))
			
			# Calculate H2O_Rawmeal for Indeks Bahan calculation (use user-entered value)
			h2o_rawmeal = g.get('h2o_rawmeal', 0.50)  # Use user-entered value from General tab
			rm_df = state.get('rm_df')  # Get rm_df for material H2O values
			
			prop_data = [['Material', '% Dry', '% Wet', 'Indeks Bahan (%)', 'TPH', 'Cost (Rp/h)']]
			total_cost = 0
			indeks_bahan_values = []  # Store for % Wet normalization
			
			# First pass: calculate all Indeks Bahan values
			for material, percentage in sol.items():
				if percentage is not None:
					tph = (percentage/100) * g.get('tonKF', 533.0)
					# Find HPP and H2O for cost and Indeks Bahan calculation
					hpp = 0
					h2o_material = 0.0
					if rm_df is not None and not rm_df.empty:
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
					
					indeks_bahan_values.append((material, percentage, indeks_bahan, tph, hpp))
			
			# Calculate total Indeks Bahan for % Wet normalization
			total_indeks_bahan = sum(item[2] for item in indeks_bahan_values)
			
			# Second pass: create prop_data with % Wet column
			for material, percentage, indeks_bahan, tph, hpp in indeks_bahan_values:
				# Calculate % Wet (normalized Indeks Bahan)
				percent_wet = (indeks_bahan / total_indeks_bahan * 100) if total_indeks_bahan > 0 else 0.0
				
				cost_per_hour = tph * hpp
				total_cost += cost_per_hour
				prop_data.append([material, f"{percentage:.2f}", f"{percent_wet:.2f}", f"{indeks_bahan:.2f}", f"{tph:.1f}", f"{cost_per_hour:,.0f}"])
			
			# Add total row with calculated Indeks Bahan total
			total_percentage = sum(percentage for percentage in sol.values() if percentage is not None)
			prop_data.append(['TOTAL', f"{total_percentage:.2f}", "100.00", f"{total_indeks_bahan:.2f}", f"{g.get('tonKF', 533.0):.1f}", f"{total_cost:,.0f}"])
			
			table = Table(prop_data, colWidths=[1.5*inch, 1.0*inch, 1.0*inch, 1.2*inch, 1.0*inch, 1.3*inch])
			table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.grey),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, 0), 10),
				('BOTTOMPADDING', (0, 0), (-1, 0), 12),
				('BACKGROUND', (0, 1), (-1, -2), colors.beige),
				('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),  # Total row
				('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
				('GRID', (0, 0), (-1, -1), 1, colors.black)
			]))
			story.append(table)
			story.append(Spacer(1, 20))
			
			# Process Information
			story.append(Paragraph("Process Information", styles['Heading2']))
			process_data = [
				['Parameter', 'Value', 'Unit'],
				['STEC', f"{g.get('stec', 0):.1f}", 'kcal/kg'],
				['Clinker Production', f"{g.get('clinker_tph', 0):.1f}", 'TPH'],
				['Kiln Feed', f"{g.get('tonKF', 0):.1f}", 'TPH'],
				['Dust Ratio', f"{g.get('dust_ratio', 0):.1f}", '%'],
				['Dust to Silo', f"{g.get('pSilo', 0):.1f}", '%'],
				['Dust to Kiln', f"{g.get('pKiln', 0):.1f}", '%'],
				['Free Lime Clinker', f"{g.get('fcao', 0):.1f}", '%']
			]
			
			# Add fuel information if available
			if results.get('total_fuel_tph'):
				process_data.extend([
					['Total Fuel', f"{results.get('total_fuel_tph', 0):.1f}", 'TPH'],
					['Total Ash', f"{results.get('total_ash_tph', 0):.1f}", 'TPH'],
					['Alt. Fuel Heat', f"{results.get('alternative_fuel_heat_pct', 0):.1f}", '%']
				])
			
			process_table = Table(process_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
			process_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.grey),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, 0), 10),
				('BOTTOMPADDING', (0, 0), (-1, 0), 12),
				('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
				('GRID', (0, 0), (-1, -1), 1, colors.black)
			]))
			story.append(process_table)
			story.append(Spacer(1, 20))
			
			# Quality Moduli Summary (if available)
			try:
				from core.compute import calculate_all_stages, calculate_quality_moduli
				if state.get("rm_dict"):
					dust = state.get("dust", {})
					ash_comp = results.get("ash_comp", {})
					RM = state.get("rm_dict", {})
					
					stages = calculate_all_stages(
						RM=RM, x_percent=sol, dust=dust,
						pSilo=g.get("pSilo", 10.0) / 100.0,
						pKiln=g.get("pKiln", 0.0) / 100.0,
						tonKF=g.get("tonKF", 533.0),
						clinker_tph=g.get("clinker_tph", 342.0),
						dust_ratio=g.get("dust_ratio", 3.0) / 100.0,
						ASH=ash_comp, FCaO_cl=g.get("fcao", 1.0)
					)
					
					moduli_data = [['Stage', 'LSF', 'SM', 'AM', 'NaEq']]
					for stage_name, composition in [('Raw Meal', stages['raw_meal']), ('Kiln Feed', stages['kiln_feed']), ('Clinker', stages['clinker'])]:
						moduli = calculate_quality_moduli(composition)
						moduli_data.append([
							stage_name,
							f"{moduli['LSF']:.1f}",
							f"{moduli['SM']:.2f}",
							f"{moduli['AM']:.2f}",
							f"{moduli['NaEq']:.3f}"
						])
					
					story.append(Paragraph("Quality Moduli Summary", styles['Heading2']))
					moduli_table = Table(moduli_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
					moduli_table.setStyle(TableStyle([
						('BACKGROUND', (0, 0), (-1, 0), colors.grey),
						('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
						('ALIGN', (0, 0), (-1, -1), 'CENTER'),
						('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
						('FONTSIZE', (0, 0), (-1, 0), 10),
						('BOTTOMPADDING', (0, 0), (-1, 0), 12),
						('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
						('GRID', (0, 0), (-1, -1), 1, colors.black)
					]))
					story.append(moduli_table)
			except:
				pass  # Skip if moduli calculation fails
			
		else:
			story.append(Paragraph("No optimization results available.", styles['Normal']))
			story.append(Paragraph("Please run the calculation first.", styles['Normal']))
		
		# Footer
		story.append(Spacer(1, 30))
		story.append(Paragraph("Generated by Raw Mix Design Optimizer", styles['Italic']))
		
		doc.build(story)
		buffer.seek(0)
		return buffer.getvalue()
	
	except Exception as e:
		st.error(f"Error creating PDF report: {str(e)}")
		return None

# Load defaults
DEFAULTS_PATH = Path("data/defaults.json")
if DEFAULTS_PATH.exists():
	defaults = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8"))
else:
	defaults = {}

# Initialize database and load project data
if "state" not in st.session_state:
	# Initialize with proper column names
	raw_mix_data = defaults.get("raw_mix_rows", [])
	if raw_mix_data:
		rm_df = pd.DataFrame(raw_mix_data, columns=[
			"Material","H2O","LOI","SiO2","Al2O3","Fe2O3","CaO","MgO","K2O","Na2O","SO3","Cl","HPP","min%","max%"
		])
	else:
		rm_df = pd.DataFrame(columns=[
			"Material","H2O","LOI","SiO2","Al2O3","Fe2O3","CaO","MgO","K2O","Na2O","SO3","Cl","HPP","min%","max%"
		])
	
	st.session_state.state = {
		"general": defaults.get("general", {}),
		"rm_df": rm_df,
		"fuel_rows": defaults.get("fuel_rows", []),
		"constraints": defaults.get("constraints", {}),
		"dust": defaults.get("dust", {}),
	}
	
	# Initialize cache for results and change tracking
	st.session_state.results_cache = None
	st.session_state.last_state_hash = None

# Load project data from database if project is selected
if "current_project_id" in st.session_state:
	# Check if we need to load data (project changed or first load)
	if not hasattr(st.session_state, 'loaded_project_id') or st.session_state.loaded_project_id != st.session_state.current_project_id:
		load_project_data()
		st.session_state.loaded_project_id = st.session_state.current_project_id

state = st.session_state.state

# Function to calculate state hash for change detection
def calculate_state_hash(state_data, mode):
	"""Calculate hash of current state to detect changes"""
	try:
		# Create a simplified representation for hashing
		hash_data = {
			'general': state_data.get('general', {}),
			'rm_df': state_data.get('rm_df', pd.DataFrame()).to_string() if not state_data.get('rm_df', pd.DataFrame()).empty else '',
			'fuel_rows': str(state_data.get('fuel_rows', [])),
			'constraints': state_data.get('constraints', {}),
			'dust': state_data.get('dust', {}),
			'mode': mode
		}
		return hashlib.md5(str(hash_data).encode()).hexdigest()
	except:
		return None

# Tabs
tab_general, tab_rm, tab_fuel, tab_constr, tab_results, tab_history = st.tabs([
	"General", "Raw Mix", "Fuel", "Constraints", "Results", "History"
])

with tab_general:
	state["general"], state["dust"] = build_general_tab(state.get("general", {}), state.get("dust", {}))

with tab_rm:
	state["rm_df"] = build_rawmix_tab(state.get("rm_df"))

with tab_fuel:
	state["fuel_rows"] = build_fuel_tab(state.get("fuel_rows", []))

with tab_constr:
	state["constraints"] = build_constraints_tab(state.get("constraints", {}))

# Sidebar Controls
st.sidebar.markdown("### ⚙️ Controls")
auto = st.sidebar.toggle("Auto-resolve on change", True, key="auto_resolve")
solve_clicked = st.sidebar.button("Calculate", key="solve_button")
mode = st.sidebar.selectbox("Objective", ["Feasibility", "Cost Minimization"], index=0, key="objective_mode")

# Dust scenario toggle - Simplified approach
st.sidebar.markdown("---")
st.sidebar.markdown("**🌪️ Dust Routing**")

# Simple radio button selection
dust_scenario = st.sidebar.radio(
	"Dust routing (for B):",
	options=["Dust → Silo", "Dust → Kiln"],
	index=0,
	key="dust_scenario_radio",
	horizontal=True
)

# Dynamic sliders based on selection
if dust_scenario == "Dust → Kiln":
	# Dust to Kiln scenario
	dust_to_kiln_pct = st.sidebar.slider(
		"Dust → Kiln [% of Kiln Feed]",
		min_value=0.0,
		max_value=20.0,
		value=5.0,
		step=0.1,
		key="dust_to_kiln_slider"
	)
	# Set values
	state["general"]["pKiln"] = dust_to_kiln_pct
	state["general"]["pSilo"] = 0.0
	st.sidebar.info(f"📍 Dust→Kiln: {dust_to_kiln_pct:.1f}% of kiln feed")
else:
	# Dust to Silo scenario  
	dust_to_silo_pct = st.sidebar.slider(
		"Dust → Silo [% of Dust]",
		min_value=0.0,
		max_value=20.0,
		value=10.0,
		step=0.1,
		key="dust_to_silo_slider"
	)
	# Set values
	state["general"]["pSilo"] = dust_to_silo_pct
	state["general"]["pKiln"] = 0.0
	st.sidebar.info(f"📍 Dust→Silo: {dust_to_silo_pct:.1f}% of dust")

# Add performance info
if "last_solve_time" in st.session_state:
	st.sidebar.caption(f"Last solve: {st.session_state.last_solve_time:.2f}s")

# Add status info
if hasattr(st.session_state, 'results_cache') and st.session_state.results_cache:
	st.sidebar.success("✅ Results cached")
elif auto:
	st.sidebar.info("🔄 Auto-resolve enabled")
else:
	st.sidebar.info("⏸️ Manual mode")

# Summary Results Section
st.sidebar.markdown("---")
st.sidebar.markdown("**📈 Summary Results**")

if hasattr(st.session_state, 'results_cache') and st.session_state.results_cache and st.session_state.results_cache.get("status") == 1:
	results = st.session_state.results_cache
	sol = results.get("solution", {})
	
	try:
		# Calculate stage compositions for moduli display
		from core.compute import calculate_all_stages, calculate_quality_moduli
		
		if sol and state.get("rm_dict"):
			g = state.get("general", {})
			dust = state.get("dust", {})
			ash_comp = results.get("ash_comp", {})
			RM = state.get("rm_dict", {})
			
			# Calculate all stages
			stages = calculate_all_stages(
				RM=RM,
				x_percent=sol,
				dust=dust,
				pSilo=g.get("pSilo", 10.0) / 100.0,
				pKiln=g.get("pKiln", 0.0) / 100.0,
				tonKF=g.get("tonKF", 533.0),
				clinker_tph=g.get("clinker_tph", 342.0),
				dust_ratio=g.get("dust_ratio", 3.0) / 100.0,
				ASH=ash_comp,
				FCaO_cl=g.get("fcao", 1.0)
			)
			
			# Calculate moduli for each stage
			rm_moduli = calculate_quality_moduli(stages["raw_meal"])
			kf_moduli = calculate_quality_moduli(stages["kiln_feed"])
			cl_moduli = calculate_quality_moduli(stages["clinker"])
			
			# Display moduli in compact format
			st.sidebar.markdown("**Raw Meal:**")
			st.sidebar.caption(f"LSF: {rm_moduli['LSF']:.1f} | SM: {rm_moduli['SM']:.2f} | AM: {rm_moduli['AM']:.2f}")
			
			st.sidebar.markdown("**Kiln Feed:**")
			st.sidebar.caption(f"LSF: {kf_moduli['LSF']:.1f} | SM: {kf_moduli['SM']:.2f} | AM: {kf_moduli['AM']:.2f}")
			
			st.sidebar.markdown("**Clinker:**")
			st.sidebar.caption(f"LSF: {cl_moduli['LSF']:.1f} | SM: {cl_moduli['SM']:.2f} | AM: {cl_moduli['AM']:.2f}")
			
			# Calculate total cost
			rm_df = state.get('rm_df')
			tonKF = g.get('tonKF', 533.0)
			total_cost = 0
			if rm_df is not None and not rm_df.empty:
				for material, percentage in sol.items():
					if percentage is not None:
						tph = (percentage/100) * tonKF
						# Find HPP from DataFrame
						for _, row in rm_df.iterrows():
							if str(row.get('Material', '')).strip() == material:
								hpp = float(row.get('HPP', 0) or 0)
								total_cost += tph * hpp
								break
			
			st.sidebar.markdown("**Economics:**")
			st.sidebar.caption(f"Total Cost: Rp {total_cost:,.0f}/hour")
			
			# Dust and fuel metrics
			dust_tph = g.get('dust_ratio', 3.0) / 100.0 * g.get('clinker_tph', 342.0)
			total_fuel_tph = results.get('total_fuel_tph', 0)
			alternative_fuel_heat_pct = results.get('alternative_fuel_heat_pct', 0)
			
			st.sidebar.markdown("**Operations:**")
			st.sidebar.caption(f"Dust Loss: {dust_tph:.1f} TPH")
			st.sidebar.caption(f"Total Fuel: {total_fuel_tph:.1f} TPH")
			st.sidebar.caption(f"Alt. Fuel Heat: {alternative_fuel_heat_pct:.1f}%")
			
	except Exception as e:
		st.sidebar.error(f"Summary calc error: {str(e)[:30]}...")
else:
	st.sidebar.info("📊 Run calculation to see summary")

# Export Section
st.sidebar.markdown("---")
st.sidebar.markdown("📋 **Export Report**")

if hasattr(st.session_state, 'results_cache') and st.session_state.results_cache and st.session_state.results_cache.get("status") == 1:
	# Export buttons
	col1, col2 = st.sidebar.columns(2)
	
	with col1:
		if st.button("📄 Excel", key="export_excel", help="Export detailed report to Excel format", use_container_width=True):
			try:
				excel_data = create_excel_report(state, st.session_state.results_cache)
				if excel_data:
					timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
					filename = f"RawMix_Report_{timestamp}.xlsx"
					st.download_button(
						label="⬇️ Download Excel",
						data=excel_data,
						file_name=filename,
						mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
						key="download_excel"
					)
					st.success("✅ Excel report ready!")
			except Exception as e:
				st.error(f"❌ Excel export failed: {str(e)}")
	
	with col2:
		if st.button("📜 PDF", key="export_pdf", help="Export summary report to PDF format", use_container_width=True):
			try:
				pdf_data = create_pdf_report(state, st.session_state.results_cache)
				if pdf_data:
					timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
					filename = f"RawMix_Report_{timestamp}.pdf"
					st.download_button(
						label="⬇️ Download PDF",
						data=pdf_data,
						file_name=filename,
						mime="application/pdf",
						key="download_pdf"
					)
					st.success("✅ PDF report ready!")
			except Exception as e:
				st.error(f"❌ PDF export failed: {str(e)}")

else:
	st.sidebar.info("📋 Export available after successful calculation")


def try_solve():
	try:
		# Prepare inputs
		rm_df = state["rm_df"].copy()
		if rm_df is None or rm_df.empty:
			st.warning("⚠️ Raw Mix table is empty.")
			return None

		# Validate raw materials
		if len(rm_df) < 2:
			st.warning("⚠️ At least 2 raw materials required for optimization.")
			return None

		RM = to_rm_dict(rm_df)
		costs = to_costs_dict(rm_df)
		bounds = to_bounds_dict(rm_df)
		
		if not RM:
			st.error("❌ No valid raw materials found. Check material names and compositions.")
			return None

		dust = state.get("dust", {})
		g = state.get("general", {})
		c = state.get("constraints", {})

		# Validate general parameters
		if g.get("stec", 0) <= 0:
			st.error("❌ STEC must be greater than 0.")
			return None
		if g.get("clinker_tph", 0) <= 0:
			st.error("❌ Clinker production rate must be greater than 0.")
			return None
		if g.get("tonKF", 0) <= 0:
			st.error("❌ Kiln Feed rate must be greater than 0.")
			return None

		# Validate dust percentages
		pSilo = g.get("pSilo", 10.0)
		pKiln = g.get("pKiln", 0.0)
		if pSilo < 0 or pKiln < 0:
			st.error("❌ Dust percentages cannot be negative.")
			return None
		if pSilo > 0 and pKiln > 0:
			st.warning("⚠️ Both Dust→Silo and Dust→Kiln are set. Using Dust→Silo scenario.")
			pKiln = 0

		# Validate constraints
		for param, min_key, max_key in [("LSF", "LSF_min", "LSF_max"), ("SM", "SM_min", "SM_max"), ("AM", "AM_min", "AM_max"), ("C3S", "C3S_min", "C3S_max")]:
			min_val = c.get(min_key, 0)
			max_val = c.get(max_key, 0)
			if min_val >= max_val:
				st.error(f"❌ {param} minimum ({min_val}) must be less than maximum ({max_val}).")
				return None

		# Fuel handling
		fuels = state.get("fuel_rows", [])
		
		# Validate fuel proportions
		total_fuel_prop = sum(f.get("prop", 0) for f in fuels)
		if total_fuel_prop <= 0:
			st.warning("⚠️ No fuel proportions set. Using default fuel mix.")
			# Use default if no fuels specified
			fuels = [
				{"Fuel":"Fine Coal","prop":75.3,"cv":4800,"ash":14.0,"S":0.3,"SiO2":11.87,"Al2O3":9.03,"Fe2O3":51.37,"CaO":4.0,"K2O":0.20,"Na2O":0.30,"LOI":0.0},
				{"Fuel":"Sekam","prop":19.5,"cv":2500,"ash":25.0,"S":0.3,"SiO2":95.0,"Al2O3":0.17,"Fe2O3":0.35,"CaO":0.91,"K2O":0.11,"Na2O":0.43,"LOI":0.0},
				{"Fuel":"SBE","prop":1.2,"cv":1800,"ash":65.0,"S":0.5,"SiO2":64.0,"Al2O3":16.0,"Fe2O3":1.2,"CaO":1.2,"K2O":1.54,"Na2O":2.25,"LOI":0.0},
				{"Fuel":"Tankos","prop":4.0,"cv":3000,"ash":11.0,"S":0.2,"SiO2":40.0,"Al2O3":10.0,"Fe2O3":2.0,"CaO":10.0,"K2O":0.11,"Na2O":30.0,"LOI":0.0},
			]
		else:
			# Normalize fuel proportions to 100%
			for f in fuels:
				f["prop"] = (f.get("prop", 0) / total_fuel_prop) * 100

		cv_total = compute_cv_total(fuels)
		if cv_total <= 0:
			st.error("❌ Total calorific value must be greater than 0.")
			return None

		total_fuel_tph = compute_total_fuel_tph(g.get("stec", 800.0), g.get("clinker_tph", 342.0), cv_total)
		total_ash_tph = compute_total_ash_tph(fuels, total_fuel_tph)
		ash_comp = compute_ash_composition(fuels)
		
		# Add total ash TPH to ash composition for use in calculations
		if ash_comp:
			ash_comp['total_ash_tph'] = total_ash_tph

		# Solve
		status, sol, meta = solve_rawmix(
			RM=RM,
			DUST=dust,
			ASH=ash_comp,
			costs=costs,
			bounds=bounds,
			pSilo=pSilo / 100.0,  # Convert percentage to decimal
			pKiln=pKiln / 100.0,   # Convert percentage to decimal
			tonKF=g.get("tonKF", 533.0),
			clinkerTPH=g.get("clinker_tph", 342.0),
			dust_ratio=g.get("dust_ratio", 3.0) / 100.0,  # Convert percentage to decimal
			totalAshTPH=total_ash_tph,
			LSF_min=c.get("LSF_min", 95.5), LSF_max=c.get("LSF_max", 96.5),
			SM_min=c.get("SM_min", 2.28), SM_max=c.get("SM_max", 2.32),
			AM_min=c.get("AM_min", 1.55), AM_max=c.get("AM_max", 1.60),
			NaEq_max=c.get("NaEq_max", 0.60),
			C3S_min=c.get("C3S_min", 58.0), C3S_max=c.get("C3S_max", 65.0),
			FCaO_cl=g.get("fcao", 1.0),
			epsilon=0.001 if mode == "Feasibility" else 0.0,
			objective_mode=("cost" if mode == "Cost Minimization" else "feasibility"),
		)

		# Store RM dict for composition calculations
		state["rm_dict"] = RM

		# Check solution status and provide helpful feedback
		if status != 1:
			if status == -1:
				st.error("❌ Optimization problem is infeasible. Try:")
				st.write("• Relaxing constraint ranges (wider LSF, SM, AM, C3S limits)")
				st.write("• Checking raw material compositions for errors")
				st.write("• Adjusting dust scenarios or fuel mix")
			elif status == -2:
				st.error("❌ Optimization problem is unbounded.")
			elif status == -3:
				st.error("❌ Optimization problem is undefined.")
			else:
				st.error(f"❌ Solver failed with status: {status}")
			return {"status": status, "solution": {}, "meta": {}}

		# Calculate alternative fuel heat percentage
		alternative_fuel_heat_pct = compute_alternative_fuel_heat_percentage(fuels)

		return {
			"status": status,
			"solution": sol,
			"meta": meta,
			"total_fuel_tph": total_fuel_tph,
			"total_ash_tph": total_ash_tph,
			"cv_total": cv_total,
			"ash_comp": ash_comp,
			"alternative_fuel_heat_pct": alternative_fuel_heat_pct,
		}
	
	except Exception as e:
		st.error(f"❌ An error occurred during optimization: {str(e)}")
		st.write("Please check your input data and try again.")
		return None

# Smart auto/manual solve trigger with change detection
current_state_hash = calculate_state_hash(state, mode)
state_changed = (current_state_hash != st.session_state.get('last_state_hash'))

# Determine if we should solve
should_solve = False
if solve_clicked:
	# Manual solve always runs
	should_solve = True
	st.session_state.last_state_hash = current_state_hash
elif auto and state_changed:
	# Auto-resolve only if state actually changed
	should_solve = True
	st.session_state.last_state_hash = current_state_hash

# Use cached results if available and state hasn't changed
if not should_solve and hasattr(st.session_state, 'results_cache'):
	results = st.session_state.results_cache
else:
	results = None
	if should_solve:
		# Record solve time for performance monitoring
		solve_start_time = time.time()
		results = try_solve()
		solve_end_time = time.time()
		st.session_state.last_solve_time = solve_end_time - solve_start_time
		
		# Cache the results
		if results:
			st.session_state.results_cache = results

with tab_results:
	render_results_tab(state, results)

with tab_history:
	build_project_history_tab()
