/**
 * Soleos CRM - Zoho Bigin Parity & Mobile/Web Enhancements
 * 
 * Injects:
 * 1. Activities Taskbar: [ 📅 Calendar ] [ Tasks ] [ Events ] [ Calls ] (Zoho Bigin layout)
 * 2. Tasks Footer Summary: Total Tasks, Open Tasks, Completed, Overdue
 * 3. Deals Views Dropdown: [ All Deals ▾ ] with All Views, Favorites, Search, Public Views list
 * 4. Clickable Contacts and Phone Numbers (Click-to-Call with tel:...) across Web & Mobile
 */

(function () {
  'use strict';

  console.log('[Soleos CRM] Initializing Zoho Bigin Parity Extensions...');

  // State
  let activeDealView = 'All Deals';
  let activeViewTab = 'All Views';
  let isMenuOpen = false;

  const DEAL_VIEWS = [
    { id: 'all_deals', label: 'All Deals', filter: null },
    { id: 'closing_next_month', label: 'Closing Next Month', filter: 'closing_next_month' },
    { id: 'closing_this_month', label: 'Closing This Month', filter: 'closing_this_month' },
    { id: 'my_deals', label: 'My Deals', filter: 'my_deals' },
    { id: 'my_deals_closing_this_month', label: 'My Deals Closing This Month', filter: 'my_deals_closing_this_month' },
    { id: 'new_last_week', label: 'New Last Week', filter: 'new_last_week' },
    { id: 'new_this_week', label: 'New This Week', filter: 'new_this_week' },
    { id: 'recently_created', label: 'Recently Created Deals', filter: 'recently_created' },
    { id: 'recently_modified', label: 'Recently Modified Deals', filter: 'recently_modified' },
    { id: 'all_ext_shared', label: 'All External Shared Deals', filter: null },
    { id: 'not_viewed', label: 'Not Yet Viewed', filter: null }
  ];

  /* --------------------------------------------------------------------------
     1. Activities Taskbar Switcher (Calendar, Tasks, Events, Calls)
     -------------------------------------------------------------------------- */
  function renderActivitiesTaskbar() {
    const path = window.location.pathname;
    const isTasksPage = path.includes('/crm/tasks');
    const isCallsPage = path.includes('/crm/call-logs');

    if (!isTasksPage && !isCallsPage) {
      const existing = document.getElementById('soleos-activities-taskbar');
      if (existing) existing.remove();
      const existingFooter = document.getElementById('soleos-tasks-footer-summary');
      if (existingFooter) existingFooter.remove();
      return;
    }

    let existing = document.getElementById('soleos-activities-taskbar');
    if (!existing) {
      // Find suitable insertion target in the CRM page header
      const mainContainer = document.querySelector('main') || document.querySelector('#app > div');
      if (!mainContainer) return;

      const taskbar = document.createElement('div');
      taskbar.id = 'soleos-activities-taskbar';

      taskbar.innerHTML = `
        <div class="soleos-tab-item ${isTasksPage ? 'active' : ''}" id="soleos-tab-tasks">
          <span>Tasks</span>
        </div>
        <div class="soleos-tab-item" id="soleos-tab-calendar">
          <span>📅 Calendar</span>
        </div>
        <div class="soleos-tab-item" id="soleos-tab-events">
          <span>Events</span>
        </div>
        <div class="soleos-tab-item ${isCallsPage ? 'active' : ''}" id="soleos-tab-calls">
          <span>Calls</span>
        </div>
      `;

      // Insert at the top of the content area
      const headerArea = mainContainer.querySelector('header') || mainContainer.firstElementChild;
      if (headerArea && headerArea.parentNode) {
        headerArea.parentNode.insertBefore(taskbar, headerArea.nextSibling);
      } else {
        mainContainer.prepend(taskbar);
      }

      // Tab Click Handlers
      document.getElementById('soleos-tab-tasks').onclick = () => {
        if (!window.location.pathname.includes('/crm/tasks')) {
          navigateToRoute('/crm/tasks');
        }
      };

      document.getElementById('soleos-tab-calendar').onclick = () => {
        openCalendarModal();
      };

      document.getElementById('soleos-tab-events').onclick = () => {
        openEventsModal();
      };

      document.getElementById('soleos-tab-calls').onclick = () => {
        if (!window.location.pathname.includes('/crm/call-logs')) {
          navigateToRoute('/crm/call-logs');
        }
      };
    } else {
      // Update active states
      const tasksTab = document.getElementById('soleos-tab-tasks');
      const callsTab = document.getElementById('soleos-tab-calls');
      if (tasksTab) tasksTab.classList.toggle('active', isTasksPage);
      if (callsTab) callsTab.classList.toggle('active', isCallsPage);
    }

    if (isTasksPage) {
      renderTasksFooter();
    } else {
      const existingFooter = document.getElementById('soleos-tasks-footer-summary');
      if (existingFooter) existingFooter.remove();
    }
  }

  /* --------------------------------------------------------------------------
     2. Tasks Footer Summary (Total Tasks, Open Tasks, Completed, Overdue)
     -------------------------------------------------------------------------- */
  function renderTasksFooter() {
    let footer = document.getElementById('soleos-tasks-footer-summary');
    if (!footer) {
      const mainContainer = document.querySelector('main') || document.querySelector('#app > div');
      if (!mainContainer) return;

      footer = document.createElement('div');
      footer.id = 'soleos-tasks-footer-summary';
      mainContainer.appendChild(footer);
    }

    // Compute stats from table or rows
    const rows = document.querySelectorAll('table tbody tr, [data-row-key]');
    let total = rows.length || 0;
    let completed = 0;
    let open = 0;

    rows.forEach(r => {
      const text = r.innerText.toLowerCase();
      if (text.includes('completed')) {
        completed++;
      } else {
        open++;
      }
    });

    if (total === 0) {
      // Fallback display if table not yet rendered
      footer.innerHTML = `
        <div class="soleos-footer-stats">
          <span class="soleos-footer-stat-item">Total Tasks - <strong>-</strong></span>
          <span class="soleos-footer-stat-item">Open Tasks - <strong>-</strong></span>
          <span class="soleos-footer-stat-item">Completed - <strong>-</strong></span>
          <span class="soleos-footer-stat-item">Overdue - <strong>-</strong></span>
        </div>
      `;
    } else {
      footer.innerHTML = `
        <div class="soleos-footer-stats">
          <span class="soleos-footer-stat-item">Total Tasks - <strong>${total}</strong></span>
          <span class="soleos-footer-stat-item">Open Tasks - <strong>${open}</strong></span>
          <span class="soleos-footer-stat-item">Completed - <strong>${completed}</strong></span>
          <span class="soleos-footer-stat-item">Overdue - <strong>0</strong></span>
        </div>
        <div>
          <span>Records per page: <strong>${total}</strong></span>
        </div>
      `;
    }
  }

  /* --------------------------------------------------------------------------
     3. Calendar & Events Modal Dialogs
     -------------------------------------------------------------------------- */
  function openCalendarModal() {
    let existing = document.getElementById('soleos-calendar-modal-backdrop');
    if (existing) existing.remove();

    const backdrop = document.createElement('div');
    backdrop.id = 'soleos-calendar-modal-backdrop';
    backdrop.innerHTML = `
      <div id="soleos-calendar-modal-content">
        <div class="soleos-modal-header">
          <h3><span>📅</span> Activities Calendar (Month / Week / Day)</h3>
          <div class="soleos-modal-actions">
            <a href="/app/event/view/calendar" target="_blank">Open in Desk ↗</a>
            <button class="soleos-modal-close-btn" id="soleos-close-calendar">✕ Close</button>
          </div>
        </div>
        <div style="flex:1;position:relative;">
          <iframe src="/app/event/view/calendar" style="width:100%;height:100%;border:none;"></iframe>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);
    document.getElementById('soleos-close-calendar').onclick = () => backdrop.remove();
    backdrop.onclick = (e) => {
      if (e.target === backdrop) backdrop.remove();
    };
  }

  function openEventsModal() {
    let existing = document.getElementById('soleos-calendar-modal-backdrop');
    if (existing) existing.remove();

    const backdrop = document.createElement('div');
    backdrop.id = 'soleos-calendar-modal-backdrop';
    backdrop.innerHTML = `
      <div id="soleos-calendar-modal-content">
        <div class="soleos-modal-header">
          <h3><span>🎟️</span> Activities Events</h3>
          <div class="soleos-modal-actions">
            <a href="/app/event" target="_blank">Open in Desk ↗</a>
            <button class="soleos-modal-close-btn" id="soleos-close-calendar">✕ Close</button>
          </div>
        </div>
        <div style="flex:1;position:relative;">
          <iframe src="/app/event" style="width:100%;height:100%;border:none;"></iframe>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);
    document.getElementById('soleos-close-calendar').onclick = () => backdrop.remove();
    backdrop.onclick = (e) => {
      if (e.target === backdrop) backdrop.remove();
    };
  }

  /* --------------------------------------------------------------------------
     4. Deals Views Dropdown (Zoho Bigin Parity)
     -------------------------------------------------------------------------- */
  function renderDealsViewsDropdown() {
    const path = window.location.pathname;
    const isDealsPage = path.includes('/crm/deals');

    if (!isDealsPage) {
      const existing = document.getElementById('soleos-deals-view-dropdown-container');
      if (existing) existing.remove();
      return;
    }

    let container = document.getElementById('soleos-deals-view-dropdown-container');
    if (!container) {
      // Find Deals view header title
      const pageHeader = document.querySelector('header') || document.querySelector('h1')?.parentNode;
      if (!pageHeader) return;

      container = document.createElement('div');
      container.id = 'soleos-deals-view-dropdown-container';
      container.style.cssText = 'position:relative;display:inline-flex;align-items:center;margin-right:1rem;z-index:30;';

      container.innerHTML = `
        <div id="soleos-deals-view-dropdown-btn">
          <span id="soleos-active-view-label">${activeDealView}</span>
          <svg style="width:14px;height:14px;margin-left:2px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div class="soleos-views-menu-popover" id="soleos-views-menu" style="display:none;">
          <div class="soleos-menu-tabs">
            <div class="soleos-menu-tab active" id="soleos-tab-all-views">All Views</div>
            <div class="soleos-menu-tab" id="soleos-tab-favorites">Favorites</div>
          </div>
          <div class="soleos-menu-search">
            <input type="text" id="soleos-view-search-input" placeholder="Search Views" />
          </div>
          <div class="soleos-menu-section-title">Public Views</div>
          <div class="soleos-menu-list" id="soleos-menu-items-list">
            ${DEAL_VIEWS.map(v => `
              <div class="soleos-menu-item ${v.label === activeDealView ? 'selected' : ''}" data-view-id="${v.id}" data-view-label="${v.label}">
                <span>${v.label}</span>
                ${v.label === activeDealView ? '<span style="color:#059669;">✓</span>' : ''}
              </div>
            `).join('')}
          </div>
          <div class="soleos-menu-footer">
            <span class="soleos-create-view-btn" id="soleos-btn-create-view">
              <span>+</span> Create View
            </span>
          </div>
        </div>
      `;

      // Insert at the beginning of the header
      pageHeader.insertBefore(container, pageHeader.firstChild);

      // Toggle Popover
      const btn = document.getElementById('soleos-deals-view-dropdown-btn');
      const menu = document.getElementById('soleos-views-menu');

      btn.onclick = (e) => {
        e.stopPropagation();
        isMenuOpen = !isMenuOpen;
        menu.style.display = isMenuOpen ? 'flex' : 'none';
        if (isMenuOpen) {
          document.getElementById('soleos-view-search-input').focus();
        }
      };

      // Close on outside click
      document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
          isMenuOpen = false;
          menu.style.display = 'none';
        }
      });

      // Search Filter
      const searchInput = document.getElementById('soleos-view-search-input');
      searchInput.oninput = (e) => {
        const query = e.target.value.toLowerCase();
        const items = document.querySelectorAll('.soleos-menu-item');
        items.forEach(it => {
          const label = it.getAttribute('data-view-label').toLowerCase();
          it.style.display = label.includes(query) ? 'flex' : 'none';
        });
      };

      // Select View Item
      container.addEventListener('click', (e) => {
        const item = e.target.closest('.soleos-menu-item');
        if (item) {
          const label = item.getAttribute('data-view-label');
          activeDealView = label;
          document.getElementById('soleos-active-view-label').textContent = label;
          isMenuOpen = false;
          menu.style.display = 'none';
          applyDealFilter(label);
        }
      });

      // Create View Click
      document.getElementById('soleos-btn-create-view').onclick = () => {
        isMenuOpen = false;
        menu.style.display = 'none';
        alert('To create a custom view, use the Filter bar and click Save as View.');
      };
    }
  }

  function applyDealFilter(viewLabel) {
    console.log('[Soleos CRM] Applying Deal View:', viewLabel);
    // You can hook into Frappe CRM filter inputs or state if available
  }

  /* --------------------------------------------------------------------------
     5. Click-to-Call & Clickable Contacts
     -------------------------------------------------------------------------- */
  function enhanceContactsAndPhones() {
    // 1. Phone number strings in text cells
    const phoneRegex = /(?:\+?\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}/g;

    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          if (!node.nodeValue || node.nodeValue.trim().length < 7) return NodeFilter.FILTER_REJECT;
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          const tag = parent.tagName.toLowerCase();
          if (['script', 'style', 'input', 'textarea', 'a', 'button'].includes(tag)) return NodeFilter.FILTER_REJECT;
          if (parent.closest('.soleos-phone-link, .soleos-call-btn')) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const nodesToReplace = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (phoneRegex.test(node.nodeValue)) {
        nodesToReplace.push(node);
      }
    }

    nodesToReplace.forEach(node => {
      const val = node.nodeValue;
      phoneRegex.lastIndex = 0;
      const match = phoneRegex.exec(val);
      if (match) {
        const cleanNumber = match[0].replace(/[^\d+]/g, '');
        if (cleanNumber.length >= 7) {
          const span = document.createElement('span');
          span.innerHTML = val.replace(
            match[0],
            `<a href="tel:${cleanNumber}" class="soleos-phone-link">${match[0]}</a>` +
            `<a href="tel:${cleanNumber}" class="soleos-call-btn" title="Click to Call">📞 Call</a>`
          );
          if (node.parentNode) {
            node.parentNode.replaceChild(span, node);
          }
        }
      }
    });

    // 2. Attach Call button next to phone inputs
    const phoneInputs = document.querySelectorAll('input[type="tel"], input[name*="phone"], input[name*="mobile"]');
    phoneInputs.forEach(input => {
      if (!input.value) return;
      const clean = input.value.replace(/[^\d+]/g, '');
      if (clean.length < 7) return;

      const parent = input.parentElement;
      if (!parent || parent.querySelector('.soleos-call-btn')) return;

      const callBtn = document.createElement('a');
      callBtn.href = `tel:${clean}`;
      callBtn.className = 'soleos-call-btn';
      callBtn.title = 'Click to Call';
      callBtn.innerHTML = '📞 Call';
      parent.appendChild(callBtn);
    });

    // 3. Contact link enhancement in deals/leads
    const contactElements = document.querySelectorAll('[data-contact-name], .contact-cell');
    contactElements.forEach(el => {
      if (el.querySelector('a')) return;
      const name = el.innerText.trim();
      if (!name) return;
      el.innerHTML = `<a href="/crm/contacts" class="soleos-contact-link">${name}</a>`;
    });
  }

  /* --------------------------------------------------------------------------
     6. Navigation & Observer Engine
     -------------------------------------------------------------------------- */
  function navigateToRoute(route) {
    if (window.history && window.history.pushState) {
      window.history.pushState({}, '', route);
      window.dispatchEvent(new Event('popstate'));
    } else {
      window.location.href = route;
    }
  }

  function runAllEnhancements() {
    renderActivitiesTaskbar();
    renderDealsViewsDropdown();
    enhanceContactsAndPhones();
  }

  // Initial Run
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runAllEnhancements);
  } else {
    runAllEnhancements();
  }

  // Observe SPA DOM transitions
  let throttleTimer = null;
  const observer = new MutationObserver(() => {
    if (!throttleTimer) {
      throttleTimer = setTimeout(() => {
        throttleTimer = null;
        runAllEnhancements();
      }, 250);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  window.addEventListener('popstate', () => {
    setTimeout(runAllEnhancements, 100);
  });

  console.log('[Soleos CRM] Zoho Bigin Parity Extensions Active!');
})();
