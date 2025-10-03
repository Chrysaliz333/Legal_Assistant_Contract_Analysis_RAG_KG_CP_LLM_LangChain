"""
Setup Verification Script

Checks that all prerequisites are in place before running the demo:
- Python dependencies installed
- Database exists with sample data
- API key configured
- All agent modules loadable

Usage:
    python3 verify_setup.py
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """Verify Python version is 3.8+"""
    print("✓ Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"  ❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n✓ Checking Python dependencies...")

    required = [
        'anthropic',
        'langchain',
        'langchain_anthropic',
        'langgraph',
        'textblob',
        'pydantic',
        'pydantic_settings'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (not installed)")
            missing.append(package)

    if missing:
        print(f"\n  To install missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True


def check_api_key():
    """Check if ANTHROPIC_API_KEY is set"""
    print("\n✓ Checking API key...")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY not set")
        print("\n  Please set your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return False

    # Check if it looks valid (starts with 'sk-ant-')
    if not api_key.startswith('sk-ant-'):
        print(f"  ⚠️  API key doesn't start with 'sk-ant-' (got: {api_key[:10]}...)")
        print("  Are you sure this is a valid Anthropic API key?")
        return False

    print(f"  ✅ ANTHROPIC_API_KEY set ({api_key[:10]}...)")
    return True


def check_database():
    """Check if database exists and has data"""
    print("\n✓ Checking database...")

    db_path = Path("legal_assistant.db")
    if not db_path.exists():
        print("  ❌ legal_assistant.db not found")
        print("\n  Create it by running:")
        print("  cd 'Supply Agreement Schema'")
        print("  python3 setup_sqlite.py")
        return False

    print(f"  ✅ Database exists ({db_path.stat().st_size / 1024:.1f} KB)")

    # Try to query it
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM policies")
        policy_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM playbook_rules")
        rule_count = cursor.fetchone()[0]

        conn.close()

        print(f"  ✅ Contains {policy_count} policies and {rule_count} playbook rules")
        return True

    except Exception as e:
        print(f"  ❌ Error reading database: {e}")
        return False


def check_project_structure():
    """Verify key files exist"""
    print("\n✓ Checking project structure...")

    required_files = [
        'src/agents/state.py',
        'src/agents/diligent_reviewer.py',
        'src/agents/neutral_rationale.py',
        'src/agents/personality.py',
        'src/agents/editor.py',
        'src/agents/workflow.py',
        'get_policies.py',
        'demo_workflow.py',
        'config/settings.py'
    ]

    missing = []
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (missing)")
            missing.append(file_path)

    if missing:
        print(f"\n  ⚠️  {len(missing)} files missing!")
        return False

    return True


def check_module_imports():
    """Try to import key modules"""
    print("\n✓ Checking module imports...")

    modules = [
        ('src.agents.state', 'AnalysisContext'),
        ('src.agents.diligent_reviewer', 'DiligentReviewerAgent'),
        ('src.agents.neutral_rationale', 'NeutralRationaleAgent'),
        ('src.agents.personality', 'PersonalityAgent'),
        ('src.agents.editor', 'EditorAgent'),
        ('src.agents.workflow', 'ContractAnalysisWorkflow'),
        ('get_policies', 'get_all_policies'),
        ('config.settings', 'settings')
    ]

    failed = []
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name} - {str(e)[:50]}...")
            failed.append((module_name, class_name))

    if failed:
        print(f"\n  ⚠️  {len(failed)} imports failed!")
        return False

    return True


def main():
    """Run all checks"""
    print("="*70)
    print("SETUP VERIFICATION")
    print("="*70)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("API Key", check_api_key),
        ("Database", check_database),
        ("Project Structure", check_project_structure),
        ("Module Imports", check_module_imports)
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n  ❌ Unexpected error: {e}")
            results[name] = False

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    all_passed = all(results.values())

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status:10s} {name}")

    print("\n" + "="*70)

    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nYou're ready to run the demo:")
        print("  ./run_demo.sh")
        print("\nOr directly:")
        print("  python3 demo_workflow.py")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before running the demo.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
