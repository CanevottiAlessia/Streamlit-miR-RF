# miR-RF Browser

An interactive Streamlit web application to explore, filter, and export the pre-miRNA annotations generated in **miR-RF**, as described in *"An operational workflow for the systematic annotation of human miRNAs"*.
The app enables interactive inspection of human pre-miRNAs evaluated through an integrative framework combining **structural stability**, **evolutionary conservation**, and **tissue expression**, and supports flexible, user-defined filtering strategies tailored to different biological questions.

🔗 **Live app:**
[https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/](https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/)

---

## Overview

Accurate interpretation of pre-miRNA annotations often depends on the research context. Rather than enforcing a single definition of “valid” pre-miRNAs, this application enables users to explore the full annotation and apply custom filters.

The browser integrates:

* miR-RF structural stability classes (R/D/I/S),
* multi-species conservation profiles and human specificity,
* tissue expression values (RPMM),
* miRNA family context (miRBase / MirGeneDB),
* repeat annotation.

All results correspond to the analyses reported in the accompanying manuscript and are provided as a reusable resource for downstream studies.

---

## Key features

### Interactive filtering (sidebar)

Filters can be combined arbitrarily:

* ### **Global search** across all columns (“Search any column”) --> Search for one or more miRNAs.

* **Pass/fail selectors** (with *Show all* option) for:
  * ### Evolutionary conservation (PASSED / NOT PASSED) --> Retain or exclude human pre-miRNAs based on conservation status across species.
  * ### Expression (PASSED / NOT PASSED) --> Retain or exclude human pre-miRNAs based on evidence of tissue expression.
  * ### Structural stability (PASSED / NOT PASSED) --> Retain or exclude human pre-miRNAs according to their structural stability classification.

* ### **Human specificity selector** (with *Show all* option)  
  * Only hsa-specific / Not hsa-specific --> Restrict results to human-specific miRNAs or exclude them.

* ### **Family context**
  * Single miRNAs vs miRNAs in a family (miRBase and/or MirGeneDB) --> Distinguish isolated miRNAs from those belonging to annotated miRNA families.

* ### **Repeat class selection**
  * LINE, SINE, LTR, DNA, Simple repeats, No repeat, etc. --> Filter miRNAs based on the presence and type of overlapping repeat elements.
* ### **Show repeat class distribution** --> Show barplots (under the table) of repeat class distribution with relative counts. 

---

### Advanced options

Advanced filters and column display can be enabled through the **Advanced options** toggle.

#### Evolutionary conservation

* Show species-specific columns (optional)
* Filter by:
  * **Found in:** selected species.
  * **Not found in:** selected species.
* Optional stratification by structural stability when “Found in” is active:
  * Stable (R/D) vs Unstable (S/I)

#### Tissue expression

* Show tissue columns **by anatomical system**.
* Filter by:
  * **Expressed in:** selected tissues (RPMM ≥ 1.5)
  * **Not expressed in:** selected tissues (RPMM < 1.5)
* Tissues are organized by anatomical systems and visual icons to support navigation.

#### Database / class

* Optional display of miRBase / MirGeneDB class columns
* Filter entries:
  * present in both databases
  * annotated only in miRBase
* Filter by miRBase structural class (R, D, I, S)

---

### Filter reset and state management

- For exploratory analyses, the app includes a **Reset all filters** button at the bottom of the sidebar.
* The button appears **only when at least one filter is active**
* One click clears all filters, restores defaults, collapses advanced options, and reloads the full table.

---

## Table visualization

Results are displayed in a responsive, scrollable table with:

* Sticky header and sticky first column
* Color-coded cells with an integrated legend for:
  * pass/fail status (structure, conservation, expression)
  * family membership
  * hsa-specificity
  * repeat presence
  * species-level stability and “not found” status
  * tissue expression threshold (RPMM ≥ 1.5 vs < 1.5)
  * miRBase / MirGeneDB structural classes (R/D/I/S), when enabled

---

## Data export

The currently filtered dataset can be exported as:
* **TSV table** (only visible columns; clean formatting)
* **FASTA file** for the filtered subset (from the `sequence` column)

These exports are intended to support downstream analyses and custom pipelines.

---

## Summary plots (optional)

A **repeat class distribution** bar plot (Altair) can be displayed **on demand** by enabling
**“Show repeat class distribution”** in the sidebar. The plot is computed on the currently filtered subset.

---

## Repository contents

* `app.py` – Streamlit application code
* `sfile2_NEW_plusFam.csv` – curated dataset used by the app
* `*.png` – anatomical system icons used in the interface
* `README.md` – documentation

---

## Citation

If you use this resource, please cite the accompanying manuscript:

> *Authors*. *Title*. *Journal*, year. (aggiorna)

---

## Notes

* The application is intended as a **companion resource** to the manuscript and reflects the same thresholds and classification criteria.
* Users are encouraged to apply filtering strategies appropriate to their research goals (e.g., prioritizing structural robustness for functional studies vs. relaxing constraints for exploratory expression surveys).

---

### Example use cases

**Using the pre-miRNA Annotation Browser as a support tool**, the application can be used to narrow the search space by combining a set of complementary filters. 

### Use case 1 - Cardiovascular-associated miRNAs conserved in mouse

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

### Use case 2 - Brain-associated miRNAs conserved in primates

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

This subset can be used both to inspect known brain-associated miRNAs and to identify additional candidates sharing similar annotation profiles.
