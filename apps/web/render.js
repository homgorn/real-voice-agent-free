const snapshotConfig = [
  ["published_agents", "Published agents"],
  ["draft_agents", "Draft agents"],
  ["active_phone_numbers", "Active numbers"],
  ["connected_integrations", "Connected integrations"],
  ["total_calls", "Total calls"],
  ["completed_calls", "Completed calls"],
  ["failed_calls", "Failed calls"],
  ["total_bookings", "Total bookings"],
];

export function renderApp(state, dom) {
  renderHeader(state, dom);
  renderTabs(state, dom);
  renderOverview(state, dom);
  renderAgents(state, dom);
  renderCalls(state, dom);
  renderBookings(state, dom);
  renderSetup(state, dom);
}

function renderHeader(state, dom) {
  dom.orgName.textContent = state.data.overview?.organization?.name || "Connect API to begin";
  dom.orgSlug.textContent = state.data.overview
    ? `${state.data.overview.organization.slug} | ${state.data.overview.organization.id}`
    : "No organization loaded";
  dom.statusPill.textContent = state.ui.status;
}

function renderTabs(state, dom) {
  dom.tabButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tabTarget === state.ui.activeTab);
  });
  dom.tabSections.forEach((section) => {
    section.classList.toggle("active", section.dataset.tab === state.ui.activeTab);
  });
}

function renderOverview(state, dom) {
  const overview = state.data.overview;
  if (!overview) {
    dom.snapshotGrid.innerHTML = renderPlaceholderCards();
    dom.actionItems.innerHTML = renderEmptyState("Connect to load launch blockers and next steps.");
    dom.overviewBookings.innerHTML = renderEmptyState("No bookings loaded.");
    dom.overviewCalls.innerHTML = renderTableShell(["Call", "Status", "Outcome", "Duration"], renderEmptyState("No calls loaded."));
    return;
  }

  dom.snapshotGrid.innerHTML = snapshotConfig
    .map(([key, label]) => `<article class="card panel"><span>${label}</span><strong>${overview.snapshot[key] ?? 0}</strong></article>`)
    .join("");

  dom.actionItems.innerHTML = overview.action_items.length
    ? overview.action_items
        .map(
          (item) => `
            <article class="list-item">
              <header>
                <strong>${escapeHtml(item.title)}</strong>
                <span class="badge ${item.priority}">${item.priority}</span>
              </header>
              <p>${escapeHtml(item.description)}</p>
              <button type="button" class="link-button" data-nav-href="${escapeHtml(item.href)}">Open ${escapeHtml(item.href)}</button>
            </article>`,
        )
        .join("")
    : renderEmptyState("No blockers. Focus on optimization and QA.");

  dom.overviewBookings.innerHTML = overview.upcoming_bookings.length
    ? overview.upcoming_bookings
        .map(
          (booking) => `
            <article class="list-item">
              <header>
                <strong>${escapeHtml(booking.contact_name)}</strong>
                <span class="badge ${booking.status}">${booking.status}</span>
              </header>
              <p>${escapeHtml(booking.service)}</p>
              <small>${formatDateTime(booking.start_at)}</small>
            </article>`,
        )
        .join("")
    : renderEmptyState("No upcoming bookings.");

  dom.overviewCalls.innerHTML = renderCallsTable(overview.recent_calls, true);
}

function renderAgents(state, dom) {
  dom.agentsList.innerHTML = state.data.agents.length
    ? renderTableShell(
        ["Agent", "Template", "Status", "Actions"],
        state.data.agents
          .map(
            (agent) => `
              <div class="table-row table-row-4">
                <div><strong>${escapeHtml(agent.name)}</strong><br /><small>${escapeHtml(agent.timezone)}</small></div>
                <div>${escapeHtml(agent.template_id)}</div>
                <div><span class="badge ${agent.status}">${agent.status}</span></div>
                <div>
                  ${agent.status === "draft" ? `<button type="button" class="table-action" data-publish-agent="${agent.id}">Publish</button>` : `<span class="muted">Live</span>`}
                </div>
              </div>`,
          )
          .join(""),
      )
    : renderTableShell(["Agent", "Template", "Status", "Actions"], renderEmptyState("No agents yet."));
}

function renderCalls(state, dom) {
  dom.callsList.innerHTML = renderCallsTable(state.data.calls, false);

  if (!state.data.selectedCall) {
    dom.callInspector.innerHTML = renderEmptyState("Select or simulate a call to inspect transcript and summary.");
    return;
  }

  const { call, transcript, summary, workflow } = state.data.selectedCall;
  const latestTurn = transcript?.turns?.[transcript.turns.length - 1] || null;
  dom.callInspector.innerHTML = `
    <article class="inspector-card">
      <header class="inspector-head">
        <strong>${escapeHtml(call.id)}</strong>
        <span class="badge ${call.status}">${call.status}</span>
      </header>
      ${workflow ? `<p><strong>Assistant reply:</strong> ${escapeHtml(workflow.assistant_text)}</p>` : ""}
      ${workflow?.response_audio_ref ? `<p><strong>Audio:</strong> <code>${escapeHtml(workflow.response_audio_ref)}</code></p>` : ""}
      <p><strong>Outcome:</strong> ${escapeHtml(call.outcome || "--")}</p>
      <p><strong>Summary:</strong> ${escapeHtml(summary?.summary_text || "No summary yet")}</p>
      ${latestTurn ? `
        <details open>
          <summary>Latest tools</summary>
          ${renderToolCalls(latestTurn.tool_calls || [])}
        </details>` : ""}
      <details open>
        <summary>Transcript</summary>
        <pre>${escapeHtml(transcript?.transcript_text || "Transcript not available")}</pre>
      </details>
    </article>`;
}

function renderBookings(state, dom) {
  const availability = state.data.availability;
  dom.availabilityMeta.textContent = availability
    ? `${availability.timezone} | ${availability.calendar_connected ? "calendar connected" : "internal schedule only"}`
    : "Select an agent to inspect upcoming availability.";
  dom.availabilityList.innerHTML = renderAvailability(availability);

  dom.bookingsList.innerHTML = state.data.bookings.length
    ? renderTableShell(
        ["Contact", "Service", "Start", "Actions"],
        state.data.bookings
          .map(
            (booking) => `
              <div class="table-row table-row-4">
                <div><strong>${escapeHtml(booking.contact_name)}</strong><br /><small>${escapeHtml(booking.contact_phone)}</small></div>
                <div>${escapeHtml(booking.service)}<br /><span class="badge ${booking.status}">${booking.status}</span></div>
                <div>${formatDateTime(booking.start_at)}</div>
                <div>
                  ${booking.status !== "cancelled" ? `<button type="button" class="table-action" data-cancel-booking="${booking.id}">Cancel</button>` : `<span class="muted">Closed</span>`}
                </div>
              </div>`,
          )
          .join(""),
      )
    : renderTableShell(["Contact", "Service", "Start", "Actions"], renderEmptyState("No bookings yet."));
}

function renderSetup(state, dom) {
  dom.phoneList.innerHTML = state.data.phoneNumbers.length
    ? renderTableShell(
        ["Number", "Provider", "Status", "Actions"],
        state.data.phoneNumbers
          .map(
            (number) => `
              <div class="table-row table-row-4">
                <div><strong>${escapeHtml(number.number)}</strong><br /><small>${escapeHtml(number.label || "Unlabeled")}</small></div>
                <div>${escapeHtml(number.provider)}</div>
                <div><span class="badge ${number.status}">${number.status}</span></div>
                <div>
                  <button type="button" class="table-action" data-toggle-number="${number.id}" data-next-status="${number.status === "active" ? "inactive" : "active"}">
                    Mark ${number.status === "active" ? "inactive" : "active"}
                  </button>
                </div>
              </div>`,
          )
          .join(""),
      )
    : renderTableShell(["Number", "Provider", "Status", "Actions"], renderEmptyState("No phone numbers yet."));

  dom.integrationsList.innerHTML = state.data.integrations.length
    ? renderTableShell(
        ["Provider", "Status", "Config", "Actions"],
        state.data.integrations
          .map(
            (integration) => `
              <div class="table-row table-row-4">
                <div><strong>${escapeHtml(integration.provider)}</strong></div>
                <div><span class="badge ${integration.status === "connected" ? "completed" : "medium"}">${escapeHtml(integration.status)}</span></div>
                <div><small>${escapeHtml(JSON.stringify(integration.config || {}))}</small></div>
                <div>
                  <button type="button" class="table-action" data-test-integration="${integration.provider}">Test</button>
                </div>
              </div>`,
          )
          .join(""),
      )
    : renderTableShell(["Provider", "Status", "Config", "Actions"], renderEmptyState("No integrations yet."));
}

function renderAvailability(availability) {
  if (!availability) {
    return renderEmptyState("Availability will appear after the first data sync.");
  }
  if (!availability.slots.length) {
    return renderEmptyState("No open slots found for the selected window.");
  }
  return availability.slots
    .map(
      (slot) => `
        <article class="list-item">
          <header>
            <strong>${escapeHtml(slot.local_label)}</strong>
            <span class="badge completed">open</span>
          </header>
          <p>${formatDateTime(slot.start_at)} - ${formatDateTime(slot.end_at)}</p>
          <div class="button-row">
            <button type="button" class="table-action" data-select-slot="${escapeHtml(slot.start_at)}">Use slot</button>
          </div>
        </article>`,
    )
    .join("");
}

function renderToolCalls(toolCalls) {
  if (!toolCalls.length) {
    return `<p class="muted">No tool execution recorded.</p>`;
  }
  return toolCalls
    .map((toolCall) => {
      const slots = Array.isArray(toolCall.available_slots) ? toolCall.available_slots : [];
      return `
        <article class="list-item">
          <header>
            <strong>${escapeHtml(toolCall.tool_name || "tool")}</strong>
            <span class="badge ${toolCall.status === "completed" ? "completed" : "medium"}">${escapeHtml(toolCall.status || "unknown")}</span>
          </header>
          <p>${toolCall.calendar_connected ? "Calendar connected." : "Using internal schedule."}</p>
          ${slots.length ? `<div class="button-row">${slots.map((slot) => `<button type="button" class="table-action" data-select-slot="${escapeHtml(slot.start_at)}">${escapeHtml(slot.local_label)}</button>`).join("")}</div>` : `<p class="muted">No slot payload.</p>`}
        </article>`;
    })
    .join("");
}

function renderCallsTable(calls, compact) {
  if (!calls.length) {
    return renderTableShell(["Call", "Status", "Outcome", "Actions"], renderEmptyState("No calls yet."));
  }

  return renderTableShell(
    ["Call", "Status", "Outcome", compact ? "Duration" : "Actions"],
    calls
      .map(
        (call) => `
          <div class="table-row table-row-4">
            <div><strong>${escapeHtml(call.id)}</strong><br /><small>${escapeHtml(call.from_number)}</small></div>
            <div><span class="badge ${call.status}">${call.status}</span></div>
            <div>${escapeHtml(call.outcome || "--")}</div>
            <div>
              ${compact ? `${call.duration_ms ? `${Math.round(call.duration_ms / 1000)}s` : "--"}` : `<button type="button" class="table-action" data-inspect-call="${call.id}">Inspect</button>`}
            </div>
          </div>`,
      )
      .join(""),
  );
}

function renderPlaceholderCards() {
  return snapshotConfig
    .map(([, label]) => `<article class="card panel"><span>${label}</span><strong>--</strong></article>`)
    .join("");
}

function renderTableShell(headers, body) {
  return `
    <div class="table-row table-head ${headers.length === 4 ? "table-row-4" : ""}">
      ${headers.map((header) => `<div>${escapeHtml(header)}</div>`).join("")}
    </div>
    ${body}`;
}

function renderEmptyState(message) {
  return `<article class="list-item empty-state"><p>${escapeHtml(message)}</p></article>`;
}

function formatDateTime(value) {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? escapeHtml(value) : parsed.toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
