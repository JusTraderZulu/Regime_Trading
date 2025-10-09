# GitHub Upload Checklist

## ✅ **Pre-Upload Security Check**

Before pushing to GitHub, verify:

### 1. API Keys Protected
```bash
# Check .gitignore exists
cat .gitignore | grep "polygon_key"

# Should see:
# *.txt
# polygon_key.txt
# open_ai.txt
# hugging_face.txt
```

### 2. No Secrets in Staged Files
```bash
# Initialize git (if not done)
git init
git add .

# Check what will be committed
git status

# ❌ If you see ANY of these, DO NOT COMMIT:
# - polygon_key.txt
# - open_ai.txt
# - hugging_face.txt
# - .env

# ✅ These should be committed:
# - README.md
# - src/
# - config/settings.yaml
# - requirements.txt
```

### 3. Remove Sensitive Data from History
```bash
# If you accidentally committed keys, remove them:
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch polygon_key.txt open_ai.txt hugging_face.txt" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## 🚀 **Upload to GitHub**

### First-Time Upload

```bash
# 1. Initialize repository (if not done)
git init

# 2. Add files
git add .

# 3. Commit
git commit -m "Initial commit: Crypto Regime Analysis System - Phase 1 Complete"

# 4. Link to GitHub repo
git remote add origin https://github.com/JusTraderZulu/Regime_Trading.git

# 5. Push
git branch -M main
git push -u origin main
```

### Subsequent Updates

```bash
# 1. Check status
git status

# 2. Add changes
git add .

# 3. Commit with message
git commit -m "Update: [describe your changes]"

# 4. Push
git push
```

---

## 🔒 **Security Verification**

After pushing, verify on GitHub web interface:

1. Go to: https://github.com/JusTraderZulu/Regime_Trading
2. Check files - should NOT see:
   - ❌ polygon_key.txt
   - ❌ open_ai.txt  
   - ❌ hugging_face.txt
   - ❌ Any .env files
   - ❌ data/ contents
   - ❌ artifacts/ contents
3. Should see:
   - ✅ README.md
   - ✅ src/ directory
   - ✅ requirements.txt
   - ✅ .gitignore

**If you accidentally pushed keys:**
1. Delete them from GitHub immediately
2. Rotate your API keys (get new ones)
3. Force push cleaned history

---

## 📋 **What Gets Committed vs Ignored**

### ✅ Committed to GitHub:
```
✅ Source code (src/)
✅ Documentation (*.md files)
✅ Configuration template (config/settings.yaml)
✅ Dependencies (requirements.txt, pyproject.toml)
✅ Tests (tests/)
✅ .gitignore
✅ Makefile
✅ artifacts/README.md (guide)
✅ data/.gitkeep, artifacts/.gitkeep (directory markers)
```

### ❌ NOT Committed (gitignored):
```
❌ polygon_key.txt (YOUR API KEY)
❌ open_ai.txt (YOUR API KEY)
❌ hugging_face.txt (YOUR TOKEN)
❌ .env (environment variables)
❌ data/*/ (cached market data - can be regenerated)
❌ artifacts/*/ (analysis outputs - user-generated)
❌ __pycache__/ (Python cache)
❌ .venv/ (virtual environment)
```

---

## 👥 **For Others Cloning Your Repo**

When someone clones your repository, they'll need to:

1. **Clone** the repo
```bash
git clone https://github.com/JusTraderZulu/Regime_Trading.git
cd Regime_Trading
```

2. **Setup** virtual environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

3. **Add THEIR OWN API keys**
```bash
echo "their_polygon_key" > polygon_key.txt
echo "their_openai_key" > open_ai.txt
```

4. **Run** their first analysis
```bash
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
```

**They will NOT have your keys - they must get their own!** ✅

---

## ✅ **Final Checklist Before Upload**

- [ ] `.gitignore` file exists
- [ ] API key files NOT in git status
- [ ] README.md updated with setup instructions
- [ ] Security section explains API key requirement
- [ ] Tested `git add .` and verified no secrets
- [ ] Committed with descriptive message
- [ ] Pushed to GitHub
- [ ] Verified on GitHub web - no secrets visible

---

**Safe to upload!** Your codebase and intellectual property are protected, while your API keys remain private. ✅

