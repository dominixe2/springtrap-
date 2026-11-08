import { router, json, error, requireAuth, ai, db, ws } from "@appdeploy/sdk";

type Memory = { id: number; content: string; category: string; created_at: string };
type Preference = { id: number; category: string; preference: string; value: string; source: string; updated_at: string };
type Plan = { id: string; title: string; objective: string; status: string; steps: string[]; sources: string[]; version: number; created_at: string; updated_at: string };
type Message = { id: number; role: "user" | "assistant"; content: string; created_at: string };
type Task = { id: string; title: string; input_text: string; kind: string; status: string; result?: string; error?: string; created_at: string; completed_at?: string; attempts?: number };
type Report = { id: string; created_at: string; summary: string; task_count: number; active_plan_count: number };
type Subscription = { connection_id: string; user_id: string; entity_type: string; entity_id: string; created_at: string };
type State = {
  profile: { agent_name: string; language: string; style: string };
  memories: Memory[];
  preferences: Preference[];
  messages: Message[];
  learningPlans: Plan[];
  tasks: Task[];
  reports: Report[];
  nextId: number;
};

const initialState = (): State => ({
  profile: { agent_name: "Micro Helper", language: "cs-CZ", style: "friendly" },
  memories: [], preferences: [], messages: [], learningPlans: [], tasks: [], reports: [], nextId: 1
});
const tableFor = (userId: string) => "mh_" + userId.replace(/[^A-Za-z0-9_-]/g, "");
const subscriptionsTableFor = (userId: string) => "mhs_" + userId.replace(/[^A-Za-z0-9_-]/g, "");
const jobsTableFor = (userId: string) => "mhq_" + userId.replace(/[^A-Za-z0-9_-]/g, "");
type AgentJob = { id: string; user_id: string; task_id: string; status: "queued" | "running" | "completed" | "failed" | "cancelled"; attempts: number; lease_until?: number; lease_token?: string; created_at: string; updated_at: string; error?: string };
const MAX_AGENT_ATTEMPTS = 3;
const AGENT_LEASE_MS = 4 * 60 * 1000;

async function notifySubscribers(userId: string) {
  const table = subscriptionsTableFor(userId);
  try {
    const subscriptions = await db.list<Subscription>(table, { limit: 100 });
    await Promise.all(subscriptions.items
      .filter(item => item.user_id === userId && item.entity_type === "user_state" && item.entity_id === userId)
      .map(async item => {
        try {
          const result = await ws.send([item.connection_id], {
            type: "entity.update",
            entity_type: "user_state",
            entity_id: userId,
            updated_at: stamp()
          });
          if (result.gone) await db.delete(table, [item.id]);
          else if (!result.ok) console.error("Micro Helper realtime delivery was not accepted", result.error);
        } catch (err) {
          console.error("Micro Helper realtime notification failed", err);
        }
      }));
  } catch (err) {
    console.error("Micro Helper subscription lookup failed", err);
  }
}
async function readState(userId: string): Promise<State> {
  const table = tableFor(userId);
  const userKey = "u_" + userId.replace(/[^A-Za-z0-9_-]/g, "");
  const [registered] = await db.get<{ userId: string }>("mh_users", [userKey]);
  if (!registered) await db.tx.add("mh_users", [{ id: userKey, userId }]);
  const [saved] = await db.get<{ state: State }>(table, ["state"]);
  if (saved?.state) {
    const state = saved.state;
    // Migrate only the retired default; preserve any name explicitly chosen by the user.
    if (state.profile?.agent_name === "Mykla") {
      state.profile = { ...state.profile, agent_name: "Micro Helper" };
      await writeState(userId, state);
    }
    return state;
  }
  await db.tx.add(table, [{ id: "state", state: initialState() }]);
  const [created] = await db.get<{ state: State }>(table, ["state"], { consistent: true });
  if (!created?.state) throw new Error("Nepodařilo se inicializovat uživatelská data.");
  return created.state;
}
async function writeState(userId: string, state: State) {
  const [updated] = await db.update(tableFor(userId), [{ id: "state", record: { state } }]);
  if (!updated) throw new Error("Nepodařilo se uložit data.");
  await notifySubscribers(userId);
}
const stamp = () => new Date().toISOString();
const bodyOf = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" ? value as Record<string, unknown> : {};

function learnExplicitPreference(state: State, message: string) {
  const match = message.match(/((?:preferuji|preferuju|mám rád(?:a)?|líbí se mi|nesnáším|nechci, aby)[ ]+[^.!?]{3,120})/i);
  if (!match) return;
  const value = match[0].trim().slice(0, 200);
  if (state.preferences.some(item => item.source === "automatic" && item.value.toLowerCase() === value.toLowerCase())) return;
  state.preferences.push({ id: state.nextId++, category: "learned", preference: "Výslovně uvedená preference", value, source: "automatic", updated_at: stamp() });
  state.preferences = state.preferences.slice(-100);
}

export const dailyReviewHandler = async (event: { type: "cron"; name: string; payload: Record<string, never>; scheduledTime: string }) => {
  const users = await db.list<{ userId: string }>("mh_users", { limit: 100 });
  for (const entry of users.items) {
    try {
      const state = await readState(entry.userId);
      const activePlans = state.learningPlans.filter(plan => plan.status === "active");
      const pendingTasks = state.tasks.filter(task => !["cancelled", "completed"].includes(task.status));
      const context = [
        "Aktivní plány:", ...activePlans.map(plan => `${plan.title}: ${plan.objective}; kroky: ${plan.steps.join("; ")}`),
        "Úkoly:", ...pendingTasks.map(task => `${task.title} (${task.status}): ${task.input_text}`),
        "Poslední konverzace:", ...state.messages.slice(-8).map(message => `${message.role}: ${message.content}`)
      ].join(" | ").slice(0, 9000);
      const generated = await ai.generate({
        system: "Jsi osobní asistent Micro Helper. V češtině vytvoř stručný denní přehled: co se posunulo, co čeká, případné překážky a jeden realistický další krok. Nic si nevymýšlej. Pokud nejsou data, řekni to.",
        prompt: context || "Uživatel zatím nemá žádné plány ani úkoly. Vytvoř krátký neutrální přehled.",
        maxTokens: 500,
        thinkingMode: "FAST"
      });
      state.reports = (state.reports || []).concat({ id: crypto.randomUUID(), created_at: stamp(), summary: String(generated.text || "Denní přehled se nepodařilo vytvořit."), task_count: pendingTasks.length, active_plan_count: activePlans.length }).slice(-30);
      await writeState(entry.userId, state);
    } catch (err) {
      console.error("Micro Helper daily review failed for a user", err);
    }
  }
  return { statusCode: 200 };
};


/**
 * Durable, bounded background worker. The app creates a database job and returns immediately.
 * This scheduled handler runs independently of browser/mobile sessions. A lease allows recovery
 * after a worker timeout or restart; only one invocation can claim a given queued/expired job.
 */
export const agentWorkerHandler = async (_event: { type: "cron"; name: string; payload: Record<string, never>; scheduledTime: string }) => {
  const users = await db.list<{ userId: string }>("mh_users", { limit: 100 });
  let processed = 0;
  const maxPerTick = 5;
  for (const entry of users.items) {
    if (processed >= maxPerTick) break;
    const userId = entry.userId;
    const queueTable = jobsTableFor(userId);
    let page;
    try {
      page = await db.list<AgentJob>(queueTable, { limit: 20 });
    } catch (err) {
      console.error("Micro Helper queue read failed", err);
      continue;
    }
    for (const candidate of page.items) {
      if (processed >= maxPerTick) break;
      const now = Date.now();
      if (candidate.status === "failed" || candidate.status === "completed" || candidate.status === "cancelled") {
        // Task history is stored in user state; prune terminal queue records to keep this table bounded.
        await db.delete(queueTable, [candidate.id]);
        continue;
      }
      const reclaimable = candidate.status === "running" && Number(candidate.lease_until || 0) < now;
      if (candidate.status !== "queued" && !reclaimable) continue;
      const token = crypto.randomUUID();
      const expected = candidate.status === "queued"
        ? { status: "queued" }
        : { status: "running", lease_until: candidate.lease_until };
      const [claimed] = await db.tx.update(queueTable, [{
        id: candidate.id,
        if: expected,
        record: {
          status: "running",
          lease_until: now + AGENT_LEASE_MS,
          lease_token: token,
          attempts: Number(candidate.attempts || 0) + 1,
          updated_at: stamp()
        }
      }], { patch: true });
      if (!claimed) continue;
      processed++;
      try {
        const state = await readState(userId);
        const task = state.tasks.find(item => item.id === candidate.task_id);
        if (!task || task.status === "cancelled") {
          await db.delete(queueTable, [candidate.id]);
          continue;
        }
        if (task.status === "completed" && task.result) {
          await db.delete(queueTable, [candidate.id]);
          continue;
        }
        task.status = "running";
        task.error = undefined;
        task.attempts = Number(candidate.attempts || 0) + 1;
        await writeState(userId, state);
        const preferences = state.preferences.map(item => item.preference + ": " + item.value).join("\\n").slice(0, 3500);
        const memories = state.memories.slice(-12).map(item => item.content).join("\\n").slice(0, 2500);
        const generated = await ai.generate({
          system: "Jsi vykonavatel úkolů v Micro Helperu. Pracuj po krocích, ale používej pouze skutečně dostupné nástroje. V této verzi smíš vytvořit kvalitní textový výstup, rozpad úkolu a ověřovací plán; nesmíš tvrdit, že jsi upravil repozitář, spustil testy nebo nasadil aplikaci. Vrať konkrétní použitelný výsledek v češtině. Preference uživatele: " + (preferences || "neuvedeny") + "\\nPoznámky: " + (memories || "neuvedeny"),
          prompt: "Úkol: " + task.title + "\\nZadání: " + task.input_text + "\\nVrať výsledek včetně konkrétních kroků a kritérií ověření.",
          maxTokens: 1800,
          thinkingMode: "DEEP"
        });
        const output = String(generated.text || "").trim();
        if (!output) throw new Error("AI nevrátila žádný výsledek.");
        const latest = await readState(userId);
        const latestTask = latest.tasks.find(item => item.id === candidate.task_id);
        if (!latestTask || latestTask.status === "cancelled") {
          await db.delete(queueTable, [candidate.id]);
          continue;
        }
        latestTask.status = "completed";
        latestTask.result = output.slice(0, 12000);
        latestTask.error = undefined;
        latestTask.completed_at = stamp();
        await writeState(userId, latest);
        await db.delete(queueTable, [candidate.id]);
      } catch (err) {
        console.error("Micro Helper background task failed", err);
        const attempts = Number(candidate.attempts || 0) + 1;
        const retry = attempts < MAX_AGENT_ATTEMPTS;
        try {
          const state = await readState(userId);
          const task = state.tasks.find(item => item.id === candidate.task_id);
          if (task && task.status !== "cancelled") {
            task.status = retry ? "queued" : "error";
            task.error = retry ? "Dočasná chyba. Úkol bude automaticky zkusen znovu." : "Úkol se nepodařilo dokončit po třech pokusech.";
            await writeState(userId, state);
          }
          if (retry) {
            await db.tx.update(queueTable, [{
              id: candidate.id,
              if: { status: "running", lease_token: token },
              record: {
                status: "queued",
                attempts,
                error: String(err).slice(0, 500),
                updated_at: stamp(),
                lease_until: undefined,
                lease_token: undefined
              }
            }], { patch: true });
          } else {
            await db.delete(queueTable, [candidate.id]);
          }
        } catch (recoveryError) {
          console.error("Micro Helper job recovery checkpoint failed", recoveryError);
        }
      }
    }
  }
  return { statusCode: 200, processed };
};

export const handler = router({
  "POST /api/subscriptions": [requireAuth(), async ({ user, body }) => {
    const data = bodyOf(body);
    const connectionId = String(data.connection_id || "").trim();
    const entityType = String(data.entity_type || "");
    const entityId = String(data.entity_id || "");
    if (connectionId.length < 8 || connectionId.length > 200) return error("Neplatné realtime spojení.", 422);
    if (entityType !== "user_state" || entityId !== user!.userId) return error("K tomuto synchronizačnímu kanálu nemáš přístup.", 403);
    const id = connectionId.replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 120);
    const table = subscriptionsTableFor(user!.userId);
    const [saved] = await db.update(table, [{
      id,
      record: {
        connection_id: connectionId,
        user_id: user!.userId,
        entity_type: entityType,
        entity_id: entityId,
        created_at: stamp()
      }
    }]);
    if (!saved) return error("Realtime spojení se nepodařilo zaregistrovat.", 503);
    return json({ subscribed: true, entity_type: entityType, entity_id: entityId });
  }],
  "DELETE /api/subscriptions": [requireAuth(), async ({ user, body }) => {
    const data = bodyOf(body);
    const connectionId = String(data.connection_id || "").trim();
    if (connectionId.length < 8 || connectionId.length > 200) return error("Neplatné realtime spojení.", 422);
    const id = connectionId.replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 120);
    const [deleted] = await db.delete(subscriptionsTableFor(user!.userId), [id]);
    return json({ unsubscribed: Boolean(deleted) });
  }],
  "GET /api/v1/status": [requireAuth(), async ({ user }) => json({
    product: "Micro Helper", mode: "cloud-ai", authenticated: true,
    storage: "private-per-user-cloud", userId: user!.userId
  })],
  "GET /api/v1/profile": [requireAuth(), async ({ user }) => json((await readState(user!.userId)).profile)],
  "PUT /api/v1/profile": [requireAuth(), async ({ user, body }) => {
    const state = await readState(user!.userId);
    const data = bodyOf(body);
    const name = String(data.agent_name || "Micro Helper").trim().slice(0, 30) || "Micro Helper";
    state.profile = { ...state.profile, agent_name: name, language: "cs-CZ" };
    await writeState(user!.userId, state);
    return json(state.profile);
  }],
  "GET /api/v1/memories": [requireAuth(), async ({ user }) => json({ memories: [...(await readState(user!.userId)).memories].reverse() })],
  "POST /api/v1/memories": [requireAuth(), async ({ user, body }) => {
    const state = await readState(user!.userId);
    const data = bodyOf(body);
    const content = String(data.content || "").trim();
    if (!content) return error("Poznámka nesmí být prázdná.", 422);
    const item: Memory = { id: state.nextId++, content: content.slice(0, 4000), category: String(data.category || "preference"), created_at: stamp() };
    state.memories.push(item); state.memories = state.memories.slice(-200);
    await writeState(user!.userId, state);
    return json(item, 201);
  }],
  "PUT /api/v1/memories/:id": [requireAuth(), async ({ user, params, body }) => {
    const state = await readState(user!.userId);
    const item = state.memories.find(x => x.id === Number(params.id));
    if (!item) return error("Poznámka nenalezena.", 404);
    const data = bodyOf(body), content = String(data.content || "").trim();
    if (!content) return error("Poznámka nesmí být prázdná.", 422);
    item.content = content.slice(0, 4000); item.category = String(data.category || item.category);
    await writeState(user!.userId, state); return json(item);
  }],
  "DELETE /api/v1/memories/:id": [requireAuth(), async ({ user, params }) => {
    const state = await readState(user!.userId);
    state.memories = state.memories.filter(x => x.id !== Number(params.id));
    await writeState(user!.userId, state); return json({ deleted: true });
  }],
  "GET /api/v1/preferences": [requireAuth(), async ({ user }) => json({ preferences: (await readState(user!.userId)).preferences })],
  "POST /api/v1/preferences": [requireAuth(), async ({ user, body }) => {
    const state = await readState(user!.userId), data = bodyOf(body);
    const category = String(data.category || "other"), preference = String(data.preference || "").trim(), value = String(data.value || "").trim();
    if (!preference || !value) return error("Preference nesmí být prázdná.", 422);
    let item = state.preferences.find(x => x.category === category && x.preference === preference);
    if (item) { item.value = value.slice(0, 2000); item.updated_at = stamp(); }
    else {
      item = { id: state.nextId++, category, preference: preference.slice(0, 100), value: value.slice(0, 2000), source: "user", updated_at: stamp() };
      state.preferences.push(item);
    }
    state.preferences = state.preferences.slice(-100);
    await writeState(user!.userId, state); return json(item, 201);
  }],
  "DELETE /api/v1/preferences/:id": [requireAuth(), async ({ user, params }) => {
    const state = await readState(user!.userId);
    state.preferences = state.preferences.filter(x => x.id !== Number(params.id));
    await writeState(user!.userId, state); return json({ deleted: true });
  }],
  "GET /api/v1/conversations": [requireAuth(), async ({ user }) => json({ messages: (await readState(user!.userId)).messages })],
  "DELETE /api/v1/conversations": [requireAuth(), async ({ user }) => {
    const state = await readState(user!.userId); state.messages = [];
    await writeState(user!.userId, state); return json({ deleted: true });
  }],
  "POST /api/v1/chat": [requireAuth(), async ({ user, body }) => {
    const data = bodyOf(body), message = String(data.message || "").trim();
    if (!message) return error("Zpráva je prázdná.", 422);
    const state = await readState(user!.userId);
    learnExplicitPreference(state, message);
    const historyInput = Array.isArray(data.history) ? data.history : [];
    const history = historyInput.slice(-12).flatMap(entry => {
      const item = bodyOf(entry);
      const role = item.role === "assistant" ? "assistant" : item.role === "user" ? "user" : null;
      const content = typeof item.content === "string" ? item.content.slice(0, 4000) : "";
      return role && content ? [{ role, content }] : [];
    });
    const memoryContext = [
      ...state.preferences.map(x => x.preference + ": " + x.value),
      ...state.memories.slice(-20).map(x => x.content)
    ].join("\n").slice(0, 7000);
    const system = "Jsi " + state.profile.agent_name + ", osobní AI pomocník uživatele. Odpovídej česky, přirozeně, prakticky a přátelsky. Respektuj uživatelovy preference. Nepředstírej, že něco provádíš na pozadí nebo že máš přístup k zařízení, pokud to není výslovně dostupné. Uložené preference a poznámky uživatele:\n" + (memoryContext || "Zatím žádné.");
    const thinkingMode = data.thinkingMode === "DEEP" ? "DEEP" : "FAST";
    try {
      const result = await ai.generate({ system, messages: [...history, { role: "user", content: message }], maxTokens: thinkingMode === "DEEP" ? 1400 : 800, thinkingMode });
      const reply = String(result.text || "").trim();
      if (!reply) return error("AI nevrátila odpověď. Zkus to znovu.", 503);
      state.messages.push(
        { id: state.nextId++, role: "user", content: message.slice(0, 4000), created_at: stamp() },
        { id: state.nextId++, role: "assistant", content: reply.slice(0, 12000), created_at: stamp() }
      );
      state.messages = state.messages.slice(-100);
      await writeState(user!.userId, state);
      return json({ reply, mode: "cloud-ai" });
    } catch (err) {
      console.error("Micro Helper AI request failed", err);
      return error("AI služba je právě nedostupná nebo je vyčerpaný její limit. Zkus to později.", 503);
    }
  }],
  "GET /api/v1/learning/plans": [requireAuth(), async ({ user }) => json({ plans: [...(await readState(user!.userId)).learningPlans].sort((a, b) => b.updated_at.localeCompare(a.updated_at)) })],
  "POST /api/v1/learning/plans": [requireAuth(), async ({ user, body }) => {
    const state = await readState(user!.userId), data = bodyOf(body);
    const title = String(data.title || "").trim(), objective = String(data.objective || "").trim(), status = String(data.status || "draft");
    const steps = Array.isArray(data.steps) ? data.steps.map(String).slice(0, 40) : [];
    const sources = Array.isArray(data.sources) ? data.sources.map(String).slice(0, 40) : [];
    if (!title || title.length > 120 || !objective || objective.length > 4000 || !["draft", "active", "paused"].includes(status)) return error("Neplatný učební plán.", 422);
    const plan: Plan = { id: crypto.randomUUID(), title, objective, status, steps, sources, version: 1, created_at: stamp(), updated_at: stamp() };
    state.learningPlans.push(plan); state.learningPlans = state.learningPlans.slice(-50);
    await writeState(user!.userId, state); return json(plan, 201);
  }],
  "PUT /api/v1/learning/plans/:id": [requireAuth(), async ({ user, params, body }) => {
    const state = await readState(user!.userId), plan = state.learningPlans.find(x => x.id === params.id);
    if (!plan) return error("Učební plán nebyl nalezen.", 404);
    const data = bodyOf(body), title = String(data.title || "").trim(), objective = String(data.objective || "").trim(), status = String(data.status || "draft");
    if (!title || title.length > 120 || !objective || objective.length > 4000 || !["draft", "active", "paused"].includes(status)) return error("Neplatný učební plán.", 422);
    plan.title = title; plan.objective = objective; plan.status = status;
    plan.steps = Array.isArray(data.steps) ? data.steps.map(String).slice(0, 40) : [];
    plan.sources = Array.isArray(data.sources) ? data.sources.map(String).slice(0, 40) : [];
    plan.version++; plan.updated_at = stamp();
    await writeState(user!.userId, state); return json(plan);
  }],
  "DELETE /api/v1/learning/plans/:id": [requireAuth(), async ({ user, params }) => {
    const state = await readState(user!.userId), before = state.learningPlans.length;
    state.learningPlans = state.learningPlans.filter(x => x.id !== params.id);
    await writeState(user!.userId, state);
    return before === state.learningPlans.length ? error("Učební plán nebyl nalezen.", 404) : json({ deleted: true });
  }],
  "GET /api/v1/reports": [requireAuth(), async ({ user }) => json({ reports: [...((await readState(user!.userId)).reports || [])].reverse() })],
  "GET /api/v1/tasks": [requireAuth(), async ({ user, query }) => {
    const state = await readState(user!.userId);
    const limit = Math.min(50, Math.max(1, Number(query.limit || 30)));
    return json({ tasks: [...state.tasks].reverse().slice(0, limit) });
  }],
  "POST /api/v1/tasks": [requireAuth(), async ({ user, body }) => {
    const state = await readState(user!.userId), data = bodyOf(body);
    const title = String(data.title || "").trim(), input_text = String(data.input_text || "").trim();
    if (!title || title.length > 120 || !input_text || input_text.length > 4000) return error("Úkol potřebuje název do 120 znaků a zadání do 4000 znaků.", 422);
    const task: Task = { id: crypto.randomUUID(), title, input_text, kind: String(data.kind || "agent.draft"), status: "queued", created_at: stamp(), attempts: 0 };
    const queueTable = jobsTableFor(user!.userId);
    const [jobId] = await db.tx.add(queueTable, [{
      id: task.id,
      user_id: user!.userId,
      task_id: task.id,
      status: "queued",
      attempts: 0,
      created_at: stamp(),
      updated_at: stamp()
    }]);
    if (!jobId) return error("Úkol se nepodařilo bezpečně zařadit do fronty.", 503);
    state.tasks.push(task); state.tasks = state.tasks.slice(-50);
    try {
      await writeState(user!.userId, state);
    } catch (err) {
      await db.tx.update(queueTable, [{ id: task.id, if: { status: "queued" }, record: { status: "failed", error: "Task state save failed", updated_at: stamp() } }], { patch: true });
      throw err;
    }
    return json(task, 201);
  }],
  "POST /api/v1/tasks/:id/run": [requireAuth(), async ({ user, params }) => {
    const state = await readState(user!.userId);
    const task = state.tasks.find(item => item.id === params.id);
    if (!task) return error("Úkol nebyl nalezen.", 404);
    if (task.status === "running" || task.status === "queued") return json({ ...task, queued: true });
    if (task.status === "cancelled") return error("Zrušený úkol nelze spustit.", 409);
    if (task.status === "completed" && task.result) return json(task);
    const queueTable = jobsTableFor(user!.userId);
    const [jobId] = await db.tx.add(queueTable, [{
      id: task.id + "_" + crypto.randomUUID().slice(0, 8),
      user_id: user!.userId,
      task_id: task.id,
      status: "queued",
      attempts: 0,
      created_at: stamp(),
      updated_at: stamp()
    }]);
    if (!jobId) return error("Úkol se nepodařilo zařadit do fronty.", 503);
    task.status = "queued"; task.error = undefined; task.attempts = 0;
    await writeState(user!.userId, state);
    return json({ ...task, queued: true });
  }],
  "POST /api/v1/tasks/:id/cancel": [requireAuth(), async ({ user, params }) => {
    const state = await readState(user!.userId), task = state.tasks.find(x => x.id === params.id);
    if (!task) return error("Úkol nebyl nalezen.", 404);
    task.status = "cancelled";
    await writeState(user!.userId, state);
    const queueTable = jobsTableFor(user!.userId);
    // Queue IDs include a random suffix, so locate by task_id rather than assuming task.id is the queue record ID.
    const queuedJobs = await db.list<AgentJob>(queueTable, { limit: 20 });
    const job = queuedJobs.items.find(item => item.task_id === task.id);
    if (job && (job.status === "queued" || job.status === "running")) {
      await db.tx.update(queueTable, [{
        id: job.id,
        if: { status: job.status },
        record: { status: "cancelled", updated_at: stamp(), lease_until: undefined, lease_token: undefined }
      }], { patch: true });
    }
    return json({ cancelled: true });
  }],
  "POST /api/v1/images/generate": [requireAuth(), async ({ body }) => {
    const data = bodyOf(body);
    const prompt = String(data.prompt || "").trim();
    const images = Array.isArray(data.images) ? data.images.slice(0, 5).flatMap(item => {
      const image = bodyOf(item);
      const encoded = typeof image.data === "string" ? image.data : "";
      const mimeType = String(image.mimeType || "");
      if (!encoded || !["image/jpeg", "image/png", "image/webp"].includes(mimeType)) return [];
      return [{ data: encoded, mimeType }];
    }) : [];
    const decodedBytes = images.reduce((sum, item) => sum + Math.floor(item.data.length * 3 / 4), 0);
    if (!prompt || prompt.length > 4000) return error("Popis obrázku musí mít 1 až 4000 znaků.", 422);
    if (images.length !== (Array.isArray(data.images) ? data.images.length : 0) || decodedBytes > 6 * 1024 * 1024) {
      return error("Obrázek není platný nebo překračuje limit 6 MB. Zmenši ho a zkus to znovu.", 422);
    }
    try {
      const result = await ai.imageGen({ prompt, images, maxOutputBytes: 1000000 });
      return json({ image: result.image, mode: "cloud-ai" });
    } catch (err) {
      console.error("Micro Helper image generation failed", err);
      return error("Generování obrázku se nezdařilo. Zkontroluj dostupný AI limit a zkus to znovu.", 503);
    }
  }],
  "POST /api/v1/images/analyze": [requireAuth(), async ({ body }) => {
    const data = bodyOf(body), image = bodyOf(data.image);
    const encoded = typeof image.data === "string" ? image.data : "";
    const mimeType = String(image.mimeType || "");
    if (!encoded || !["image/jpeg", "image/png", "image/webp"].includes(mimeType) || Math.floor(encoded.length * 3 / 4) > 6 * 1024 * 1024) {
      return error("Nahraj platný obrázek do 6 MB.", 422);
    }
    const prompt = String(data.prompt || "Podrobně popiš, co je na obrázku, a upozorni na důležité detaily.").trim().slice(0, 2000);
    try {
      const result = await ai.generate({
        system: "Jsi vizuální asistent Micro Helper. Obrázek pečlivě analyzuj, odděluj jistá pozorování od odhadů a česky odpověz prakticky.",
        prompt,
        images: [{ data: encoded, mimeType }],
        maxTokens: 1200,
        thinkingMode: "DEEP"
      });
      return json({ text: String(result.text || "").trim(), mode: "cloud-ai" });
    } catch (err) {
      console.error("Micro Helper image analysis failed", err);
      return error("Analýza obrázku se nezdařila. Zkus to znovu.", 503);
    }
  }],
  "POST /api/v1/images/ocr": [requireAuth(), async ({ body }) => {
    const data = bodyOf(body), image = bodyOf(data.image);
    const encoded = typeof image.data === "string" ? image.data : "";
    const mimeType = String(image.mimeType || "");
    if (!encoded || !["image/jpeg", "image/png", "image/webp"].includes(mimeType) || Math.floor(encoded.length * 3 / 4) > 6 * 1024 * 1024) {
      return error("Nahraj platný obrázek do 6 MB.", 422);
    }
    try {
      const result = await ai.ocr({
        images: [{ data: encoded, mimeType }],
        prompt: String(data.prompt || "Přepiš veškerý čitelný text z obrázku a zachovej jeho strukturu.").slice(0, 1000),
        maxTokens: 3000,
        thinkingMode: "FAST"
      });
      return json({ text: String(result.text || ""), mode: "cloud-ai" });
    } catch (err) {
      console.error("Micro Helper image OCR failed", err);
      return error("Rozpoznání textu z obrázku se nezdařilo. Zkus to znovu.", 503);
    }
  }],
  "POST /api/v1/search": [requireAuth(), async ({ body }) => {
    const data = bodyOf(body);
    const query = String(data.query || "").trim();
    if (query.length < 2 || query.length > 240) return error("Zadej hledaný výraz o délce 2 až 240 znaků.", 422);
    try {
      const searchUrl = "https://html.duckduckgo.com/html/?q=" + encodeURIComponent(query);
      const scraped = await ai.scrape({ url: searchUrl });
      if (scraped.status >= 400 || !String(scraped.text || "").trim()) return error("Vyhledávač teď nevrátil výsledky. Zkus to za chvíli znovu.", 502);
      const sourceText = String(scraped.text).slice(0, 16000);
      const matches = [...sourceText.matchAll(/\[([^\]]{2,180})\]\((https?:\/\/[^)\s]+)\)/g)];
      const seen = new Set<string>();
      let results = matches.flatMap(match => {
        try {
          let url = new URL(match[2]);
          const redirected = url.searchParams.get("uddg");
          if (redirected) url = new URL(redirected);
          if (!["http:", "https:"].includes(url.protocol) || seen.has(url.href)) return [];
          seen.add(url.href);
          return [{ title: match[1].replace(/<[^>]*>/g, "").slice(0, 180), url: url.href }];
        } catch { return []; }
      }).slice(0, 8);
      if (!results.length) {
        const plainUrls = [...sourceText.matchAll(/https?:\/\/[^\s<>"')\]]+/g)];
        results = plainUrls.flatMap(match => {
          try {
            let url = new URL(match[0].replace(/[.,;]+$/, ""));
            const redirected = url.searchParams.get("uddg");
            if (redirected) url = new URL(redirected);
            if (!["http:", "https:"].includes(url.protocol) || seen.has(url.href)) return [];
            seen.add(url.href);
            return [{ title: url.hostname, url: url.href }];
          } catch { return []; }
        }).slice(0, 8);
      }
      const summaryResult = await ai.generate({
        system: "Jsi rešeršní asistent. Shrň pouze informace obsažené ve vstupních výsledcích. Nevymýšlej fakta, datum ani zdroje. Pokud jsou výsledky neúplné, výslovně to řekni. Piš česky, stručně a přehledně.",
        prompt: "Vyhledávací dotaz: " + query + "\n\nVýsledky vyhledávání:\n" + sourceText,
        maxTokens: 700,
        thinkingMode: "FAST"
      });
      return json({ query, summary: String(summaryResult.text || "Výsledky se podařilo načíst, ale shrnutí není dostupné."), results, source: "DuckDuckGo", searched_at: stamp() });
    } catch (err) {
      console.error("Micro Helper web search failed", err);
      return error("Webové vyhledávání je momentálně nedostupné. Zkus to znovu.", 503);
    }
  }],
  "GET /api/v1/models": [requireAuth(), async () => json({ available: false, models: [], note: "Ollama běží pouze na tvém vlastním zařízení. Cloud AI je dostupná přes chat." })]
});