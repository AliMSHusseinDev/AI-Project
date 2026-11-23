import { useState, useEffect, useRef } from "react";
import {
  SlidersHorizontal,
  Shuffle,
  MousePointer2,
  Undo2,
  Redo2,
  Trash2,
  Plus,
} from "lucide-react";
import type { Env, Limits } from "./types";

const tips: Record<string, string> = {
  "Site spacing": "Grid units between adjacent monitoring and candidate sites.",
  "Environment seed":
    "Generate a layout from this seed. Generating the same layout again advances the seed.",
  "Algorithm seed": "Repeat the random choices of the search.",
  Population: "Deployments maintained in each full generation.",
  Generations: "Maximum evolutionary rounds.",
  "Evaluation budget": "Maximum new unique fitness scores per method.",
  "Local fraction":
    "Probability of local search on each MA child (0.45 means 45%).",
  "Base station X": "Column of the station center.",
  "Base station Y": "Row of the station center.",
  "Sensing radius": "Maximum clear sensing distance in grid units.",
  "Communication radius": "Maximum clear radio distance in grid units.",
};
export function NumberField({
  label,
  value,
  set,
  min,
  max,
  step = 1,
  disabled = false,
}: {
  label: string;
  value: number;
  set: (n: number) => void;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
}) {
  const [draft, update] = useState(String(value));
  useEffect(() => update(String(value)), [value]);
  return (
    <label className="num-field" title={tips[label]}>
      {label}
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        value={draft}
        onChange={(e) => update(e.target.value)}
        onBlur={(e) => {
          if (e.target.validity.valid && draft !== "") {
            set(Number(draft));
          }
          update(String(value));
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
        }}
      />
    </label>
  );
}
type Props = {
  env: Env;
  limits: Limits;
  manual: boolean;
  mode: (v: boolean) => void;
  selected: string | null;
  count: number;
  setCount: (n: number) => void;
  change: (e: Env) => void;
  generate: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  capacity: number;
  remove: () => void;
  tool: "point" | "obstacle" | null;
  setTool: (tool: Props["tool"]) => void;
  selectedPoint: number | null;
};
export function Controls(p: Props) {
  const { env, limits } = p,
    max = Math.floor(env.size ** 2 / limits.area_per_obstacle);
  const [draftSize, setDraftSize] = useState<number | null>(null);
  const sliding = useRef(false);
  const resize = (size: number) =>
    p.change({
      ...env,
      size,
      base: [
        Math.max(
          env.base_margin,
          Math.min(env.base[0], size - 1 - env.base_margin),
        ),
        Math.max(
          env.base_margin,
          Math.min(env.base[1], size - 1 - env.base_margin),
        ),
      ],
    });
  return (
    <section className="panel config">
      <h2>
        <SlidersHorizontal />
        Environment settings
      </h2>
      <div className="control-body">
        <div className="label-row">
          <label htmlFor="size">Grid size</label>
          <div className="readout">
            <input
              aria-label="Grid size value"
              key={env.size}
              type="number"
              defaultValue={env.size}
              min="20"
              max="100"
              onBlur={(e) => {
                if (e.target.validity.valid && e.target.value)
                  resize(+e.target.value);
                e.target.value = String(env.size);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") e.currentTarget.blur();
              }}
            />{" "}
            × {env.size}
          </div>
        </div>
        <input
          id="size"
          type="range"
          min="20"
          max="100"
          value={draftSize ?? env.size}
          aria-valuetext={
            draftSize === null
              ? String(env.size)
              : `Requested ${draftSize}, current grid ${env.size}`
          }
          onPointerDown={(e) => {
            sliding.current = true;
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onChange={(e) =>
            sliding.current
              ? setDraftSize(+e.target.value)
              : resize(+e.target.value)
          }
          onPointerUp={(e) => {
            if (sliding.current) resize(+e.currentTarget.value);
            sliding.current = false;
            setDraftSize(null);
          }}
          onLostPointerCapture={() => {
            sliding.current = false;
            setDraftSize(null);
          }}
        />
        <div className="limits">
          <span>20 × 20</span>
          <span>100 × 100</span>
        </div>
        <div className="label-row">
          <label htmlFor="count">Obstacle count</label>
          <span className="readout">
            {p.manual ? env.obstacles.length : p.count}
          </span>
        </div>
        <input
          id="count"
          type="range"
          min="0"
          max={max}
          value={p.manual ? env.obstacles.length : p.count}
          disabled={p.manual}
          onChange={(e) => p.setCount(+e.target.value)}
        />
        <div className="limits">
          <span>0</span>
          <span>Max {max}</span>
        </div>
        <label className="label">Obstacle placement</label>
        <div className="seg">
          <button
            className={!p.manual ? "active" : ""}
            onClick={() => p.mode(false)}
          >
            <Shuffle />
            Automatic
          </button>
          <button
            className={p.manual ? "active" : ""}
            onClick={() => p.mode(true)}
          >
            <MousePointer2 />
            Manual
          </button>
        </div>
        {p.manual ? (
          <>
            <div className="row wrap">
              <button
                disabled={p.capacity === 0}
                aria-pressed={p.tool === "obstacle"}
                onClick={() =>
                  p.setTool(p.tool === "obstacle" ? null : "obstacle")
                }
              >
                <Plus />
                Add (O)
              </button>
              <button disabled={!p.selected} onClick={p.remove}>
                <Trash2 />
                Delete
              </button>
              <button title="Undo" disabled={!p.canUndo} onClick={p.undo}>
                <Undo2 />
              </button>
              <button title="Redo" disabled={!p.canRedo} onClick={p.redo}>
                <Redo2 />
              </button>
            </div>
            <p className="hint">
              Press O over a free cell, or choose Add and click the map. Select
              a block to move it, press R to resize, or Delete to remove.
            </p>
          </>
        ) : (
          <button className="wide soft" onClick={p.generate}>
            <Shuffle />
            Generate obstacles
          </button>
        )}
        <hr />
        <h3>Monitoring points</h3>
        <div className="seg" role="group" aria-label="Monitoring points mode">
          {(["automatic", "manual"] as const).map((m) => (
            <button
              key={m}
              aria-label={
                m === "automatic"
                  ? "Automatic monitoring points"
                  : "Manual monitoring points"
              }
              aria-pressed={env.monitoring_mode === m}
              className={env.monitoring_mode === m ? "active" : ""}
              onClick={() => {
                p.setTool(null);
                p.change({ ...env, monitoring_mode: m });
              }}
            >
              {m === "automatic" ? "Automatic" : "Manual"}
            </button>
          ))}
        </div>
        {env.monitoring_mode === "manual" && (
          <>
            <div className="row wrap">
              <button
                aria-pressed={p.tool === "point"}
                onClick={() => p.setTool(p.tool === "point" ? null : "point")}
              >
                <Plus />
                Add points
              </button>
              <button disabled={p.selectedPoint === null} onClick={p.remove}>
                Delete point
              </button>
              {!p.manual && (
                <>
                  <button title="Undo" disabled={!p.canUndo} onClick={p.undo}>
                    <Undo2 />
                  </button>
                  <button title="Redo" disabled={!p.canRedo} onClick={p.redo}>
                    <Redo2 />
                  </button>
                </>
              )}
            </div>
            <p className="hint">
              {p.tool === "point"
                ? "Click a free cell for each target. Press Escape to finish."
                : "Select and drag a point to move it. Alt-click accesses the station beneath a point."}{" "}
              Candidate sensor spacing is {env.spacing}.
            </p>
          </>
        )}
        <hr />
        <h3>Sensor ranges</h3>
        <div className="two">
          <NumberField
            label="Sensing radius"
            value={env.sensing}
            min={0.1}
            max={30}
            step={0.1}
            set={(sensing) => p.change({ ...env, sensing })}
          />
          <NumberField
            label="Communication radius"
            value={env.communication}
            min={0.1}
            max={30}
            step={0.1}
            set={(communication) => p.change({ ...env, communication })}
          />
        </div>
        <hr />
        <h3>Terrain parameters</h3>
        <p className="hint">
          Drag the station to move it. Select it and press R over it to resize.
        </p>
        <div className="two">
          <NumberField
            label="Base station X"
            min={0}
            max={env.size - 1}
            value={env.base[0]}
            set={(x) => p.change({ ...env, base: [x, env.base[1]] })}
          />
          <NumberField
            label="Base station Y"
            min={0}
            max={env.size - 1}
            value={env.base[1]}
            set={(y) => p.change({ ...env, base: [env.base[0], y] })}
          />
          <NumberField
            label="Site spacing"
            disabled={env.monitoring_mode === "manual"}
            min={2}
            max={6}
            value={env.spacing}
            set={(spacing) => p.change({ ...env, spacing })}
          />
          <NumberField
            label="Environment seed"
            min={0}
            max={2147483647}
            value={env.seed}
            set={(seed) => p.change({ ...env, seed })}
          />
        </div>
      </div>
    </section>
  );
}
