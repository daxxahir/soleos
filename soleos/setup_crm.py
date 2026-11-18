import json
import frappe

def setup_bigin_pipeline():
    """
    Sets up Zoho Bigin-style Deal Pipeline stages, Kanban view, and Desk Workspace in Frappe CRM.
    """
    frappe.logger("soleos").info("Setting up Zoho Bigin Pipeline in Soleos App...")

    # 1. Define Zoho Bigin Pipeline Stages
    stages = [
        {"deal_status": "Qualification", "type": "Open", "position": 1, "color": "gray", "probability": 10},
        {"deal_status": "Needs Analysis", "type": "Ongoing", "position": 2, "color": "blue", "probability": 20},
        {"deal_status": "Proposal/Price Quote", "type": "Ongoing", "position": 3, "color": "amber", "probability": 50},
        {"deal_status": "Negotiation/Review", "type": "Ongoing", "position": 4, "color": "violet", "probability": 75},
        {"deal_status": "Closed Won", "type": "Won", "position": 5, "color": "green", "probability": 100},
        {"deal_status": "Closed Lost", "type": "Lost", "position": 6, "color": "red", "probability": 0},
    ]

    # Map previous Frappe CRM default statuses to Bigin stages
    rename_map = {
        "Demo/Making": "Needs Analysis",
        "Proposal/Quotation": "Proposal/Price Quote",
        "Negotiation": "Negotiation/Review",
        "Won": "Closed Won",
        "Lost": "Closed Lost",
    }

    for old_name, new_name in rename_map.items():
        if frappe.db.exists("CRM Deal Status", old_name) and not frappe.db.exists("CRM Deal Status", new_name):
            frappe.rename_doc("CRM Deal Status", old_name, new_name, force=True)

    # Clean up "Ready to Close" if present
    if frappe.db.exists("CRM Deal Status", "Ready to Close"):
        deal_count = frappe.db.count("CRM Deal", {"status": "Ready to Close"})
        if deal_count == 0:
            frappe.delete_doc("CRM Deal Status", "Ready to Close", force=True)
        else:
            frappe.db.sql("UPDATE `tabCRM Deal` SET status='Negotiation/Review' WHERE status='Ready to Close'")
            frappe.delete_doc("CRM Deal Status", "Ready to Close", force=True)

    # Ensure all target stages exist with correct attributes
    for s in stages:
        if frappe.db.exists("CRM Deal Status", s["deal_status"]):
            doc = frappe.get_doc("CRM Deal Status", s["deal_status"])
            doc.update(s)
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.get_doc({"doctype": "CRM Deal Status", **s})
            doc.insert(ignore_permissions=True)

    # 2. Setup "Pipelines" View in CRM View Settings (Sidebar Pinned / Public View)
    view_label = "Pipelines"
    existing_view_name = frappe.db.exists("CRM View Settings", {"label": view_label, "dt": "CRM Deal"})
    if not existing_view_name:
        existing_view_name = frappe.db.exists("CRM View Settings", {"label": "Sales Pipeline", "dt": "CRM Deal"})

    kanban_cols = [
        {"name": s["deal_status"], "color": s["color"]}
        for s in stages
    ]

    view_data = {
        "doctype": "CRM View Settings",
        "label": view_label,
        "dt": "CRM Deal",
        "route_name": "Deals",
        "type": "kanban",
        "pinned": 1,
        "public": 1,
        "is_default": 1,
        "is_standard": 1,
        "user": "",  # Visible to all users
        "column_field": "status",
        "title_field": "organization",
        "columns": json.dumps([{"name": s["deal_status"]} for s in stages]),
        "kanban_columns": json.dumps(kanban_cols),
        "kanban_fields": json.dumps(["annual_revenue", "email", "mobile_no", "deal_owner", "modified"]),
        "order_by": "modified desc",
        "filters": "{}",
    }

    if existing_view_name:
        view_doc = frappe.get_doc("CRM View Settings", existing_view_name)
        view_doc.update(view_data)
        view_doc.save(ignore_permissions=True)
    else:
        view_doc = frappe.get_doc(view_data)
        view_doc.insert(ignore_permissions=True)

    # 3. Create or Update Desk Workspace "Pipelines"
    if not frappe.db.exists("Workspace", "Pipelines"):
        workspace_doc = frappe.get_doc({
            "doctype": "Workspace",
            "label": "Pipelines",
            "title": "Pipelines",
            "icon": "filter",
            "indicator_color": "blue",
            "module": "Soleos",
            "public": 1,
            "type": "Workspace",
            "sequence_id": 2.0,
            "shortcuts": [
                {
                    "color": "Blue",
                    "doc_view": "Kanban",
                    "label": "Deal Pipeline (Kanban)",
                    "type": "URL",
                    "url": "/crm/deals/view/kanban",
                },
                {
                    "color": "Grey",
                    "doc_view": "List",
                    "label": "CRM Portal Page",
                    "type": "URL",
                    "url": "/crm",
                },
                {
                    "color": "Grey",
                    "doc_view": "List",
                    "label": "Deals",
                    "link_to": "CRM Deal",
                    "type": "DocType",
                },
                {
                    "color": "Grey",
                    "doc_view": "List",
                    "label": "Leads",
                    "link_to": "CRM Lead",
                    "type": "DocType",
                },
                {
                    "color": "Grey",
                    "doc_view": "List",
                    "label": "Organizations",
                    "link_to": "CRM Organization",
                    "type": "DocType",
                },
                {
                    "color": "Grey",
                    "doc_view": "List",
                    "label": "Deal Stages",
                    "link_to": "CRM Deal Status",
                    "type": "DocType",
                },
            ],
            "links": [
                {
                    "label": "Sales & Deals",
                    "type": "Card Break",
                },
                {
                    "label": "Deals",
                    "link_to": "CRM Deal",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "Leads",
                    "link_to": "CRM Lead",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "Organizations",
                    "link_to": "CRM Organization",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "Contacts",
                    "link_to": "Contact",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "Pipeline Settings",
                    "type": "Card Break",
                },
                {
                    "label": "Deal Stages",
                    "link_to": "CRM Deal Status",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "Lost Reasons",
                    "link_to": "CRM Lost Reason",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "Lead Statuses",
                    "link_to": "CRM Lead Status",
                    "link_type": "DocType",
                    "type": "Link",
                },
                {
                    "label": "ERPNext CRM Settings",
                    "link_to": "ERPNext CRM Settings",
                    "link_type": "DocType",
                    "type": "Link",
                },
            ],
        })
        workspace_doc.insert(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()
    frappe.logger("soleos").info("Zoho Bigin Pipeline setup completed successfully.")
