# E-Invoice Module Tests

Unit tests for the refactored E-Invoice module.

## Running Tests

### Run All Tests

```bash
# From bench directory
bench --site development.localhost run-tests --module einvoice.e_invoice.tests
```

### Run Specific Test File

```bash
# Run validator tests
bench --site development.localhost run-tests --module einvoice.e_invoice.tests.test_validators

# Run helper tests
bench --site development.localhost run-tests --module einvoice.e_invoice.tests.test_helpers

# Run builder tests
bench --site development.localhost run-tests --module einvoice.e_invoice.tests.test_builders
```

### Run Specific Test Class

```bash
# Run company validator tests
bench --site development.localhost run-tests --module einvoice.e_invoice.tests.test_validators --class TestCompanyValidator

# Run currency helper tests
bench --site development.localhost run-tests --module einvoice.e_invoice.tests.test_helpers --class TestCurrencyHelper
```

### Run Specific Test Method

```bash
# Run specific test
bench --site development.localhost run-tests --module einvoice.e_invoice.tests.test_validators --method test_validate_company_with_all_fields
```

## Test Coverage

### Validators (test_validators.py)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestCompanyValidator | 3 | Company field validation |
| TestCustomerValidator | 6 | Customer field validation |

**Total:** 9 tests

### Helpers (test_helpers.py)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestNumeroControlHelper | 3 | Control number generation |
| TestCurrencyHelper | 6 | Currency validation & discount |
| TestMappingHelper | 8 | Code mapping |

**Total:** 17 tests

### Builders (test_builders.py)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestParamBuilder | 2 | PARAM section building |
| TestClienteBuilder | 4 | Cliente section building |
| TestCondicionBuilder | 2 | Condicion section building |

**Total:** 8 tests

### Grand Total: **34 tests**

## Test Fixtures

The tests use the following Frappe test fixtures:

- `_Test Company`: Default test company
- `_Test Customer`: Default test customer
- `_Test Item`: Default test item
- `_Test Payment Term`: Default payment term

## Writing New Tests

### Test Structure

```python
import unittest
import frappe
from frappe.tests.utils import FrappeTestCase

from ..helpers.example_helper import example_function


class TestExampleHelper(FrappeTestCase):
    """Tests for example helper."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {...}
    
    def test_example_function_valid(self):
        """Test example function with valid data."""
        result = example_function(self.test_data)
        self.assertEqual(result, expected_value)
    
    def test_example_function_invalid(self):
        """Test example function with invalid data."""
        with self.assertRaises(frappe.ValidationError):
            example_function(invalid_data)


if __name__ == "__main__":
    unittest.main()
```

### Best Practices

1. **Use FrappeTestCase**: Extends unittest with Frappe-specific features
2. **setUp method**: Create test data once, reuse in all tests
3. **Descriptive names**: `test_function_scenario_expected_result`
4. **Test edge cases**: Valid, invalid, boundary conditions
5. **Keep tests independent**: Each test should run independently
6. **Use assertions**: `assertEqual`, `assertTrue`, `assertRaises`, etc.

## Continuous Integration

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: bench --site development.localhost run-tests --module einvoice.e_invoice.tests
      language: system
      pass_filenames: false
      always_run: true
```

### GitHub Actions

Add to `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install frappe-bench
          bench init --skip-redis-config-generation --frappe-branch version-15 frappe-bench
          cd frappe-bench
          bench get-app einvoice --branch develop
          bench setup requirements --dev
          bench new-site development.localhost
          bench --site development.localhost install-app einvoice
      
      - name: Run tests
        run: |
          cd frappe-bench
          bench --site development.localhost run-tests --module einvoice.e_invoice.tests
```

## Coverage Report

Generate coverage report:

```bash
bench --site development.localhost run-tests --module einvoice.e_invoice.tests --coverage
```

View coverage report:

```bash
# HTML report
open coverage_html_report/index.html

# Console report
coverage report
```

## Troubleshooting

### Test Not Found

```
Error: No tests found in module einvoice.e_invoice.tests
```

**Solution:** Make sure `__init__.py` exists in tests directory and imports test files.

### Fixture Not Found

```
Error: Customer _Test Customer not found
```

**Solution:** Create test fixtures or use existing ones:

```bash
bench --site development.localhost create-test-data
```

### Database Errors

```
Error: Table 'tabSales Invoice' doesn't exist
```

**Solution:** Run migrations:

```bash
bench --site development.localhost migrate
```

---

**Last Updated:** 2026-03-27
**Status:** Phase 5 Complete ✅
**Total Tests:** 34
