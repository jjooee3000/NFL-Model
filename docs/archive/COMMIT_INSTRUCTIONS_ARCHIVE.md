# Archiving Instructions for AI Assistants

## When to Archive Old Model Versions

Whenever a new model version is created (e.g., v4, v5), **immediately archive** the previous versions.

## How to Archive

### Step 1: Create archive directory (if it doesn't exist)
```bash
mkdir -p src/models/archive
```

### Step 2: Move old model files
```bash
# Example: When creating v4, move v3 to archive
mv src/models/model_v3.py src/models/archive/
```

### Step 3: Update documentation
Edit `src/models/README.md` to:
- Mark the new version as **ACTIVE**
- Update the version table
- Document key improvements

### Step 4: Update root README.md
Update the "Current active model" reference to point to the new version.

## Why Archive?

1. **Clarity** - Only show production-ready code in main directory
2. **History** - Preserve development evolution for reference
3. **Maintenance** - Avoid confusion about which version to use
4. **Performance** - Reduce cognitive load when navigating codebase

## What Gets Archived?

- **Archive:** Old model versions (model_v0.py, model_v1.py, etc.)
- **Keep:** Current production model, scripts, utilities, data

## Archive Location

`src/models/archive/` - Contains all deprecated model versions with evolution history preserved.

---

**Note for AI Assistants:** When you see multiple model versions (v0, v1, v2, v3...) in the main models directory, proactively suggest archiving old versions following these instructions.
