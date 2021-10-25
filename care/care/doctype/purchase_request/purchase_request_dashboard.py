from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'purchase_request',
        'transactions': [
            {
                'label': _('Material Demand'),
                'items': ['Material Demand']
            }
        ]
    }