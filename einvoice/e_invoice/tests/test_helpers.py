"""
Unit tests for E-Invoice helpers.
Tests numero control, currency, and mapping helpers.
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase

from ..helpers.numero_control_helper import (
    generar_numero_control,
    asignar_numero_control
)
from ..helpers.currency_helper import (
    validar_moneda_sifen,
    get_descuento_global,
    VALID_CURRENCIES
)
from ..helpers.mapping_helper import (
    get_sifen_unidad_medida,
    get_sifen_tipo_iva_item
)
from ..utils.utils import get_country_codes


class TestNumeroControlHelper(FrappeTestCase):
    """Tests for numero control helper."""
    
    def test_generar_numero_control_format(self):
        """Test generated control number has correct format."""
        control = generar_numero_control("_Test Company")
        
        # Should be 9 digits
        self.assertEqual(len(control), 9)
        self.assertTrue(control.isdigit())
    
    def test_generar_numero_control_unique(self):
        """Test generated control numbers are unique."""
        control1 = generar_numero_control("_Test Company")
        control2 = generar_numero_control("_Test Company")
        
        # Should be different (very high probability)
        self.assertNotEqual(control1, control2)
    
    def test_generar_numero_control_leading_zeros(self):
        """Test control number has leading zeros if needed."""
        # Generate multiple to ensure we get small numbers
        for _ in range(100):
            control = generar_numero_control("_Test Company")
            self.assertEqual(len(control), 9)


class TestCurrencyHelper(FrappeTestCase):
    """Tests for currency helper."""
    
    def test_validar_moneda_pyg_valid(self):
        """Test PYG is valid currency."""
        # Should not raise
        validar_moneda_sifen("PYG", "TEST-001")
    
    def test_validar_moneda_usd_valid(self):
        """Test USD is valid currency."""
        # Should not raise
        validar_moneda_sifen("USD", "TEST-001")
    
    def test_validar_moneda_invalid(self):
        """Test invalid currency raises error."""
        with self.assertRaises(frappe.ValidationError):
            validar_moneda_sifen("INVALID", "TEST-001")
    
    def test_valid_currencies_list(self):
        """Test VALID_CURRENCIES contains expected currencies."""
        self.assertIn("PYG", VALID_CURRENCIES)
        self.assertIn("USD", VALID_CURRENCIES)
        self.assertIn("EUR", VALID_CURRENCIES)
        self.assertIn("ARS", VALID_CURRENCIES)
        self.assertIn("BRL", VALID_CURRENCIES)
    
    def test_get_descuento_global_pyg_rounding(self):
        """Test discount rounding for PYG."""
        invoice = frappe.new_doc("Sales Invoice")
        invoice.currency = "PYG"
        invoice.append("items", {
            "item_code": "_Test Item",
            "qty": 1,
            "rate": 1000,
            "discount_amount": 123.456
        })
        
        discount = get_descuento_global(invoice, "PYG")
        
        # Should be rounded to integer
        self.assertEqual(discount, round(123.456))
    
    def test_get_descuento_global_foreign_rounding(self):
        """Test discount rounding for foreign currency."""
        invoice = frappe.new_doc("Sales Invoice")
        invoice.currency = "USD"
        invoice.append("items", {
            "item_code": "_Test Item",
            "qty": 1,
            "rate": 100,
            "discount_amount": 12.3456789
        })
        
        discount = get_descuento_global(invoice, "USD")
        
        # Should be rounded to 8 decimals
        self.assertEqual(discount, round(12.3456789, 8))


class TestMappingHelper(FrappeTestCase):
    """Tests for mapping helper."""
    
    def test_get_sifen_unidad_medida_nos(self):
        """Test UOM mapping for Nos."""
        result = get_sifen_unidad_medida("Nos")
        self.assertEqual(result, 77)  # Unidad
    
    def test_get_sifen_unidad_medida_kg(self):
        """Test UOM mapping for Kg."""
        result = get_sifen_unidad_medida("Kg")
        self.assertEqual(result, 83)  # Kilogramos
    
    def test_get_sifen_unidad_medida_litros(self):
        """Test UOM mapping for Litros."""
        result = get_sifen_unidad_medida("Litros")
        self.assertEqual(result, 89)  # Litros
    
    def test_get_sifen_unidad_medida_hora(self):
        """Test UOM mapping for Hora."""
        result = get_sifen_unidad_medida("Hora")
        self.assertEqual(result, 100)  # Hora
    
    def test_get_sifen_unidad_medida_default(self):
        """Test UOM mapping returns default for unknown."""
        result = get_sifen_unidad_medida("Unknown UOM")
        self.assertEqual(result, 77)  # Default: Unidad
    
    def test_get_country_codes_paraguay(self):
        """Test country code for Paraguay."""
        codigo, nombre = get_country_codes("Paraguay")
        self.assertEqual(codigo, "PRY")
        self.assertEqual(nombre, "Paraguay")
    
    def test_get_country_codes_argentina(self):
        """Test country code for Argentina."""
        codigo, nombre = get_country_codes("Argentina")
        self.assertEqual(codigo, "ARG")
        self.assertEqual(nombre, "Argentina")
    
    def test_get_country_codes_brasil(self):
        """Test country code for Brasil."""
        codigo, nombre = get_country_codes("Brasil")
        self.assertEqual(codigo, "BRA")
        self.assertEqual(nombre, "Brasil")
    
    def test_get_country_codes_default(self):
        """Test country code returns default for unknown."""
        codigo, nombre = get_country_codes(None)
        self.assertEqual(codigo, "PRY")
        self.assertEqual(nombre, "Paraguay")


if __name__ == "__main__":
    unittest.main()
