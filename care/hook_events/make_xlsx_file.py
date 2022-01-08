import frappe
import re
from io import BytesIO
import openpyxl
import xlrd
from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from care.utils.xlsxutils import handle_html

ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')

columns_heading = ["Item Code", "Item Name", "Required By", "Description", "Item Group", "Brand",
               "Quantity", "Stock UOM", "Target Warehouse", "UOM", "UOM Conversion Factor",
               "Stock Qty", "Actual Qty", "Completed Qty", "Received Qty", "Rate", "Amount",
               "Project", "Cost Center", "Expense Account"]

def make_xlsx(purchase_request, wb=None, column_widths=None):
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook(write_only=True)

    m_demand = frappe.db.sql("""select name, supplier, warehouse 
                    from `tabMaterial Demand` 
                    where purchase_request ='{0}'""".format(purchase_request),as_dict=True)
    number = 0
    for res in m_demand:
        sheet_name = str(res.warehouse) + "-" + str(res.supplier)
        ws = wb.create_sheet(sheet_name, number)

        for i, column_width in enumerate(column_widths):
            if column_width:
                ws.column_dimensions[get_column_letter(i + 1)].width = column_width

        row1 = ws.row_dimensions[1]
        row1.font = Font(name='Calibri', bold=True)

        data = frappe.db.sql("""select item_code, item_name, schedule_date, description, item_group,brand, 
                qty, stock_uom, warehouse, uom, conversion_factor, 
                stock_qty, actual_qty, ordered_qty, received_qty, rate, amount,
                project, cost_center, expense_account
                from `tabMaterial Demand Item` 
                where parent = '{0}'""".format(res.name), as_list=True)

        ws.append(columns_heading)
        for row in data:
            clean_row = []
            for item in row:
                pass
                if isinstance(item, str) and (sheet_name not in ['Data Import Template', 'Data Export']):
                    value = handle_html(item)
                else:
                    value = item

                if isinstance(item, str) and next(ILLEGAL_CHARACTERS_RE.finditer(value), None):
                    # Remove illegal characters from the string
                    value = re.sub(ILLEGAL_CHARACTERS_RE, '', value)

                clean_row.append(value)

            ws.append(clean_row)
        number += 1

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file


def build_xlsx_response(purchase_request):
    xlsx_file = make_xlsx(purchase_request)
    # # write out response as a xlsx type
    frappe.response['filename'] = purchase_request + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'
