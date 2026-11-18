import json
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def setup_all():
    """Master setup function called on migration and app install."""
    frappe.logger("soleos").info("Running Soleos App Setup...")
    setup_bigin_pipeline()
    setup_activity_workflows()
    setup_activities_views()
    setup_activities_workspace()
    cleanup_other_workspaces()
    frappe.clear_cache()
    frappe.logger("soleos").info("Soleos App Setup completed.")


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

    if frappe.db.exists("CRM Deal Status", "Ready to Close"):
        deal_count = frappe.db.count("CRM Deal", {"status": "Ready to Close"})
        if deal_count == 0:
            frappe.delete_doc("CRM Deal Status", "Ready to Close", force=True)
        else:
            frappe.db.sql("UPDATE `tabCRM Deal` SET status='Negotiation/Review' WHERE status='Ready to Close'")
            frappe.delete_doc("CRM Deal Status", "Ready to Close", force=True)

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
        "user": "",
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


def setup_activity_workflows():
    """
    Configures Zoho Bigin-style workflows and statuses for Tasks, Calls, and Events.
    """
    frappe.logger("soleos").info("Configuring Activity workflows...")

    # 1. CRM Task Status & Priority (Zoho Bigin options)
    task_statuses = "Not Started\nIn Progress\nCompleted\nDeferred\nWaiting on someone else"
    make_property_setter(
        "CRM Task", "status", "options", task_statuses, "Select", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Task", "status", "default", "Not Started", "Data", for_doctype=False, validate_fields_for_doctype=False
    )

    task_priorities = "High\nNormal\nLow"
    make_property_setter(
        "CRM Task", "priority", "options", task_priorities, "Select", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Task", "priority", "default", "Normal", "Data", for_doctype=False, validate_fields_for_doctype=False
    )

    # 2. CRM Call Log Statuses (Zoho Bigin options)
    call_statuses = "Scheduled\nInitiated\nRinging\nIn Progress\nCompleted\nBusy\nNo Answer\nMissed\nCanceled"
    make_property_setter(
        "CRM Call Log", "status", "options", call_statuses, "Select", for_doctype=False, validate_fields_for_doctype=False
    )


def setup_activities_views():
    """
    Adds Activities, Calls, and Notes to CRM View Settings (public/pinned for sidebar).
    """
    frappe.logger("soleos").info("Configuring Activities views in CRM View Settings...")

    views = [
        {
            "label": "Activities",
            "dt": "CRM Task",
            "route_name": "Tasks",
            "type": "list",
            "pinned": 1,
            "public": 1,
            "is_default": 1,
            "is_standard": 1,
            "icon": "lucide-calendar-check",
            "user": "",
            "order_by": "due_date asc",
            "filters": "{}",
            "load_default_columns": 1,
        },
        {
            "label": "Calls",
            "dt": "CRM Call Log",
            "route_name": "Call Logs",
            "type": "list",
            "pinned": 1,
            "public": 1,
            "is_default": 1,
            "is_standard": 1,
            "icon": "lucide-phone-call",
            "user": "",
            "order_by": "modified desc",
            "filters": "{}",
            "load_default_columns": 1,
        },
        {
            "label": "Notes",
            "dt": "FCRM Note",
            "route_name": "Notes",
            "type": "list",
            "pinned": 1,
            "public": 1,
            "is_default": 1,
            "is_standard": 1,
            "icon": "lucide-file-text",
            "user": "",
            "order_by": "modified desc",
            "filters": "{}",
            "load_default_columns": 1,
        },
    ]

    for v in views:
        view_name = frappe.db.exists("CRM View Settings", {"label": v["label"], "dt": v["dt"]})
        if view_name:
            doc = frappe.get_doc("CRM View Settings", view_name)
            doc.update(v)
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.get_doc({"doctype": "CRM View Settings", **v})
            doc.insert(ignore_permissions=True)


def setup_activities_workspace():
    """
    Creates or updates the 'Activities' Workspace in Frappe Desk.
    """
    frappe.logger("soleos").info("Ensuring Activities Workspace in Desk...")
    
    workspace_data = {
        "doctype": "Workspace",
        "label": "Activities",
        "title": "Activities",
        "icon": "calendar",
        "indicator_color": "green",
        "module": "Soleos",
        "public": 1,
        "type": "Workspace",
        "sequence_id": 3.0,
        "shortcuts": [
            {
                "color": "Green",
                "doc_view": "List",
                "label": "Calendar View",
                "type": "URL",
                "url": "/app/event/view/calendar",
            },
            {
                "color": "Blue",
                "doc_view": "List",
                "label": "Tasks",
                "link_to": "CRM Task",
                "stats_filter": "[]",
                "type": "DocType",
            },
            {
                "color": "Orange",
                "doc_view": "List",
                "label": "Events",
                "link_to": "Event",
                "stats_filter": "[]",
                "type": "DocType",
            },
            {
                "color": "Cyan",
                "doc_view": "List",
                "label": "Calls",
                "link_to": "CRM Call Log",
                "stats_filter": "[]",
                "type": "DocType",
            },
            {
                "color": "Grey",
                "doc_view": "List",
                "label": "Notes",
                "link_to": "FCRM Note",
                "stats_filter": "[]",
                "type": "DocType",
            },
            {
                "color": "Grey",
                "doc_view": "List",
                "label": "CRM Portal Page",
                "type": "URL",
                "url": "/crm",
            },
        ],
        "links": [
            {
                "label": "Activities",
                "type": "Card Break",
            },
            {
                "label": "Tasks",
                "link_to": "CRM Task",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Events",
                "link_to": "Event",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Calls",
                "link_to": "CRM Call Log",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Notes",
                "link_to": "FCRM Note",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Telephony & Integrations",
                "type": "Card Break",
            },
            {
                "label": "Telephony Agents",
                "link_to": "CRM Telephony Agent",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Telephony Phones",
                "link_to": "CRM Telephony Phone",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Twilio Settings",
                "link_to": "CRM Twilio Settings",
                "link_type": "DocType",
                "type": "Link",
            },
            {
                "label": "Exotel Settings",
                "link_to": "CRM Exotel Settings",
                "link_type": "DocType",
                "type": "Link",
            },
        ],
    }

    if frappe.db.exists("Workspace", "Activities"):
        doc = frappe.get_doc("Workspace", "Activities")
        doc.update(workspace_data)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc(workspace_data)
        doc.insert(ignore_permissions=True)


def cleanup_other_workspaces():
    """
    Removes activity doctypes (Tasks, Calls, Notes, Events) from other workspaces
    so they are exclusively housed in the 'Activities' workspace.
    """
    frappe.logger("soleos").info("Cleaning up activity doctypes from other workspaces...")
    activity_doctypes = {"CRM Task", "CRM Call Log", "FCRM Note", "Event"}

    workspaces_to_check = ["Frappe CRM", "Pipelines", "CRM"]
    for ws_name in workspaces_to_check:
        if frappe.db.exists("Workspace", ws_name):
            ws = frappe.get_doc("Workspace", ws_name)
            modified = False

            # Filter shortcuts
            new_shortcuts = [s for s in ws.shortcuts if s.link_to not in activity_doctypes and (s.url or "") != "/app/event/view/calendar"]
            if len(new_shortcuts) != len(ws.shortcuts):
                ws.shortcuts = new_shortcuts
                modified = True

            # Filter links
            new_links = [l for l in ws.links if l.link_to not in activity_doctypes]
            if len(new_links) != len(ws.links):
                ws.links = new_links
                modified = True

            if modified:
                ws.save(ignore_permissions=True)
                frappe.logger("soleos").info(f"Cleaned up {ws_name} workspace.")

    frappe.db.commit()


if __name__ == "__main__":
    import os
    os.chdir('/home/soleos/frappe-bench/sites')
    frappe.init("soleos.localhost")
    frappe.connect()
    setup_all()
