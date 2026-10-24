# Analysis and design

The user supplies a map and search settings. The program checks the terrain, prepares distances and visibility, runs the chosen algorithm, verifies the answer, and shows or saves it. There is no database and no external API in the running application.

## Use cases

```mermaid
flowchart LR
    U[Student or tester] --> A[Choose terrain and settings]
    U --> B[Run GA or MA]
    U --> C[Inspect map and metrics]
    U --> D[Save result and plot]
    U --> E[Run tests and experiments]
    B --> F[Verify coverage and base connectivity]
    D --> F
```

## Data flow

```mermaid
flowchart LR
    J[Terrain JSON] --> T[Validate terrain]
    S[Seed and settings] --> O[GA or MA]
    T --> P[Free points, distances, visibility and links]
    P --> O
    O --> V[Independent result verifier]
    V --> R[JSON result and CSV summaries]
    V --> W[Browser map and metrics]
    R --> G[Plots and report]
```

The optimiser uses precomputed matrices. The independent verifier rebuilds the checks from exported coordinates with scalar distances and line-of-sight checks. It does not reuse those matrices.

## Main data classes and functions

```mermaid
classDiagram
    class Terrain {
        name
        width
        height
        base
        sensing_range
        communication_range
        obstacles
        free(point)
        load(path)
    }
    class Problem {
        points
        cover
        links
        base_links
        evaluate(genes)
        state(genes)
        paths_from_base()
    }
    class Evaluation {
        sensors
        covered
        connected
        components
        feasible
        fitness(max_nodes)
    }
    class Settings {
        population
        generations
        mutation_rate
        crossover_rate
        local_steps
        evaluation_budget
    }
    Terrain "1" --> "1" Problem : builds
    Problem --> Evaluation : evaluates layouts
    Settings --> Problem : search uses settings and problem
```

`optimise` is a function, not a class. It uses `Problem` and `Settings`, and returns a JSON-compatible dictionary. GA and MA share this function. The `algorithm` option turns the local phase on or off.

## GA flow

```mermaid
flowchart TD
    A[Build a greedy feasible seed] --> B[Make the shared initial population]
    B --> C[Evaluate coverage, connectivity and sensor count]
    C --> D{Generation or evaluation limit reached?}
    D -->|Yes| J[Return best layout found]
    D -->|No| E[Keep two elites]
    E --> F[Tournament selection]
    F --> G[Set crossover]
    G --> H[Delete, add or move mutation]
    H --> I[Evaluate offspring]
    I --> K{Population full?}
    K -->|No| F
    K -->|Yes| C
    J --> L[Independently verify exported coordinates]
```

## MA flow

```mermaid
flowchart TD
    A[Use the same GA steps and initial population] --> B[Rank the offspring]
    B --> C[Choose up to four layouts]
    C --> D[Find coverage holes and sensors outside the base component]
    D --> E[Propose moves of one to three grid units]
    E --> F[If feasible, also try removing a sensor]
    F --> G[Evaluate every proposed full layout]
    G --> H[Accept a strict fitness improvement]
    H --> I{Local step limit reached or no improvement?}
    I -->|No| D
    I -->|Yes| J[Continue the next evolutionary cycle]
```

Local search does not teleport a sensor across the map. It moves towards a target by a small distance, rounds to a legal integer point, and rejects blocked or duplicate locations. It checks the whole layout because fixing one hole can create another hole or break a link.

## Browser request sequence

```mermaid
sequenceDiagram
    actor Student
    participant UI as Browser
    participant Server as Python HTTP server
    participant Search as Optimiser
    participant Check as Independent verifier
    Student->>UI: Choose map, algorithm, seed and generations
    UI->>Server: POST /api/solve
    Server->>Server: Validate input and acquire run lock
    Server->>Search: Build problem and run search
    Search-->>Server: Best layout, history and metrics
    Server->>Check: Check saved coordinates and metrics
    Check-->>Server: Verified metrics
    Server-->>UI: JSON result
    UI-->>Student: Map, metrics and download button
```

Only one search runs at a time in the demo server. An overlapping request gets a clear busy message. The HTTP server serves the demo page and two API routes; it does not expose arbitrary repository files.

## Exported result

| Field | Meaning |
|---|---|
| `algorithm`, `seed`, `settings` | How the run was made |
| `terrain` | Full map and range values |
| `coordinates`, `location_ids` | Chosen active sensor positions |
| `metrics` | Coverage, connectivity, components, count, feasibility |
| `history` | Best score and metrics after each recorded cycle |
| `evaluations` | Unique search fitness evaluations; cache repeats excluded |
| `runtime_seconds` | Search timing; shared geometry setup is outside it |
| `stop_reason` | Generation limit or evaluation budget |

The static SVG diagrams in `figures/` are also used in the printable report. Mermaid diagrams above remain editable in GitHub.
