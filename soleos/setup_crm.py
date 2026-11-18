import json
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def setup_all():
    """Master setup function called on migration and app install."""
    frappe.logger("soleos").info("Running Soleos App Setup...")
    setup_bigin_pipeline()
    setup_activity_workflows()
    setup_activities_workspace()
    cleanup_other_workspaces()
    remove_unwanted_sidebar_views()
    frappe.clear_cache()
    frappe.logger("soleos").info("Soleos App Setup completed.")


def setup_bigin_pipeline():
    """
    Sets up Zoho Bigin-style Deal Pipeline stages in Frappe CRM.
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


def setup_activity_workflows():
    """
    Configures Zoho Bigin-style workflows and statuses for Tasks and Calls.
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


def remove_unwanted_sidebar_views():
    """
    Ensures separate activity options (Tasks, Calls, Notes, Activities) do NOT
    show up as separate pinned views or loose links in the sidebar.
    """
    unwanted_labels = ["Activities", "Calls", "Notes", "Activities: Tasks", "Activities: Calls", "Activities: Notes"]
    for lbl in unwanted_labels:
        views = frappe.get_all("CRM View Settings", filters={"label": lbl})
        for v in views:
            frappe.delete_doc("CRM View Settings", v.name, force=True)
            frappe.logger("soleos").info(f"Removed sidebar view '{lbl}'.")


def setup_activities_workspace():
    """
    Creates or updates the 'Activities' Workspace in Frappe Desk with the 4 options
    (Calendar, Tasks, Events, Calls) exclusively located under the Activities taskbar.
    """
    frappe.logger("soleos").info("Configuring Activities Workspace with top taskbar...")
    
    content_json = json.dumps([
        {
            "id": "header_act",
            "type": "header",
            "data": {"text": "<span class=\"h4\"><b>Activities</b></span>", "col": 12}
        },
        {
            "id": "taskbar_label",
            "type": "paragraph",
            "data": {"text": "<b>Activities Taskbar:</b> Quick access to your Calendar, Tasks, Events, and Calls.", "col": 12}
        },
        {
            "id": "tb_calendar",
            "type": "shortcut",
            "data": {"shortcut_name": "Calendar", "col": 3}
        },
        {
            "id": "tb_tasks",
            "type": "shortcut",
            "data": {"shortcut_name": "Tasks", "col": 3}
        },
        {
            "id": "tb_events",
            "type": "shortcut",
            "data": {"shortcut_name": "Events", "col": 3}
        },
        {
            "id": "tb_calls",
            "type": "shortcut",
            "data": {"shortcut_name": "Calls", "col": 3}
        },
        {
            "id": "spacer1",
            "type": "spacer",
            "data": {"col": 12}
        },
        {
            "id": "header_records",
            "type": "header",
            "data": {"text": "<span class=\"h5\"><b>Activity Records & Telephony Settings</b></span>", "col": 12}
        },
        {
            "id": "card_act",
            "type": "card",
            "data": {"card_name": "All Activities", "col": 6}
        },
        {
            "id": "card_tel",
            "type": "card",
            "data": {"card_name": "Telephony & Integrations", "col": 6}
        }
    ])

    shortcuts = [
        {
            "color": "Green",
            "doc_view": "List",
            "label": "Calendar",
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
    ]

    links = [
        {
            "label": "All Activities",
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
    ]

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
        "content": content_json,
    }

    if frappe.db.exists("Workspace", "Activities"):
        doc = frappe.get_doc("Workspace", "Activities")
        doc.update(workspace_data)
        doc.shortcuts = []
        doc.links = []
        for s in shortcuts:
            doc.append("shortcuts", s)
        for l in links:
            doc.append("links", l)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc(workspace_data)
        for s in shortcuts:
            doc.append("shortcuts", s)
        for l in links:
            doc.append("links", l)
        doc.insert(ignore_permissions=True)


def cleanup_other_workspaces():
    """
    Safely removes activity doctypes/URLs (Calendar, Tasks, Calls, Notes, Events) from all
    other workspaces using direct database queries so validation on third-party links is not triggered.
    """
    frappe.logger("soleos").info("Cleaning up activity items from other workspaces...")
    
    # Remove shortcuts from non-Activities workspaces
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent != 'Activities'
        AND (
            link_to IN ('CRM Task', 'CRM Call Log', 'FCRM Note', 'Event')
            OR LOWER(COALESCE(url, '')) LIKE '%calendar%'
            OR LOWER(COALESCE(url, '')) LIKE '%/crm/tasks%'
            OR LOWER(COALESCE(url, '')) LIKE '%/crm/call-logs%'
        )
    """)

    # Remove links from non-Activities workspaces
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Link`
        WHERE parent != 'Activities'
        AND link_to IN ('CRM Task', 'CRM Call Log', 'FCRM Note', 'Event')
    """)

    frappe.db.commit()


if __name__ == "__main__":
    import os
    os.chdir('/home/soleos/frappe-bench/sites')
    frappe.init("soleos.localhost")
    frappe.connect()
    setup_all()
