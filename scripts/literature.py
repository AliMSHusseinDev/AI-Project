"""Review notes from the publisher's archived full texts."""

from xml.sax.saxutils import escape
from report_layout import paragraph, heading, table, save

REVISION = "9bc052c2c9d93494940a9b8ddb75dce7d41ef0dd"
PAPERS = [
    (
        "02828",
        "PySensors: A Python package for sparse sensor placement",
        "Brian M. de Silva, Krithika Manohar, Emily Clark, Bingni W. Brunton, Steven L. Brunton, and J. Nathan Kutz",
        2021,
        "Where should a small set of sensors go if the aim is to recover a signal or tell classes apart? A sensor may be costly. The number of possible sets grows fast.",
        "The authors reduce the data to a smaller set of patterns. They select measurement sites using these patterns. Different routines support signal recovery and classification.",
        "One package brings the two tasks together. Its examples reproduce earlier placement studies. Users can vary the sensor count and the data basis and check the effect on prediction.",
        "Both projects choose a subset of sites. The definition of a good subset changes the answer. PySensors scores information from measurements. Fieldlab needs every free cell to be visible and every radio to have a route. Our GA and MA therefore score both conditions.",
    ),
    (
        "00032",
        "Advanced viewshed analysis: a Quantum GIS plug-in for the analysis of visual landscapes",
        "Zoran Cuckovic",
        2016,
        "A viewshed is the area visible from one point. A yes or no answer for one view gives little detail about how a whole landscape links observation sites.",
        "The plug-in runs repeated viewshed calculations on elevation data. It can measure how far a place lies below the visible horizon and map sites that can see one another.",
        "The paper shows a network of sites joined by visibility. It also describes support for repeated views from many points. Figure 1 is an example of the network output.",
        "This explains why a range circle alone is too broad. Fieldlab also checks a path between endpoints. Here the blockers are flat rectangles. We store clear paths for repeated GA and MA scores.",
    ),
    (
        "06915",
        "DiffeRT2d: A Differentiable Ray Tracing Python Framework for Radio Propagation",
        "Jérome Eertmans, Claude Oestges, and Laurent Jacques",
        2024,
        "How can researchers test radio paths and adjust a small scene without an expensive closed simulator?",
        "The authors implement two-dimensional ray tracing in Python with JAX. Their methods trace paths and can compute how a result changes as scene parameters move.",
        "Figure 2 shows received power for single-reflection paths around a reflecting surface. The paper also reports visible edge noise from the path search. Reflected signals can reach places without a direct path.",
        "Fieldlab assumes a blocked direct path gives no radio link. This paper gives a concrete limit of that assumption. Its reflection model would change which relays GA or MA needs.",
    ),
    (
        "07322",
        "pycellga: A Python package for improved cellular genetic algorithms",
        "Sevgi Akten Karakaya and Mehmet Hakan Satman",
        2025,
        "A genetic search can lose variety as good individuals spread. Cellular algorithms limit which individuals can share genes.",
        "The population lives on a grid. Nearby individuals take part in local selection. The package supports different chromosome types and user-selected crossover and mutation.",
        "The authors give a worked sum-of-squares example with tournament selection. They show how to plug an objective and operators into a cellular GA. The worked example has a known minimum.",
        "A population grid describes which parents meet. Our terrain grid describes physical sensor sites. Our tournament draws from the whole population. Crossover uses sensor coordinates. The paper helps explain why representation and operator choice matter.",
    ),
    (
        "04723",
        "Metaheuristics: A Julia Package for Single- and Multi-Objective Optimization",
        "Jesús-Adolfo Mejía-de-Dios and Efrén Mezura-Montes",
        2022,
        "Researchers need common tools to compare search methods when a problem has bounds, constraints, or several goals.",
        "The package gives several search algorithms the same interface. It includes test functions, measures of quality, and methods for handling constraints.",
        "In the worked bounded example, differential evolution reports a minimum of zero after 27,500 function calls. This is one run on its test function. The authors note that random runs can differ.",
        "Counting generations alone can favor MA because it scores extra neighbors. We charge every new local score to the same budget as GA. We record both the number of calls that compute a score and the elapsed time.",
    ),
    (
        "08862",
        "Ivy: A Data Acquisition System for Distributed Sensor Networks Supporting Remote Configuration and Software Updates",
        "Moritz Makowski and Jia Chen",
        2025,
        "Remote environmental sensors produce measurements and logs. Maintaining their software in the field is costly.",
        "Ivy provides a reusable design for software on sensor nodes. A team adds code for its own hardware. Nodes can receive configuration and software changes remotely.",
        "The paper presents the design after several iterations of field networks. The authors describe a project with 20 autonomous greenhouse-gas nodes. The contribution is a reusable acquisition design.",
        "A sensor has value only if its data reaches a collector. This motivates Fieldlab's route check. Fieldlab searches for placement and relays. Ivy describes the software that runs after deployment.",
    ),
]


def write_reviews(folder):
    for index, (identifier, title, authors, year, *notes) in enumerate(PAPERS, 1):
        url = f"https://raw.githubusercontent.com/openjournals/joss-papers/{REVISION}/joss.{identifier}/10.21105.joss.{identifier}.pdf"
        body = [
            paragraph(escape(authors) + f" ({year}). Journal of Open Source Software."),
            paragraph(
                f'<link href="{url}" color="#17674e"><u>Read the paper in the journal archive</u></link>   |   DOI 10.21105/joss.{identifier}',
                "small",
            ),
        ]
        for label, text in zip(
            ["Problem", "Proposed method", "Key results", "Relation to our project"],
            notes,
        ):
            body.extend([heading(label), paragraph(text)])
        name = title.replace(":", " -")
        save(folder / f"{index}.{name}.pdf", title, body, "Literature review")
    rows = [["Member Name", "Member ID", "Member Number", "Literature"]] + [
        ["[Name]", "[ID]", i, title] for i, (_, title, *_) in enumerate(PAPERS, 1)
    ]
    save(
        folder / "Team Literature Assignment.pdf",
        "Team literature assignment",
        [
            paragraph(
                "Each member leads the discussion of one paper. Fill in names and IDs after team registration."
            ),
            table(rows, [83, 61, 70, 276]),
        ],
        "Team allocation",
    )
