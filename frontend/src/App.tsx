import { useState, useRef, useEffect, lazy, Suspense } from "react";
import {
  Network,
  Map,
  ChartNoAxesCombined,
  FlaskConical,
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
  Grid2X2,
  Dna,
  Focus,
} from "lucide-react";
import TerrainCanvas from "./TerrainCanvas";
import { Controls, NumberField } from "./Controls";
const Results = lazy(() =>
  import("./Results").then((module) => ({ default: module.Results })),
);
const BenchTable = lazy(() =>
  import("./Results").then((module) => ({ default: module.BenchTable })),
);
import {
  api,
  legal,
  saveFile,
  type Env,
  type Result,
  type Audit,
  type Layers,
  type Limits,
  type Summary,
} from "./types";

const initial: Env = {
  size: 40,
  base: [20, 20],
  sensing: 5.5,
  communication: 8,
  spacing: 2,
  seed: 42,
  obstacles: [],
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
const paths = ["Environment", "Results", "Experiments"] as const;
type Page = (typeof paths)[number];
const settingsDefault = {
  seed: 7,
  budget: 300,
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
  const [showLayers, setShowLayers] = useState(false),
    [cursor, setCursor] = useState("—"),
    [notice, setNotice] = useState("");
  const [before, setBefore] = useState<Env[]>([]),
    [after, setAfter] = useState<Env[]>([]);
  const [busy, setBusy] = useState(false),
    [job, setJob] = useState(""),
    [progress, setProgress] = useState({ label: "", percent: 0 });
  const [mode, setMode] = useState("Comparison"),
    [settings, setSettings] = useState(settingsDefault);
  const [results, setResults] = useState<Result[]>([]),
    [index, setIndex] = useState(0),
    [audits, setAudits] = useState<Audit[]>([]),
    [fine, setFine] = useState(false);
  const [format, setFormat] = useState("csv"),
    [trials, setTrials] = useState(1),
    [history, setHistory] = useState<{ rows: Summary[]; trials: number }[]>([]),
    [historyIndex, setHistoryIndex] = useState(0);
  const file = useRef<HTMLInputElement>(null),
    version = useRef(0),
    active = useRef(""),
    editing = useRef(false);
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
    setCount(next.obstacles.length);
    select((id) => (next.obstacles.some((r) => r.id === id) ? id : null));
    clearResults();
  }
  function change(next: Env) {
    if (busy || JSON.stringify(next) === JSON.stringify(env)) return;
    const max = Math.floor(next.size ** 2 / limits.area_per_obstacle);
    if (
      next.obstacles.length > max ||
      next.obstacles.some((r) => !legal(next, r, limits))
    ) {
      setNotice(
        "This edit would invalidate an obstacle. The previous layout is still active.",
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
  function undo() {
    if (before.length && !busy) {
      setAfter([...after, env]);
      setBefore(before.slice(0, -1));
      apply(before.at(-1)!);
    }
  }
  function redo() {
    if (after.length && !busy) {
      setBefore([...before, env]);
      setAfter(after.slice(0, -1));
      apply(after.at(-1)!);
    }
  }
  async function generate(append: boolean) {
    if (editing.current || busy) return;
    editing.current = true;
    const stamp = version.current;
    try {
      const next = await api("generate", {
        environment: env,
        count: append ? env.obstacles.length + 1 : count,
        append,
      });
      if (stamp === version.current) {
        change(next);
        setCount(next.obstacles.length);
        if (append) select(next.obstacles.at(-1).id);
        setNotice(
          append
            ? "Obstacle added."
            : "Obstacles generated with seed " + env.seed + ".",
        );
      }
    } catch (e) {
      setNotice(String(e));
    } finally {
      editing.current = false;
    }
  }
  useEffect(() => {
    let live = true;
    Promise.all([
      api("health"),
      api("generate", { environment: initial, count: 4 }),
    ])
      .then(([health, next]) => {
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
        !manual ||
        e.repeat ||
        (e.target as HTMLElement).closest(
          "input,textarea,select,[contenteditable=true]",
        )
      )
        return;
      if (e.ctrlKey && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
      } else if (e.ctrlKey && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      } else if (!e.ctrlKey && e.key.toLowerCase() === "o") {
        e.preventDefault();
        void generate(true);
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  async function run(method: string) {
    if (busy) return;
    if (method !== "Benchmark") clearResults();
    const stamp = version.current;
    setBusy(true);
    setNotice("");
    setProgress({ label: "Preparing run", percent: 0 });
    try {
      const { id } = await api("jobs", {
        mode: method,
        environment: env,
        settings,
        trials,
      });
      active.current = id;
      while (stamp === version.current) {
        const response = await api("jobs/" + id);
        if (stamp !== version.current) break;
        if (response.state === "cancelled") {
          setNotice("Run cancelled.");
          break;
        }
        if (response.state === "failed") throw Error(response.error);
        if (response.state === "complete") {
          if (method === "Benchmark") {
            setHistory((old) => [
              { rows: response.result.summary, trials },
              ...old,
            ]);
            setHistoryIndex(0);
          } else {
            setResults(response.result);
            setIndex(0);
            setJob(id);
            setNotice(
              response.result.some((r: Result) => !r.possible)
                ? "No feasible deployment exists on these candidate sites."
                : "Run complete. Inspect the layout or validate the solution.",
            );
          }
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
      const data = await api("jobs/" + job + "/validate?fine=" + fine, env);
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
  const blocked = env.obstacles.reduce((sum, r) => sum + r.w * r.h, 0);
  return (
    <>
      <header>
        <div className="brand">
          <span className="brandmark">
            <Network size={23} />
          </span>
          Fieldlab
        </div>
        <nav>
          {paths.map((name, i) => {
            const Icon = [Map, ChartNoAxesCombined, FlaskConical][i];
            return (
              <button
                key={name}
                aria-current={page === name ? "page" : undefined}
                onClick={() => setPage(name)}
              >
                <Icon />
                {name}
              </button>
            );
          })}
        </nav>
        <span className="engine">
          <i className={online ? "ok" : ""} />
          {online ? "Engine online" : "Connecting"}
        </span>
      </header>
      <main>
        <div className="titlebar">
          <div>
            <h1>
              {page === "Environment"
                ? "Deployment studio"
                : page === "Results"
                  ? "Optimization results"
                  : "Experiment bench"}
            </h1>
            <p>
              {page === "Environment"
                ? "Optimize wireless sensor placement, coverage, and connectivity."
                : page === "Results"
                  ? "Inspect the best deployments found on the current terrain."
                  : "Compare both algorithms across grid sizes and obstacle layouts."}
            </p>
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
                change(next);
                setCount(next.obstacles.length);
                setNotice("Environment loaded.");
              }
            } catch (error) {
              setNotice(String(error));
            }
          }}
        />
        {notice && (
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
              onClick={() =>
                active.current &&
                api("jobs/" + active.current, undefined, "DELETE").catch((e) =>
                  setNotice(String(e)),
                )
              }
            >
              Cancel
            </button>
          </div>
        )}
        {page === "Environment" && (
          <div className="workspace">
            <aside>
              <fieldset disabled={busy || !online}>
                <Controls
                  env={env}
                  limits={limits}
                  manual={manual}
                  mode={(v) => {
                    setManual(v);
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
                  remove={() => {
                    change({
                      ...env,
                      obstacles: env.obstacles.filter((r) => r.id !== selected),
                    });
                    setCount(env.obstacles.length - 1);
                  }}
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
                        onClick={() => setMode(m)}
                        key={m}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                  <details>
                    <summary>
                      <Dna />
                      Search parameters
                      <ChevronDown />
                    </summary>
                    <div className="two">
                      {(
                        [
                          ["seed", "Algorithm seed", 0, 2147483647],
                          ["budget", "Evaluation budget", 80, 5000],
                          ["population", "Population", 4, 80],
                          ["generations", "Generations", 1, 300],
                          ["local_fraction", "Local fraction", 0, 1],
                        ] as const
                      ).map(([key, label, min, max]) => (
                        <NumberField
                          key={key}
                          label={label}
                          min={min}
                          max={max}
                          step={key === "local_fraction" ? 0.05 : 1}
                          value={settings[key]}
                          set={(n) => setSettings({ ...settings, [key]: n })}
                        />
                      ))}
                    </div>
                  </details>
                  <button
                    className="wide primary"
                    disabled={busy || !online}
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
                    "Grid coverage",
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
                  manual={manual && !busy}
                  selected={selected}
                  select={select}
                  commit={change}
                  limits={limits}
                  onCursor={setCursor}
                />
                <div className="map-foot">
                  <span>
                    <Grid2X2 />
                    {env.size ** 2 - blocked} monitoring points
                  </span>
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
                    {cursor}
                  </span>
                </div>
                <div className="legend">
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
                  <label>
                    <input
                      type="checkbox"
                      checked={fine}
                      onChange={(e) => {
                        setFine(e.target.checked);
                        setAudits([]);
                      }}
                    />
                    Fine sampling
                  </label>
                  <button disabled={!job || busy} onClick={audit}>
                    Validate Solution
                  </button>
                </div>
                {audits.length > 0 && (
                  <div className="audit">
                    {audits.map((a, i) => (
                      <div key={i}>
                        <strong>
                          {results[i]?.algorithm} · {a.passed ? "PASS" : "FAIL"}
                        </strong>{" "}
                        · Coverage {a.coverage.toFixed(2)}% · Connected{" "}
                        {a.connectivity.toFixed(2)}% · Coordinates{" "}
                        {a.checks["Unique legal coordinates"]
                          ? "valid"
                          : "invalid"}
                        {Object.entries(a.checks)
                          .filter(([, ok]) => !ok)
                          .map(([k]) => (
                            <div key={k}>{k} failed</div>
                          ))}
                        {a.fine && (
                          <div>
                            Fine samples covered {a.fine.covered}/{a.fine.total}{" "}
                            ({a.fine.percent.toFixed(2)}%)
                          </div>
                        )}
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
        {page === "Experiments" && (
          <section className="panel report">
            <h2>
              <FlaskConical />
              Paired benchmark
            </h2>
            <p>
              Run both methods on five saved scenario recipes. Each trial uses
              the same terrain, algorithm seed, and budget of 100 evaluations.
            </p>
            <div className="row">
              <NumberField
                label="Trials per scenario"
                value={trials}
                min={1}
                max={10}
                set={setTrials}
              />
              <button
                className="primary"
                disabled={busy || !online}
                onClick={() => run("Benchmark")}
              >
                <Play />
                Run benchmark
              </button>
            </div>
            {history.length > 0 && (
              <>
                <h3>Experiment history</h3>
                <select
                  aria-label="Benchmark history"
                  value={historyIndex}
                  onChange={(e) => setHistoryIndex(+e.target.value)}
                >
                  {history.map((h, i) => (
                    <option key={i} value={i}>
                      Run {history.length - i} · {h.trials} trial(s) per
                      scenario
                    </option>
                  ))}
                </select>
                <Suspense fallback={<p>Loading table…</p>}>
                  <BenchTable rows={history[historyIndex].rows} />
                </Suspense>
              </>
            )}
          </section>
        )}
      </main>
      <footer>
        <span>
          <Network />
          Fieldlab
        </span>
        Wireless sensor network optimization
      </footer>
    </>
  );
}
