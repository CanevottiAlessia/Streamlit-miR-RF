# pre-miRNA Annotation Browser

An interactive **Streamlit** web application to explore the results reported in our manuscript **titolo**.  
The app enables intuitive filtering, inspection, and export of **pre-miRNA annotations** and **sequences** across **evolutionary conservation**, **tissue expression**, **repeat content**, and **family context** (miRBase / MirGeneDB).

> This repository is meant as a resource for the paper: it **presents the curated results** and **supports interactive exploration**.

---

## Features

### Interactive filtering (sidebar)
- **Global search** across all columns (“Search any column”)
- **Pass/fail filters** for:
  - **Conservation** (PASSED / NOT PASSED)
  - **Expression** (PASSED / NOT PASSED)
  - **Structure** (PASSED / NOT PASSED)
- **Family context** filters:
  - Single miRNAs vs miRNAs in a family (miRBase and/or MirGeneDB)
- **Human specificity** filter:
  - hsa-specific vs not hsa-specific
- **Repeat class** selection (e.g., LINE/SINE/LTR/DNA/No repeat, etc.)

### Advanced options
Enable **“Advanced options”** to access:
- **Evolutionary conservation**
  - Show species columns
  - Filter by “Found in” / “Not found in”
  - Optional structural stability stratification (Stable vs Unstable), when “Found in” is on 
- **Tissue expression**
  - Show tissue columns
  - Filter by **Expressed in** / **Not expressed in**
  - Tissue selection organized by **anatomical systems** (with icons)
  - Expression threshold used by the app: **RPMM ≥ 1.5** (expressed) vs **< 1.5** (not expressed)
- **Database / Class**
  - Show Class columns (miRBase / MirGeneDB)
  - Filter entries “in both” vs “only in miRBase”
  - Filter by **miRBase class**

### Table visualization
- Responsive, scrollable table with **sticky header** and **sticky first column**
- Color-coded cells (legend included in the UI) for:
  - Pass/fail (conservation/expression/structure)
  - Family membership
  - hsa-specificity
  - Repeat presence
  - Species-level structural stability / absence
  - Tissue expression threshold
  - miRBase/MirGeneDB classes (R/D/I/S)

### Exports
- **TSV export** of the currently filtered table (“Download table (TSV)”)
- **FASTA export** for the currently filtered set (“Get FASTA”), using the `sequence` column.

### Summary plot
- **Repeat class distribution** bar chart (Altair) computed on the filtered subset.
