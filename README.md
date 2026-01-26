# pre-miRNA Annotation Browser

An interactive Streamlit web application to explore, filter, and export the pre-miRNA annotations generated in **miR-RF**, as described in *[Manuscript title]*.
This app provides an intuitive interface to inspect human pre-miRNAs evaluated through an integrative framework combining **structural stability**, **evolutionary conservation**, and **tissue expression**, and supports flexible, user-defined filtering strategies tailored to different biological questions.

🔗 **Live app:**
[https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/](https://app-mir-rf-vfd7s8nncj3mx6anbaaxrh.streamlit.app/)

---

## Overview

Accurate interpretation of pre-miRNA annotations often depends on the specific research context. Rather than enforcing a single definition of bona fide microRNAs, this application enables users to interactively explore the full set of annotations and apply custom filters based on complementary sources of evidence.

The browser integrates:
* miR-RF structural stability classes (R/D/I/S),
* multi-species conservation profiles,
* tissue-specific expression data,
* miRNA family context (miRBase / MirGeneDB),
* repeat annotation and human specificity.

All results correspond to the analyses reported in the accompanying manuscript and are provided as a reusable resource for downstream studies.

---

## Key features

### Interactive filtering

Filters are available through a sidebar and can be combined arbitrarily:

* **Global search** across all columns
* **Pass/fail filters** for:
  * Structural stability
  * Evolutionary conservation
  * Expression (RPMM ≥ 1.5)
* **Family context**
  * Single miRNAs vs miRNAs in a family (miRBase and/or MirGeneDB)
* **Human specificity**
  * hsa-specific vs non–hsa-specific
* **Repeat class**
  * LINE, SINE, LTR, DNA, Simple repeats, No repeat, etc.

---

### Advanced options

Advanced filters can be enabled to refine queries further:

#### Evolutionary conservation

* Show species-specific columns
* Filter by:
  * “Found in” selected species
  * “Not found in” selected species
* Optional stratification by structural stability (stable R/D vs unstable I/S)

#### Tissue expression

* Show tissue-specific expression columns
* Filter by:
  * Expressed in selected tissues (RPMM ≥ 1.5)
  * Not expressed in selected tissues
* Tissues are organized by **anatomical systems**, with visual icons for navigation

#### Database and class
* Show miRBase / MirGeneDB class annotations
* Filter miRNAs:
  * present in both databases
  * annotated only in miRBase
* Filter by structural stability class (R, D, I, S)

---

## Table visualization

Results are displayed in a responsive, scrollable table with:
* Sticky header and first column
* Color-coded cells with an integrated legend for:
  * pass/fail status (structure, conservation, expression)
  * family membership
  * human specificity
  * repeat presence
  * species-level stability
  * tissue expression threshold
  * miRBase / MirGeneDB structural classes

---

## Data export

The currently filtered dataset can be exported as:
* **TSV table**
  (all visible columns, clean formatting)
* **FASTA file**
  containing the pre-miRNA sequences of the selected entries

These exports allow downstream analyses and custom pipelines.

---

## Summary plots

The app dynamically generates a **repeat class distribution bar plot** (Altair) based on the currently filtered subset, enabling rapid assessment of repeat-associated patterns.

---

## Repository contents

* `app.py` – Streamlit application code
* `sfile2_NEW_plusFam.csv` – curated dataset used by the app
* `*.png` – anatomical system icons used in the interface
* `README.md` – this documentation

---

## Citation

If you use this resource, please cite the accompanying manuscript:

> *Author list*. **Title**. *Journal*, year.
> (aggiungere link mi)

---

## Notes

* The application is designed as a **companion resource** to the manuscript and reflects the same thresholds and classification criteria.
* Users are encouraged to apply their own filtering strategies depending on their specific biological or clinical research question.

---
