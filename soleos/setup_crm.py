import json
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def setup_all():
    """Master setup function called on migration and app install."""
    frappe.logger("soleos").info("Running Soleos App Setup...")
    setup_bigin_pipeline()
    setup_activity_workflows()
    setup_activities_workspace()
    setup_sidebar_views()
    setup_crm_activities_scripts()
    setup_clickable_contacts_and_phones()
    cleanup_other_workspaces()
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

    # 3. CRM Task Field Labels (Zoho Bigin field naming)
    make_property_setter(
        "CRM Task", "title", "label", "Task Name", "Data", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Task", "assigned_to", "label", "Task Owner", "Data", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Task", "reference_docname", "label", "Related To", "Data", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Task", "reference_doctype", "label", "Related To Type", "Data", for_doctype=False, validate_fields_for_doctype=False
    )

    # 4. CRM Call Log Field Labels (Zoho Bigin field naming)
    make_property_setter(
        "CRM Call Log", "title", "label", "Subject", "Data", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Call Log", "assigned_to", "label", "Call Owner", "Data", for_doctype=False, validate_fields_for_doctype=False
    )
    make_property_setter(
        "CRM Call Log", "reference_docname", "label", "Related To", "Data", for_doctype=False, validate_fields_for_doctype=False
    )


def setup_sidebar_views():
    """
    Adds single 'Activities' and 'Pipelines' entries to CRM View Settings (public/pinned for sidebar).
    Removes any separate/individual views for Calls, Notes, Tasks, or Calendar so the sidebar stays clean.
    """
    frappe.logger("soleos").info("Configuring sidebar views in CRM View Settings...")

    # 1. Remove any loose/individual views
    unwanted_labels = ["Calls", "Notes", "Activities: Tasks", "Activities: Calls", "Activities: Notes"]
    for lbl in unwanted_labels:
        views = frappe.get_all("CRM View Settings", filters={"label": lbl})
        for v in views:
            frappe.delete_doc("CRM View Settings", v.name, force=True)

    # 2. Ensure 'Pipelines' view is pinned in the sidebar
    stages = ["Qualification", "Needs Analysis", "Proposal/Price Quote", "Negotiation/Review", "Closed Won", "Closed Lost"]
    kanban_cols = [{"name": s, "color": "gray"} for s in stages]
    pipeline_view_name = frappe.db.exists("CRM View Settings", {"label": "Pipelines", "dt": "CRM Deal"})
    pipeline_data = {
        "doctype": "CRM View Settings",
        "label": "Pipelines",
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
        "columns": json.dumps([{"name": s} for s in stages]),
        "kanban_columns": json.dumps(kanban_cols),
        "kanban_fields": json.dumps(["annual_revenue", "email", "mobile_no", "deal_owner", "modified"]),
        "order_by": "modified desc",
        "filters": "{}",
    }
    if pipeline_view_name:
        p_doc = frappe.get_doc("CRM View Settings", pipeline_view_name)
        p_doc.update(pipeline_data)
        p_doc.save(ignore_permissions=True)
    else:
        p_doc = frappe.get_doc(pipeline_data)
        p_doc.insert(ignore_permissions=True)

    # 3. Ensure single 'Activities' view is pinned in the sidebar with Zoho Bigin columns
    activities_view_name = frappe.db.exists("CRM View Settings", {"label": "Activities", "dt": "CRM Task"})
    zoho_columns = [
        {"label": "Task Name", "type": "Data", "key": "title", "width": "16rem"},
        {"label": "Due Date", "type": "Datetime", "key": "due_date", "width": "10rem"},
        {"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
        {"label": "Priority", "type": "Select", "key": "priority", "width": "8rem"},
        {"label": "Related To", "type": "Dynamic Link", "key": "reference_docname", "width": "12rem"},
        {"label": "Task Owner", "type": "Link", "key": "assigned_to", "width": "12rem"},
    ]
    act_data = {
        "doctype": "CRM View Settings",
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
        "load_default_columns": 0,
        "columns": json.dumps(zoho_columns),
        "rows": json.dumps(["name", "title", "due_date", "status", "priority", "reference_docname", "reference_doctype", "assigned_to", "modified"]),
    }
    if activities_view_name:
        act_doc = frappe.get_doc("CRM View Settings", activities_view_name)
        act_doc.update(act_data)
        act_doc.save(ignore_permissions=True)
    else:
        act_doc = frappe.get_doc(act_data)
        act_doc.insert(ignore_permissions=True)


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
            "data": {"text": "<b>Activities Taskbar:</b> Switch between Calendar, Tasks, Events, and Calls.", "col": 12}
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


def setup_crm_activities_scripts():
    """
    Creates CRM Form Scripts for CRM Task and CRM Call Log (List view) to inject:
    1. The Zoho Bigin Activities Taskbar (Calendar, Tasks, Events, Calls) above the list.
    2. Header action buttons for Calendar, Events, and Calls beside Create.
    3. An integrated FullCalendar popup modal so Calendar opens right in CRM without leaving.
    """
    frappe.logger("soleos").info("Configuring CRM Activities Scripts...")

    task_script = """function setupList(obj) {
  function renderTaskbar() {
    let container = document.getElementById('zoho-activities-taskbar');
    if (!container) {
      let target = document.querySelector('.layout-header') || document.querySelector('[class*="LayoutHeader"]');
      if (!target) return;

      container = document.createElement('div');
      container.id = 'zoho-activities-taskbar';
      container.style.cssText = 'display:flex;align-items:center;gap:12px;padding:8px 20px;border-bottom:1px solid #e5e7eb;background:#ffffff;font-size:13px;font-weight:500;z-index:20;position:relative;';

      container.innerHTML = `
        <div id="act-tab-calendar" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#4b5563;transition:all 0.2s;" onmouseover="this.style.backgroundColor='#f3f4f6'" onmouseout="this.style.backgroundColor='transparent'">
          <span>📅</span> <span style="font-weight:500;">Calendar</span>
        </div>
        <div id="act-tab-tasks" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#16a34a;background-color:#f0fdf4;border:1px solid #bbf7d0;font-weight:600;">
          <span>📋</span> <span>Tasks</span>
        </div>
        <div id="act-tab-events" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#4b5563;transition:all 0.2s;" onmouseover="this.style.backgroundColor='#f3f4f6'" onmouseout="this.style.backgroundColor='transparent'">
          <span>🤝</span> <span style="font-weight:500;">Events</span>
        </div>
        <div id="act-tab-calls" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#4b5563;transition:all 0.2s;" onmouseover="this.style.backgroundColor='#f3f4f6'" onmouseout="this.style.backgroundColor='transparent'">
          <span>📞</span> <span style="font-weight:500;">Calls</span>
        </div>
      `;

      if (target.parentNode) {
        target.parentNode.insertBefore(container, target.nextSibling);
      }

      let calBtn = document.getElementById('act-tab-calendar');
      if (calBtn) calBtn.onclick = () => openCalendarModal();

      let evBtn = document.getElementById('act-tab-events');
      if (evBtn) evBtn.onclick = () => window.open('/app/event', '_blank');

      let callBtn = document.getElementById('act-tab-calls');
      if (callBtn) callBtn.onclick = () => {
        if (obj && obj.router) obj.router.push({ name: 'Call Logs' });
        else window.location.href = '/crm/call-logs';
      };
    }
  }

  function openCalendarModal() {
    let existing = document.getElementById('crm-calendar-modal');
    if (existing) existing.remove();

    let modal = document.createElement('div');
    modal.id = 'crm-calendar-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(2px);';
    modal.innerHTML = `
      <div style="background:#ffffff;width:92%;height:88%;border-radius:12px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.3);display:flex;flex-direction:column;overflow:hidden;border:1px solid #e5e7eb;">
        <div style="padding:12px 20px;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;background:#f9fafb;">
          <div style="display:flex;align-items:center;gap:8px;font-weight:600;font-size:15px;color:#111827;">
            <span>📅</span> Activities Calendar (Month / Week / Day)
          </div>
          <div style="display:flex;gap:10px;align-items:center;">
            <a href="/app/event/view/calendar" target="_blank" style="padding:6px 12px;border-radius:6px;background:#e5e7eb;color:#374151;text-decoration:none;font-size:13px;font-weight:500;">Open in Desk ↗</a>
            <button id="close-cal-modal" style="border:none;background:#fee2e2;color:#991b1b;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">✕ Close</button>
          </div>
        </div>
        <div style="flex:1;position:relative;">
          <iframe src="/app/event/view/calendar" style="width:100%;height:100%;border:none;"></iframe>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    document.getElementById('close-cal-modal').onclick = () => modal.remove();
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
  }

  setTimeout(renderTaskbar, 200);
  let timer = setInterval(renderTaskbar, 800);
  setTimeout(() => clearInterval(timer), 12000);

  return {
    actions: [
      {
        label: 'Calendar',
        icon: 'lucide-calendar',
        onClick: () => openCalendarModal()
      },
      {
        label: 'Events',
        icon: 'lucide-calendar-days',
        onClick: () => window.open('/app/event', '_blank')
      },
      {
        label: 'Calls',
        icon: 'lucide-phone',
        onClick: () => {
          if (obj && obj.router) obj.router.push({ name: 'Call Logs' });
          else window.location.href = '/crm/call-logs';
        }
      }
    ],
    bulk_actions: []
  };
}"""

    call_script = """function setupList(obj) {
  function renderTaskbar() {
    let container = document.getElementById('zoho-activities-taskbar');
    if (!container) {
      let target = document.querySelector('.layout-header') || document.querySelector('[class*="LayoutHeader"]');
      if (!target) return;

      container = document.createElement('div');
      container.id = 'zoho-activities-taskbar';
      container.style.cssText = 'display:flex;align-items:center;gap:12px;padding:8px 20px;border-bottom:1px solid #e5e7eb;background:#ffffff;font-size:13px;font-weight:500;z-index:20;position:relative;';

      container.innerHTML = `
        <div id="act-tab-calendar" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#4b5563;transition:all 0.2s;" onmouseover="this.style.backgroundColor='#f3f4f6'" onmouseout="this.style.backgroundColor='transparent'">
          <span>📅</span> <span style="font-weight:500;">Calendar</span>
        </div>
        <div id="act-tab-tasks" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#4b5563;transition:all 0.2s;" onmouseover="this.style.backgroundColor='#f3f4f6'" onmouseout="this.style.backgroundColor='transparent'">
          <span>📋</span> <span style="font-weight:500;">Tasks</span>
        </div>
        <div id="act-tab-events" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#4b5563;transition:all 0.2s;" onmouseover="this.style.backgroundColor='#f3f4f6'" onmouseout="this.style.backgroundColor='transparent'">
          <span>🤝</span> <span style="font-weight:500;">Events</span>
        </div>
        <div id="act-tab-calls" style="cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;color:#16a34a;background-color:#f0fdf4;border:1px solid #bbf7d0;font-weight:600;">
          <span>📞</span> <span>Calls</span>
        </div>
      `;

      if (target.parentNode) {
        target.parentNode.insertBefore(container, target.nextSibling);
      }

      let calBtn = document.getElementById('act-tab-calendar');
      if (calBtn) calBtn.onclick = () => openCalendarModal();

      let taskBtn = document.getElementById('act-tab-tasks');
      if (taskBtn) taskBtn.onclick = () => {
        if (obj && obj.router) obj.router.push({ name: 'Tasks' });
        else window.location.href = '/crm/tasks';
      };

      let evBtn = document.getElementById('act-tab-events');
      if (evBtn) evBtn.onclick = () => window.open('/app/event', '_blank');
    }
  }

  function openCalendarModal() {
    let existing = document.getElementById('crm-calendar-modal');
    if (existing) existing.remove();

    let modal = document.createElement('div');
    modal.id = 'crm-calendar-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(2px);';
    modal.innerHTML = `
      <div style="background:#ffffff;width:92%;height:88%;border-radius:12px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.3);display:flex;flex-direction:column;overflow:hidden;border:1px solid #e5e7eb;">
        <div style="padding:12px 20px;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;background:#f9fafb;">
          <div style="display:flex;align-items:center;gap:8px;font-weight:600;font-size:15px;color:#111827;">
            <span>📅</span> Activities Calendar (Month / Week / Day)
          </div>
          <div style="display:flex;gap:10px;align-items:center;">
            <a href="/app/event/view/calendar" target="_blank" style="padding:6px 12px;border-radius:6px;background:#e5e7eb;color:#374151;text-decoration:none;font-size:13px;font-weight:500;">Open in Desk ↗</a>
            <button id="close-cal-modal" style="border:none;background:#fee2e2;color:#991b1b;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">✕ Close</button>
          </div>
        </div>
        <div style="flex:1;position:relative;">
          <iframe src="/app/event/view/calendar" style="width:100%;height:100%;border:none;"></iframe>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    document.getElementById('close-cal-modal').onclick = () => modal.remove();
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
  }

  setTimeout(renderTaskbar, 200);
  let timer = setInterval(renderTaskbar, 800);
  setTimeout(() => clearInterval(timer), 12000);

  return {
    actions: [
      {
        label: 'Calendar',
        icon: 'lucide-calendar',
        onClick: () => openCalendarModal()
      },
      {
        label: 'Tasks',
        icon: 'lucide-check-square',
        onClick: () => {
          if (obj && obj.router) obj.router.push({ name: 'Tasks' });
          else window.location.href = '/crm/tasks';
        }
      },
      {
        label: 'Events',
        icon: 'lucide-calendar-days',
        onClick: () => window.open('/app/event', '_blank')
      }
    ],
    bulk_actions: []
  };
}"""

    # Upsert scripts
    scripts = [
        {"name": "Activities Taskbar for CRM Task", "dt": "CRM Task", "script": task_script},
        {"name": "Activities Taskbar for CRM Call Log", "dt": "CRM Call Log", "script": call_script},
    ]

    for s in scripts:
        if frappe.db.exists("CRM Form Script", s["name"]):
            d = frappe.get_doc("CRM Form Script", s["name"])
            d.script = s["script"]
            d.dt = s["dt"]
            d.view = "List"
            d.enabled = 1
            d.save(ignore_permissions=True)
        else:
            d = frappe.get_doc({
                "doctype": "CRM Form Script",
                "name": s["name"],
                "dt": s["dt"],
                "view": "List",
                "enabled": 1,
                "is_standard": 0,
                "script": s["script"]
            })
            d.insert(ignore_permissions=True)


def setup_clickable_contacts_and_phones():
    """
    Configures CRM Form Scripts across Deal, Lead, Contact, Organization, Call Log, and Task
    so phone numbers are clickable to call (tel:...) and contacts are clickable to view
    everywhere phone numbers/contacts appear on CRM web and mobile app.
    """
    frappe.logger("soleos").info("Configuring clickable contacts and phone numbers across CRM...")

    shared_engine = """
(function() {
  if (window.__soleos_phone_engine_active) return;
  window.__soleos_phone_engine_active = true;

  if (!document.getElementById('soleos-clickable-phone-css')) {
    const style = document.createElement('style');
    style.id = 'soleos-clickable-phone-css';
    style.textContent = `
      .soleos-phone-link {
        color: #15803d !important;
        font-weight: 500 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
        padding: 2px 4px !important;
        border-radius: 4px !important;
        transition: all 0.15s ease !important;
      }
      .soleos-phone-link:hover {
        background-color: #f0fdf4 !important;
        text-decoration: underline !important;
        color: #166534 !important;
      }
      .soleos-call-btn {
        display: inline-flex !important;
        align-items: center !important;
        gap: 4px !important;
        padding: 3px 8px !important;
        margin-left: 6px !important;
        border-radius: 5px !important;
        background: #f0fdf4 !important;
        color: #16a34a !important;
        border: 1px solid #bbf7d0 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        vertical-align: middle !important;
        transition: all 0.15s ease !important;
        white-space: nowrap !important;
      }
      .soleos-call-btn:hover {
        background: #dcfce7 !important;
        border-color: #86efac !important;
        color: #15803d !important;
      }
      .soleos-contact-link {
        color: #1d4ed8 !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 4px !important;
        transition: all 0.15s ease !important;
      }
      .soleos-contact-link:hover {
        text-decoration: underline !important;
        color: #1e40af !important;
      }
    `;
    document.head.appendChild(style);
  }

  function cleanPhone(val) {
    if (!val || typeof val !== 'string') return '';
    let trimmed = val.trim();
    if (trimmed.includes('/') || trimmed.includes('@') || trimmed.includes('₹') || trimmed.includes('$')) return '';
    let digits = trimmed.replace(/\\D/g, '');
    if (digits.length >= 7 && digits.length <= 15) {
      return trimmed.replace(/[^0-9+]/g, '');
    }
    return '';
  }

  function callNumber(phone, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    let clean = cleanPhone(phone);
    if (clean) {
      window.location.href = 'tel:' + clean;
    }
  }

  function goToContact(nameOrId, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (window.__crm_router) {
      window.__crm_router.push({ name: 'Contact', params: { contactId: nameOrId } });
    } else {
      window.location.href = '/crm/contacts/' + encodeURIComponent(nameOrId);
    }
  }

  function enhanceDOM() {
    // 1. Form Inputs with Phone/Mobile Number
    let fields = document.querySelectorAll('.field, [data-field]');
    fields.forEach(field => {
      let labelEl = field.querySelector('.truncate, label');
      let labelText = labelEl ? labelEl.textContent.trim().toLowerCase() : '';
      let isPhone = labelText.includes('phone') || labelText.includes('mobile') || labelText.includes('call');
      if (isPhone) {
        let input = field.querySelector('input');
        if (input && input.value) {
          let clean = cleanPhone(input.value);
          if (clean && !field.querySelector('.soleos-call-btn')) {
            let btn = document.createElement('a');
            btn.className = 'soleos-call-btn';
            btn.href = 'tel:' + clean;
            btn.title = 'Call ' + input.value;
            btn.innerHTML = '📞 <span>Call</span>';
            btn.onclick = (e) => callNumber(clean, e);
            if (input.parentNode) input.parentNode.appendChild(btn);
          }
        } else {
          let valEl = field.querySelector('.text-ink-gray-5, .text-ink-gray-9, .cursor-pointer');
          if (valEl && valEl.textContent && !valEl.querySelector('.soleos-call-btn')) {
            let clean = cleanPhone(valEl.textContent);
            if (clean && valEl.parentNode && !valEl.parentNode.querySelector('.soleos-call-btn')) {
              let btn = document.createElement('a');
              btn.className = 'soleos-call-btn';
              btn.href = 'tel:' + clean;
              btn.title = 'Call ' + clean;
              btn.innerHTML = '📞 <span>Call</span>';
              btn.onclick = (e) => callNumber(clean, e);
              valEl.parentNode.appendChild(btn);
            }
          }
        }
      }
    });

    // 2. Deal Contacts Section & MobileDeal Contacts
    let phoneRows = document.querySelectorAll('.flex.items-center.gap-3');
    phoneRows.forEach(row => {
      if (row.dataset.soleosPhoneEnhanced) return;
      let text = row.textContent.trim();
      let clean = cleanPhone(text);
      if (clean && !row.querySelector('.soleos-phone-link')) {
        row.dataset.soleosPhoneEnhanced = 'true';
        let svg = row.querySelector('svg');
        let iconHtml = svg ? svg.outerHTML : '📞';
        row.innerHTML = `
          <a href="tel:${clean}" class="soleos-phone-link" title="Call ${text}">
            ${iconHtml}
            <span>${text}</span>
          </a>
        `;
        let a = row.querySelector('a');
        if (a) a.onclick = (e) => callNumber(clean, e);
      }
    });

    // 3. Contact Headers in Deal / MobileDeal
    let contactHeaders = document.querySelectorAll('button[class*="header"], .font-semibold');
    contactHeaders.forEach(el => {
      if (el.dataset.soleosContactEnhanced) return;
      let parent = el.closest('[class*="Section"], .section, tr, [class*="list-row"]');
      if (parent && (parent.textContent.toLowerCase().includes('mobile') || parent.textContent.toLowerCase().includes('phone') || parent.querySelector('.soleos-phone-link, a[href^="tel:"]'))) {
        let name = el.textContent.trim();
        if (name && !name.includes('Contacts') && !name.includes('Details') && !el.querySelector('a')) {
          el.dataset.soleosContactEnhanced = 'true';
          el.style.cursor = 'pointer';
          el.title = 'View Contact: ' + name;
          el.classList.add('soleos-contact-link');
          el.onclick = (e) => goToContact(name, e);
        }
      }
    });

    // 4. List View & Table Cells (Contacts list, Deals list, Leads list, Call logs)
    let cells = document.querySelectorAll('[class*="list-row"] [class*="truncate"], td');
    cells.forEach(cell => {
      if (cell.dataset.soleosCellEnhanced) return;
      let text = cell.textContent.trim();
      let clean = cleanPhone(text);
      if (clean && !cell.querySelector('a[href^="tel:"]')) {
        cell.dataset.soleosCellEnhanced = 'true';
        cell.innerHTML = `
          <a href="tel:${clean}" class="soleos-phone-link" title="Call ${text}">
            📞 <span>${text}</span>
          </a>
        `;
        let a = cell.querySelector('a');
        if (a) a.onclick = (e) => callNumber(clean, e);
      }
    });
  }

  // Global click interception
  document.addEventListener('click', function(e) {
    let a = e.target.closest('a[href^="tel:"]');
    if (a) {
      e.stopPropagation();
      return;
    }
    let text = e.target.textContent ? e.target.textContent.trim() : '';
    let clean = cleanPhone(text);
    if (clean && e.target.closest('.field, [data-field], [class*="list-row"], [class*="Section"]')) {
      callNumber(clean, e);
    }
  }, true);

  // MutationObserver for SPA responsiveness
  let timer = null;
  const obs = new MutationObserver(() => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(enhanceDOM, 200);
  });
  obs.observe(document.body, { childList: true, subtree: true });

  setTimeout(enhanceDOM, 300);
  setInterval(enhanceDOM, 2500);
})();
"""

    doctypes = ["CRM Deal", "CRM Lead", "Contact", "CRM Organization", "CRM Call Log", "CRM Task"]
    
    for dt in doctypes:
        dt_class_name = dt.replace(" ", "")
        form_script = f"""class {dt_class_name} {{
  mounted() {{
    if (this && this.router) window.__crm_router = this.router;
    {shared_engine}
  }}
}}"""

        list_script = f"""function setupList(obj) {{
  if (obj && obj.router) window.__crm_router = obj.router;
  {shared_engine}
  return {{ actions: [], bulk_actions: [] }};
}}"""

        form_name = f"Clickable Contacts & Phones for {dt} Form"
        if frappe.db.exists("CRM Form Script", form_name):
            d = frappe.get_doc("CRM Form Script", form_name)
            d.script = form_script
            d.enabled = 1
            d.save(ignore_permissions=True)
        else:
            d = frappe.get_doc({
                "doctype": "CRM Form Script",
                "name": form_name,
                "dt": dt,
                "view": "Form",
                "script": form_script,
                "enabled": 1,
                "is_standard": 0,
            })
            d.insert(ignore_permissions=True)

        if dt not in ["CRM Task", "CRM Call Log"]:
            list_name = f"Clickable Contacts & Phones for {dt} List"
            if frappe.db.exists("CRM Form Script", list_name):
                d = frappe.get_doc("CRM Form Script", list_name)
                d.script = list_script
                d.enabled = 1
                d.save(ignore_permissions=True)
            else:
                d = frappe.get_doc({
                    "doctype": "CRM Form Script",
                    "name": list_name,
                    "dt": dt,
                    "view": "List",
                    "script": list_script,
                    "enabled": 1,
                    "is_standard": 0,
                })
                d.insert(ignore_permissions=True)


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
    import os, sys
    sys.path.insert(0, "/home/soleos/frappe-bench/apps/soleos")
    os.chdir("/home/soleos/frappe-bench/sites")
    frappe.init("soleos.localhost", sites_path="/home/soleos/frappe-bench/sites")
    frappe.connect()
    setup_all()
