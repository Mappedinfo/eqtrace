# Citing and archiving EqTrace

EqTrace is a personal side project by **Shiqi Wang**. Public contact: **qtec@outlook.com**. Public author metadata contains no institutional affiliation, address, or ORCID.

## Cite the software now

`CITATION.cff` is the canonical software citation metadata. GitHub uses this file to provide **Cite this repository**, including APA and BibTeX formats. A DOI is not required for that feature. [GitHub documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)

> Wang, S. (2026). *EqTrace: Inspectable Contracts between Papers, Code, and Execution* (Version 0.1.0) [Computer software]. GitHub. https://github.com/Mappedinfo/eqtrace/releases/tag/v0.1.0

A BibLaTeX-compatible `@software` entry is available in [CITATION.bib](../CITATION.bib). Use the version actually used in the research. The technical report documents the software; it has not undergone peer review.

## Register a persistent archive

**Status: no Zenodo record or DOI has been registered for this release.** Repository preparation and a GitHub release alone do not mint a DOI.

Zenodo can archive public GitHub software releases and issue DOIs. Connecting a repository requires a Zenodo account and GitHub authorization; an organization may need to approve access for the integration. [GitHub archiving guide](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content)

For the first archive:

1. Sign in to [Zenodo](https://zenodo.org/login/) and authorize the GitHub integration.
2. Open [Zenodo's GitHub settings](https://zenodo.org/account/settings/github/) and enable `Mappedinfo/eqtrace`. Review organization access if requested.
3. Prepare a new release from the corrected current source. Update `version` and `date-released` consistently in package and citation metadata. Do not assume an older release will be retroactively archived.
4. Check the metadata before release: creator **Shiqi Wang**, software title, MIT license, software resource type, description, and the exact version. Leave affiliation, location, ORCID, grants, and institutional fields empty. The contact email is already in the paper and project documentation.
5. Publish that GitHub release, check the resulting Zenodo archive, and verify the assigned DOI resolves to the intended files and author metadata.
6. Only then add the actual **version DOI** to `CITATION.cff`, the BibTeX entry, and the recommended citation. Use the **concept DOI** for an optional project-wide badge or general project reference. Regenerate the README examples from the verified metadata.

Zenodo's creator schema makes affiliation and ORCID optional. Its API can reserve a DOI for a draft, but the DOI is registered only upon publication. A reserved identifier is not an already published citation. [Zenodo metadata documentation](https://developers.zenodo.org/#representation)

The integration accepts `CITATION.cff`. This project deliberately avoids a duplicate `.zenodo.json`: when both exist, Zenodo uses `.zenodo.json` and ignores the citation file, creating another metadata source to keep synchronized. [Zenodo citation-file documentation](https://help.zenodo.org/docs/github/describe-software/citation-file/)

## Version DOI and concept DOI

A version DOI identifies an exact archived version and is the normal choice for reproducible research citations. A concept DOI identifies the evolving project across versions and resolves to the latest version. Neither identifier certifies software correctness or peer review. [Zenodo versioning guidance](https://zenodo.org/help/versioning)

## Software and report

Start with one software record containing the versioned source and its documentation. A separate report DOI is optional if the report later becomes an independently released research output. Link the records if that happens; do not label a software archive as a peer-reviewed article.
