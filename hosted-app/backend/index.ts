import { router, json, error, requireAuth, ai, db, ws, secrets } from "@appdeploy/sdk";

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

async function* registeredUsers() {
  let nextToken: string | undefined;
  for (let page = 0; page < 10; page++) {
    const result = await db.list<{ userId: string }>("mh_users", {
      limit: 100,
      ...(nextToken ? { nextToken } : {})
    });
    for (const user of result.items) yield user;
    if (!result.nextToken) return;
    nextToken = result.nextToken;
  }
}

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


const MICRO_HELPER_OWNER_ID = "t81TcaSyFEZzExHpNxCZ3u52TCs1";
const MICRO_HELPER_REPO = "dominixe2/springtrap-";
const MICRO_HELPER_BASE_BRANCH = "micro-helper";
const GITHUB_EDIT_PREFIXES = ["hosted-app/", "windows-companion/", "android-wrapper/", "cloud-relay/", "cloudflare/", "scripts/", "docs/"];
const GITHUB_ALLOWED_WORKFLOWS = ["hosted-app-checks.yml", "android-apk.yml", "windows-companion.yml"];

function safeRepoPath(path: string) {
  const normalized = String(path || "").replace(/^\/+/, "");
  if (!normalized || normalized.includes("..") || normalized.includes("\\") || normalized.startsWith(".github/") || !GITHUB_EDIT_PREFIXES.some(prefix => normalized.startsWith(prefix))) {
    throw new Error("Cesta souboru není v povolené oblasti repozitáře.");
  }
  return normalized;
}
function encodeBase64Utf8(value: string) {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}
function decodeBase64Utf8(value: string) {
  const binary = atob(value.replace(/\s/g, ""));
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
async function githubApi(path: string, init: RequestInit = {}) {
  const token = await secrets.readSecret("GITHUB_TOKEN");
  const response = await fetch("https://api.github.com" + path, {
    ...init,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + token,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...(init.headers || {})
    }
  });
  const raw = await response.text();
  if (!response.ok) throw new Error("GitHub API " + response.status + ": " + raw.slice(0, 700));
  return raw ? JSON.parse(raw) : {};
}
async function githubTokenReady() {
  try { return (await secrets.listSecretNames()).includes("GITHUB_TOKEN"); }
  catch { return false; }
}
async function runGitHubTaskAgent(userId: string, task: Task, state: State) {
  if (userId !== MICRO_HELPER_OWNER_ID || !(await githubTokenReady())) return null;
  let branchName = "";
  let changedFiles: string[] = [];
  let pullRequestUrl = "";
  let pullRequestNumber = 0;
  const toolList = [
    { name: "github_list_files", description: "List relevant source files in the connected Micro Helper repository. Only the configured repository is accessible.", parameters: { type: "object", properties: { path_prefix: { type: "string" }, ref: { type: "string" } }, required: [] } },
    { name: "github_read_file", description: "Read one source file from the configured repository. Only approved project folders are readable.", parameters: { type: "object", properties: { path: { type: "string" }, ref: { type: "string" } }, required: ["path"] } },
    { name: "github_create_branch", description: "Create a new isolated working branch from the production branch. Never write to the production branch.", parameters: { type: "object", properties: {}, required: [] } },
    { name: "github_update_file", description: "Commit a complete replacement for one approved project file on the agent working branch. Requires the current file SHA from github_read_file or github_list_files.", parameters: { type: "object", properties: { path: { type: "string" }, content: { type: "string" }, sha: { type: "string" }, message: { type: "string" } }, required: ["path", "content", "sha", "message"] } },
    { name: "github_open_pull_request", description: "Open a draft pull request from the agent branch to micro-helper. Never merge it.", parameters: { type: "object", properties: { title: { type: "string" }, body: { type: "string" } }, required: ["title", "body"] } },
    { name: "github_dispatch_checks", description: "Dispatch an allowlisted GitHub Actions validation or build workflow on the agent branch.", parameters: { type: "object", properties: { workflow: { type: "string", enum: GITHUB_ALLOWED_WORKFLOWS } }, required: ["workflow"] } },
    { name: "github_check_commit", description: "Read GitHub check-run status for a commit SHA. This does not change repository state.", parameters: { type: "object", properties: { sha: { type: "string" } }, required: ["sha"] } }
  ];
  const preferences = state.preferences.map(item => item.preference + ": " + item.value).join("\n").slice(0, 2500);
  const memories = state.memories.slice(-10).map(item => item.content).join("\n").slice(0, 1800);
  const result = await ai.run({
    system: "Jsi autonomní vývojový agent Micro Helperu. Pracuješ výhradně v repozitáři " + MICRO_HELPER_REPO + ". Pokud zadání vyžaduje změny kódu, nejprve prozkoumej relevantní soubory, vytvoř vlastní pracovní branch z micro-helper, proveď malé cílené změny, otevři draft pull request a spusť odpovídající ověřovací workflow. Nikdy neupravuj produkční branch micro-helper přímo, nikdy nemergeuj PR, nemaž repozitáře, soubory ani data a nikdy neměň GitHub Actions workflow, bezpečnostní konfiguraci, secrets nebo oprávnění. Neprováděj změny mimo povolené cesty. Neoznačuj práci za dokončenou, dokud nejsou změny a ověření skutečně potvrzené. Pokud chybí oprávnění nebo workflow není dostupné, přesně popiš blokaci. Pokud úkol není vývojový, odpověz běžným použitelným výsledkem bez změn repozitáře. Piš česky. Preference: " + (preferences || "neuvedeny") + ". Poznámky: " + (memories || "neuvedeny"),
    prompt: "Název úkolu: " + task.title + "\nZadání uživatele:\n" + task.input_text + "\n\nPracuj skutečnými nástroji, ne pouze plánem. Pokud provádíš změny, vytvoř draft PR a spusť kontroly. V závěru uveď konkrétní změněné soubory, branch, PR a stav kontrol. Neuváděj testy jako úspěšné, pokud to potvrzuje GitHub.",
    tools: toolList,
    maxSteps: 10,
    maxTokens: 2600,
    thinkingMode: "DEEP",
    onToolCall: async (name, args) => {
      if (name === "github_list_files") {
        const ref = String(args.ref || MICRO_HELPER_BASE_BRANCH).slice(0, 120);
        const tree = await githubApi("/repos/" + MICRO_HELPER_REPO + "/git/trees/" + encodeURIComponent(ref) + "?recursive=1");
        const prefix = String(args.path_prefix || "");
        return { truncated: Boolean(tree.truncated), files: (tree.tree || []).filter((item: any) => item.type === "blob" && GITHUB_EDIT_PREFIXES.some(p => String(item.path).startsWith(p)) && (!prefix || String(item.path).startsWith(prefix))).slice(0, 160).map((item: any) => ({ path: item.path, sha: item.sha, size: item.size })) };
      }
      if (name === "github_read_file") {
        const path = safeRepoPath(String(args.path || ""));
        const ref = String(args.ref || branchName || MICRO_HELPER_BASE_BRANCH).slice(0, 120);
        const file = await githubApi("/repos/" + MICRO_HELPER_REPO + "/contents/" + path.split("/").map(encodeURIComponent).join("/") + "?ref=" + encodeURIComponent(ref));
        if (file.encoding !== "base64" || typeof file.content !== "string") throw new Error("GitHub nevrátil textový obsah souboru.");
        return { path, sha: file.sha, content: decodeBase64Utf8(file.content).slice(0, 24000), truncated: Number(file.size || 0) > 24000 };
      }
      if (name === "github_create_branch") {
        if (branchName) return { branch: branchName, already_created: true };
        const base = await githubApi("/repos/" + MICRO_HELPER_REPO + "/git/ref/heads/" + MICRO_HELPER_BASE_BRANCH);
        branchName = "micro-helper/agent-" + task.id.replace(/-/g, "").slice(0, 12);
        try {
          await githubApi("/repos/" + MICRO_HELPER_REPO + "/git/refs", { method: "POST", body: JSON.stringify({ ref: "refs/heads/" + branchName, sha: base.object.sha }) });
        } catch (err) {
          if (!String(err).includes("422")) throw err;
          await githubApi("/repos/" + MICRO_HELPER_REPO + "/git/ref/heads/" + branchName);
        }
        return { branch: branchName, base: MICRO_HELPER_BASE_BRANCH, base_sha: base.object.sha };
      }
      if (name === "github_update_file") {
        if (!branchName || !branchName.startsWith("micro-helper/agent-")) throw new Error("Nejdřív vytvoř pracovní branch.");
        const path = safeRepoPath(String(args.path || ""));
        const content = String(args.content || "");
        const sha = String(args.sha || "");
        if (!sha || content.length > 90000) throw new Error("Chybí SHA souboru nebo je obsah příliš velký.");
        const message = String(args.message || "feat(micro-helper): implement task").slice(0, 120);
        const saved = await githubApi("/repos/" + MICRO_HELPER_REPO + "/contents/" + path.split("/").map(encodeURIComponent).join("/"), {
          method: "PUT",
          body: JSON.stringify({ message, content: encodeBase64Utf8(content), branch: branchName, sha })
        });
        if (!changedFiles.includes(path)) changedFiles.push(path);
        return { path, commit_sha: saved.commit?.sha, content_sha: saved.content?.sha, branch: branchName };
      }
      if (name === "github_open_pull_request") {
        if (!branchName || !changedFiles.length) throw new Error("Nelze otevřít PR bez změn na pracovní branch.");
        const pr = await githubApi("/repos/" + MICRO_HELPER_REPO + "/pulls", {
          method: "POST",
          body: JSON.stringify({
            title: String(args.title || "Micro Helper autonomous update").slice(0, 240),
            body: String(args.body || "Automaticky připravené změny Micro Helperu.").slice(0, 12000),
            head: branchName,
            base: MICRO_HELPER_BASE_BRANCH,
            draft: true
          })
        });
        pullRequestUrl = String(pr.html_url || "");
        pullRequestNumber = Number(pr.number || 0);
        return { number: pullRequestNumber, url: pullRequestUrl, draft: true, head_sha: pr.head?.sha, changed_files: changedFiles };
      }
      if (name === "github_dispatch_checks") {
        if (!branchName) throw new Error("Nejdřív vytvoř pracovní branch.");
        const workflow = String(args.workflow || "");
        if (!GITHUB_ALLOWED_WORKFLOWS.includes(workflow)) throw new Error("Workflow není povolen.");
        await githubApi("/repos/" + MICRO_HELPER_REPO + "/actions/workflows/" + encodeURIComponent(workflow) + "/dispatches", {
          method: "POST",
          body: JSON.stringify({ ref: branchName })
        });
        return { dispatched: true, workflow, branch: branchName };
      }
      if (name === "github_check_commit") {
        const commitSha = String(args.sha || "");
        if (!/^[0-9a-f]{40}$/i.test(commitSha)) throw new Error("Neplatné SHA commitu.");
        const checks = await githubApi("/repos/" + MICRO_HELPER_REPO + "/commits/" + commitSha + "/check-runs?per_page=50");
        const statuses = await githubApi("/repos/" + MICRO_HELPER_REPO + "/commits/" + commitSha + "/statuses");
        return {
          check_runs: (checks.check_runs || []).map((item: any) => ({ name: item.name, status: item.status, conclusion: item.conclusion, html_url: item.html_url })),
          statuses: (statuses || []).map((item: any) => ({ context: item.context, state: item.state, target_url: item.target_url }))
        };
      }
      throw new Error("Neznámý GitHub nástroj.");
    }
  });
  const output = String(result.text || "").trim();
  return { output, branch: branchName, changedFiles, pullRequestUrl, pullRequestNumber, steps: result.steps };
}

export const dailyReviewHandler = async (event: { type: "cron"; name: string; payload: Record<string, never>; scheduledTime: string }) => {
  for await (const entry of registeredUsers()) {
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
export const agentWorkerHandler = async (_event: { type: "cron"; name: string; payload: { userId?: string; taskId?: string }; scheduledTime: string }) => {
  let processed = 0;
  const maxPerTick = 5;
  const userEntries = _event.payload.userId
    ? [{ userId: _event.payload.userId }]
    : registeredUsers();
  for await (const entry of userEntries) {
    if (processed >= maxPerTick) break;
    const userId = entry.userId;
    const queueTable = jobsTableFor(userId);
    let queueCursor: string | undefined;
    let queuePages = 0;
    do {
      let page;
      try {
        page = await db.list<AgentJob>(queueTable, {
          limit: 20,
          ...(queueCursor ? { nextToken: queueCursor } : {})
        });
      } catch (err) {
        console.error("Micro Helper queue read failed", err);
        break;
      }
      for (const candidate of page.items) {
      if (processed >= maxPerTick) break;
      if (_event.payload.taskId && candidate.task_id !== _event.payload.taskId) continue;
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
        const repoExecution = await runGitHubTaskAgent(userId, task, state);
        const generated = repoExecution ? null : await ai.generate({
          system: "Jsi vykonavatel úkolů v Micro Helperu. Pokud nejsou dostupné skutečné nástroje, vytvoř pouze textový návrh a výslovně řekni, co nebylo provedeno. Nikdy netvrď, že jsi upravil repozitář, spustil testy nebo nasadil aplikaci bez ověření. Vrať konkrétní použitelný výsledek v češtině. Preference uživatele: " + (preferences || "neuvedeny") + "\\nPoznámky: " + (memories || "neuvedeny"),
          prompt: "Úkol: " + task.title + "\\nZadání: " + task.input_text + "\\nVrať výsledek včetně konkrétních kroků a kritérií ověření.",
          maxTokens: 1800,
          thinkingMode: "DEEP"
        });
        const output = String(repoExecution?.output || generated?.text || "").trim();
        if (!output) throw new Error("AI nevrátila žádný výsledek.");
        const latest = await readState(userId);
        const latestTask = latest.tasks.find(item => item.id === candidate.task_id);
        if (!latestTask || latestTask.status === "cancelled") {
          await db.delete(queueTable, [candidate.id]);
          continue;
        }
        // Repository changes are delivered as an unmerged draft PR. Never imply production completion.
        if (repoExecution?.pullRequestUrl) {
          latestTask.status = "needs_review";
          latestTask.result = (output + "\\n\\nDraft PR: " + repoExecution.pullRequestUrl + "\\nBranch: " + repoExecution.branch + "\\nZměněné soubory: " + repoExecution.changedFiles.join(", ") + "\\nPR nebyl sloučen ani nasazen.").slice(0, 12000);
          latestTask.error = "Změny jsou připravené v draft PR. Čekají na kontrolu a sloučení.";
        } else {
          latestTask.status = "needs_execution";
          latestTask.result = output.slice(0, 12000);
          latestTask.error = repoExecution?.changedFiles?.length
            ? "Změny existují na pracovní větvi, ale nebylo potvrzeno vytvoření pull requestu."
            : "Textový návrh je připraven. Skutečné změny v repozitáři ani ověřené testy nebyly provedeny.";
        }
        latestTask.completed_at = undefined;
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
      queueCursor = page.nextToken;
      queuePages++;
    } while (queueCursor && queuePages < 10 && processed < maxPerTick);
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
    await agentWorkerHandler({
      type: "cron",
      name: "on-demand-task",
      payload: { userId: user!.userId, taskId: task.id },
      scheduledTime: stamp()
    });
    const latest = await readState(user!.userId);
    return json(latest.tasks.find(item => item.id === task.id) || task, 201);
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
    await agentWorkerHandler({
      type: "cron",
      name: "on-demand-task",
      payload: { userId: user!.userId, taskId: task.id },
      scheduledTime: stamp()
    });
    const latest = await readState(user!.userId);
    return json(latest.tasks.find(item => item.id === task.id) || task);
  }],
  "POST /api/v1/tasks/:id/cancel": [requireAuth(), async ({ user, params }) => {
    const state = await readState(user!.userId), task = state.tasks.find(x => x.id === params.id);
    if (!task) return error("Úkol nebyl nalezen.", 404);
    task.status = "cancelled";
    await writeState(user!.userId, state);
    const queueTable = jobsTableFor(user!.userId);
    // Queue IDs may include a random suffix. Find the active record by task_id across bounded pages.
    let queueCursor: string | undefined;
    let queuePages = 0;
    let activeJob: AgentJob | undefined;
    while (!activeJob && queuePages < 10) {
      const page = await db.list<AgentJob>(queueTable, {
        limit: 20,
        ...(queueCursor ? { nextToken: queueCursor } : {})
      });
      activeJob = page.items.find(item =>
        item.task_id === task.id && (item.status === "queued" || item.status === "running")
      );
      queueCursor = page.nextToken;
      queuePages++;
      if (!queueCursor) break;
    }
    if (activeJob) {
      await db.tx.update(queueTable, [{
        id: activeJob.id,
        if: { status: activeJob.status },
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