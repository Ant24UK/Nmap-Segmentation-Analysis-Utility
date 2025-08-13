# Segmentation Matrix Tool

This tool analyses multiple Nmap `.gnmap` files (from different network segments) and produces:

- A colour-coded communication matrix in your terminal
- An HTML report (`segmentation_matrix.html`) with a coloured table, segment classification, and areas of concern

## How to Use

1. **Prepare your `.gnmap` files**  
   Place all `.gnmap` files in the same directory as the script.  
   Name each file using the format:  
   - `PCI - SEGMENTNAME.gnmap` for PCI segments  
   - `NON PCI - SEGMENTNAME.gnmap` for non-PCI segments  
   For example:  
   - `PCI - pro_pci.gnmap`  
   - `NON PCI - pro_non_pci.gnmap`

2. **Run the script**  
   ```bash
   python3 scriptname.py
