# Setup Guide - First Time Setup

**Follow these steps once. After this, just use `COMMANDS.md`**

---

## ✅ **Prerequisites (Already Done!)**

- [x] Python 3.11+ installed
- [x] Virtual environment created (`.venv/`)
- [x] Dependencies installed
- [x] QC credentials configured

---

## 🔐 **Credentials Setup**

### **Option 1: Use .env File (Recommended)**

Edit your `.env` file and add:

```bash
# QuantConnect
QC_USER_ID=YOUR_QC_USER_ID
QC_API_TOKEN=YOUR_QC_API_TOKEN_HERE
QC_PROJECT_ID=YOUR_QC_PROJECT_ID
```

### **Option 2: Use .txt Files (Current Setup)**

Files already created ✅:
- `qc_token.txt` - Your API token
- `qc_user.txt` - User ID (YOUR_QC_USER_ID)
- `qc_project_id.txt` - Project ID (YOUR_QC_PROJECT_ID)

**Both methods work!** System checks .env first, then .txt files.

---

## 🚀 **QuantConnect One-Time Setup**

### **Upload Strategy Library (Do Once)**

```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python scripts/setup_qc_project.py
```

**What this does**:
- Uploads `strategies_library.py` to QC (all 9 strategies)
- Uploads `main.py` to QC (signal processor)

**Output**:
```
✅ strategies_library.py uploaded successfully
✅ main.py uploaded successfully
```

**Only run this**:
- First time setting up
- When you add new strategies
- If you update strategy code

---

## ✅ **Verify Setup**

```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python scripts/test_qc_integration.py
```

**Expected output**:
```
✓ API Token: abc123def4...
✓ User ID: YOUR_QC_USER_ID
✓ Project ID: YOUR_QC_PROJECT_ID
✓ Signals: ready

✅ All tests passed!
```

---

## 🎯 **You're Ready!**

Now go to → **`COMMANDS.md`** for daily use commands!

Just copy & paste any command and it will work.

---

## 📚 **File Guide**

| File | When to Use |
|------|-------------|
| `COMMANDS.md` | **→ Daily use** - Copy/paste commands |
| `SETUP.md` | This file - First time only |
| `HOW_TO_USE.md` | Detailed reference |
| `COMPLETE_SYSTEM_GUIDE.md` | Architecture & adding features |
| `README.md` | Full documentation |

---

**Setup complete!** System is ready to use. ✅

