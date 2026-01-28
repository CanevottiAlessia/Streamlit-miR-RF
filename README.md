# pre-miRNA Annotation Browser

An interactive Streamlit web application to explore, filter, and export the pre-miRNA annotations generated in **miR-RF**, as described in *[article title]*.
The app enables interactive inspection of human pre-miRNAs evaluated through an integrative framework combining **structural stability**, **evolutionary conservation**, and **tissue expression**, and supports flexible, user-defined filtering strategies tailored to different biological questions.

🔗 **Live app:**
[https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/](https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/)

---

## Overview

Accurate interpretation of pre-miRNA annotations often depends on the research context. Rather than enforcing a single definition of “valid” pre-miRNAs, this application enables users to explore the full annotation space and apply custom filters based on complementary evidence.

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

* **Global search** across all columns (“Search any column”)
* **Pass/fail selectors** (with *Show all* option) for:

  * Evolutionary conservation (PASSED / NOT PASSED)
  * Expression (PASSED / NOT PASSED)
  * Structural stability (PASSED / NOT PASSED)
* **Human specificity selector** (with *Show all* option)

  * Only hsa-specific / Not hsa-specific
* **Family context**

  * Single miRNAs vs miRNAs in a family (miRBase and/or MirGeneDB)
* **Repeat class selection**

  * LINE, SINE, LTR, DNA, Simple repeats, No repeat, etc.

---

### Advanced options

Advanced filters and column display can be enabled through the **Advanced options** toggle.

#### Evolutionary conservation

* Show species-specific columns (optional)
* Filter by:

  * **Found in:** selected species
  * **Not found in:** selected species
* Optional stratification by structural stability when “Found in” is active:

  * Stable (R/D) vs Unstable (S/I)

#### Tissue expression

* Show tissue columns **by anatomical system** (rather than individual tissue lists)
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

For exploratory analyses, the app includes a **Reset all filters** button at the bottom of the sidebar.

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

> *Authors*. *Title*. *Journal*, year. (to be updated)

---

## Notes

* The application is intended as a **companion resource** to the manuscript and reflects the same thresholds and classification criteria.
* Users are encouraged to apply filtering strategies appropriate to their research goals (e.g., prioritizing structural robustness for functional studies vs. relaxing constraints for exploratory expression surveys).

---

## Example use cases

### Use case 1 - Cardiovascular-associated miRNAs conserved in mouse
A researcher interested in cardiovascular biology in mouse may wish to identify human pre-miRNAs that are evolutionarily conserved in Mus musculus, structurally robust, and expressed in cardiovascular-related tissues, either to support existing knowledge or to generate hypotheses for downstream analyses.

**Using the pre-miRNA Annotation Browser as a support tool** → The application can be used to narrow the search space by combining simple filters:

**Conservation support**
- Set Conservation to PASSED.
- In Advanced options → Evolutionary conservation, select Mus musculus under "Found in". This restricts the table to pre-miRNAs with detectable conservation in mouse.

**Tissue expression context**
- Set Expression to PASSED.
- In Advanced options → Tissue expression, select tissues belonging to the Cardiorespiratory system (e.g. artery, heart, ventricle, vein, circulating compartments). This highlights loci expressed in cardiovascular-relevant contexts.

**Structural robustness**
- Set Structure to PASSED to focus on pre-miRNAs with stable predicted hairpins.

Under these conditions, 99 precursors appear among the filtered entries. The app shows that this locus:
- is conserved in mouse;
- displays high expression in multiple cardiovascular tissues;
- is classified as structurally stable (R/D).

Alternatively, individual miRNAs of interest (e.g. hsa-mir-145) can be queried directly using the global search bar to inspect their conservation, expression, and structural profiles in the context of the full annotation dataset. For example, miR-145 has been implicated in vascular smooth muscle cell biology and pulmonary arterial hypertension in mouse models, where its dysregulation influences vascular remodeling and disease progression in vivo (Caruso et al., *Circulation Research*, 2012, https://doi.org/10.1161/CIRCRESAHA.112.267591).

---

### Use case 2 - Brain-associated miRNAs conserved in primates

A researcher interested in brain-related processes in primates may wish to identify human pre-miRNAs that are conserved in closely related species, such as *Pan troglodytes* and *Pan paniscus*, and that show evidence of expression in neural tissues.

**Using the pre-miRNA Annotation Browser as a support tool** → The application can be used to narrow the search space by combining simple filters:

**Conservation support**
- Set *Conservation* to **PASSED**.
- In *Advanced options → Evolutionary conservation*, select *Pan troglodytes* and *Pan paniscus* under **Found in**.  
  This restricts the table to pre-miRNAs conserved across closely related primate species.

**Tissue expression context**
- Set *Expression* to **PASSED**.
- In *Advanced options → Tissue expression*, select tissues belonging to the **Neuro-Endocrine system** (e.g. brain, cortex, cerebellum, hippocampus, neuron-related samples).  
  This highlights loci with detectable expression in neural contexts.

**Structural robustness**
- Set *Structure* to **PASSED** to focus on pre-miRNAs with stable predicted hairpin structures.

Under these conditions, the filtered results provide a focused subset of pre-miRNAs that are conserved across primates, expressed in brain-related tissues, and supported by structurally robust hairpins. This subset can be used to inspect known brain-associated miRNAs or to identify additional candidates sharing similar annotation profiles.

As in the mouse use case, individual loci of interest can also be queried directly using the global search bar to rapidly inspect conservation patterns, tissue expression profiles, and structural classification for specific miRNAs.
