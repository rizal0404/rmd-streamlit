# Raw Mix Design Clinker – Panduan Teknis & Blueprint Aplikasi (Streamlit + PuLP)

> **Tujuan**  
> Dokumen Markdown ini adalah _single source of truth_ untuk membangun aplikasi **Raw Mix Design** berbasis **Python + Streamlit** dengan **Linear Programming (PuLP)**. Semua perhitungan mengikuti alur A–K (Raw Meal → Kilnfeed → Unignited → Clinker) dengan **kendala mutu pada basis Clinker** (LSF, SM, AM, NaEq, C3S).  
> UI meniru layout Excel referensi: **input = kuning**, **output = abu-abu & hijau** (on-spec).

---

## 0) Ringkasan Fitur

- **Optimasi proporsi feeder** (LS, CY, SS, CS, dst.) dengan **Σ% = 100**.
- **Kendala mutu di basis Clinker**: LSF, SM, AM, NaEq, C3S (bisa tambah LP, C3A/C4AF).
- **Dukungan skenario dust**: _Dust→Silo_ **atau** _Dust→Kiln_.
- **Integrasi Fuel**: STEC, CV, Proporsi fuel, Ash% → Hitung **Total Fuel TPH**, **Total Ash TPH** dan **komposisi abu**.
- **UI modern**: `tabs`, `data_editor`, indikator warna (grey/green), tombol **Calculate** dan opsi **Auto-resolve** (re-solve saat input berubah).
- **Ekspor**: unduh CSV hasil proporsi & mutu, snapshot parameter.

---

## 1) Struktur Direktori (disarankan)

```
rawmix-app/
├─ app.py                 # Streamlit app
├─ core/
│  ├─ model.py            # formulasi LP (PuLP)
│  ├─ compute.py          # perhitungan A–E, I (mass balance & moduli)
│  └─ ui.py               # komponen tampilan (tabel styler, widgets)
├─ data/
│  └─ defaults.json       # default komposisi & parameter (opsional)
├─ requirements.txt
└─ README.md
```

**requirements.txt**
```
streamlit>=1.36
pulp>=2.7
pandas>=2.2
numpy>=1.26
```

Jalankan:
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 2) Data Model & Input (warna **kuning**)

### 2.1 Raw Mix (basis kering) & HPP
Empat bahan baku default (dapat diperluas):

| Bahan | H₂O | LOI | SiO₂ | Al₂O₃ | Fe₂O₃ | CaO  | MgO  | K₂O  | Na₂O | SO₃ | Cl  | **HPP (Rp/t)** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **LS** | 7.50 | 43.00 | 1.07 | 1.24 | 0.55 | 53.28 | 0.26 | 0.04 | 0.03 | 0.05 | 0.01 | 48632 |
| **CY** | 16.00 | 13.87 | 67.00 | 15.27 | 9.09 | 1.28 | 1.42 | 1.18 | 0.58 | 0.12 | 0.01 | 79130 |
| **SS** | 11.36 | 2.45 | 84.11 | 6.40 | 4.21 | 0.56 | 0.09 | 0.22 | 0.01 | 0.01 | 0.00 | 106507 |
| **CS** | 3.20 | 0.00 | 35.40 | 4.28 | 52.06 | 5.77 | 2.17 | 0.03 | 0.01 | 0.03 | 0.00 | 353510 |

> **Catatan**: Nama CS diasumsikan _copper slag_ (Fe₂O₃ tinggi). Anda bebas mengganti/menambah material.

### 2.2 Dust (EP/GCT)
```
Dust: { H2O:0.00, LOI:10.06, SiO2:3.76, Al2O3:2.23, Fe2O3:45.90, CaO:40.00, MgO:0.54,
        K2O:0.12, Na2O:0.39, SO3:0.02, Cl:0.02 }
```

### 2.3 Fuel & Operational
Empat fuel default (bisa 0% jika tidak dipakai):

| Fuel | H₂O | LOI | SiO₂ | Al₂O₃ | Fe₂O₃ | CaO | MgO | K₂O | Na₂O | SO₃ | Cl | **Prop. %** | **CV (kcal/kg)** | **Ash %** | **S %** | **SO₃ fuel %** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fine Coal | 0.00 | 23.43 | 11.87 | 9.03 | 51.37 | 4.00 | 0.21 | 0.20 | 0.30 | 0.00 | – | 75.3 | 4800 | 14.00 | 0.30 | 0.37 |
| Sekam     | 25.00 | 4.75  | 95.00 | 0.17 | 0.35 | 0.91 | 0.42 | 0.11 | 0.43 | 0.63 | – | 19.5 | 2500 | 25.00 | 0.30 | 0.32 |
| SBE       | 8.25  | 7.90  | 64.00 | 16.00| 1.20 | 1.20 | 2.10 | 1.54 | 2.25 | 0.49 | – | 1.2  | 1800 | 65.00 | 0.50 | 0.37 |
| Tankos    | 47.70 | 4.00  | 40.00 | 10.00| 2.00 | 10.00| 3.00 | 0.11 | 30.00| 1.00 | – | 4.0  | 3000 | 11.00 | 0.20 | 0.32 |

**Parameter operasi**:
- **STEC** (kcal/kg klinker) – default 800
- **Clinker Prod.** (TPH) – default 342
- **Kiln Feed (TPH)** – default 533 (bisa dihitung dari faktor konversi)
- **Raw Meal (TPH)** – default 750
- **Faktor konversi Kilnfeed → Clinker** – default **0.641**
- **Dust Ratio %** (hilang/terikut) – default 3.0
- **%Dust to Silo** & **%Dust to Kiln** (pilih salah satu 100/0)
- **Free Lime (FCaO) clinker %** – default 1.0

### 2.4 Target Mutu (basis **Clinker**)
- **LSF [%]**: min–max (cth 95.5–96.5)  
- **SM**: min–max (cth 2.28–2.32)  
- **AM**: min–max (cth 1.55–1.60)  
- **Na₂Oeq [%]**: max (cth 0.60)  
- **C3S [%]**: min–max (cth 58–65)

---

## 3) Alur Perhitungan (A–E, I)

> Semua step dihitung ulang **otomatis** setelah solver memberikan proporsi optimal, sebagai verifikasi dan tampilan di UI.

### A. Raw Meal
Untuk setiap oksida **Ox**:
```
Ox_RM(%) = Σ_i ( Ox_i[%] * proporsi_i[%] ) / 100
```
(Proporsi basis kering.)

### B. Kiln Feed (pilih skenario dust)
- **Dust→Silo**: `Ox_KF = (1−pSilo)*Ox_RM + pSilo*Ox_Dust`
- **Dust→Kiln**: `Ox_KF = (Ox_RM + pKiln*Ox_Dust)/(1+pKiln)`

### C. Unignited (KF + Ash − DustLoss)
- `tonDustLoss = DustRatio * ClinkerTPH`
- `TotalFuelTPH = (STEC * ClinkerTPH) / CV_total`
- `TotalAshTPH = Σ_i (Ash%_i * Fuel_i_TPH)`
- `D = tonKF − tonDustLoss + TotalAshTPH` (konstan dari input)

Untuk setiap **Ox**:
```
Ox_u = ( Ox_KF*tonKF − Ox_Dust*tonDustLoss + Ox_Ash*TotalAshTPH ) / D
```
`LOI_u` dihitung dengan cara sama.

### D. Clinker (bebas LOI)
```
Ox_cl = Ox_u / (100 − LOI_u) * 100
```

### E. Fuel & Total Fuel
- `CV_total = Σ(p_i * CV_i) / Σ(p_i)`  
- `Fuel_i_TPH = p_i * TotalFuelTPH`  
- `Ash_i_TPH  = Ash%_i * Fuel_i_TPH`  
- `Ox_Ash` (komposisi abu total) = rata–rata tertimbang dengan bobot `Ash_i_TPH`.

### I. Moduli & Turunan
- **LSF**: `CaO/(2.8SiO2 + 1.18Al2O3 + 0.65Fe2O3)*100`
- **SM**: `SiO2/(Al2O3 + Fe2O3)`
- **AM**: `Al2O3/Fe2O3`
- **NaEq**: `Na2O + 0.658*K2O`
- **Bogue (Clinker)**:
  - `C3S = 4.07*CaO_eff − 7.60*SiO2 − 6.72*Al2O3 − 1.43*Fe2O3`
  - `C2S = 2.87*SiO2 − 0.7544*C3S` (atau rumus alternatif linear)
  - `C3A = 2.65*Al2O3 − 1.69*Fe2O3`
  - `C4AF = 3.04*Fe2O3`  
  `CaO_eff = CaO_cl − FCaO_cl`

---

## 4) Formulasi Solver (F) – **Kendala Mutu di Basis Clinker** (Linear)

> **Kunci linearitas**: kerjakan di **basis Unignited** lalu **normalisasi batal** untuk rasio; untuk constraint yang memakai `%clinker` di RHS, kalikan dengan `Z/100`, dengan `Z = 100 − LOI_u` (linear).

- **Variabel Keputusan**: proporsi feeder (LS, CY, SS, CS) dalam **%** (0–100).
- **Equality**: `LS + CY + SS + CS = 100` (gaya Excel).
- **Objective**:  
  - **Feasibility** (0) **+ tie-breaker kecil** (ε * total biaya) → solusi stabil.  
  - Alternatif: mode **Cost Minimization** (toggle UI).

**Kendala mutu (linear, basis clinker):**
- **LSF**:
  ```
  Ca_u ≥ (LSF_min/100) * (2.8*Si_u + 1.18*Al_u + 0.65*Fe_u)
  Ca_u ≤ (LSF_max/100) * (2.8*Si_u + 1.18*Al_u + 0.65*Fe_u)
  ```
- **SM**:
  ```
  Si_u ≥ SM_min * (Al_u + Fe_u)
  Si_u ≤ SM_max * (Al_u + Fe_u)
  ```
- **AM**:
  ```
  Al_u ≥ AM_min * Fe_u
  Al_u ≤ AM_max * Fe_u
  ```
- **NaEq ≤ max**:
  ```
  (Na_u + 0.658*K_u) ≤ NaEq_max * (Z/100)
  ```
- **C3S (Bogue, dengan Free Lime)**:
  ```
  Ca_u_eff = Ca_u − FCaO_cl * (Z/100)
  C3S_lin  = 4.07*Ca_u_eff − 7.60*Si_u − 6.72*Al_u − 1.43*Fe_u
  C3S_lin ≥ C3S_min * (Z/100)
  C3S_lin ≤ C3S_max * (Z/100)
  ```

> Semua `*_u` dan `Z` adalah **linear** karena `D, tonKF, tonDustLoss, TotalAshTPH` = **konstan input**.

---

## 5) Contoh Implementasi – **model.py** (PuLP, ringkas)

```python
import pulp

def solve_rawmix(
    RM, DUST, ASH,
    costs, bounds,  # costs: dict HPP per feeder; bounds: dict {name:(min,max)}
    pSilo, pKiln, tonKF, clinkerTPH, dust_ratio, totalAshTPH,
    LSF_min, LSF_max, SM_min, SM_max, AM_min, AM_max, NaEq_max, C3S_min, C3S_max,
    FCaO_cl=1.0, epsilon=1e-3
):
    # 1) konstanta mass balance
    tonDustLoss = dust_ratio * clinkerTPH
    D = tonKF - tonDustLoss + totalAshTPH  # denominator unignited (konstan)

    # 2) LP model
    m = pulp.LpProblem("RawMix_ClinkerQuality", pulp.LpMinimize)

    # 3) Vars proporsi
    x = {k: pulp.LpVariable(k, lowBound=bounds[k][0], upBound=bounds[k][1]) for k in bounds}

    # 4) Sum-to-100
    m += pulp.lpSum(x.values()) == 100, "Sum100"

    # 5) Raw Meal oxides (linear in x)
    def ox_rm(ox):
        return pulp.lpSum(x[k] * RM[k][ox] for k in x) / 100.0

    Si_RM, Al_RM = ox_rm("SiO2"), ox_rm("Al2O3")
    Fe_RM, Ca_RM = ox_rm("Fe2O3"), ox_rm("CaO")
    K_RM, Na_RM  = ox_rm("K2O"),  ox_rm("Na2O")
    LOI_RM       = ox_rm("LOI")

    # 6) Kiln Feed oxides
    if pSilo > 0:
        Si_KF = (1-pSilo)*Si_RM + pSilo*DUST["SiO2"]
        Al_KF = (1-pSilo)*Al_RM + pSilo*DUST["Al2O3"]
        Fe_KF = (1-pSilo)*Fe_RM + pSilo*DUST["Fe2O3"]
        Ca_KF = (1-pSilo)*Ca_RM + pSilo*DUST["CaO"]
        K_KF  = (1-pSilo)*K_RM  + pSilo*DUST["K2O"]
        Na_KF = (1-pSilo)*Na_RM + pSilo*DUST["Na2O"]
        LOI_KF= (1-pSilo)*LOI_RM+ pSilo*DUST["LOI"]
    else:
        denom = 1 + pKiln
        Si_KF = (Si_RM + pKiln*DUST["SiO2"]) / denom
        Al_KF = (Al_RM + pKiln*DUST["Al2O3"]) / denom
        Fe_KF = (Fe_RM + pKiln*DUST["Fe2O3"]) / denom
        Ca_KF = (Ca_RM + pKiln*DUST["CaO"])  / denom
        K_KF  = (K_RM  + pKiln*DUST["K2O"])  / denom
        Na_KF = (Na_RM + pKiln*DUST["Na2O"]) / denom
        LOI_KF= (LOI_RM+ pKiln*DUST["LOI"])  / denom

    # 7) Unignited
    def ox_u(Ox_KF, Ox_name):
        return ((Ox_KF*tonKF) - (DUST[Ox_name]*tonDustLoss) + (ASH[Ox_name]*totalAshTPH)) / D

    Si_u, Al_u, Fe_u, Ca_u = ox_u(Si_KF,"SiO2"), ox_u(Al_KF,"Al2O3"), ox_u(Fe_KF,"Fe2O3"), ox_u(Ca_KF,"CaO")
    K_u, Na_u = ox_u(K_KF,"K2O"), ox_u(Na_KF,"Na2O")
    LOI_u     = ((LOI_KF*tonKF) - (DUST["LOI"]*tonDustLoss) + (ASH["LOI"]*totalAshTPH)) / D
    Z = 100 - LOI_u
    Ca_u_eff = Ca_u - FCaO_cl * (Z/100.0)
    C3S_lin  = 4.07*Ca_u_eff - 7.60*Si_u - 6.72*Al_u - 1.43*Fe_u

    # 8) Constraints mutu (clinker)
    m += Ca_u >= (LSF_min/100.0)*(2.8*Si_u + 1.18*Al_u + 0.65*Fe_u)
    m += Ca_u <= (LSF_max/100.0)*(2.8*Si_u + 1.18*Al_u + 0.65*Fe_u)

    m += Si_u >= SM_min * (Al_u + Fe_u)
    m += Si_u <= SM_max * (Al_u + Fe_u)

    m += Al_u >= AM_min * Fe_u
    m += Al_u <= AM_max * Fe_u

    m += (Na_u + 0.658*K_u) <= NaEq_max * (Z/100.0)

    m += C3S_lin >= C3S_min * (Z/100.0)
    m += C3S_lin <= C3S_max * (Z/100.0)

    # 9) Objective: feasibility + tie-breaker biaya kecil
    m += epsilon * pulp.lpSum(x[k]*costs[k] for k in x)

    # 10) Solve
    status = m.solve(pulp.PULP_CBC_CMD(msg=False))
    sol = {k: x[k].value() for k in x}
    return status, sol, dict(C3S_lin=C3S_lin.value(), Z=Z.value(), LOI_u=LOI_u.value())
```

---

## 6) Perhitungan Mass Balance & Mutu – **compute.py**

```python
import numpy as np
import pandas as pd

def compute_cv_total(fuels):
    num = sum(f["prop"]*f["cv"] for f in fuels)
    den = sum(f["prop"] for f in fuels) or 1.0
    return num/den

def compute_total_fuel_tph(stec, clinker_tph, cv_total):
    return (stec * clinker_tph) / cv_total

def compute_total_ash_tph(fuels, total_fuel_tph):
    return sum((f["ash"]/100.0) * (f["prop"]/100.0) * total_fuel_tph for f in fuels)

def compute_ash_composition(fuels):
    # TODO: rata-rata tertimbang komposisi abu berdasarkan Ash_i_TPH
    pass

def compute_bogue(cl):
    CaO_eff = cl["CaO"] - cl.get("FCaO", 0.0)
    C3S = 4.07*CaO_eff - 7.60*cl["SiO2"] - 6.72*cl["Al2O3"] - 1.43*cl["Fe2O3"]
    C4AF = 3.04*cl["Fe2O3"]
    C3A  = 2.65*cl["Al2O3"] - 1.69*cl["Fe2O3"]
    C2S  = 2.87*cl["SiO2"] - 0.7544*C3S
    return dict(C3S=C3S, C2S=C2S, C3A=C3A, C4AF=C4AF)
```

> **Catatan**: di app, setelah solusi proporsi diperoleh, hitung ulang Ox_RM → Ox_KF → Ox_u → Ox_cl, lalu hitung LSF/SM/AM/NaEq & Bogue untuk ditampilkan.

---

## 7) UI – **app.py** (kerangka)

```python
import streamlit as st
import pandas as pd
from core.model import solve_rawmix

st.set_page_config(page_title="Raw Mix Design Optimizer", layout="wide")

st.title("Raw Mix Design Optimizer (Streamlit + PuLP)")
st.caption("Proporsi feeder Σ=100 dengan kendala mutu di basis Clinker (LSF, SM, AM, NaEq, C3S).")

tab_in, tab_res = st.tabs(["🟡 Input Data", "✅ Solver & Result"])

with tab_in:
    st.subheader("Raw Materials (dry basis) – Kuning")
    rm_df = pd.DataFrame([
        ["LS",7.50,43.00,1.07,1.24,0.55,53.28,0.26,0.04,0.03,0.05,0.01,48632,0,100],
        ["CY",16.00,13.87,67.00,15.27,9.09,1.28,1.42,1.18,0.58,0.12,0.01,79130,0,100],
        ["SS",11.36,2.45,84.11,6.40,4.21,0.56,0.09,0.22,0.01,0.01,0.00,106507,0,100],
        ["CS",3.20,0.00,35.40,4.28,52.06,5.77,2.17,0.03,0.01,0.03,0.00,353510,0,100],
    ], columns=["Material","H2O","LOI","SiO2","Al2O3","Fe2O3","CaO","MgO","K2O","Na2O","SO3","Cl","HPP","min%","max%"])
    rm_df = st.data_editor(rm_df, num_rows="dynamic", use_container_width=True)

    st.subheader("Dust – Kuning")
    dust = {"H2O":0.0,"LOI":10.06,"SiO2":3.76,"Al2O3":2.23,"Fe2O3":45.90,"CaO":40.00,"MgO":0.54,"K2O":0.12,"Na2O":0.39,"SO3":0.02,"Cl":0.02}
    cols = st.columns(len(dust))
    for i,k in enumerate(dust): dust[k] = cols[i].number_input(k, value=float(dust[k]))

    st.subheader("Fuel & Operational – Kuning")
    c1,c2,c3,c4,c5 = st.columns(5)
    STEC = c1.number_input("STEC (kcal/kg)", 800.0)
    clinkerTPH = c2.number_input("Clinker Prod (TPH)", 342.0)
    tonKF = c3.number_input("Kiln Feed (TPH)", 533.0)
    dust_ratio = c4.number_input("Dust Ratio (%)", 3.0)/100.0
    FCaO_cl = c5.number_input("Free Lime Clinker (%)", 1.0)

    c6,c7 = st.columns(2)
    pSilo = c6.number_input("% Dust→Silo", 10.0)/100.0
    pKiln = c7.number_input("% Dust→Kiln", 0.0)/100.0

    st.markdown("**Target Mutu (Clinker)**")
    c1,c2,c3,c4,c5 = st.columns(5)
    LSF_min = c1.number_input("LSF min", 95.5); LSF_max = c1.number_input("LSF max", 96.5)
    SM_min  = c2.number_input("SM  min", 2.28); SM_max  = c2.number_input("SM  max", 2.32)
    AM_min  = c3.number_input("AM  min", 1.55); AM_max  = c3.number_input("AM  max", 1.60)
    NaEq_max= c4.number_input("NaEq max (%)", 0.60)
    C3S_min = c5.number_input("C3S min (%)", 58.0); C3S_max = c5.number_input("C3S max (%)", 65.0)

    auto = st.toggle("Auto-resolve saat input berubah", True)
    go = st.button("Calculate")

with tab_res:
    st.subheader("Hasil Solver & Rekap – Abu-abu/Hijau")
    st.info("Hook hasil solver & tabel rekap ditaruh di sini (lihat core/model.py).")
```

---

## 8) Perhitungan Pasca-Solver (G & K)

Setelah proporsi optimal `x_i` diperoleh:
- **%Dry** = output solver.  
- **Index Bahan (%Wet)** ≈ `Proporsi_dry_i * ((100 − H2O_RM)/(100 − H2O_i))`  
- **TPH_i** = `%Dry_i/100 * tonKF`  
- **Cost_i [Rp/h]** = `TPH_i * HPP_i`  
- **Summaries**: `Ton Fuel`, `Ton Raw Meal`, `Ton Kiln Feed`, `Ton Clinker`, `Ton Dust`, `Ash% in system`, dll.  
- **Mutu**: hitung LSF/SM/AM NaEq untuk **Raw Meal**, **Kiln Feed**, **Clinker**; hitung **Bogue** (C3S, C2S, C3A, C4AF) dan (opsional) **Liquid Phase**.

---

## 9) Mode Objective

- **Mode Excel-like (default)**: `Σ% = 100` (equality), objective = 0 + `ε * biaya` (tie-breaker).  
- **Mode Cost Minimization** (opsional toggle di UI): objective = `Σ x_i * HPP_i` dengan constraint `Σ% = 100`.

---

## 10) Validasi & Edge Cases

- **Infeasible**: tampilkan status solver + hint mana batas yang ketat (mis. kurangi LSF_min atau naikkan max CY).  
- **Dust conflict**: pastikan **pSilo + pKiln ≤ 1**; jika user isi keduanya, normalisasi.  
- **Fuel**: jika Σ proporsi fuel ≠ 100, normalisasi sebelum hitung `CV_total`.  
- **NaN/negatif**: clamp hasil Bogue < 0 menjadi 0 untuk tampilan.  
- **Units**: konsisten **% berat** dan **TPH**.

---

## 11) Checklist Pengujian

1. Ubah **LSF target** (mis. 96.0→95.0). **Auto-resolve** harus memberi proporsi baru on-spec.  
2. Set **Dust→Kiln=100%**. Pastikan mutu clinker tetap dihitung benar (melalui _unignited_).  
3. Ubah **STEC** & komposisi fuel → cek **TotalFuelTPH**, **TotalAshTPH** berubah dan mempengaruhi kendala.  
4. Matikan **auto**, klik **Calculate** manual → hasil sama.  
5. Uji **Mode Cost Minimization**: biaya total turun vs mode feasibility.

---

## 12) Roadmap Pengembangan

- **Tambah bahan baku/fuel dinamis** (tambah/hapus baris di `data_editor`).  
- **Preset mutu** (OPC, PPC, Low-Alkali) → 1 klik switch target.  
- **LP/Coating Index** constraint opsional.  
- **Ekspor**: PDF/Excel ringkas hasil & input.  
- **Histori model**: simpan scenario & hasil di SQLite.

---

## 13) Lampiran – Contoh Panggilan `solve_rawmix`

```python
RM = { "LS":{"SiO2":1.07,"Al2O3":1.24,"Fe2O3":0.55,"CaO":53.28,"K2O":0.04,"Na2O":0.03,"LOI":43.00},
       "CY":{"SiO2":67.00,"Al2O3":15.27,"Fe2O3":9.09,"CaO":1.28,"K2O":1.18,"Na2O":0.58,"LOI":13.87},
       "SS":{"SiO2":84.11,"Al2O3":6.40,"Fe2O3":4.21,"CaO":0.56,"K2O":0.22,"Na2O":0.01,"LOI":2.45},
       "CS":{"SiO2":35.40,"Al2O3":4.28,"Fe2O3":52.06,"CaO":5.77,"K2O":0.03,"Na2O":0.01,"LOI":0.00} }
dust = {"H2O":0.0,"LOI":10.06,"SiO2":3.76,"Al2O3":2.23,"Fe2O3":45.90,"CaO":40.00,"MgO":0.54,"K2O":0.12,"Na2O":0.39,"SO3":0.02,"Cl":0.02}
ASH  = {"SiO2":24.7,"Al2O3":2.9,"Fe2O3":33.1,"CaO":0.68,"K2O":0.26,"Na2O":0.29,"LOI":0.0}
costs= {"LS":48632,"CY":79130,"SS":106507,"CS":353510}
bounds={"LS":(0,100),"CY":(0,100),"SS":(0,100),"CS":(0,100)}

# Contoh konstanta operasi
pSilo, pKiln = 0.10, 0.00
tonKF, clinkerTPH, dust_ratio, totalAshTPH = 533.0, 342.0, 0.03, 16.6

# Target mutu
LSF_min, LSF_max = 95.5, 96.5
SM_min, SM_max   = 2.28, 2.32
AM_min, AM_max   = 1.55, 1.60
NaEq_max         = 0.60
C3S_min, C3S_max = 58.0, 65.0
FCaO_cl = 1.0

from core.model import solve_rawmix
status, sol, meta = solve_rawmix(
    RM=RM, DUST=dust, ASH=ASH, costs=costs, bounds=bounds,
    pSilo=pSilo, pKiln=pKiln, tonKF=tonKF, clinkerTPH=clinkerTPH,
    dust_ratio=dust_ratio, totalAshTPH=totalAshTPH,
    LSF_min=LSF_min, LSF_max=LSF_max, SM_min=SM_min, SM_max=SM_max,
    AM_min=AM_min, AM_max=AM_max, NaEq_max=NaEq_max,
    C3S_min=C3S_min, C3S_max=C3S_max, FCaO_cl=FCaO_cl, epsilon=1e-3
)
```

---

## 14) Glossary Singkat

- **Raw Meal**: campuran bahan baku sebelum kiln.  
- **Kiln Feed**: raw meal setelah opsi dust mixing (to silo / to kiln).  
- **Unignited**: komposisi sebelum normalisasi LOI, setelah (KF + Ash − DustLoss).  
- **Clinker**: hasil normalisasi bebas LOI.  
- **LSF/SM/AM**: modulus mutu klasik klinker.  
- **NaEq**: `Na2O + 0.658*K2O`.  
- **Bogue**: estimasi fasa klinker (C3S, C2S, C3A, C4AF).  
- **STEC**: konsumsi panas spesifik (kcal/kg klinker).
