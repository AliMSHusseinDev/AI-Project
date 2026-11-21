import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  contains,
  legal,
  type Env,
  type Rect,
  type Result,
  type Layers,
  type Limits,
} from "./types";

type Props = {
  env: Env;
  result?: Result;
  layers: Layers;
  manual: boolean;
  selected: string | null;
  select: (id: string | null) => void;
  commit: (e: Env) => void;
  limits: Limits;
  onCursor: (p: string) => void;
};
type Drag = {
  original: Rect;
  current: Rect;
  start: number[];
  handle: number[] | null;
  pointer: number;
};
export default function TerrainCanvas({
  env,
  result,
  layers,
  manual,
  selected,
  select,
  commit,
  limits,
  onCursor,
}: Props) {
  const canvas = useRef<HTMLCanvasElement>(null),
    transform = useRef({ left: 0, top: 0, scale: 1 });
  const hover = useRef<number[] | null>(null),
    drag = useRef<Drag | null>(null);
  const [resize, setResize] = useState(false),
    [preview, setPreview] = useState<Rect | null>(null),
    [dimension, setDimension] = useState(0);
  useLayoutEffect(() => {
    const observer = new ResizeObserver(() => setDimension((v) => v + 1));
    observer.observe(canvas.current!);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    setResize(false);
  }, [selected, manual]);
  useEffect(() => {
    setPreview(null);
    drag.current = null;
  }, [manual, env]);
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if (
        (event.target as HTMLElement).closest(
          "input,textarea,select,[contenteditable=true]",
        ) ||
        !manual ||
        event.repeat
      )
        return;
      const rect = env.obstacles.find((r) => r.id === selected),
        point = hover.current;
      if (
        event.key.toLowerCase() === "r" &&
        rect &&
        point &&
        contains(rect, point[0], point[1])
      )
        setResize((v) => !v);
      if (event.key === "Escape") {
        setResize(false);
        select(null);
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [env, manual, selected, select]);
  useLayoutEffect(() => {
    const frame = requestAnimationFrame(() => {
      const node = canvas.current!,
        ctx = node.getContext("2d")!,
        box = node.getBoundingClientRect();
      const width = box.width,
        height = box.height,
        dpr = window.devicePixelRatio || 1;
      if (
        node.width !== Math.round(width * dpr) ||
        node.height !== Math.round(height * dpr)
      ) {
        node.width = Math.round(width * dpr);
        node.height = Math.round(height * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const scale = Math.min((width - 68) / env.size, (height - 44) / env.size);
      const side = scale * env.size,
        left = (width - side) / 2 + 4,
        top = (height - side) / 2 - 3;
      transform.current = { left, top, scale };
      const cx = (x: number) => left + (x + 0.5) * scale,
        cy = (y: number) => top + (y + 0.5) * scale;
      ctx.fillStyle = "#fbfdfb";
      ctx.fillRect(left, top, side, side);
      ctx.font = '10px "DM Sans", sans-serif';
      ctx.textAlign = "center";
      for (let i = 0; i <= env.size; i++) {
        ctx.strokeStyle = i % 5 === 0 ? "#bfd2c8" : "#e0e9e2";
        ctx.lineWidth = i % 5 === 0 ? 0.9 : 0.65;
        ctx.beginPath();
        ctx.moveTo(left + i * scale, top);
        ctx.lineTo(left + i * scale, top + side);
        ctx.moveTo(left, top + i * scale);
        ctx.lineTo(left + side, top + i * scale);
        ctx.stroke();
        if (
          i % Math.max(5, Math.ceil(env.size / 10 / 5) * 5) === 0 &&
          i < env.size
        ) {
          ctx.fillStyle = "#73877e";
          ctx.fillText(String(i), cx(i), top + side + 15);
          ctx.fillText(String(i), left - 14, cy(i) + 3);
        }
      }
      const circle = (
        x: number,
        y: number,
        r: number,
        fill: string,
        stroke?: string,
      ) => {
        ctx.beginPath();
        ctx.arc(cx(x), cy(y), r, 0, Math.PI * 2);
        ctx.fillStyle = fill;
        ctx.fill();
        if (stroke) {
          ctx.strokeStyle = stroke;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      };
      ctx.save();
      ctx.beginPath();
      ctx.rect(left, top, side, side);
      ctx.clip();
      if (result) {
        const holes = new Set(result.holes.map((p) => p.join(","))),
          unreachable = new Set(result.unreachable.map((p) => p.join(",")));
        if (layers.points || layers.holes)
          for (let y = 0; y < env.size; y++)
            for (let x = 0; x < env.size; x++) {
              const hole = holes.has(x + "," + y);
              if (
                (hole ? layers.holes : layers.points) &&
                !env.obstacles.some((r) => contains(r, x, y))
              )
                circle(
                  x,
                  y,
                  Math.max(0.7, scale * 0.085),
                  hole ? "#dd763a" : "#8abdad",
                );
            }
        for (const [x, y] of result.positions) {
          if (layers.communication)
            circle(x, y, env.communication * scale, "#699ee30a", "#759edb65");
          if (layers.sensing)
            circle(x, y, env.sensing * scale, "#fa8c9220", "#dc98997a");
        }
        if (layers.links)
          for (const [a, b] of result.links) {
            ctx.strokeStyle = "#529b8ab5";
            ctx.beginPath();
            ctx.moveTo(cx(a[0]), cy(a[1]));
            ctx.lineTo(cx(b[0]), cy(b[1]));
            ctx.stroke();
          }
        for (const p of result.positions)
          circle(
            ...p,
            Math.max(3, scale * 0.25),
            unreachable.has(p.join(",")) ? "#d05a4e" : "#177866",
            "white",
          );
      }
      for (const stored of env.obstacles) {
        const r = preview?.id === stored.id ? preview : stored;
        const x = left + r.x * scale,
          y = top + r.y * scale,
          w = r.w * scale,
          h = r.h * scale;
        ctx.fillStyle = "#869991";
        ctx.fillRect(x, y, w, h);
        ctx.save();
        ctx.beginPath();
        ctx.rect(x, y, w, h);
        ctx.clip();
        ctx.strokeStyle = "#adbbb4";
        ctx.lineWidth = 0.8;
        for (let k = -h; k < w; k += 6) {
          ctx.beginPath();
          ctx.moveTo(x + k, y + h);
          ctx.lineTo(x + k + h, y);
          ctx.stroke();
        }
        ctx.restore();
        ctx.strokeStyle = r.id === selected ? "#e39c22" : "#607a70";
        ctx.lineWidth = r.id === selected ? 3 : 1;
        ctx.strokeRect(x, y, w, h);
        if (resize && manual && selected === r.id)
          for (const dx of [0, 1])
            for (const dy of [0, 1]) {
              ctx.fillStyle = "#fff";
              ctx.fillRect(x + dx * w - 3, y + dy * h - 3, 6, 6);
              ctx.strokeRect(x + dx * w - 3, y + dy * h - 3, 6, 6);
            }
      }
      const [bx, by] = env.base;
      circle(bx, by, 12, "#7457ac20");
      ctx.save();
      ctx.translate(cx(bx), cy(by));
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = "#71529b";
      ctx.fillRect(-5, -5, 10, 10);
      ctx.restore();
      ctx.restore();
    });
    return () => cancelAnimationFrame(frame);
  }, [env, result, layers, selected, preview, resize, manual, dimension]);
  function coordinates(event: React.PointerEvent) {
    const box = canvas.current!.getBoundingClientRect(),
      t = transform.current;
    return [
      (event.clientX - box.left - t.left) / t.scale,
      (event.clientY - box.top - t.top) / t.scale,
    ];
  }
  function down(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!manual || event.button !== 0) return;
    const p = coordinates(event);
    let rect = env.obstacles.find((r) => contains(r, p[0], p[1]));
    let handle: number[] | null = null;
    if (resize) {
      const selectedRect = env.obstacles.find((r) => r.id === selected);
      if (selectedRect)
        for (const dx of [0, 1])
          for (const dy of [0, 1]) {
            if (
              Math.hypot(
                p[0] - selectedRect.x - dx * selectedRect.w,
                p[1] - selectedRect.y - dy * selectedRect.h,
              ) *
                transform.current.scale <
              8
            ) {
              handle = [dx, dy];
              rect = selectedRect;
            }
          }
    }
    select(rect?.id ?? null);
    if (!rect || (resize && rect.id === selected && !handle)) return;
    drag.current = {
      original: rect,
      current: rect,
      start: p,
      handle,
      pointer: event.pointerId,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event: React.PointerEvent) {
    const p = coordinates(event);
    hover.current = p;
    onCursor(
      p.every((v) => v >= 0 && v < env.size)
        ? p.map(Math.floor).join(", ")
        : "—",
    );
    const edit = drag.current;
    if (!edit || event.pointerId !== edit.pointer) return;
    const delta = p.map((v, i) => Math.round(v - edit.start[i]));
    const wanted = { ...edit.original };
    if (edit.handle) {
      if (edit.handle[0] === 0) {
        wanted.x += delta[0];
        wanted.w -= delta[0];
      } else wanted.w += delta[0];
      if (edit.handle[1] === 0) {
        wanted.y += delta[1];
        wanted.h -= delta[1];
      } else wanted.h += delta[1];
    } else {
      wanted.x += delta[0];
      wanted.y += delta[1];
    }
    // Sweep one cell at a time on each axis so fast pointers cannot tunnel.
    let current = edit.current;
    for (const axis of [0, 1]) {
      const pos = axis === 0 ? "x" : "y",
        size = axis === 0 ? "w" : "h";
      const field = edit.handle ? size : pos;
      const step = Math.sign(wanted[field] - current[field]);
      while (current[field] !== wanted[field]) {
        const next = { ...current };
        next[field] += step;
        if (edit.handle?.[axis] === 0) next[pos] -= step;
        if (!legal(env, next, limits)) break;
        current = next;
      }
    }
    edit.current = current;
    setPreview(current);
  }
  function finish(event: React.PointerEvent, accept: boolean) {
    const edit = drag.current;
    if (!edit || event.pointerId !== edit.pointer) return;
    drag.current = null;
    setPreview(null);
    if (accept && edit.current !== edit.original)
      commit({
        ...env,
        obstacles: env.obstacles.map((r) =>
          r.id === edit.original.id ? edit.current : r,
        ),
      });
  }
  return (
    <div className="map-surface">
      <canvas
        aria-label="Interactive terrain grid"
        ref={canvas}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={(e) => finish(e, true)}
        onPointerCancel={(e) => finish(e, false)}
        onPointerLeave={() => {
          hover.current = null;
          onCursor("—");
        }}
      />
      {resize && (
        <span className="resize-hint">Resize mode · drag a corner</span>
      )}
    </div>
  );
}
