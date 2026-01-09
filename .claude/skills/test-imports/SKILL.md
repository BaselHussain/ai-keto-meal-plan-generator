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

(Arguments are ignored - this skill tests all core modules)

## Task

Test Python module imports to ensure all modules are correctly structured and importable.

### Steps

1. **Navigate to Backend Directory and Run Import Test**:

   ```bash
   cd backend && python -c "
import sys
sys.path.insert(0, '.')

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
        if hasattr(module, '__all__'):
            exports = module.__all__
            print('[OK] {} ({} exports)'.format(module_name, len(exports)))
        elif hasattr(module, '__dict__'):
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

2. **Report Results**:
   - If all imports successful: Exit with code 0
   - If any imports failed: Show error details and exit with code 1

### Success Criteria

- All core modules import without errors
- No missing dependencies
- No circular import issues
- All exports are accessible

### Error Handling

If imports fail:
1. Check error message for missing dependencies (e.g., "No module named 'pydantic'")
2. Install missing dependencies: `pip install <package-name>`
3. Rerun the test-imports skill
4. Verify file structure matches module paths
5. Ensure `__init__.py` files exist in all package directories

This skill should be run:
- After creating new modules or schemas
- After refactoring imports
- Before committing code changes
- To quickly verify all imports are working
