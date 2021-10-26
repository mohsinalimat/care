from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'material_demand',
        'transactions': [
            {
                'label': _('Purchase Order'),
                'items': ['Purchase Order']
            },
            {
                'label': _('Purchase Receipt'),
                'items': ['Purchase Receipt']
            }
        ]
    }