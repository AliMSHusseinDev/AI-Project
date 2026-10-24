# Academic source checks

Six academic references are used in `docs/REPORT.md`. Their titles, authors, venues, pages, and DOI records were checked through Crossref on 24 October 2026. A selected metadata snapshot is in `crossref-metadata.json`. This avoids invented titles, authors, and DOI links.

## What was checked

| Key | Publication | Crossref result |
|---|---|---|
| meguerdichian2001 | Coverage problems in wireless ad-hoc sensor networks | Matching title and authors, INFOCOM, pages 1380–1387 |
| huang2005 | The Coverage Problem in a Wireless Sensor Network | Matching title and authors, journal volume 10(4), pages 519–528 |
| bai2006 | Deploying wireless sensors to achieve both coverage and connectivity | Matching title and five authors, MobiHoc, pages 131–142 |
| dhillon2003 | Sensor placement for effective coverage and surveillance in distributed sensor networks | Matching title and authors, WCNC, pages 1609–1614 |
| deb2002 | A fast and elitist multiobjective genetic algorithm: NSGA-II | Matching title and four authors, journal volume 6(2), pages 182–197 |
| neri2012 | Memetic algorithms and memetic computing optimization: A literature review | Matching title and authors, journal volume 2, pages 1–14 |

Some conference records do not include a `published` date in the selected response. Their years are given by the named conference and publication record; the snapshot does not pretend to contain missing fields.

## Access and review limits

Publisher pages were requested as recorded in `access-log.json`. They did not provide usable full text: the three IEEE requests returned empty 202 responses; ACM returned 403; Springer and Elsevier were blocked by the network proxy. The Crossref records did not supply abstracts for these six items.

The report therefore provides a short conceptual literature review, with checked references and a clear link to the implementation. It does not claim that the assistant read all six full papers, checked detailed proofs, or reproduced their experiments. It uses no unverified numeric results from those papers.

Before submission, each member should read the assigned paper through the university library or an authorised author copy, discuss it with the team, and expand or correct the review if needed. That human reading task is not recorded as completed. No publisher article PDFs are copied into this repository.

## Verify the metadata again

The DOI values in the report can be opened through the DOI resolver. The raw records can also be requested using:

```text
https://api.crossref.org/works/<DOI>
```

Crossref search briefly returned a rate limit during setup. Direct DOI lookups succeeded, and the saved snapshot contains those direct responses. A source's identity check is not proof that full text is open access.
