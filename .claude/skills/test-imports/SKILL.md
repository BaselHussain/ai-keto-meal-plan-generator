---
description: Test Python module imports to verify correct installation and structure
handoffs:
  - label: Fix Import Errors
    agent: backend-engineer
    prompt: Fix the import errors identified in the test report
    send: false
---

## User Input

```text
$ARGUMENTS
```

Module path to test (e.g., `src.lib.email_utils`, `src.schemas`, `src.models`). If empty, tests all core modules.

## Task

Test Python module imports to ensure all modules are correctly structured and importable.

### Steps

1. **Navigate to Backend Directory**:
   ```bash
   cd backend
   ```

2. **Determine Modules to Test**:
   - If `$ARGUMENTS` is provided: Test the specified module
   - If `$ARGUMENTS` is empty: Test all core modules

3. **Test Imports Using Python Script**:

   Create a temporary test script and execute it:

   ```bash
   python -c "
import sys
sys.path.insert(0, '.')

# Test imports based on arguments
modules_to_test = []

# If specific module provided, test only that
import os
if '$ARGUMENTS':
    modules_to_test = ['$ARGUMENTS']
else:
    # Test all core modules
    modules_to_test = [
        'src.lib.email_utils',
        'src.lib.preferences',
        'src.lib.database',
        'src.lib.redis_client',
        'src.services.calorie_calculator',
        'src.models',
        'src.schemas',
        'src.schemas.quiz',
        'src.schemas.meal_plan',
        'src.schemas.auth',
        'src.schemas.recovery',
        'src.schemas.common'
    ]

print('Testing Python module imports...')
print('=' * 60)

failed_imports = []
successful_imports = []

for module_name in modules_to_test:
    try:
        module = __import__(module_name, fromlist=[''])

        # For package modules, list exported items
        if hasattr(module, '__all__'):
            exports = module.__all__
            print('[OK] {} ({} exports)'.format(module_name, len(exports)))
        elif hasattr(module, '__dict__'):
            # Count public items (non-underscore)
            public_items = [k for k in module.__dict__.keys() if not k.startswith('_')]
            print('[OK] {} ({} public items)'.format(module_name, len(public_items)))
        else:
            print('[OK] {}'.format(module_name))

        successful_imports.append(module_name)
    except Exception as e:
        print('[FAIL] {}: {}'.format(module_name, str(e)))
        failed_imports.append((module_name, str(e)))

print('=' * 60)
print('Results: {} passed, {} failed'.format(len(successful_imports), len(failed_imports)))

if failed_imports:
    print()
    print('Failed Imports:')
    for module, error in failed_imports:
        print('  - {}: {}'.format(module, error))
    sys.exit(1)
else:
    print()
    print('All imports successful!')
    sys.exit(0)
"
   ```

4. **Report Results**:
   - If all imports successful: Report success with count of tested modules
   - If any imports failed: Report failures with specific error messages and exit with code 1

### Examples

**Test all core modules**:
```bash
/test-imports
```

**Test specific module**:
```bash
/test-imports src.schemas
```

**Test specific submodule**:
```bash
/test-imports src.schemas.meal_plan
```

### Success Criteria

- All specified modules import without errors
- No missing dependencies
- No circular import issues
- All exports are accessible

### Error Handling

If imports fail:
1. Check for missing dependencies in requirements.txt or pyproject.toml
2. Verify file structure matches module paths
3. Check for circular imports
4. Ensure `__init__.py` files exist in all package directories
5. Verify Python path is correctly configured

This skill should be run:
- After creating new modules or schemas
- After refactoring imports
- Before committing code changes
- As part of CI/CD validation
