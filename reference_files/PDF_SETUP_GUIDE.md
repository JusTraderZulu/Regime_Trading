# PDF Report Generation Guide

## 🎯 Overview

Your system now supports **PDF report generation** in addition to markdown reports! Perfect for:
- 📊 **Presentations** (Quantinsti submission)
- 📧 **Sharing** with mentors/stakeholders
- 🖨️ **Printing** professional reports
- 📁 **Archiving** formatted documents

---

## ⚡ Quick Start

### Option 1: Best Quality (Recommended) - Using Pandoc

```bash
# 1. Install pandoc (system-level)
brew install pandoc                    # macOS
# sudo apt-get install pandoc          # Ubuntu/Debian
# choco install pandoc                 # Windows

# 2. Run analysis with PDF flag
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
```

### Option 2: Python-Only (No system dependencies)

```bash
# 1. Install PDF dependencies
pip install -e .[pdf]

# 2. Run analysis with PDF flag
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
```

---

## 📦 Installation Options

### Method 1: Pandoc (Best Quality) ⭐ RECOMMENDED

**Pros:**
- ✅ Best formatting and quality
- ✅ Handles complex markdown
- ✅ Better font support
- ✅ Industry standard

**Installation:**

```bash
# macOS (Homebrew)
brew install pandoc

# macOS also needs BasicTeX for PDF generation
brew install basictex
# Then add to PATH: export PATH="/Library/TeX/texbin:$PATH"

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install pandoc texlive-xetex

# Windows (Chocolatey)
choco install pandoc
choco install miktex

# Or download from: https://pandoc.org/installing.html
```

**Usage:**
```bash
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
```

### Method 2: WeasyPrint (Python-Only)

**Pros:**
- ✅ No system dependencies
- ✅ Pure Python
- ✅ Good quality

**Cons:**
- ⚠️ Requires some system libraries on Linux

**Installation:**

```bash
# Install Python packages
pip install -e .[pdf]

# Linux may need additional libs:
# sudo apt-get install python3-dev libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

**Usage:**
```bash
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
```

### Method 3: Manual Conversion (Fallback)

If automated PDF generation doesn't work:

```bash
# 1. Generate markdown report (always works)
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough

# 2. Manually convert to PDF using online tools:
# - Markdown to PDF: https://www.markdowntopdf.com/
# - Dillinger: https://dillinger.io/ (export as PDF)
# - VSCode: Use "Markdown PDF" extension
```

---

## 🚀 Usage Examples

### Basic Usage

```bash
# Generate both markdown and PDF
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
```

**Output:**
```
artifacts/X:BTCUSD/2025-10-09/
├── report.md          ← Markdown (for LLM analysis)
├── report.pdf         ← PDF (for presentation)
├── backtest_st.json   ← Data
├── features_st.json
└── ...
```

### Multiple Formats Workflow

```bash
# 1. Run thorough analysis with PDF
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf

# 2. Use markdown for LLM analysis
cat artifacts/X:BTCUSD/2025-10-09/report.md | pbcopy  # macOS
# Paste into ChatGPT/Claude for analysis

# 3. Use PDF for presentation
open artifacts/X:BTCUSD/2025-10-09/report.pdf  # macOS
# Email to mentor or include in slides
```

### Makefile Shortcuts

Add to your `Makefile`:

```makefile
# Run with PDF generation
run-pdf:
	$(BIN)/python -m src.ui.cli run --symbol $(SYMBOL) --mode thorough --pdf

# Example: make run-pdf SYMBOL=X:BTCUSD
```

---

## 📊 What You Get

### Markdown Report (Always Generated)
```
✅ Perfect for LLM analysis
✅ Copy-paste friendly
✅ Version control friendly
✅ Quick viewing in any editor
```

### PDF Report (When --pdf flag used)
```
✅ Professional formatting
✅ Print-ready
✅ Shareable
✅ Archival quality
```

---

## 🔧 Troubleshooting

### Issue: "pandoc not found"

**Solution:**
```bash
# Install pandoc
brew install pandoc  # macOS

# Verify installation
which pandoc
pandoc --version
```

### Issue: "pdflatex not found" (when using pandoc)

**Solution:**
```bash
# macOS
brew install basictex
export PATH="/Library/TeX/texbin:$PATH"

# Ubuntu
sudo apt-get install texlive-xetex

# Verify
which xelatex
```

### Issue: "WeasyPrint failed to generate PDF"

**Solution:**
```bash
# macOS - usually works out of the box
pip install --upgrade weasyprint

# Ubuntu - install system dependencies
sudo apt-get install python3-dev libcairo2 libpango-1.0-0

# Windows - try conda environment
conda install -c conda-forge weasyprint
```

### Issue: "All PDF generation methods failed"

**Fallback Options:**

1. **Use the markdown report** (always works):
   ```bash
   python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
   cat artifacts/X:BTCUSD/2025-10-09/report.md
   ```

2. **Convert manually**:
   - Open `report.md` in VSCode
   - Install "Markdown PDF" extension
   - Right-click → "Markdown PDF: Export (pdf)"

3. **Online converter**:
   - Upload `report.md` to https://www.markdowntopdf.com/
   - Download PDF

---

## 🎨 PDF Styling

The PDF includes professional styling:
- Clean typography
- Proper headers and sections
- Color-coded metrics
- Table formatting
- Code syntax highlighting
- Consistent margins

### Customization (Advanced)

If you want to customize PDF styling, edit `src/reporters/pdf_report.py`:

```python
# Modify the CSS in _try_html_to_pdf()
styled_html = f"""
    <style>
        h1 {{ color: #your-color; }}
        /* Add your custom styles */
    </style>
"""
```

---

## 📋 Comparison: Methods

| Method | Quality | Speed | Setup | Notes |
|--------|---------|-------|-------|-------|
| **Pandoc** | ⭐⭐⭐⭐⭐ | Fast | Medium | Best overall |
| **WeasyPrint** | ⭐⭐⭐⭐ | Fast | Easy | Pure Python |
| **Manual** | ⭐⭐⭐ | Slow | None | Fallback |

---

## 💡 Best Practices

### For Your Quantinsti Presentation:

1. **Generate both formats:**
   ```bash
   python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
   ```

2. **Use PDF for:**
   - Submission document
   - Printed handouts
   - Email to mentor

3. **Use Markdown for:**
   - Your own LLM analysis
   - Quick reference
   - Version control

### For Daily Analysis:

1. **Skip PDF in fast mode** (faster execution):
   ```bash
   python -m src.ui.cli run --symbol X:BTCUSD --mode fast
   ```

2. **Generate PDF only when needed:**
   ```bash
   python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
   ```

---

## 🎓 For Presentations

### Professional Touch:

1. **Generate comprehensive PDF:**
   ```bash
   python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf
   ```

2. **Print or include in slides:**
   - Open PDF in Preview/Adobe
   - Export pages as images for slides
   - Or include as appendix

3. **Show both formats:**
   - "This is the markdown that feeds my LLM assistant"
   - "And here's the same data as a professional PDF report"

---

## ✅ Verification

Test that PDF generation works:

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Install PDF dependencies
pip install -e .[pdf]

# 3. Run test
python -m src.ui.cli run --symbol X:XRPUSD --mode fast --pdf

# 4. Check output
ls -lh artifacts/X:XRPUSD/$(date +%Y-%m-%d)/
# Should see both report.md and report.pdf
```

---

## 🚀 Quick Commands

```bash
# Basic (markdown only)
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough

# With PDF (best quality - requires pandoc)
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough --pdf

# Fast analysis (no backtest, no PDF)
python -m src.ui.cli run --symbol X:BTCUSD --mode fast

# View PDF after generation
open artifacts/X:BTCUSD/2025-10-09/report.pdf  # macOS
xdg-open artifacts/X:BTCUSD/2025-10-09/report.pdf  # Linux
```

---

## 📚 Summary

| Feature | Markdown | PDF |
|---------|----------|-----|
| **LLM Analysis** | ✅ Perfect | ⚠️ Harder |
| **Presentation** | ⚠️ Basic | ✅ Professional |
| **Printing** | ⚠️ Plain | ✅ Formatted |
| **Sharing** | ✅ Easy | ✅ Universal |
| **Speed** | ✅ Instant | ⚠️ +1-2 sec |
| **Setup** | ✅ None | ⚠️ Dependencies |

**Recommendation:** Use **both**! 
- Markdown for your workflow
- PDF for presentations and sharing

---

**Happy reporting! 📊📄**

