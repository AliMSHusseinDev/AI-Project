export type Point = [number, number];
export type Rect = { id: string; x: number; y: number; w: number; h: number };
export type Env = {
  size: number;
  base: Point;
  base_margin: number;
  sensing: number;
  communication: number;
  spacing: number;
  seed: number;
  obstacles: Rect[];
};
export type Layers = {
  points: boolean;
  holes: boolean;
  links: boolean;
  sensing: boolean;
  communication: boolean;
};
export type Audit = {
  passed: boolean;
  checks: Record<string, boolean>;
  coverage: number;
  connectivity: number;
};
export type Result = {
  algorithm: string;
  positions: Point[];
  holes: Point[];
  unreachable: Point[];
  links: [Point, Point][];
  feasible: boolean;
  possible: boolean;
  count: number;
  coverage: number;
  connectivity: number;
  seconds: number;
  cost: number;
  evaluations: number;
  generations: number;
  termination: string;
  history: { generation: number; evaluations: number; cost: number }[];
  local: { attempts: number; improvements: number; evaluations: number };
};
export type Limits = {
  area_per_obstacle: number;
  blocked_percent: number;
  max_side: number;
};
export const contains = (r: Rect, x: number, y: number) =>
  x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h;
// Empty IDs cannot occur in a validated obstacle file.
export const BASE_ID = "";
export function baseRect(e: Env): Rect {
  const margin = e.base_margin;
  return {
    id: BASE_ID,
    x: e.base[0] - margin,
    y: e.base[1] - margin,
    w: 2 * margin + 1,
    h: 2 * margin + 1,
  };
}
export const overlaps = (a: Rect, b: Rect) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
export function legalBase(e: Env, r: Rect) {
  return (
    r.x >= 0 &&
    r.y >= 0 &&
    r.x + r.w <= e.size &&
    r.y + r.h <= e.size &&
    r.w === r.h &&
    r.w >= 1 &&
    r.w <= 11 &&
    r.w % 2 === 1 &&
    !e.obstacles.some((o) => overlaps(o, r))
  );
}
export function terrainStats(e: Env, limits: Limits) {
  const cells = e.size ** 2,
    total = Math.ceil(e.size / e.spacing) ** 2;
  let area = 0,
    blocked = 0;
  function samples(start: number, length: number) {
    return (
      Math.ceil((start + length) / e.spacing) - Math.ceil(start / e.spacing)
    );
  }
  for (const r of e.obstacles) {
    area += r.w * r.h;
    blocked += samples(r.x, r.w) * samples(r.y, r.h);
  }
  const capacity = Math.min(
    Math.floor(cells / limits.area_per_obstacle) - e.obstacles.length,
    Math.floor((cells * limits.blocked_percent) / 100) - area,
    cells - area - baseRect(e).w ** 2,
  );
  return { cells, total, area, blocked, available: total - blocked, capacity };
}
export function legal(e: Env, r: Rect, limits: Limits) {
  const others = e.obstacles.filter((o) => o.id !== r.id);
  return (
    r.x >= 0 &&
    r.y >= 0 &&
    r.w >= 1 &&
    r.h >= 1 &&
    Math.max(r.w, r.h) <= limits.max_side &&
    r.x + r.w <= e.size &&
    r.y + r.h <= e.size &&
    !overlaps(r, baseRect(e)) &&
    !others.some((o) => overlaps(o, r)) &&
    100 * (others.reduce((sum, o) => sum + o.w * o.h, 0) + r.w * r.h) <=
      limits.blocked_percent * e.size ** 2
  );
}
export async function api(path: string, body?: unknown, method?: string) {
  const response = await fetch("/api/" + path, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json();
    throw Error(
      typeof error.detail === "string"
        ? error.detail
        : (error.detail?.[0]?.msg ?? "Request failed"),
    );
  }
  return response.json();
}
export const saveFile = (blob: Blob, name: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
};
