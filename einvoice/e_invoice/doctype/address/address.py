import frappe
from frappe import _

def get_paraguay_departments():
    """
    Get dictionary of Paraguay departments with their codes.
    Returns: {code: name}
    """
    return {
        1: "CAPITAL",
        2: "CONCEPCION",
        3: "SAN PEDRO",
        4: "CORDILLERA",
        5: "GUAIRA",
        6: "CAAGUAZU",
        7: "CAAZAPA",
        8: "ITAPUA",
        9: "MISIONES",
        10: "PARAGUARI",
        11: "ALTO PARANA",
        12: "CENTRAL",
        13: "NEEMBUCU",
        14: "AMAMBAY",
        15: "PTE. HAYES",
        16: "BOQUERON",
        17: "ALTO PARAGUAY",
        18: "CANINDEYU"
    }
