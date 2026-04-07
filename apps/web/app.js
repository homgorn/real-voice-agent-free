import { VoiceAgentApi } from "./api.js";
import { renderApp } from "./render.js";

const dom = {
  authForm: document.getElementById("auth-form"),
  apiBaseInput: document.getElementById("api-base"),
  apiKeyInput: document.getElementById("api-key"),
  reloadButton: document.getElementById("reload-button"),
  orgName: document.getElementById("org-name"),
  orgSlug: document.getElementById("org-slug"),
  statusPill: document.getElementById("status-pill"),
  errorBanner: document.getElementById("error-banner"),
  successBanner: document.getElementById("success-banner"),
  snapshotGrid: document.getElementById("snapshot-grid"),
  actionItems: document.getElementById("action-items"),
  overviewBookings: document.getElementById("overview-bookings"),
  overviewCalls: document.getElementById("overview-calls"),
  agentsList: document.getElementById("agents-list"),
  callsList: document.getElementById("calls-list"),
  callInspector: document.getElementById("call-inspector"),
  bookingsList: document.getElementById("bookings-list"),
  availabilityMeta: document.getElementById("availability-meta"),
  availabilityList: document.getElementById("availability-list"),
  phoneList: document.getElementById("phone-list"),
  integrationsList: document.getElementById("integrations-list"),
  tabButtons: [...document.querySelectorAll("[data-tab-target]")],
  tabSections: [...document.querySelectorAll(".tab-section")],
  agentForm: document.getElementById("agent-form"),
  bookingForm: document.getElementById("booking-form"),
  phoneForm: document.getElementById("phone-form"),
  integrationForm: document.getElementById("integration-form"),
  callForm: document.getElementById("call-form"),
  bookingRefreshSlots: document.getElementById("booking-refresh-slots"),
  agentTemplate: document.getElementById("agent-template"),
  agentName: document.getElementById("agent-name"),
  agentTimezone: document.getElementById("agent-timezone"),
  agentLanguage: document.getElementById("agent-language"),
  agentHours: document.getElementById("agent-hours"),
  agentPublish: document.getElementById("agent-publish"),
  bookingAgent: document.getElementById("booking-agent"),
  bookingName: document.getElementById("booking-name"),
  bookingPhone: document.getElementById("booking-phone"),
  bookingService: document.getElementById("booking-service"),
  bookingStart: document.getElementById("booking-start"),
  phoneProvider: document.getElementById("phone-provider"),
  phoneNumber: document.getElementById("phone-number"),
  phoneLabel: document.getElementById("phone-label"),
  phoneStatus: document.getElementById("phone-status"),
  integrationProvider: document.getElementById("integration-provider"),
  integrationReference: document.getElementById("integration-reference"),
  callAgent: document.getElementById("call-agent"),
  callPhoneNumber: document.getElementById("call-phone-number"),
  callFromNumber: document.getElementById("call-from-number"),
  callToNumber: document.getElementById("call-to-number"),
  callVoice: document.getElementById("call-voice"),
  callInput: document.getElementById("call-input"),
  callOutcome: document.getElementById("call-outcome"),
  callDuration: document.getElementById("call-duration"),
  callAutoComplete: document.getElementById("call-auto-complete"),
};

const state = {
  api: null,
  ui: {
    activeTab: "overview",
    status: "Idle",
  },
  data: {
    overview: null,
    templates: [],
    agents: [],
    calls: [],
    bookings: [],
    phoneNumbers: [],
    integrations: [],
    availability: null,
    selectedCall: null,
  },
};

bindEvents();
restoreSession();
render();

function bindEvents() {
  dom.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await connectAndLoad();
  });

  dom.reloadButton.addEventListener("click", async () => {
    if (!state.api) {
      showError("Connect API first.");
      return;
    }
    await loadAllData();
  });

  dom.tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.ui.activeTab = button.dataset.tabTarget;
      render();
    });
  });

  dom.bookingAgent.addEventListener("change", async () => {
    await runAction(async () => {
      await loadAvailability();
      render();
    }, { preserveBanner: true });
  });

  dom.bookingRefreshSlots.addEventListener("click", async () => {
    await runAction(async () => {
      await loadAvailability();
      render();
      showSuccess("Availability refreshed.");
    });
  });

  dom.agentForm.addEventListener("submit", handleAgentSubmit);
  dom.bookingForm.addEventListener("submit", handleBookingSubmit);
  dom.phoneForm.addEventListener("submit", handlePhoneSubmit);
  dom.integrationForm.addEventListener("submit", handleIntegrationSubmit);
  dom.callForm.addEventListener("submit", handleCallSimulation);

  document.body.addEventListener("click", handleActionClick);
}

async function connectAndLoad() {
  hideBanners();
  const apiBase = dom.apiBaseInput.value.trim();
  const apiKey = dom.apiKeyInput.value.trim();
  if (!apiBase || !apiKey) {
    showError("API base URL and API key are required.");
    return;
  }

  state.api = new VoiceAgentApi({ apiBase, apiKey });
  localStorage.setItem("voiceagent.apiBase", apiBase);
  localStorage.setItem("voiceagent.apiKey", apiKey);
  await loadAllData();
}

async function loadAllData() {
  if (!state.api) {
    return;
  }
  state.ui.status = "Loading";
  render();
  hideBanners();

  try {
    const [overview, templates, agents, calls, bookings, phoneNumbers, integrations] = await Promise.all([
      state.api.getDashboardOverview(),
      state.api.listTemplates(),
      state.api.listAgents(),
      state.api.listCalls(),
      state.api.listBookings(),
      state.api.listPhoneNumbers(),
      state.api.listIntegrations(),
    ]);

    const selectedCallId = state.data.selectedCall?.call?.id || null;
    const selectedWorkflow = state.data.selectedCall?.workflow || null;

    state.data.overview = overview;
    state.data.templates = templates.items || [];
    state.data.agents = agents.items || [];
    state.data.calls = calls.items || [];
    state.data.bookings = bookings.items || [];
    state.data.phoneNumbers = phoneNumbers.items || [];
    state.data.integrations = integrations.items || [];

    syncFormOptions();
    await loadAvailability({ silent: true });
    state.ui.status = "Live";

    if (selectedCallId && state.data.calls.some((item) => item.id === selectedCallId)) {
      await inspectCall(selectedCallId, selectedWorkflow);
    } else if (state.data.calls[0]) {
      await inspectCall(state.data.calls[0].id);
    } else {
      state.data.selectedCall = null;
    }

    showSuccess("Control plane data refreshed.");
  } catch (error) {
    state.ui.status = "Error";
    showError(error.message);
  }

  render();
}

async function loadAvailability(options = {}) {
  if (!state.api || !dom.bookingAgent.value) {
    state.data.availability = null;
    return;
  }
  try {
    state.data.availability = await state.api.getAgentAvailability(dom.bookingAgent.value, { days: 5, limit: 8 });
  } catch (error) {
    state.data.availability = null;
    if (!options.silent) {
      throw error;
    }
  }
}

function syncFormOptions() {
  setOptions(dom.agentTemplate, state.data.templates, (item) => item.id, (item) => item.name);
  setOptions(dom.bookingAgent, state.data.agents, (item) => item.id, (item) => `${item.name} (${item.status})`);

  const liveAgents = state.data.agents.filter((agent) => agent.status === "published");
  setOptions(dom.callAgent, liveAgents.length ? liveAgents : state.data.agents, (item) => item.id, (item) => `${item.name} (${item.status})`);

  const phoneOptions = [{ id: "", label: "No explicit mapping" }, ...state.data.phoneNumbers.map((number) => ({ id: number.id, label: `${number.number} (${number.status})` }))];
  setOptions(dom.callPhoneNumber, phoneOptions, (item) => item.id, (item) => item.label);
}

function setOptions(select, items, valueFn, labelFn) {
  const current = select.value;
  select.innerHTML = items.length
    ? items.map((item) => `<option value="${escapeAttribute(valueFn(item))}">${escapeHtml(labelFn(item))}</option>`).join("")
    : '<option value="">No options available</option>';

  if (items.some((item) => valueFn(item) === current)) {
    select.value = current;
  }
}

async function handleAgentSubmit(event) {
  event.preventDefault();
  await runAction(async () => {
    const payload = {
      name: dom.agentName.value.trim(),
      template_id: dom.agentTemplate.value,
      timezone: dom.agentTimezone.value.trim(),
      default_language: dom.agentLanguage.value.trim(),
      business_hours: { mon_fri: [dom.agentHours.value.trim()] },
    };
    const created = await state.api.createAgent(payload);
    if (dom.agentPublish.checked) {
      await state.api.publishAgent(created.id);
    }
    await loadAllData();
    state.ui.activeTab = "agents";
    showSuccess(`Agent ${created.name} created${dom.agentPublish.checked ? " and published" : ""}.`);
  });
}

async function handleBookingSubmit(event) {
  event.preventDefault();
  await runAction(async () => {
    const payload = {
      agent_id: dom.bookingAgent.value,
      contact_name: dom.bookingName.value.trim(),
      contact_phone: dom.bookingPhone.value.trim(),
      service: dom.bookingService.value.trim(),
      start_at: new Date(dom.bookingStart.value).toISOString(),
    };
    const booking = await state.api.createBooking(payload);
    await loadAllData();
    state.ui.activeTab = "bookings";
    dom.bookingStart.value = buildDefaultBookingStart();
    showSuccess(`Booking ${booking.id} created for ${booking.contact_name}.`);
  });
}

async function handlePhoneSubmit(event) {
  event.preventDefault();
  await runAction(async () => {
    const payload = {
      provider: dom.phoneProvider.value.trim(),
      number: dom.phoneNumber.value.trim(),
      label: dom.phoneLabel.value.trim(),
      status: dom.phoneStatus.value,
      capabilities: { voice: true },
    };
    const record = await state.api.createPhoneNumber(payload);
    await loadAllData();
    state.ui.activeTab = "setup";
    showSuccess(`Phone number ${record.number} saved.`);
  });
}

async function handleIntegrationSubmit(event) {
  event.preventDefault();
  await runAction(async () => {
    const provider = dom.integrationProvider.value;
    const payload = {
      config: {
        calendar_id: dom.integrationReference.value.trim(),
      },
    };
    const record = await state.api.connectIntegration(provider, payload);
    await loadAllData();
    state.ui.activeTab = "setup";
    showSuccess(`Integration ${record.provider} connected.`);
  });
}

async function handleCallSimulation(event) {
  event.preventDefault();
  await runAction(async () => {
    const createdCall = await state.api.createCall({
      agent_id: dom.callAgent.value,
      phone_number_id: dom.callPhoneNumber.value || null,
      direction: "inbound",
      from_number: dom.callFromNumber.value.trim(),
      to_number: dom.callToNumber.value.trim(),
    });

    const turn = await state.api.respondToCall(createdCall.id, {
      input_text: dom.callInput.value.trim(),
      voice_id: dom.callVoice.value.trim(),
    });

    let finalCall = createdCall;
    let completed = false;
    if (dom.callAutoComplete.checked) {
      finalCall = await state.api.completeCall(createdCall.id, {
        outcome: dom.callOutcome.value,
        duration_ms: Number(dom.callDuration.value) * 1000,
        recording_available: Boolean(turn.response_audio_ref),
        summary_text: `Simulated from control plane: ${dom.callInput.value.trim()}`,
        structured_summary: {
          source: "control_plane",
          assistant_text: turn.assistant_text,
          tool_calls: turn.tool_calls,
        },
      });
      completed = true;
    }

    await loadAllData();
    await inspectCall(finalCall.id, { assistant_text: turn.assistant_text, response_audio_ref: turn.response_audio_ref });
    state.ui.activeTab = "calls";
    showSuccess(`Simulated call ${finalCall.id} ${completed ? "completed" : "responded"}.`);
  });
}

async function handleActionClick(event) {
  const target = event.target.closest("button");
  if (!target) {
    return;
  }

  if (target.dataset.navHref) {
    state.ui.activeTab = tabFromHref(target.dataset.navHref);
    render();
    return;
  }

  if (target.dataset.selectSlot) {
    dom.bookingStart.value = toDateTimeLocalValue(target.dataset.selectSlot);
    state.ui.activeTab = "bookings";
    render();
    showSuccess("Booking slot prefilled.");
    return;
  }

  if (target.dataset.publishAgent) {
    await runAction(async () => {
      await state.api.publishAgent(target.dataset.publishAgent);
      await loadAllData();
      state.ui.activeTab = "agents";
      showSuccess("Agent published.");
    });
    return;
  }

  if (target.dataset.inspectCall) {
    await inspectCall(target.dataset.inspectCall);
    state.ui.activeTab = "calls";
    render();
    return;
  }

  if (target.dataset.cancelBooking) {
    await runAction(async () => {
      await state.api.updateBooking(target.dataset.cancelBooking, { status: "cancelled" });
      await loadAllData();
      state.ui.activeTab = "bookings";
      showSuccess("Booking cancelled.");
    });
    return;
  }

  if (target.dataset.toggleNumber) {
    await runAction(async () => {
      await state.api.updatePhoneNumber(target.dataset.toggleNumber, { status: target.dataset.nextStatus });
      await loadAllData();
      state.ui.activeTab = "setup";
      showSuccess(`Phone number marked ${target.dataset.nextStatus}.`);
    });
    return;
  }

  if (target.dataset.testIntegration) {
    await runAction(async () => {
      const result = await state.api.testIntegration(target.dataset.testIntegration);
      await loadAllData();
      state.ui.activeTab = "setup";
      showSuccess(`Integration test: ${result.status}.`);
    });
  }
}

async function inspectCall(callId, workflow = null) {
  await runAction(async () => {
    const call = state.data.calls.find((item) => item.id === callId) || { id: callId, status: "active", outcome: null };
    const [transcript, summary] = await Promise.all([
      state.api.getCallTranscript(callId),
      state.api.getCallSummary(callId).catch(() => null),
    ]);
    state.data.selectedCall = { call, transcript, summary, workflow };
  }, { preserveBanner: true, preserveStatus: true });
}

async function runAction(action, options = {}) {
  if (!state.api) {
    showError("Connect API first.");
    return;
  }
  if (!options.preserveBanner) {
    hideBanners();
  }
  if (!options.preserveStatus) {
    state.ui.status = "Working";
    render();
  }
  try {
    await action();
  } catch (error) {
    showError(error.message);
  } finally {
    if (!options.preserveStatus) {
      state.ui.status = state.api ? "Live" : "Idle";
      render();
    }
  }
}

function restoreSession() {
  const savedApiBase = localStorage.getItem("voiceagent.apiBase");
  const savedApiKey = localStorage.getItem("voiceagent.apiKey");
  if (savedApiBase) {
    dom.apiBaseInput.value = savedApiBase;
  }
  if (savedApiKey) {
    dom.apiKeyInput.value = savedApiKey;
    connectAndLoad().catch((error) => showError(error.message));
  }
  dom.bookingStart.value = buildDefaultBookingStart();
}

function buildDefaultBookingStart() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(15, 0, 0, 0);
  return toDateTimeLocalValue(date.toISOString());
}

function toDateTimeLocalValue(value) {
  const date = new Date(value);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function tabFromHref(href) {
  if (href.includes("agents")) return "agents";
  if (href.includes("calls")) return "calls";
  if (href.includes("bookings")) return "bookings";
  if (href.includes("phone") || href.includes("integrations")) return "setup";
  return "overview";
}

function showError(message) {
  dom.errorBanner.textContent = message;
  dom.errorBanner.classList.remove("hidden");
}

function showSuccess(message) {
  dom.successBanner.textContent = message;
  dom.successBanner.classList.remove("hidden");
}

function hideBanners() {
  dom.errorBanner.classList.add("hidden");
  dom.successBanner.classList.add("hidden");
  dom.errorBanner.textContent = "";
  dom.successBanner.textContent = "";
}

function render() {
  renderApp(state, dom);
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "");
}
