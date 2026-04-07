const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
};

export class VoiceAgentApi {
  constructor({ apiBase, apiKey }) {
    this.apiBase = apiBase.replace(/\/$/, "");
    this.apiKey = apiKey;
  }

  async getDashboardOverview() {
    return this.request("/v1/dashboard/overview");
  }

  async listTemplates() {
    return this.request("/v1/templates");
  }

  async listAgents() {
    return this.request("/v1/agents?limit=50&offset=0");
  }

  async getAgentAvailability(agentId, query = {}) {
    const search = buildQueryString({
      days: query.days ?? 5,
      limit: query.limit ?? 8,
      slot_minutes: query.slotMinutes,
      start_at: query.startAt,
    });
    return this.request(`/v1/agents/${agentId}/availability${search}`);
  }

  async createAgent(payload) {
    return this.request("/v1/agents", {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async publishAgent(agentId) {
    return this.request(`/v1/agents/${agentId}/publish`, {
      method: "POST",
      body: JSON.stringify({ target_environment: "production" }),
      idempotent: true,
    });
  }

  async listCalls() {
    return this.request("/v1/calls?limit=50&offset=0");
  }

  async getCallTranscript(callId) {
    return this.request(`/v1/calls/${callId}/transcript`);
  }

  async getCallSummary(callId) {
    return this.request(`/v1/calls/${callId}/summary`);
  }

  async createCall(payload) {
    return this.request("/v1/calls", {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async respondToCall(callId, payload) {
    return this.request(`/v1/calls/${callId}/respond`, {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async completeCall(callId, payload) {
    return this.request(`/v1/calls/${callId}/complete`, {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async listBookings() {
    return this.request("/v1/bookings?limit=50&offset=0");
  }

  async createBooking(payload) {
    return this.request("/v1/bookings", {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async updateBooking(bookingId, payload) {
    return this.request(`/v1/bookings/${bookingId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async listPhoneNumbers() {
    return this.request("/v1/phone-numbers?limit=50&offset=0");
  }

  async createPhoneNumber(payload) {
    return this.request("/v1/phone-numbers", {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async updatePhoneNumber(numberId, payload) {
    return this.request(`/v1/phone-numbers/${numberId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async listIntegrations() {
    return this.request("/v1/integrations?limit=50&offset=0");
  }

  async connectIntegration(provider, payload) {
    return this.request(`/v1/integrations/${provider}/connect`, {
      method: "POST",
      body: JSON.stringify(payload),
      idempotent: true,
    });
  }

  async testIntegration(provider) {
    return this.request(`/v1/integrations/${provider}/test`, {
      method: "POST",
      body: JSON.stringify({}),
      idempotent: true,
    });
  }

  async request(path, options = {}) {
    const headers = {
      ...DEFAULT_HEADERS,
      Authorization: `Bearer ${this.apiKey}`,
      ...(options.headers || {}),
    };

    if (options.idempotent) {
      headers["Idempotency-Key"] = buildIdempotencyKey(path);
    }

    const response = await fetch(`${this.apiBase}${path}`, {
      method: options.method || "GET",
      headers,
      body: options.body,
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      throw new Error(resolveErrorMessage(payload));
    }

    return payload;
  }
}

function buildIdempotencyKey(path) {
  const suffix = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36);
  const normalized = path.replaceAll("/", "-").replaceAll("?", "-");
  return `web${normalized}-${suffix}`;
}

function buildQueryString(query) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

function resolveErrorMessage(payload) {
  if (typeof payload === "string") {
    return payload || "Request failed";
  }
  return payload?.error?.message || payload?.message || "Request failed";
}
