"""
Unit tests for E-Invoice validators.
Tests company, customer, items, and payment validators.
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase

from ..validators.company_validator import (
    validate_company_sifen_fields,
    _validate_economic_activities,
    _validate_responsable_sifen
)
from ..validators.customer_validator import (
    validate_customer_sifen_fields,
    _validate_tipo_documento,
    _validate_tipo_impuesto
)


class TestCompanyValidator(FrappeTestCase):
    """Tests for company validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock company object
        class MockCompany:
            def __init__(self):
                self.name = "Test Company"
                self.tax_id = "3604076-1"
                self.codigo_establecimiento = "001"
                self.numero_timbrado = "123456789"
                self.fecha_timbrado = "2024-01-01"
                self.tipo_contribuyente = "2"
                self.tipo_regimen = "8"
                # Mock child table for actividades_economicas
                class MockActividad:
                    def __init__(self, codigo, descripcion):
                        self.codigo_actividad = codigo
                        self.descripcion_actividad = descripcion
                self.actividades_economicas = [MockActividad("01110", "Test Activity")]
                self.sifen_responsable_tipo_documento = "1|RUC"
                self.sifen_respons_numero_documento = "3604076-1"
                self.sifen_responsable_nombre = "Test User"
                self.sifen_responsable_cargo = "Manager"
        
        self.company = MockCompany()
        self.invoice = frappe.new_doc("Sales Invoice")
        self.invoice.company = self.company.name
        self.invoice.customer = "Test Customer"
    
    def test_validate_company_with_all_fields(self):
        """Test company validation with all required fields."""
        errors = validate_company_sifen_fields(self.invoice, self.company)
        
        # Should have no errors for required fields
        self.assertEqual(len(errors), 0)
    
    def test_validate_company_missing_ruc(self):
        """Test company validation without RUC."""
        self.company.tax_id = None
        
        errors = validate_company_sifen_fields(self.invoice, self.company)
        
        self.assertTrue(any("Tax ID" in err for err in errors))
    
    def test_validate_company_establishment_code_too_long(self):
        """Test company validation with establishment code > 3 digits."""
        self.company.codigo_establecimiento = "0001"  # 4 digits
        
        errors = validate_company_sifen_fields(self.invoice, self.company)
        
        self.assertTrue(any("exceed 3 digits" in err for err in errors))


class TestCustomerValidator(FrappeTestCase):
    """Tests for customer validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.customer_data = {
            "customer_type": "Company",
            "customer_group": "Company",
            "tax_id": "3604076-1",
            "sifen_contribuyente": 1,
            "sifen_tipo_documento": "1|RUC",
            "sifen_tipo_impuesto": "1|IVA (cliente local contribuyente)"
        }
        self.invoice = frappe.new_doc("Sales Invoice")
        self.invoice.customer = "Test Customer"
    
    def test_validate_customer_b2b_valid(self):
        """Test B2B customer validation with valid data."""
        errors = validate_customer_sifen_fields(
            self.invoice, self.customer_data, "Paraguay", 1
        )
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_customer_b2b_missing_documento(self):
        """Test B2B customer validation without document type."""
        self.customer_data["sifen_tipo_documento"] = ""
        
        errors = validate_customer_sifen_fields(
            self.invoice, self.customer_data, "Paraguay", 1
        )
        
        self.assertTrue(any("Document Type is empty" in err for err in errors))
    
    def test_validate_tipo_documento_b2b_wrong_type(self):
        """Test B2B customer with wrong document type."""
        errors = []
        _validate_tipo_documento(errors, self.invoice, "2|CI", 1)  # B2B expects RUC
        
        self.assertTrue(any("must have SIFEN Document Type = 'RUC'" in err for err in errors))
    
    def test_validate_tipo_documento_b2c_valid(self):
        """Test B2C customer with valid document types."""
        errors = []
        _validate_tipo_documento(errors, self.invoice, "1|RUC", 2)  # B2C accepts RUC
        self.assertEqual(len(errors), 0)
        
        errors = []
        _validate_tipo_documento(errors, self.invoice, "2|CI", 2)  # B2C accepts CI
        self.assertEqual(len(errors), 0)
    
    def test_validate_tipo_impuesto_paraguay_valid(self):
        """Test Paraguay customer with valid tax types."""
        errors = []
        _validate_tipo_impuesto(errors, self.invoice, "1|IVA", 1)  # B2B
        self.assertEqual(len(errors), 0)
        
        errors = []
        _validate_tipo_impuesto(errors, self.invoice, "2|ISC", 1)  # B2B
        self.assertEqual(len(errors), 0)
    
    def test_validate_tipo_impuesto_paraguay_invalid(self):
        """Test Paraguay customer with invalid tax types."""
        errors = []
        _validate_tipo_impuesto(errors, self.invoice, "3|Renta", 1)  # Not valid for Paraguay
        
        self.assertTrue(any("not coherent" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
