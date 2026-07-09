import { useEffect, useState } from "react";
import { api } from "./api.js";
import Workspace from "./Workspace.jsx";

function relativeTime(iso) {
  if (!iso) return "";
  const then = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  const mins = Math.max(0, Math.floor((Date.now() - then.getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return then.toISOString().slice(0, 10);
}

function groupProjects(projects) {
  // Buckets by last activity: Today / This week / Earlier, with archived
  // projects collapsed into their own group at the bottom. Projects arrive
  // sorted by last activity (backend), so group order falls out naturally.
  const now = Date.now();
  const DAY = 86400000;
  const groups = { Today: [], "This week": [], Earlier: [], Archived: [] };
  for (const p of projects) {
    if (p.archived) {
      groups.Archived.push(p);
      continue;
    }
    const iso = p.last_activity_at || p.created_at;
    const t = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").getTime();
    const age = now - t;
    if (age < DAY) groups.Today.push(p);
    else if (age < 7 * DAY) groups["This week"].push(p);
    else groups.Earlier.push(p);
  }
  return Object.entries(groups).filter(([, items]) => items.length > 0);
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [auth, setAuth] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [loginName, setLoginName] = useState("");

  const loadProjects = () =>
    api.listProjects().then(setProjects).catch((e) => setError(e.message));
  const loadAuth = () => api.authMe().then(setAuth).catch(() => {});

  useEffect(() => {
    loadProjects();
    loadAuth();
  }, []);

  async function handleLogin(e) {
    e.preventDefault();
    if (!loginName.trim()) return;
    try {
      await api.demoLogin(loginName.trim());
      setShowLogin(false);
      setLoginName("");
      await loadAuth();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleLogout() {
    try {
      await api.logout();
      await loadAuth();
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (projects.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !projects.some((p) => p.id === selectedId)) {
      setSelectedId(projects[0].id);
    }
  }, [projects, selectedId]);

  async function createProject(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const p = await api.createProject({ name: newName.trim() });
      setNewName("");
      setCreating(false);
      await loadProjects();
      setSelectedId(p.id);
    } catch (err) {
      setError(err.message);
    }
  }

  const selected = projects.find((p) => p.id === selectedId) || null;
  const normalizedFilter = filter.trim().toLowerCase();
  const visibleProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(normalizedFilter)
  );

  return (
    <div className="app">
      <header className="header">
        <h1>CCR Platform</h1>
        <span className="sub">
          Contextualized Construct Representations · theory-driven psychological text analysis
        </span>
        <span className="header-auth">
          {auth?.signed_in ? (
            <>
              <span className="small">Hi, {auth.name}</span>
              <button className="header-btn" onClick={handleLogout}>
                Sign out
              </button>
            </>
          ) : (
            <button className="header-btn" onClick={() => setShowLogin(true)}>
              Sign in
            </button>
          )}
        </span>
      </header>

      {showLogin && (
        <div className="modal-backdrop" onClick={() => setShowLogin(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Sign in</h3>
            <p className="hint">
              Signing in lifts the anonymous upload limits
              {auth?.limits?.max_rows
                ? ` (currently ${Math.round(auth.limits.max_bytes / 1048576)} MB / ${auth.limits.max_rows.toLocaleString()} rows per file)`
                : ""}
              .
            </p>
            <button className="ghost" disabled title="Arrives with lab accounts">
              Sign in with Google (coming soon)
            </button>
            <form onSubmit={handleLogin} className="mt">
              <label className="field">
                Your name (placeholder sign-in for now)
                <input
                  type="text"
                  autoFocus
                  value={loginName}
                  onChange={(e) => setLoginName(e.target.value)}
                  placeholder="e.g. Mohammad"
                />
              </label>
              <div className="row">
                <button className="primary" type="submit" disabled={!loginName.trim()}>
                  Continue
                </button>
                <button className="ghost" type="button" onClick={() => setShowLogin(false)}>
                  Cancel
                </button>
              </div>
            </form>
            <p className="small muted mt">
              This is a temporary placeholder so larger uploads can be tested. Real
              sign-in (Google + university account) arrives with lab accounts.
            </p>
          </div>
        </div>
      )}

      <div className="layout">
        <aside className="sidebar">
          <h2>
            Projects
            {projects.length > 0 && <span className="count">{projects.length}</span>}
          </h2>
          <input
            type="text"
            className="sidebar-filter"
            placeholder="Search projects..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="project-list">
            {groupProjects(visibleProjects).map(([groupLabel, items]) => (
              <div key={groupLabel}>
                <div className="group-label">{groupLabel}</div>
                {items.map((p) => (
                  <button
                    key={p.id}
                    className={"project-item" + (p.id === selectedId ? " active" : "")}
                    onClick={() => setSelectedId(p.id)}
                    title={p.name}
                  >
                    <span className="project-name">{p.name}</span>
                    <span className="date">
                      {p.n_runs > 0 ? `${p.n_runs} run${p.n_runs === 1 ? "" : "s"} · ` : ""}
                      {relativeTime(p.last_activity_at || p.created_at)}
                    </span>
                  </button>
                ))}
              </div>
            ))}
            {filter && visibleProjects.length === 0 && (
              <p className="small muted">No projects match "{filter}".</p>
            )}
          </div>

          <div className="project-create">
            {creating ? (
              <form onSubmit={createProject}>
                <input
                  type="text"
                  autoFocus
                  placeholder="Project name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
                <div className="row mt">
                  <button className="primary" type="submit">
                    Create
                  </button>
                  <button className="ghost" type="button" onClick={() => setCreating(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button className="ghost" onClick={() => setCreating(true)}>
                + New project
              </button>
            )}
          </div>
        </aside>

        <main className="main">
          {error && (
            <div className="error-banner" onClick={() => setError("")}>
              {error}
            </div>
          )}
          {selected ? (
            <Workspace
              key={selected.id}
              project={selected}
              auth={auth}
              onProjectChanged={loadProjects}
              onProjectDeleted={() => {
                setSelectedId(null);
                loadProjects();
              }}
            />
          ) : (
            <div className="card">
              <h3>Welcome</h3>
              <p className="hint">
                Create or select a project, upload a corpus (CSV/XLSX), choose a validated
                construct, and run a CCR analysis. Results include per-item loadings,
                score distributions, and a reproducibility record for every run.
              </p>
              <p className="small muted">
                Self-contained by design: embeddings run on this server itself - no
                third-party AI APIs. Demo instance: storage is ephemeral and may reset;
                please don&apos;t upload sensitive or identifiable data.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
