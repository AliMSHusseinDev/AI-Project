import multiprocessing
from concurrent.futures import Future, ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from multiprocessing.managers import DictProxy
from threading import Lock
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Response
from pydantic import Field
from .environment import (
    Environment,
    Model,
    generate,
    generate_fresh,
    AREA_PER_OBSTACLE,
    MAX_BLOCKED_PERCENT,
    MAX_SIDE,
)
from .evolution import Settings, optimize
from .benchmarks import benchmark
from .validation import validate
from .exports import export


class Run(Model):
    environment: Environment
    mode: Literal["GA", "MA", "Comparison", "Benchmark"]
    settings: Settings = Field(default_factory=Settings)
    trials: int = Field(default=1, ge=1, le=10)


class Generation(Model):
    environment: Environment
    count: int = Field(ge=0, le=66)
    append: bool = False
    fresh: bool = False


@dataclass
class Job:
    request: Run
    future: Future
    state: DictProxy


def worker(request, state):
    def report(detail):
        if state.get("cancelled"):
            raise InterruptedError("Cancelled")
        state["progress"] = detail

    if request.mode == "Benchmark":
        return benchmark(
            request.trials,
            lambda done, total, label: report(
                dict(done=done, total=total, label=label)
            ),
        )
    results = []
    modes = ("GA", "MA") if request.mode == "Comparison" else (request.mode,)
    for index, algorithm in enumerate(modes):

        def progress(generation, evaluated, cost):
            fraction = max(
                generation / request.settings.generations,
                evaluated / request.settings.budget,
            )
            report(
                dict(
                    done=index + fraction,
                    total=len(modes),
                    label=f"{algorithm} · generation {generation} · {evaluated} evaluations",
                )
            )

        report(
            dict(done=index, total=len(modes), label=f"Preparing {algorithm} geometry")
        )
        results.append(
            optimize(request.environment, request.settings, algorithm, progress)
        )
    return results


@asynccontextmanager
async def lifespan(app):
    context = multiprocessing.get_context("spawn")
    with (
        context.Manager() as manager,
        ProcessPoolExecutor(max_workers=2, mp_context=context) as pool,
    ):
        app.state.manager, app.state.pool = manager, pool
        app.state.jobs = {}
        try:
            yield
        finally:
            for job in app.state.jobs.values():
                if not job.future.done():
                    job.state["cancelled"] = True
                    job.future.cancel()


app = FastAPI(title="AI Project", lifespan=lifespan)
lock = Lock()


@app.get("/api/health")
def health():
    return dict(
        status="ready",
        area_per_obstacle=AREA_PER_OBSTACLE,
        blocked_percent=MAX_BLOCKED_PERCENT,
        max_side=MAX_SIDE,
    )


@app.post("/api/environment")
def check_environment(environment: Environment):
    return environment


@app.post("/api/generate")
def generate_obstacles(body: Generation):
    try:
        if body.fresh and not body.append:
            return generate_fresh(body.environment, body.count)
        return generate(body.environment, body.count, body.append)
    except ValueError as error:
        raise HTTPException(422, str(error))


@app.post("/api/jobs", status_code=202)
def start(body: Run):
    with lock:
        jobs = app.state.jobs
        if sum(not job.future.done() for job in jobs.values()) >= 4:
            raise HTTPException(429, "Four runs are already active.")
        if len(jobs) >= 24:
            oldest = next(key for key, job in jobs.items() if job.future.done())
            del jobs[oldest]
        key = uuid4().hex
        state = app.state.manager.dict()
        future = app.state.pool.submit(worker, body, state)
        jobs[key] = Job(body, future, state)
    return dict(id=key)


def lookup(key):
    entry = app.state.jobs.get(key)
    if not entry:
        raise HTTPException(404, "Run expired or unknown.")
    return entry


@app.get("/api/jobs/{key}")
def status(key: str):
    job = lookup(key)
    if job.state.get("cancelled"):
        return dict(state="cancelled")
    if job.future.done():
        try:
            return dict(state="complete", result=job.future.result())
        except Exception as error:
            return dict(state="failed", error=str(error))
    return dict(state="running", progress=job.state.get("progress"))


@app.delete("/api/jobs/{key}")
def cancel(key: str):
    job = lookup(key)
    job.state["cancelled"] = True
    job.future.cancel()
    return dict(state="cancelled")


def current_results(key, environment):
    job = lookup(key)
    if (
        environment != job.request.environment
        or job.request.mode == "Benchmark"
        or not job.future.done()
        or job.state.get("cancelled")
        or job.future.exception()
    ):
        raise HTTPException(409, "A completed run for this environment is required.")
    return job.future.result()


@app.post("/api/jobs/{key}/validate")
def audit(key: str, environment: Environment):
    return [validate(environment, r) for r in current_results(key, environment)]


@app.post("/api/jobs/{key}/export/{format}")
def download(key: str, format: Literal["csv", "pdf", "png"], environment: Environment):
    results = current_results(key, environment)
    if len(results) != 2:
        raise HTTPException(409, "Run Comparison before exporting.")
    data, name, media = export(results, format)
    return Response(
        data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
