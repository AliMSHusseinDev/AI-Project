import { useState, useRef, useEffect, lazy, Suspense } from "react";
import {
  Network,
  Map,
  ChartNoAxesCombined,
  RadioTower,
  ScanLine,
  Timer,
  Workflow,
  Layers3,
  MapPinned,
  Download,
  FolderOpen,
  Play,
  ShieldCheck,
  Activity,
  ChevronDown,
  Focus,
} from "lucide-react";
import TerrainCanvas from "./TerrainCanvas";
import { Controls, NumberField } from "./Controls";
const Results = lazy(() =>
  import("./Results").then((module) => ({ default: module.Results })),
);
import {
  api,
  legal,
  baseRect,
  legalBase,
  terrainStats,
  BASE_ID,
  saveFile,
  type Point,
  type Env,
  type Result,
  type Audit,
  type Layers,
  type Limits,
} from "./types";

const initial: Env = {
  size: 40,
  base: [20, 20],
  base_margin: 0,
  sensing: 5.5,
  communication: 8,
  spacing: 2,
  seed: 42,
  obstacles: [],
  monitoring_mode: "automatic",
  manual_points: [],
};
const legend = [
  ["covered", "Covered point"],
  ["hole", "Coverage hole"],
  ["sensor", "Sensor"],
  ["offline", "Disconnected sensor"],
  ["base", "Base station"],
  ["obstacle", "Obstacle"],
  ["link", "Valid link"],
  ["blue", "Communication radius"],
  ["pink", "Sensing radius"],
];
const paths = ["Environment", "Results"] as const;
type Page = (typeof paths)[number];
const settingsDefault = {
  seed: 7,
  budget: 600,
  population: 18,
  generations: 40,
  local_fraction: 0.45,
};
export default function App() {
  const [page, setPage] = useState<Page>("Environment"),
    [env, setEnv] = useState(initial),
    [manual, setManual] = useState(false),
    [count, setCount] = useState(4);
  const [limits, setLimits] = useState<Limits>({
      area_per_obstacle: 150,
      blocked_percent: 15,
      max_side: 12,
    }),
    [online, setOnline] = useState(false);
  const [selected, select] = useState<string | null>(null),
    [layers, setLayers] = useState<Layers>({
      points: true,
      holes: true,
      links: true,
      sensing: true,
      communication: true,
    });
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null);
  const [tool, setTool] = useState<"point" | "obstacle" | null>(null);
  const [showLayers, setShowLayers] = useState(false),
    [notice, setNotice] = useState("");
  const [before, setBefore] = useState<Env[]>([]),
    [after, setAfter] = useState<Env[]>([]);
  const [busy, setBusy] = useState(false),
    [generating, setGenerating] = useState(false),
    [job, setJob] = useState(""),
    [progress, setProgress] = useState({ label: "", percent: 0 });
  const [mode, setMode] = useState("Comparison"),
    [settings, setSettings] = useState(settingsDefault);
  const [results, setResults] = useState<Result[]>([]),
    [index, setIndex] = useState(0),
    [audits, setAudits] = useState<Audit[]>([]);
  const [format, setFormat] = useState("csv");
  const [preview, setPreview] = useState<Env | null>(null);
  const file = useRef<HTMLInputElement>(null),
    version = useRef(0),
    active = useRef(""),
    cancelRequested = useRef(false),
    editing = useRef(false);
  const cursor = useRef<HTMLOutputElement>(null);
  const result = results[index];
  function clearResults() {
    version.current++;
    setJob("");
    setResults([]);
    setAudits([]);
    setIndex(0);
  }
  function apply(next: Env) {
    setEnv(next);
    setSelectedPoint(null);
    setPreview(null);
    setCount(next.obstacles.length);
    select((id) =>
      id === BASE_ID || next.obstacles.some((r) => r.id === id) ? id : null,
    );
    clearResults();
  }
  function change(next: Env) {
    if (busy || JSON.stringify(next) === JSON.stringify(env)) return;
    const max = Math.floor(next.size ** 2 / limits.area_per_obstacle);
    if (
      !legalBase(next, baseRect(next)) ||
      next.obstacles.length > max ||
      next.manual_points.some((p) => p.some((v) => v < 0 || v >= next.size)) ||
      next.obstacles.some((r) => !legal(next, r, limits))
    ) {
      setNotice(
        "This edit would cross the grid boundary or overlap a protected object.",
      );
      return;
    }
    setBefore((old) => [...old.slice(-79), env]);
    setAfter([]);
    apply(next);
    const requested = Math.min(count, max);
    setCount(requested);
    setNotice(
      requested < count ? "Obstacle count adjusted to the new grid limit." : "",
    );
  }
  function placeObstacle([x, y]: Point) {
    if (!manual || busy || editing.current) return;
    if (!terrainStats(env, limits).capacity) {
      setNotice("No additional obstacle fits the current count or area limit.");
      return;
    }
    let n = 1;
    while (env.obstacles.some((r) => r.id === "manual-" + n)) n++;
    const rect = { id: "manual-" + n, x, y, w: 1, h: 1 };
    if (!legal(env, rect, limits)) {
      setNotice(
        "Choose a free cell outside the station and monitoring points.",
      );
      return;
    }
    change({ ...env, obstacles: [...env.obstacles, rect] });
    setCount(env.obstacles.length + 1);
    select(rect.id);
    setNotice("Obstacle added.");
  }
  function removeSelection() {
    if (selectedPoint !== null && env.monitoring_mode === "manual") {
      change({
        ...env,
        manual_points: env.manual_points.filter((_, i) => i !== selectedPoint),
      });
    } else if (
      manual &&
      selected &&
      env.obstacles.some((r) => r.id === selected)
    ) {
      change({
        ...env,
        obstacles: env.obstacles.filter((r) => r.id !== selected),
      });
      setCount(env.obstacles.length - 1);
      select(null);
    }
  }
  function undo() {
    setTool(null);
    if (before.length && !busy) {
      setAfter([...after, env]);
      setBefore(before.slice(0, -1));
      apply(before.at(-1)!);
    }
  }
  function redo() {
    setTool(null);
    if (after.length && !busy) {
      setBefore([...before, env]);
      setAfter(after.slice(0, -1));
      apply(after.at(-1)!);
    }
  }
  async function generate() {
    if (editing.current || busy) return;
    editing.current = true;
    setGenerating(true);
    const stamp = version.current;
    try {
      const next = await api("generate", {
        environment: env,
        count,
        fresh: true,
      });
      if (stamp === version.current) {
        change(next);
        setCount(next.obstacles.length);
        setNotice("Obstacles generated with seed " + next.seed + ".");
      }
    } catch (e) {
      setNotice(String(e));
    } finally {
      editing.current = false;
      setGenerating(false);
    }
  }
  useEffect(() => {
    let live = true;
    api("health")
      .then(async (health) => {
        if (health.protocol !== 2)
          throw Error(
            "A different API is running. Close the old server and restart this copy of AI Project.",
          );
        const next = await api("generate", { environment: initial, count: 4 });
        if (live) {
          setLimits(health);
          setOnline(true);
          if (version.current === 0) setEnv(next);
        }
      })
      .catch((e) => setNotice(String(e)));
    return () => {
      live = false;
      version.current++;
    };
  }, []);
  useEffect(() => {
    function key(e: KeyboardEvent) {
      if (
        page !== "Environment" ||
        busy ||
        generating ||
        e.repeat ||
        (e.target as HTMLElement).closest(
          "input:not([type=range]),textarea,select,[contenteditable=true]",
        )
      )
        return;
      if (e.ctrlKey && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
      } else if (e.ctrlKey && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      } else if (e.key === "Delete" && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        removeSelection();
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  async function run(method: string) {
    if (busy || editing.current || active.current) return;
    active.current = "pending";
    cancelRequested.current = false;
    clearResults();
    const stamp = version.current;
    setBusy(true);
    setNotice("");
    setProgress({ label: "Preparing run", percent: 0 });
    try {
      const { id } = await api("jobs", {
        protocol: 2,
        mode: method,
        environment: env,
        settings,
      });
      active.current = id;
      if (cancelRequested.current) await api("jobs/" + id, undefined, "DELETE");
      while (stamp === version.current) {
        const response = await api("jobs/" + id);
        if (stamp !== version.current) break;
        if (response.state === "cancelled") {
          setNotice("Run cancelled.");
          break;
        }
        if (response.state === "failed")
          throw Error(
            "The optimization failed. Check the API console for run " +
              id +
              ".",
          );
        if (response.state === "complete") {
          setResults(response.result);
          setIndex(0);
          setJob(id);
          setNotice(
            response.result.some((r: Result) => !r.possible)
              ? "No feasible deployment exists on these candidate sites."
              : "Run complete. Inspect the layout or validate the solution.",
          );
          break;
        }
        if (response.progress) {
          const p = response.progress;
          setProgress({ label: p.label, percent: (100 * p.done) / p.total });
        }
        await new Promise((resolve) => setTimeout(resolve, 220));
      }
    } catch (e) {
      setNotice(String(e));
    } finally {
      active.current = "";
      setBusy(false);
    }
  }
  async function audit() {
    const stamp = version.current;
    try {
      const data = await api("jobs/" + job + "/validate", env);
      if (stamp === version.current) setAudits(data);
    } catch (e) {
      setNotice(String(e));
    }
  }
  async function download() {
    const stamp = version.current;
    try {
      const response = await fetch("/api/jobs/" + job + "/export/" + format, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(env),
      });
      if (!response.ok) throw Error("Export requires a current comparison.");
      const blob = await response.blob();
      if (stamp === version.current)
        saveFile(
          blob,
          {
            csv: "Comparison_Results.csv",
            pdf: "Comparison_Report.pdf",
            png: "Comparison_Table.png",
          }[format]!,
        );
    } catch (e) {
      setNotice(String(e));
    }
  }
  const emptyManual =
    env.monitoring_mode === "manual" && !env.manual_points.length;
  const stats = terrainStats(preview ?? env, limits);
  return (
    <>
      <header>
        <div className="brand">
          <span className="brandmark">
            <Network size={23} />
          </span>
          AI Project
        </div>
        <nav>
          {paths.map((name, i) => {
            const Icon = [Map, ChartNoAxesCombined][i];
            return (
              <button
                key={name}
                aria-current={page === name ? "page" : undefined}
                onClick={() => {
                  setPreview(null);
                  setPage(name);
                }}
              >
                <Icon />
                {name}
              </button>
            );
          })}
        </nav>
      </header>
      <main>
        <div className="titlebar">
          <div>
            <h1>
              {page === "Environment"
                ? "Deployment studio"
                : "Optimization results"}
            </h1>
          </div>
          {page === "Environment" && (
            <div className="row">
              <button disabled={busy} onClick={() => file.current?.click()}>
                <FolderOpen />
                Load
              </button>
              <button
                onClick={() =>
                  saveFile(
                    new Blob([JSON.stringify(env, null, 2)], {
                      type: "application/json",
                    }),
                    "Environment.json",
                  )
                }
              >
                <Download />
                Save environment
              </button>
            </div>
          )}
        </div>
        <input
          ref={file}
          type="file"
          accept=".json"
          hidden
          onChange={async (e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (!f) return;
            const stamp = version.current;
            try {
              const next = await api("environment", JSON.parse(await f.text()));
              if (stamp === version.current) {
                setTool(null);
                change(next);
                setCount(next.obstacles.length);
                setNotice("Environment loaded.");
              }
            } catch (error) {
              setNotice(String(error));
            }
          }}
        />
        {notice && !busy && (
          <div role="status" className="notice">
            {notice}
            <button aria-label="Dismiss message" onClick={() => setNotice("")}>
              ×
            </button>
          </div>
        )}
        {busy && (
          <div className="notice progress" role="status">
            <Activity />
            {progress.label}
            <progress value={progress.percent} max="100" />
            <button
              onClick={() => {
                cancelRequested.current = true;
                if (active.current && active.current !== "pending")
                  api("jobs/" + active.current, undefined, "DELETE").catch(
                    (e) => setNotice(String(e)),
                  );
              }}
            >
              Cancel
            </button>
          </div>
        )}
        {page === "Environment" && (
          <div className="workspace">
            <aside>
              <fieldset disabled={busy || generating || !online}>
                <Controls
                  env={env}
                  limits={limits}
                  capacity={stats.capacity}
                  manual={manual}
                  mode={(v) => {
                    setTool(null);
                    setSelectedPoint(null);
                    setManual(v);
                    setPreview(null);
                    select(null);
                  }}
                  selected={selected}
                  count={count}
                  setCount={(v) => {
                    setCount(v);
                    clearResults();
                  }}
                  change={change}
                  generate={generate}
                  undo={undo}
                  redo={redo}
                  canUndo={!!before.length}
                  canRedo={!!after.length}
                  tool={tool}
                  setTool={setTool}
                  selectedPoint={selectedPoint}
                  remove={removeSelection}
                />
              </fieldset>
              <section className="panel config">
                <h2>
                  <Workflow />
                  Optimization
                </h2>
                <div className="control-body">
                  <label className="label">Algorithm</label>
                  <div className="seg algorithms">
                    {["GA", "MA", "Comparison"].map((m) => (
                      <button
                        className={mode === m ? "active" : ""}
                        disabled={busy}
                        onClick={() => {
                          if (mode !== m) {
                            setMode(m);
                            clearResults();
                          }
                        }}
                        key={m}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                  <div className="two">
                    {(
                      [
                        ["seed", "Algorithm seed", 0, 2147483647],
                        ["budget", "Evaluation budget", 80, 5000],
                        ["population", "Population", 4, 80],
                        ["generations", "Generations", 1, 300],
                        ["local_fraction", "Local fraction", 0, 1],
                      ] as const
                    )
                      .filter(
                        ([key]) => key !== "local_fraction" || mode !== "GA",
                      )
                      .map(([key, label, min, max]) => (
                        <NumberField
                          key={key}
                          label={label}
                          min={min}
                          max={max}
                          step={key === "local_fraction" ? 0.05 : 1}
                          value={settings[key]}
                          set={(n) => {
                            if (!busy && n !== settings[key]) {
                              setSettings({ ...settings, [key]: n });
                              clearResults();
                            }
                          }}
                          disabled={busy}
                        />
                      ))}
                  </div>

                  {emptyManual && (
                    <p className="hint">
                      Add at least one monitoring point to run.
                    </p>
                  )}
                  <button
                    className="wide primary"
                    disabled={busy || generating || !online || emptyManual}
                    onClick={() => run(mode)}
                  >
                    <Play />
                    {mode === "Comparison" ? "Run comparison" : "Run " + mode}
                  </button>
                </div>
              </section>
            </aside>
            <div className="visual">
              <div className="kpis">
                {[
                  [RadioTower, "Sensors used", result?.count, "nodes", "mint"],
                  [
                    ScanLine,
                    env.monitoring_mode === "manual"
                      ? "Selected point coverage"
                      : "Grid coverage",
                    result?.coverage.toFixed(1),
                    "%",
                    "blue",
                  ],
                  [
                    Network,
                    "Connected sensors",
                    result
                      ? result.count - result.unreachable.length
                      : undefined,
                    result ? "/ " + result.count : "nodes",
                    "purple",
                  ],
                  [Timer, "Run time", result?.seconds.toFixed(3), "s", "gold"],
                ].map(([I, label, value, unit, color]) => {
                  const Icon = I as typeof Timer;
                  return (
                    <section className="kpi panel" key={String(label)}>
                      <div className={"kicon " + color}>
                        <Icon />
                      </div>
                      <div>
                        <label>{String(label)}</label>
                        <strong>
                          {value === undefined ? "—" : String(value)}{" "}
                          <small>{String(unit)}</small>
                        </strong>
                      </div>
                    </section>
                  );
                })}
              </div>
              <section className="panel terrain">
                <div className="plothead">
                  <div className="plot-title">
                    <MapPinned />
                    <div>
                      <h2>Deployment map</h2>
                      <small>
                        {env.size} × {env.size} grid <b>·</b>{" "}
                        {env.obstacles.length} obstacles <b>·</b> Seed{" "}
                        {env.seed}
                      </small>
                    </div>
                  </div>
                  <div className="row">
                    {results.length > 1 && (
                      <select
                        aria-label="Displayed algorithm"
                        value={index}
                        onChange={(e) => setIndex(+e.target.value)}
                      >
                        {results.map((r, i) => (
                          <option key={r.algorithm} value={i}>
                            {r.algorithm}
                          </option>
                        ))}
                      </select>
                    )}
                    <div className="popover">
                      <button
                        onClick={() => setShowLayers(!showLayers)}
                        aria-expanded={showLayers}
                      >
                        <Layers3 />
                        Layers
                        <ChevronDown size={12} />
                      </button>
                      {showLayers && (
                        <div className="layerbox">
                          {Object.entries({
                            points: "Monitoring points",
                            holes: "Coverage holes",
                            links: "Communication links",
                            sensing: "Sensing circles",
                            communication: "Communication circles",
                          }).map(([k, v]) => (
                            <label key={k}>
                              <input
                                type="checkbox"
                                checked={layers[k as keyof Layers]}
                                onChange={(e) =>
                                  setLayers({
                                    ...layers,
                                    [k]: e.target.checked,
                                  })
                                }
                              />
                              {v}
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <TerrainCanvas
                  env={env}
                  result={result}
                  layers={layers}
                  manual={manual}
                  locked={busy || generating}
                  tool={tool}
                  stopTool={() => setTool(null)}
                  placeObstacle={placeObstacle}
                  selectedPoint={selectedPoint}
                  selectPoint={(i) => {
                    setSelectedPoint(i);
                    if (i !== null) select(null);
                  }}
                  notify={setNotice}
                  previewGeometry={setPreview}
                  selected={selected}
                  select={select}
                  commit={change}
                  limits={limits}
                  onCursor={(value) => {
                    if (cursor.current && cursor.current.value !== value)
                      cursor.current.value = value;
                  }}
                />
                <div className="map-foot">
                  <span>Grid coordinates</span>
                  <span>
                    {result
                      ? result.algorithm +
                        (result.feasible
                          ? " · Feasible layout"
                          : " · Infeasible layout")
                      : "Awaiting deployment"}
                  </span>
                  <span>
                    <Focus />
                    <output ref={cursor}>—</output>
                  </span>
                </div>
                <dl className="terrain-stats">
                  {Object.entries({
                    "Grid size": env.size + " × " + env.size,
                    "Total cells": stats.cells,
                    "Blocked cells": stats.area,
                    ...(env.monitoring_mode === "automatic"
                      ? {
                          "Monitoring sites": stats.total,
                          "Blocked sites": stats.blocked,
                          "Available monitoring points": stats.available,
                        }
                      : {
                          "Required monitoring points":
                            env.manual_points.length,
                        }),
                    "Blocked area":
                      ((100 * stats.area) / stats.cells).toFixed(2) + "%",
                    Obstacles: env.obstacles.length,
                    "Additional obstacles allowed": stats.capacity,
                  }).map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="legend">
                  {env.monitoring_mode === "manual" && (
                    <span>
                      <i className="symbol target" />
                      Required point
                    </span>
                  )}
                  {legend.map(([symbol, label]) => (
                    <span key={symbol}>
                      <i className={"symbol " + symbol} />
                      {label}
                    </span>
                  ))}
                </div>
              </section>
              <section className="panel validation">
                <div>
                  <h2>
                    <ShieldCheck />
                    Solution validation
                  </h2>
                  <p>
                    {result
                      ? "Check coverage and routes independently."
                      : "Run an algorithm to validate its sensor layout."}
                  </p>
                </div>
                <div className="row">
                  <button disabled={!job || busy || !!preview} onClick={audit}>
                    Validate Solution
                  </button>
                </div>
                {!preview && audits.length > 0 && (
                  <div className="audit">
                    {audits.map((a, i) => (
                      <div key={i}>
                        <strong>
                          {results[i]?.algorithm} · {a.passed ? "PASS" : "FAIL"}
                        </strong>{" "}
                        ·{" "}
                        {env.monitoring_mode === "manual"
                          ? "Selected points"
                          : "Automatic grid"}{" "}
                        {results[i].monitoring_count - results[i].holes.length}/
                        {results[i].monitoring_count} · Coverage{" "}
                        {a.coverage.toFixed(2)}% · Connectivity{" "}
                        {a.connectivity.toFixed(2)}%
                        {Object.entries(a.checks)
                          .filter(
                            ([key, ok]) =>
                              !ok ||
                              [
                                "Environment integrity",
                                "Unique legal coordinates",
                                "All monitoring points covered",
                                "Every sensor can route to base",
                              ].includes(key),
                          )
                          .map(([k, ok]) => (
                            <div key={k}>
                              {k} · {ok ? "PASS" : "FAIL"}
                            </div>
                          ))}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        )}
        {page === "Results" && (
          <Suspense fallback={<p>Loading results…</p>}>
            <Results
              results={results}
              format={format}
              setFormat={setFormat}
              download={download}
            />
          </Suspense>
        )}
      </main>
    </>
  );
}
