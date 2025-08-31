import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import uuid
from typing import Dict, List, Optional, Tuple

class RawMixDatabase:
    """Database manager for Raw Mix Design Optimizer"""
    
    def __init__(self, db_path: str = "data/rawmix.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Projects table - stores different mix design projects
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # General parameters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS general_params (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    stec REAL DEFAULT 800.0,
                    clinker_tph REAL DEFAULT 342.0,
                    tonKF REAL DEFAULT 533.0,
                    dust_ratio REAL DEFAULT 5.0,
                    fcao REAL DEFAULT 1.2,
                    pSilo REAL DEFAULT 10.0,
                    pKiln REAL DEFAULT 5.0,
                    h2o_rawmeal REAL DEFAULT 0.50,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            # Raw materials table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_materials (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    material TEXT NOT NULL,
                    h2o REAL DEFAULT 0.0,
                    loi REAL DEFAULT 0.0,
                    sio2 REAL DEFAULT 0.0,
                    al2o3 REAL DEFAULT 0.0,
                    fe2o3 REAL DEFAULT 0.0,
                    cao REAL DEFAULT 0.0,
                    mgo REAL DEFAULT 0.0,
                    k2o REAL DEFAULT 0.0,
                    na2o REAL DEFAULT 0.0,
                    so3 REAL DEFAULT 0.0,
                    cl REAL DEFAULT 0.0,
                    hpp REAL DEFAULT 0.0,
                    min_percent REAL DEFAULT 0.0,
                    max_percent REAL DEFAULT 100.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            # Fuels table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fuels (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    fuel TEXT NOT NULL,
                    prop REAL DEFAULT 0.0,
                    cv REAL DEFAULT 4000.0,
                    ash REAL DEFAULT 15.0,
                    s REAL DEFAULT 0.3,
                    sio2 REAL DEFAULT 50.0,
                    al2o3 REAL DEFAULT 25.0,
                    fe2o3 REAL DEFAULT 15.0,
                    cao REAL DEFAULT 5.0,
                    k2o REAL DEFAULT 2.0,
                    na2o REAL DEFAULT 1.0,
                    loi REAL DEFAULT 0.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            # Constraints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS constraints (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    lsf_min REAL DEFAULT 95.5,
                    lsf_max REAL DEFAULT 96.5,
                    sm_min REAL DEFAULT 2.28,
                    sm_max REAL DEFAULT 2.32,
                    am_min REAL DEFAULT 1.55,
                    am_max REAL DEFAULT 1.60,
                    naeq_max REAL DEFAULT 0.60,
                    c3s_min REAL DEFAULT 58.0,
                    c3s_max REAL DEFAULT 65.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            # Dust composition table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dust_composition (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    h2o REAL DEFAULT 0.5,
                    loi REAL DEFAULT 40.0,
                    sio2 REAL DEFAULT 10.6,
                    al2o3 REAL DEFAULT 3.76,
                    fe2o3 REAL DEFAULT 2.23,
                    cao REAL DEFAULT 45.90,
                    mgo REAL DEFAULT 0.54,
                    k2o REAL DEFAULT 0.12,
                    na2o REAL DEFAULT 0.39,
                    so3 REAL DEFAULT 0.02,
                    cl REAL DEFAULT 0.02,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            # Results history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS results_history (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    solution_data TEXT NOT NULL,
                    meta_data TEXT,
                    total_cost REAL,
                    solver_status INTEGER,
                    calculation_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
    
    # Project Management Methods
    def create_project(self, name: str, description: str = "") -> str:
        """Create a new project and return its ID"""
        project_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (id, name, description)
                VALUES (?, ?, ?)
            """, (project_id, name, description))
            conn.commit()
        
        # Initialize with default values
        self._initialize_project_defaults(project_id)
        return project_id
    
    def _initialize_project_defaults(self, project_id: str):
        """Initialize project with default values from defaults.json"""
        # Load current defaults
        defaults_path = Path("data/defaults.json")
        if defaults_path.exists():
            defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
        else:
            defaults = {}
        
        # Initialize general parameters
        general = defaults.get("general", {})
        self.save_general_params(project_id, general)
        
        # Initialize raw materials
        raw_mix_data = defaults.get("raw_mix_rows", [])
        if raw_mix_data:
            for row in raw_mix_data:
                self.add_raw_material(project_id, *row)
        
        # Initialize fuels
        fuel_data = defaults.get("fuel_rows", [])
        for fuel in fuel_data:
            self.add_fuel(project_id, fuel)
        
        # Initialize constraints
        constraints = defaults.get("constraints", {})
        self.save_constraints(project_id, constraints)
        
        # Initialize dust composition
        dust = defaults.get("dust", {})
        self.save_dust_composition(project_id, dust)
    
    def get_projects(self) -> List[Dict]:
        """Get all active projects"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, created_at, updated_at
                FROM projects 
                WHERE is_active = TRUE 
                ORDER BY updated_at DESC
            """)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def delete_project(self, project_id: str):
        """Delete a project (soft delete)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects SET is_active = FALSE 
                WHERE id = ?
            """, (project_id,))
            conn.commit()
    
    # General Parameters Methods
    def save_general_params(self, project_id: str, params: Dict):
        """Save general parameters for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete existing params
            cursor.execute("DELETE FROM general_params WHERE project_id = ?", (project_id,))
            
            # Insert new params
            cursor.execute("""
                INSERT INTO general_params (
                    id, project_id, stec, clinker_tph, tonKF, dust_ratio,
                    fcao, pSilo, pKiln, h2o_rawmeal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), project_id,
                params.get("stec", 800.0),
                params.get("clinker_tph", 342.0),
                params.get("tonKF", 533.0),
                params.get("dust_ratio", 5.0),
                params.get("fcao", 1.2),
                params.get("pSilo", 10.0),
                params.get("pKiln", 5.0),
                params.get("h2o_rawmeal", 0.50)
            ))
            conn.commit()
    
    def get_general_params(self, project_id: str) -> Dict:
        """Get general parameters for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT stec, clinker_tph, tonKF, dust_ratio, fcao, pSilo, pKiln, h2o_rawmeal
                FROM general_params WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "stec": row[0],
                    "clinker_tph": row[1],
                    "tonKF": row[2],
                    "dust_ratio": row[3],
                    "fcao": row[4],
                    "pSilo": row[5],
                    "pKiln": row[6],
                    "h2o_rawmeal": row[7]
                }
            return {}
    
    # Raw Materials Methods
    def add_raw_material(self, project_id: str, material: str, h2o: float = 0.0,
                        loi: float = 0.0, sio2: float = 0.0, al2o3: float = 0.0,
                        fe2o3: float = 0.0, cao: float = 0.0, mgo: float = 0.0,
                        k2o: float = 0.0, na2o: float = 0.0, so3: float = 0.0,
                        cl: float = 0.0, hpp: float = 0.0, min_percent: float = 0.0,
                        max_percent: float = 100.0) -> str:
        """Add a raw material to a project"""
        material_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO raw_materials (
                    id, project_id, material, h2o, loi, sio2, al2o3, fe2o3,
                    cao, mgo, k2o, na2o, so3, cl, hpp, min_percent, max_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                material_id, project_id, material, h2o, loi, sio2, al2o3, fe2o3,
                cao, mgo, k2o, na2o, so3, cl, hpp, min_percent, max_percent
            ))
            conn.commit()
        
        return material_id
    
    def get_raw_materials(self, project_id: str) -> pd.DataFrame:
        """Get raw materials for a project as DataFrame"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT material, h2o, loi, sio2, al2o3, fe2o3, cao, mgo, 
                       k2o, na2o, so3, cl, hpp, min_percent, max_percent
                FROM raw_materials 
                WHERE project_id = ? AND is_active = TRUE
                ORDER BY created_at
            """
            df = pd.read_sql_query(query, conn, params=(project_id,))
            
            # Rename columns to match existing format
            df.columns = ["Material","H2O","LOI","SiO2","Al2O3","Fe2O3","CaO","MgO","K2O","Na2O","SO3","Cl","HPP","min%","max%"]
            return df
    
    def update_raw_materials(self, project_id: str, materials_df: pd.DataFrame):
        """Update all raw materials for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete existing materials
            cursor.execute("DELETE FROM raw_materials WHERE project_id = ?", (project_id,))
            
            # Insert updated materials
            for _, row in materials_df.iterrows():
                cursor.execute("""
                    INSERT INTO raw_materials (
                        id, project_id, material, h2o, loi, sio2, al2o3, fe2o3,
                        cao, mgo, k2o, na2o, so3, cl, hpp, min_percent, max_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), project_id,
                    row["Material"], row["H2O"], row["LOI"], row["SiO2"], row["Al2O3"],
                    row["Fe2O3"], row["CaO"], row["MgO"], row["K2O"], row["Na2O"],
                    row["SO3"], row["Cl"], row["HPP"], row["min%"], row["max%"]
                ))
            
            conn.commit()
    
    def delete_raw_material(self, project_id: str, material_name: str):
        """Delete a raw material"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE raw_materials SET is_active = FALSE 
                WHERE project_id = ? AND material = ?
            """, (project_id, material_name))
            conn.commit()
    
    # Fuel Methods
    def add_fuel(self, project_id: str, fuel_data: Dict) -> str:
        """Add a fuel to a project"""
        fuel_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fuels (
                    id, project_id, fuel, prop, cv, ash, s, sio2, al2o3, 
                    fe2o3, cao, k2o, na2o, loi
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fuel_id, project_id,
                fuel_data.get("Fuel", "New Fuel"),
                fuel_data.get("prop", 0.0),
                fuel_data.get("cv", 4000.0),
                fuel_data.get("ash", 15.0),
                fuel_data.get("S", 0.3),
                fuel_data.get("SiO2", 50.0),
                fuel_data.get("Al2O3", 25.0),
                fuel_data.get("Fe2O3", 15.0),
                fuel_data.get("CaO", 5.0),
                fuel_data.get("K2O", 2.0),
                fuel_data.get("Na2O", 1.0),
                fuel_data.get("LOI", 0.0)
            ))
            conn.commit()
        
        return fuel_id
    
    def get_fuels(self, project_id: str) -> List[Dict]:
        """Get fuels for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fuel, prop, cv, ash, s, sio2, al2o3, fe2o3, cao, k2o, na2o, loi
                FROM fuels 
                WHERE project_id = ? AND is_active = TRUE
                ORDER BY created_at
            """, (project_id,))
            
            columns = ["Fuel","prop","cv","ash","S","SiO2","Al2O3","Fe2O3","CaO","K2O","Na2O","LOI"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def update_fuels(self, project_id: str, fuel_data: List[Dict]):
        """Update all fuels for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete existing fuels
            cursor.execute("DELETE FROM fuels WHERE project_id = ?", (project_id,))
            
            # Insert updated fuels
            for fuel in fuel_data:
                cursor.execute("""
                    INSERT INTO fuels (
                        id, project_id, fuel, prop, cv, ash, s, sio2, al2o3, 
                        fe2o3, cao, k2o, na2o, loi
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), project_id,
                    fuel.get("Fuel", "New Fuel"),
                    fuel.get("prop", 0.0),
                    fuel.get("cv", 4000.0),
                    fuel.get("ash", 15.0),
                    fuel.get("S", 0.3),
                    fuel.get("SiO2", 50.0),
                    fuel.get("Al2O3", 25.0),
                    fuel.get("Fe2O3", 15.0),
                    fuel.get("CaO", 5.0),
                    fuel.get("K2O", 2.0),
                    fuel.get("Na2O", 1.0),
                    fuel.get("LOI", 0.0)
                ))
            
            conn.commit()
    
    # Constraints Methods
    def save_constraints(self, project_id: str, constraints: Dict):
        """Save constraints for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete existing constraints
            cursor.execute("DELETE FROM constraints WHERE project_id = ?", (project_id,))
            
            # Insert new constraints
            cursor.execute("""
                INSERT INTO constraints (
                    id, project_id, lsf_min, lsf_max, sm_min, sm_max,
                    am_min, am_max, naeq_max, c3s_min, c3s_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), project_id,
                constraints.get("LSF_min", 95.5),
                constraints.get("LSF_max", 96.5),
                constraints.get("SM_min", 2.28),
                constraints.get("SM_max", 2.32),
                constraints.get("AM_min", 1.55),
                constraints.get("AM_max", 1.60),
                constraints.get("NaEq_max", 0.60),
                constraints.get("C3S_min", 58.0),
                constraints.get("C3S_max", 65.0)
            ))
            conn.commit()
    
    def get_constraints(self, project_id: str) -> Dict:
        """Get constraints for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT lsf_min, lsf_max, sm_min, sm_max, am_min, am_max,
                       naeq_max, c3s_min, c3s_max
                FROM constraints WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "LSF_min": row[0], "LSF_max": row[1],
                    "SM_min": row[2], "SM_max": row[3],
                    "AM_min": row[4], "AM_max": row[5],
                    "NaEq_max": row[6],
                    "C3S_min": row[7], "C3S_max": row[8]
                }
            return {}
    
    # Dust Composition Methods
    def save_dust_composition(self, project_id: str, dust: Dict):
        """Save dust composition for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete existing dust composition
            cursor.execute("DELETE FROM dust_composition WHERE project_id = ?", (project_id,))
            
            # Insert new dust composition
            cursor.execute("""
                INSERT INTO dust_composition (
                    id, project_id, h2o, loi, sio2, al2o3, fe2o3,
                    cao, mgo, k2o, na2o, so3, cl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), project_id,
                dust.get("H2O", 0.5),
                dust.get("LOI", 40.0),
                dust.get("SiO2", 10.6),
                dust.get("Al2O3", 3.76),
                dust.get("Fe2O3", 2.23),
                dust.get("CaO", 45.90),
                dust.get("MgO", 0.54),
                dust.get("K2O", 0.12),
                dust.get("Na2O", 0.39),
                dust.get("SO3", 0.02),
                dust.get("Cl", 0.02)
            ))
            conn.commit()
    
    def get_dust_composition(self, project_id: str) -> Dict:
        """Get dust composition for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h2o, loi, sio2, al2o3, fe2o3, cao, mgo, k2o, na2o, so3, cl
                FROM dust_composition WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "H2O": row[0], "LOI": row[1], "SiO2": row[2],
                    "Al2O3": row[3], "Fe2O3": row[4], "CaO": row[5],
                    "MgO": row[6], "K2O": row[7], "Na2O": row[8],
                    "SO3": row[9], "Cl": row[10]
                }
            return {}
    
    # Results History Methods
    def save_result(self, project_id: str, results: Dict, calculation_time: float = 0.0):
        """Save optimization results"""
        result_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO results_history (
                    id, project_id, solution_data, meta_data, total_cost,
                    solver_status, calculation_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result_id, project_id,
                json.dumps(results.get("solution", {})),
                json.dumps(results.get("meta", {})),
                sum(results.get("solution", {}).values()) if results.get("solution") else 0.0,
                results.get("status", 0),
                calculation_time
            ))
            conn.commit()
        
        return result_id
    
    def get_results_history(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get results history for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, solution_data, meta_data, total_cost, solver_status,
                       calculation_time, created_at
                FROM results_history 
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, limit))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                result["solution_data"] = json.loads(result["solution_data"])
                result["meta_data"] = json.loads(result["meta_data"]) if result["meta_data"] else {}
                results.append(result)
            
            return results
    
    # Export/Import Methods
    def export_project(self, project_id: str) -> Dict:
        """Export complete project data"""
        return {
            "general": self.get_general_params(project_id),
            "raw_materials": self.get_raw_materials(project_id).to_dict('records'),
            "fuels": self.get_fuels(project_id),
            "constraints": self.get_constraints(project_id),
            "dust": self.get_dust_composition(project_id),
            "results_history": self.get_results_history(project_id, limit=5)
        }
    
    def import_project(self, name: str, project_data: Dict, description: str = "") -> str:
        """Import project from data"""
        project_id = self.create_project(name, description)
        
        # Import each data type
        if "general" in project_data:
            self.save_general_params(project_id, project_data["general"])
        
        if "raw_materials" in project_data:
            materials_df = pd.DataFrame(project_data["raw_materials"])
            self.update_raw_materials(project_id, materials_df)
        
        if "fuels" in project_data:
            self.update_fuels(project_id, project_data["fuels"])
        
        if "constraints" in project_data:
            self.save_constraints(project_id, project_data["constraints"])
        
        if "dust" in project_data:
            self.save_dust_composition(project_id, project_data["dust"])
        
        return project_id

# Initialize global database instance
db = RawMixDatabase()