import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Download, ChartNoAxesCombined } from "lucide-react";
import type { Result, Summary } from "./types";
const fields: [string, (r: Result) => string | number][] = [
  ["Solution status", (r) => (r.feasible ? "Feasible" : "Infeasible")],
  ["Active sensors", (r) => r.count],
  ["Grid coverage", (r) => r.coverage.toFixed(2) + "%"],
  ["Connectivity", (r) => r.connectivity.toFixed(2) + "%"],
  ["Disconnected sensors", (r) => r.unreachable.length],
  ["Execution time", (r) => r.seconds.toFixed(4) + " s"],
  ["Fitness evaluations", (r) => r.evaluations],
  ["Best cost", (r) => r.cost],
  [
    "MA local improvements",
    (r) => (r.algorithm === "MA" ? r.local.improvements : "—"),
  ],
];
export function Results({
  results,
  format,
  setFormat,
  download,
}: {
  results: Result[];
  format: string;
  setFormat: (s: string) => void;
  download: () => void;
}) {
  const evaluations = [
    ...new Set(results.flatMap((r) => r.history.map((h) => h.evaluations))),
  ].sort((a, b) => a - b);
  const data = evaluations.map((e) =>
    Object.fromEntries([
      ["evaluations", e],
      ...results.map((r) => [
        r.algorithm,
        r.history.filter((h) => h.evaluations <= e).at(-1)?.cost,
      ]),
    ]),
  );
  return (
    <section className="panel report">
      <div className="section-heading">
        <h2>
          <ChartNoAxesCombined />
          Best found solutions
        </h2>
      </div>
      {results.length ? (
        <>
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                {results.map((r) => (
                  <th key={r.algorithm}>{r.algorithm}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fields.map(([label, get]) => (
                <tr key={label}>
                  <td>{label}</td>
                  {results.map((r) => (
                    <td key={r.algorithm}>{get(r)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Convergence</h3>
          <p className="hint">
            Best cost by fitness evaluation. Lower is better.
          </p>
          <div className="chart">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="evaluations"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                />
                <YAxis width={55} />
                <Tooltip />
                {results.map((r, i) => (
                  <Area
                    key={r.algorithm}
                    type="stepAfter"
                    dataKey={r.algorithm}
                    stroke={i ? "#a76934" : "#167461"}
                    fill={i ? "#eedbc7" : "#d8ebe2"}
                    fillOpacity={0.3}
                    isAnimationActive={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <p>
          Run GA, MA, or a comparison in the environment to see measured results
          here.
        </p>
      )}
      <div className="row">
        <select
          aria-label="Comparison export format"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
        >
          {["csv", "pdf", "png"].map((f) => (
            <option key={f} value={f}>
              {f.toUpperCase()}
            </option>
          ))}
        </select>
        <button
          className="primary"
          disabled={results.length !== 2}
          onClick={download}
        >
          <Download />
          Download Comparison
        </button>
      </div>
    </section>
  );
}
export function BenchTable({ rows }: { rows: Summary[] }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {[
              "Scenario",
              "Method",
              "Feasible",
              "Best sensors",
              "Mean ± SD",
              "Mean time (s)",
              "Evaluations",
              "Coverage",
              "Connected",
            ].map((t) => (
              <th key={t}>{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.case + r.algorithm}>
              <td>{r.case}</td>
              <td>{r.algorithm}</td>
              <td>
                {r.valid}/{r.runs}
              </td>
              <td>{r.best ?? "—"}</td>
              <td>
                {r.mean?.toFixed(2) ?? "—"} ± {r.sd?.toFixed(2) ?? "—"}
              </td>
              <td>{r.seconds.toFixed(3)}</td>
              <td>{r.evaluations.toFixed(1)}</td>
              <td>{r.coverage.toFixed(1)}%</td>
              <td>{r.connectivity.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
