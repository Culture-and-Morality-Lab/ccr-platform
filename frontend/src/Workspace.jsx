import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import ResultsView from "./ResultsView.jsx";

export default function Workspace({ project, auth, onProjectChanged, onProjectDeleted }) {
  const [corpora, setCorpora] = useState([]);
  const [constructs, setConstructs] = useState([]);
  const [models, setModels] = useState([]);
  const [jobs, setJobs] = useState([]);

  const [corpusId, setCorpusId] = useState("");
  const [textColumn, setTextColumn] = useState("");
  const [constructId, setConstructId] = useState("");
  const [modelName, setModelName] = useState("");
  const [languages, setLanguages] = useState(["en"]);
  const [language, setLanguage] = useState("en");
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [showNewConstruct, setShowNewConstruct] = useState(false);
  const [viewJobId, setViewJobId] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteText, setDeleteText] = useState("");
  const fileRef = useRef(null);

  async function toggleArchive() {
    try {
      await api.patchProject(project.id, { archived: !project.archived });
      onProjectChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete() {
    try {
      await api.deleteProject(project.id);
      setConfirmDelete(false);
      onProjectDeleted?.();
    } catch (err) {
      setError(err.message);
    }
  }

  const refreshJobs = useCallback(
    () => api.listJobs(project.id).then(setJobs).catch(() => {}),
    [project.id]
  );

  useEffect(() => {
    api.listCorpora(project.id).then(setCorpora).catch((e) => setError(e.message));
    api.listConstructs().then(setConstructs).catch((e) => setError(e.message));
    api
      .models()
      .then((m) => {
        setModels(m);
        const def = m.find((x) => x.default) || m[0];
        if (def) setModelName(def.id);
      })
      .catch((e) => setError(e.message));
    api.languages().then(setLanguages).catch(() => {});
    refreshJobs();
  }, [project.id, refreshJobs]);

  // Poll while any job is active.
  const anyActive = jobs.some((j) => j.status === "queued" || j.status === "running");
  useEffect(() => {
    if (!anyActive) return undefined;
    const t = setInterval(refreshJobs, 1200);
    return () => clearInterval(t);
  }, [anyActive, refreshJobs]);

  const corpus = corpora.find((c) => c.id === corpusId) || null;
  const construct = constructs.find((c) => c.id === constructId) || null;

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const uploaded = await api.uploadCorpus(project.id, file);
      const list = await api.listCorpora(project.id);
      setCorpora(list);
      setCorpusId(uploaded.id);
      setTextColumn(uploaded.suggested_text_column || uploaded.columns[0]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleRun() {
    setRunning(true);
    setError("");
    try {
      await api.createJob({
        project_id: project.id,
        corpus_id: corpusId,
        construct_id: constructId,
        text_column: textColumn,
        model_name: modelName,
        language,
      });
      await refreshJobs();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  if (viewJobId) {
    return (
      <ResultsView
        jobId={viewJobId}
        onBack={() => {
          setViewJobId(null);
          refreshJobs();
        }}
      />
    );
  }

  const canRun = corpusId && textColumn && constructId && modelName && !running;

  return (
    <>
      {error && (
        <div className="error-banner" onClick={() => setError("")}>
          {error}
        </div>
      )}

      {/* Project header + actions */}
      <div className="project-header">
        <div>
          <span className="project-title">{project.name}</span>
          {project.archived && <span className="pill queued">archived</span>}
        </div>
        <div className="row">
          <button className="ghost" onClick={toggleArchive}>
            {project.archived ? "Unarchive" : "Archive"}
          </button>
          <button className="ghost danger" onClick={() => setConfirmDelete(true)}>
            Delete
          </button>
        </div>
      </div>

      {confirmDelete && (
        <div className="modal-backdrop" onClick={() => setConfirmDelete(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Delete "{project.name}"?</h3>
            <p className="hint">
              This permanently deletes {corpora.length} dataset{corpora.length === 1 ? "" : "s"},{" "}
              {jobs.length} run{jobs.length === 1 ? "" : "s"}, and all uploaded and result files.
              This cannot be undone. If you might need it later, use Archive instead.
            </p>
            <label className="field">
              Type the project name to confirm
              <input
                type="text"
                autoFocus
                value={deleteText}
                onChange={(e) => setDeleteText(e.target.value)}
                placeholder={project.name}
              />
            </label>
            <div className="row">
              <button
                className="primary danger-solid"
                disabled={deleteText !== project.name}
                onClick={handleDelete}
              >
                Delete permanently
              </button>
              <button
                className="ghost"
                onClick={() => {
                  setConfirmDelete(false);
                  setDeleteText("");
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 1 - corpus */}
      <div className="card">
        <h3>
          <span className="step-badge">1</span>Corpus
        </h3>
        <p className="hint">
          Upload a CSV or XLSX file, then choose the column containing the text to analyze.
          {auth && !auth.signed_in && auth.limits?.max_rows && (
            <>
              {" "}
              Anonymous limit: {Math.round(auth.limits.max_bytes / 1048576)} MB /{" "}
              {auth.limits.max_rows.toLocaleString()} rows per file; sign in (top right) for
              larger uploads.
            </>
          )}
        </p>
        <div className="row">
          <div className="grow">
            <label className="field">
              Upload file
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>
            {uploading && <span className="small muted">Uploading…</span>}
          </div>
          <div className="grow">
            <label className="field">
              Corpus
              <select value={corpusId} onChange={(e) => setCorpusId(e.target.value)}>
                <option value="">- select -</option>
                {corpora.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.filename} ({c.n_rows.toLocaleString()} rows)
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grow">
            <label className="field">
              Text column
              <select
                value={textColumn}
                onChange={(e) => setTextColumn(e.target.value)}
                disabled={!corpus}
              >
                <option value="">- select -</option>
                {corpus?.columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                    {col === corpus.suggested_text_column ? " (suggested)" : ""}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        {corpus?.parse_info?.note && (
          <p className="small muted">⚠ {corpus.parse_info.note}</p>
        )}
      </div>

      {/* Step 2 - construct */}
      <div className="card">
        <h3>
          <span className="step-badge">2</span>Construct
        </h3>
        <p className="hint">
          Pick a validated scale from the library, or define custom items. CCR scores each
          text by its similarity to these items.
        </p>
        <div className="construct-row">
          <div className="grow">
            <select value={constructId} onChange={(e) => setConstructId(e.target.value)}>
              <option value="">- select construct -</option>
              {constructs.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.items.length} items{c.is_seed ? ", library" : ", custom"})
                </option>
              ))}
            </select>
          </div>
          <button className="ghost" onClick={() => setShowNewConstruct((s) => !s)}>
            {showNewConstruct ? "Close" : "+ Custom construct"}
          </button>
        </div>

        {construct && (
          <>
            <ul className="construct-items">
              {construct.items.map((item, i) => (
                <li key={i}>
                  {item}
                  {construct.reverse_scored?.[i] ? " (reverse-scored)" : ""}
                </li>
              ))}
            </ul>
            {construct.reference && (
              <p className="small muted mt">Reference: {construct.reference}</p>
            )}
            {construct.verification_status !== "verified" && (
              <p className="small muted">
                ⚠ Item wording not yet verified verbatim against the original publication
                (status: {construct.verification_status.replace("_", " ")}).
              </p>
            )}
          </>
        )}

        {showNewConstruct && (
          <NewConstructForm
            onCreated={async (created) => {
              const list = await api.listConstructs();
              setConstructs(list);
              setConstructId(created.id);
              setShowNewConstruct(false);
            }}
            onError={setError}
          />
        )}
      </div>

      {/* Step 3 - language, model + run */}
      <div className="card">
        <h3>
          <span className="step-badge">3</span>Language, model &amp; run
        </h3>
        <p className="hint">
          Embeddings run locally via sentence-transformers; model and language are recorded
          in the run metadata. If the corpus doesn&apos;t match the selected language or the
          model doesn&apos;t support it, you&apos;ll get a warning - never a silent result.
        </p>
        <div className="run-settings">
          <label className="field language-control">
            Text language
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              {languages.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="field model-control">
            Embedding model
            <select value={modelName} onChange={(e) => setModelName(e.target.value)}>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <button className="primary run-button" disabled={!canRun} onClick={handleRun}>
            {running ? "Starting…" : "Run CCR analysis"}
          </button>
        </div>
        {models.find((m) => m.id === modelName)?.warnings?.map((w, i) => (
          <p key={i} className="small muted">
            ⚠ {w}
          </p>
        ))}
      </div>

      {/* Jobs */}
      {jobs.length > 0 && (
        <div className="card">
          <h3>Runs</h3>
          <div className="table-wrap">
            <table className="docs">
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Corpus</th>
                  <th>Construct</th>
                  <th style={{ width: "24%" }}>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td className="muted">
                      {(j.started_at || j.created_at).replace("T", " ").slice(0, 16)}
                    </td>
                    <td>{j.corpus_filename}</td>
                    <td>{j.construct_name}</td>
                    <td>
                      {j.status === "running" ? (
                        <div className="progress-track" title={`${Math.round(j.progress * 100)}%`}>
                          <div
                            className="progress-fill"
                            style={{ width: `${Math.max(3, j.progress * 100)}%` }}
                          />
                        </div>
                      ) : (
                        <span className={`pill ${j.status}`}>{j.status}</span>
                      )}
                      {j.status === "failed" && (
                        <div className="small muted" title={j.error}>
                          {j.error.split("\n").pop()}
                        </div>
                      )}
                    </td>
                    <td>
                      {j.status === "completed" && (
                        <button className="linkish" onClick={() => setViewJobId(j.id)}>
                          View results
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

function NewConstructForm({ onCreated, onError }) {
  const [name, setName] = useState("");
  const [reference, setReference] = useState("");
  const [itemsText, setItemsText] = useState("");
  const [saving, setSaving] = useState(false);

  async function save(e) {
    e.preventDefault();
    const items = itemsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!name.trim() || items.length === 0) {
      onError("A custom construct needs a name and at least one item (one per line).");
      return;
    }
    setSaving(true);
    try {
      const created = await api.createConstruct({ name: name.trim(), reference, items });
      onCreated(created);
    } catch (err) {
      onError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="mt">
      <div className="row">
        <div className="grow">
          <label className="field">
            Name
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
        </div>
        <div className="grow">
          <label className="field">
            Reference (publication, optional)
            <input
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          </label>
        </div>
      </div>
      <label className="field">
        Scale items - one per line, verbatim from the validated instrument
        <textarea rows={5} value={itemsText} onChange={(e) => setItemsText(e.target.value)} />
      </label>
      <button className="primary" type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save construct"}
      </button>
    </form>
  );
}
