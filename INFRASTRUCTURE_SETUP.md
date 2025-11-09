# Infrastructure Setup Guide
**Date:** 2025-11-09
**Session:** Comprehensive Repository Bug Analysis - Infrastructure Improvements

---

## Overview

This guide documents the CI/CD pipeline and development infrastructure setup for BlastDock.

### What Was Added
✅ **GitHub Actions CI/CD Pipeline**
✅ **Pre-commit Hooks Configuration**
✅ **Automated Release Workflow**
✅ **Code Quality Automation**
✅ **Security Scanning**

---

## 🔄 CI/CD Pipeline (GitHub Actions)

### Test Workflow (`.github/workflows/test.yml`)

**Triggers:**
- Push to `main`, `develop`, or `claude/*` branches
- Pull requests to `main` or `develop`

**Features:**
1. **Multi-Python Version Testing**
   - Tests on Python 3.8, 3.9, 3.10, 3.11
   - Ensures compatibility across versions

2. **Automated Testing**
   - Runs full test suite with pytest
   - Generates coverage reports
   - Uploads to Codecov (on Python 3.11)

3. **Code Quality Checks**
   - Black formatting validation
   - Flake8 linting
   - MyPy type checking

4. **Security Scanning**
   - Safety (dependency vulnerabilities)
   - Bandit (code security issues)

**Usage:**
```bash
# Automatically runs on:
git push origin main
git push origin develop
git push origin claude/feature-branch

# Or when creating a PR to main/develop
```

---

### Release Workflow (`.github/workflows/release.yml`)

**Triggers:**
- Push tags matching `v*.*.*` (e.g., v2.0.1, v3.0.0)
- Manual workflow dispatch

**Features:**
1. **Build Distributions**
   - Creates wheel and source distributions
   - Validates with twine

2. **PyPI Publishing**
   - Automatically publishes to PyPI on version tags
   - Requires `PYPI_API_TOKEN` secret

3. **GitHub Releases**
   - Creates GitHub release with artifacts
   - Auto-generates release notes

**Usage:**
```bash
# Create and push a version tag
git tag v2.0.1
git push origin v2.0.1

# Or trigger manually from GitHub Actions UI
```

---

## 🪝 Pre-commit Hooks

### Setup Instructions

**1. Install pre-commit:**
```bash
pip install pre-commit
```

**2. Install hooks:**
```bash
cd /home/user/blastdock
pre-commit install
```

**3. Test hooks (optional):**
```bash
# Run on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files blastdock/utils/docker_utils.py
```

### Configured Hooks

#### 1. **General File Cleanup**
- Trailing whitespace removal
- End-of-file fixing
- YAML/JSON validation
- Large file detection
- Merge conflict detection
- Private key detection

#### 2. **Python Code Formatting**
- **Black** - Auto-format to 88 character line length
- **isort** - Sort imports automatically

#### 3. **Python Linting**
- **Flake8** - Style guide enforcement
  - Max line length: 127
  - Ignores: E203, W503 (Black compatibility)

#### 4. **Python Type Checking**
- **MyPy** - Static type checking
  - Ignores missing imports
  - Skips tests directory

#### 5. **Security**
- **Bandit** - Security issue detection
  - Low severity threshold
  - Skips test files

#### 6. **Markdown**
- **markdownlint** - Markdown style checking
  - Auto-fixes issues

### Hook Behavior

**On `git commit`:**
1. Hooks run automatically
2. If issues found, commit is blocked
3. Many hooks auto-fix issues
4. Review changes and commit again

**Example:**
```bash
$ git commit -m "fix: update docker utils"
[INFO] Initializing environment for black...
[INFO] Initializing environment for flake8...
black....................................................................Passed
flake8...................................................................Passed
mypy.....................................................................Passed
bandit...................................................................Passed
[main abc1234] fix: update docker utils
 1 file changed, 10 insertions(+), 5 deletions(-)
```

### Skipping Hooks (Emergency Only)

```bash
# Skip all hooks (not recommended)
git commit --no-verify -m "emergency fix"

# Skip specific hook
SKIP=black git commit -m "commit message"
```

---

## 📋 Required GitHub Secrets

For full CI/CD functionality, configure these secrets in GitHub repository settings:

### PyPI Publishing (Optional)
```
PYPI_API_TOKEN
```
**How to get:**
1. Go to https://pypi.org/manage/account/token/
2. Create new API token
3. Scope: Entire account or specific project
4. Add to GitHub: Settings → Secrets → Actions

### Codecov (Optional)
```
CODECOV_TOKEN
```
**How to get:**
1. Go to https://codecov.io/
2. Add your repository
3. Copy the token
4. Add to GitHub secrets

---

## 🧪 Local Testing

### Run Tests Locally
```bash
# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=blastdock --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Quality Checks
```bash
# Format code
black blastdock/ tests/

# Check formatting (without changes)
black --check blastdock/ tests/

# Lint
flake8 blastdock/ --max-line-length=127

# Type check
mypy blastdock/ --ignore-missing-imports
```

### Security Scanning
```bash
# Install tools
pip install safety bandit

# Check dependencies
safety check

# Scan code
bandit -r blastdock/
```

---

## 🔧 Configuration Files

### `.github/workflows/test.yml`
- Multi-version Python testing
- Code quality automation
- Security scanning

### `.github/workflows/release.yml`
- Build automation
- PyPI publishing
- GitHub releases

### `.pre-commit-config.yaml`
- Git hook configuration
- Auto-formatting setup
- Quality gates

---

## 📊 CI/CD Pipeline Status

### Current Status: ✅ **CONFIGURED**

| Component | Status | Notes |
|-----------|--------|-------|
| GitHub Actions Workflows | ✅ Created | Ready to run |
| Pre-commit Hooks | ✅ Created | Needs `pre-commit install` |
| Test Automation | ✅ Ready | Runs on push/PR |
| Code Quality Checks | ✅ Ready | Black, Flake8, MyPy |
| Security Scanning | ✅ Ready | Safety, Bandit |
| Release Automation | ✅ Ready | Requires PyPI token |
| Coverage Reporting | ✅ Ready | Codecov integration |

---

## 🚀 Getting Started

### For Developers

**1. Clone and setup:**
```bash
git clone https://github.com/BlastDock/blastdock.git
cd blastdock
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
```

**2. Install pre-commit:**
```bash
pre-commit install
```

**3. Run tests:**
```bash
pytest tests/ -v
```

**4. Make changes:**
```bash
# Edit files
git add .
git commit -m "feat: add new feature"
# Pre-commit hooks run automatically
git push
```

### For CI/CD

**The pipeline runs automatically when:**
- You push to main, develop, or claude/* branches
- You create a pull request
- You push a version tag (v*.*.*)

**No manual intervention needed!**

---

## 🎯 Benefits

### For Development
✅ Automatic code formatting (Black)
✅ Import organization (isort)
✅ Style enforcement (Flake8)
✅ Type safety (MyPy)
✅ Security checks (Bandit)
✅ Consistent code quality

### For CI/CD
✅ Multi-version testing
✅ Automated quality gates
✅ Coverage reporting
✅ Security scanning
✅ Automated releases
✅ Fail-fast feedback

### For Project
✅ Prevents bugs from merging
✅ Maintains code standards
✅ Catches security issues early
✅ Automates routine tasks
✅ Professional development workflow

---

## 📝 Maintenance

### Updating Pre-commit Hooks
```bash
# Update to latest versions
pre-commit autoupdate

# Review changes in .pre-commit-config.yaml
git diff .pre-commit-config.yaml

# Commit if acceptable
git add .pre-commit-config.yaml
git commit -m "chore: update pre-commit hooks"
```

### Updating GitHub Actions
- Workflows are version-pinned for stability
- Update action versions periodically
- Test in feature branch first

---

## 🐛 Troubleshooting

### Pre-commit hooks failing?

**Black formatting:**
```bash
# Auto-fix
black blastdock/ tests/
git add .
git commit
```

**Flake8 errors:**
```bash
# Review errors
flake8 blastdock/

# Fix manually or add # noqa comments if needed
```

**MyPy errors:**
```bash
# Add type hints or ignore
# type: ignore
```

### GitHub Actions failing?

1. Check the Actions tab in GitHub
2. Review error logs
3. Run tests locally first
4. Ensure all dependencies are in pyproject.toml

---

## 📚 Resources

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Pre-commit Framework:** https://pre-commit.com/
- **Black Formatter:** https://black.readthedocs.io/
- **Flake8 Linter:** https://flake8.pycqa.org/
- **MyPy Type Checker:** https://mypy.readthedocs.io/
- **Bandit Security:** https://bandit.readthedocs.io/

---

**Infrastructure Setup Complete!** ✅

All files have been created and are ready to use. Just need to:
1. Commit these files
2. Push to GitHub
3. Install pre-commit locally: `pre-commit install`
4. Configure GitHub secrets (optional for PyPI/Codecov)

