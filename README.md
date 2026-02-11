# miR-RF Browser
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

An interactive Streamlit web application to explore, filter, and export the pre-miRNA annotations generated in **miR-RF**, as described in *"An operational workflow for the systematic annotation of human miRNAs"*.
The application enables interactive inspection of human pre-miRNAs evaluated through an integrative framework combining **structural stability**, **evolutionary conservation**, and **tissue expression**, and supports flexible, user-defined filtering strategies tailored to different biological questions.

🔗 **Live app:**
[https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/](https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/)

---

## 📊 Overview

Table visualization

Results are displayed in a responsive table with:

- Sticky header and sticky first column
- Color-coded cells with an integrated legend for:
  - pass/fail status (structure, conservation, expression)
  - family membership
  - hsa-specificity
  - repeat presence
  - species-level stability and “not found” status
  - tissue expression threshold (RPMM ≥ 1.5 vs < 1.5)
  - miRBase / MirGeneDB structural classes (R/D/I/S), when enabled


The browser integrates:

* miR-RF structural stability classes (R/D/I/S)
* multi-species conservation profiles and human specificity
* tissue expression values (RPMM)
* miRNA family context (miRBase / MirGeneDB)
* repeat annotation.

All results correspond to the analyses reported in the accompanying manuscript and are provided as a reusable resource for downstream studies.

---

## ✨ Key features

### Interactive filtering (sidebar)

Filters can be combined arbitrarily:


### 🔎 Search any column

  Search for one or more miRNAs across all columns of the table
  - Matching is case-insensitive
  - The search performs a partial match: rows are retained if any cell contains the input text
  - Regular expressions (regex) are supported for advanced queries (e.g. ^hsa- to match entries starting with hsa-).


### 🐖 Conservation

  Retain or exclude human pre-miRNAs based on their evolutionary conservation status across the selected species.
  - Show all (default): no conservation filter is applied
  - PASSED: conservation evidence is detected under the defined criteria
  - NOT PASSED: no conservation support is detected under the applied criteria


### 🫁 Expression

  Retain or exclude human pre-miRNAs based on evidence of tissue expression.
  - Show all (default): no expression filter is applied
  - PASSED: expression support is detected according to the defined threshold
  - NOT PASSED: insufficient or no expression evidence is detected


### 🧬 Structural stability

  Retain or exclude human pre-miRNAs according to their structural classification in miRBase / MirGeneDB.
  - Show all (default): no structural filter is applied
  - PASSED: loci classified as R or D (structurally robust)
  - NOT PASSED: loci classified as I or S (unstable or weakly supported)


### 🧍🏼‍♀️ hsa specificity

  Filter pre-miRNAs based on human specificity (hsa).
  - Show all: do not apply any specificity filter
  - Only hsa-specific: show only loci annotated as human-specific
  - Not hsa-specific: exclude human-specific loci and retain non-hsa-specific entries


### 🧩 Family

  Filter between single miRNAs and miRNAs belonging to a family, using annotations from miRBase and/or MirGeneDB.
  - Single miRNAs: loci not assigned to any family in the selected database
  - miRNAs in family: loci annotated as part of a family (family name may be shown when available)


###  🧮 Repeat class

  Filter miRNAs based on the presence and type of overlapping repeat elements.
  - Select one or more repeat classes (e.g. LINE, SINE, LTR, DNA repeats, Low complexity repeats)
  - If multiple classes are selected, the table retains miRNAs matching any of the chosen categories


### 📈 Show repeat class distribution

  Enable “Show repeat class distribution” to visualize the repeat composition of the current filtered subset.
  - The bar plot reports counts and percentages per repeat class
  - Useful to assess whether filtering enriches for specific repeat categories
    
---

## ⚙️ Advanced options

Enable Advanced options in the sidebar to unlock additional controls and column display options.

### 🐂 Evolutionary conservation (advanced)

  - Show species columns: display per-species conservation cells
  - Filter by:
    - **Found in** selected species
    - **Not found in** selected species
  - Optional: stratify by structural stability when **Found in** is active: **Stable (R/D)** vs **Unstable (S/I)**


### 🦴 Tissue expression (advanced)

  - Show tissue columns by anatomical system (with icons)
  - Filter by:
    - **Expressed in**: selected tissues with RPMM ≥ 1.5 (all selected must pass)
    - **Not expressed in**: selected tissues with RPMM < 1.5 (all selected must pass)


### 🗂️ Database / class (advanced)

  - Show Class columns (miRBase / MirGeneDB)
  - Database filter:
    - Entries present in both databases
    - Entries only in miRBase
  - Class filter:
    - Filter by structural class (R, D, I, S)

---

### ♻️ Reset all filters

  - Use Reset all filters to clear selections and restore default settings.
  - The button appears only when at least one filter is active
  - It also resets navigation-dependent state (e.g. pagination)

---

## ⬇️ Data export

The currently filtered dataset can be exported as:
* **TSV table** (only visible columns; clean formatting)
* **FASTA file** for the filtered subset (from the `sequence` column)

These exports are intended to support downstream analyses and custom pipelines.

---

## Repository contents

* `app.py` – Streamlit application code
* `sfile2_NEW_plusFam.csv` – curated dataset used by the app
* `*.png` – anatomical system icons used in the interface
* `README.md` – documentation

---

License
This work is licensed under a Creative Commons Attribution 4.0 International License (CC BY 4.0).

You are free to:

Share — copy and redistribute the material in any medium or format
Adapt — remix, transform, and build upon the material for any purpose, even commercially
Under the following terms:

Attribution — appropriate credit must be given to the original authors and the accompanying manuscript.
For details, see: https://creativecommons.org/licenses/by/4.0/

---

## Citation

If you use this resource, please cite the accompanying manuscript:
> Canevotti et al., *"An operational workflow for the systematic annotation of human miRNAs"*, 
Manuscript under peer review.

---

## Notes

* The application is intended as a **companion resource** to the manuscript and reflects the same thresholds and classification criteria.
* Users are encouraged to apply filtering strategies appropriate to their research goals (e.g., prioritizing structural robustness for functional studies vs. relaxing constraints for exploratory expression surveys).

---

## Example use cases

**Using the pre-miRNA Annotation Browser as a support tool**, the application can be used to narrow the search space by combining a set of complementary filters. 

### 🫀🐁 Use case 1 - Cardiovascular-associated miRNAs conserved in mouse

This use case focuses on human pre-miRNAs conserved in Mus musculus, structurally robust, and expressed in cardiovascular-related tissues or fluids.

**Conservation support**
- In **Advanced options → Evolutionary conservation**, select *M. musculus* under **Found in**.
  This restricts the table to pre-miRNAs with detectable conservation in mouse.
- In **Advanced options → Evolutionary conservation**, select *STABLE (R/D)* under **Structure**.

**Tissue expression context**
- In **Advanced options → Tissue expression**, select tissues belonging to the **Cardiorespiratory system** (e.g. artery, heart, ventricle, vein, circulating compartments), under "Expressed in (select tissues by system):"
  This highlights loci expressed in cardiovascular-relevant contexts.

Under these conditions, 99 miRNAs are retained in the filtered table. For each entry, the app enables inspection of whether the locus:
- is conserved in mouse;
- displays expression across multiple cardiovascular tissues;
- is classified as structurally stable (R or D).

---

### 🧠🦧 Use case 2 - Brain-associated miRNAs conserved in primates

This use case focuses on human pre-miRNAs conserved in *Pan troglodytes* and *Pan paniscus* and showing evidence of expression in neural tissues.

**Conservation support**
- In **Advanced options → Evolutionary conservation**, select *P. troglodytes* and *P. paniscus* under **Found in**.
- In **Advanced options → Evolutionary conservation**, select *STABLE (R/D)* under **Structure**.
- In **Advanced options → Evolutionary conservation**, select *M. mulatta* and *L. catta* under **Not found in**.  

**Tissue expression context**
- In **Advanced options → Tissue expression**, select tissues belonging to the **Neuro-Endocrine system** (e.g. brain, cortex, cerebellum, hippocampus, neuron-related samples), under "Show tissue columns (by system):"
  This option displays the corresponding tissue expression columns but does not filter the results.

Under these conditions, 29 miRNAs are retained in the filtered table. For each entry, the app enables inspection of whether the locus:
- is conserved in *Pan troglodytes* and *Pan paniscus*
- not conserved in *Macaca mulatta* and *Lemur catta*
- is classified as structurally stable (R or D)
- displays expression across multiple neuro-endocrine tissues
