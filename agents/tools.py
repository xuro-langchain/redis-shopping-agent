from langchain.tools import tool, ToolRuntime
from agents.utils import db

# ------------------------------------------------------------
# Opensearch E-commerce Agent Tools
# ------------------------------------------------------------

# TODO: Add Opensearch MCP tools

# ------------------------------------------------------------
# Invoice Subagent Tools
# ------------------------------------------------------------
@tool 
def get_invoices_by_customer_sorted_by_date(runtime: ToolRuntime) -> list[dict]:
    """
    Look up all invoices for a customer using their ID, the customer ID is in a state variable, so you will not see it in the message history.
    The invoices are sorted in descending order by invoice date, which helps when the customer wants to view their most recent/oldest invoice, or if 
    they want to view invoices within a specific date range.
    
    Returns:
        list[dict]: A list of invoices for the customer.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    customer_id = runtime.state.get("customer_id", {})
    return db.run(f"SELECT * FROM Invoice WHERE CustomerId = {customer_id} ORDER BY InvoiceDate DESC;")


@tool 
def get_invoices_sorted_by_unit_price(runtime: ToolRuntime) -> list[dict]:
    """
    Use this tool when the customer wants to know the details of one of their invoices based on the unit price/cost of the invoice.
    This tool looks up all invoices for a customer, and sorts the unit price from highest to lowest. In order to find the invoice associated with the customer, 
    we need to know the customer ID. The customer ID is in a state variable, so you will not see it in the message history.

    Returns:
        list[dict]: A list of invoices sorted by unit price.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    query = f"""
        SELECT Invoice.*, InvoiceLine.UnitPrice
        FROM Invoice
        JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId
        WHERE Invoice.CustomerId = {customer_id}
        ORDER BY InvoiceLine.UnitPrice DESC;
    """
    customer_id = runtime.state.get("customer_id", {})
    return db.run(query)


@tool
def get_employee_by_invoice_and_customer(runtime: ToolRuntime, invoice_id: int) -> dict:
    """
    This tool will take in an invoice ID and a customer ID and return the employee information associated with the invoice.
    The customer ID is in a state variable, so you will not see it in the message history.
    Args:
        invoice_id (int): The ID of the specific invoice.

    Returns:
        dict: Information about the employee associated with the invoice.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    customer_id = runtime.state.get("customer_id", {})
    query = f"""
        SELECT Employee.FirstName, Employee.Title, Employee.Email
        FROM Employee
        JOIN Customer ON Customer.SupportRepId = Employee.EmployeeId
        JOIN Invoice ON Invoice.CustomerId = Customer.CustomerId
        WHERE Invoice.InvoiceId = ({invoice_id}) AND Invoice.CustomerId = ({customer_id});
    """
    
    employee_info = db.run(query, include_columns=True)
    
    if not employee_info:
        return f"No employee found for invoice ID {invoice_id} and customer identifier {customer_id}."
    return employee_info

invoice_tools = [get_invoices_by_customer_sorted_by_date, get_invoices_sorted_by_unit_price, get_employee_by_invoice_and_customer]

