"""
Unit tests for E-Invoice builders.
Tests param, data, cliente, items, and condicion builders.
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase

from ..builders.cliente_builder import (
    _determine_tipo_operacion
)
from ..builders.condicion_builder import (
    _build_entregas
)


class TestClienteBuilder(FrappeTestCase):
    """Tests for cliente builder."""
    
    def test_determine_tipo_operacion_b2b(self):
        """Test B2B operation type detection."""
        customer_data = {
            "customer_type": "Company",
            "customer_group": "Company"
        }
        
        tipo = _determine_tipo_operacion(customer_data, "Paraguay")
        self.assertEqual(tipo, 1)  # B2B
    
    def test_determine_tipo_operacion_b2c(self):
        """Test B2C operation type detection."""
        customer_data = {
            "customer_type": "Individual",
            "customer_group": "Individual"
        }
        
        tipo = _determine_tipo_operacion(customer_data, "Paraguay")
        self.assertEqual(tipo, 2)  # B2C
    
    def test_determine_tipo_operacion_b2g(self):
        """Test B2G operation type detection."""
        customer_data = {
            "customer_type": "Company",
            "customer_group": "Gubernamental"
        }
        
        tipo = _determine_tipo_operacion(customer_data, "Paraguay")
        self.assertEqual(tipo, 3)  # B2G
    
    def test_determine_tipo_operacion_b2f(self):
        """Test B2F operation type detection."""
        customer_data = {
            "customer_type": "Individual",
            "customer_group": "Individual"
        }
        
        tipo = _determine_tipo_operacion(customer_data, "Argentina")
        self.assertEqual(tipo, 4)  # B2F


class TestCondicionBuilder(FrappeTestCase):
    """Tests for condicion builder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.invoice = frappe.new_doc("Sales Invoice")
        self.invoice.customer = "Test Customer"
        self.invoice.append("items", {
            "item_code": "_Test Item",
            "qty": 1,
            "rate": 1000
        })
        self.invoice.posting_date = "2024-01-01"
        self.invoice.grand_total = 1000
    
    def test_build_entregas_from_payment_schedule(self):
        """Test entregas built from payment schedule."""
        # Add payment schedule
        self.invoice.append("payment_schedule", {
            "due_date": "2024-12-31",
            "payment_amount": 1000,
            "payment_term": "_Test Payment Term"
        })
        
        entregas = _build_entregas(self.invoice, "PYG", 1)
        
        # Should have one entrega
        self.assertEqual(len(entregas), 1)
        self.assertEqual(entregas[0]["monto"], 1000)


if __name__ == "__main__":
    unittest.main()
