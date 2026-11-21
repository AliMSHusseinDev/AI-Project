export type Point = [number, number];
export type Rect = { id: string; x: number; y: number; w: number; h: number };
export type Env = {
  size: number;
  base: Point;
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
  fine?: { covered: number; total: number; percent: number };
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
  history: { generation: number; evaluations: number; cost: number }[];
  local: { attempts: number; improvements: number; evaluations: number };
};
export type Summary = {
  case: string;
  algorithm: string;
  runs: number;
  valid: number;
  best: number | null;
  mean: number | null;
  sd: number | null;
  seconds: number;
  coverage: number;
  connectivity: number;
  evaluations: number;
};
export type Limits = {
  area_per_obstacle: number;
  blocked_percent: number;
  max_side: number;
};
export const contains = (r: Rect, x: number, y: number) =>
  x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h;
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
    !contains(r, ...e.base) &&
    !others.some(
      (o) =>
        r.x < o.x + o.w &&
        o.x < r.x + r.w &&
        r.y < o.y + o.h &&
        o.y < r.y + r.h,
    ) &&
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
