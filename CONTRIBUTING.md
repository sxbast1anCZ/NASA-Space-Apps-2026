# Contributing

## Language

Everything in this repository is written in English: commit messages, code, comments, documentation, branch names, issues and pull requests.

## Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/): `<type>: <summary>`, e.g. `feat: add burn calendar heatmap`.
- Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Write the summary in the imperative mood, under 72 characters.
- One logical change per commit.

## Pull requests

1. **No direct pushes to `main`.** One branch per piece of work: `feat/m2-ratio-per-regime`, `fix/m4-calendar-colors`.
2. **Small and frequent.** Open a pull request when one sub-step works, not when the module is finished.
3. **Before opening:** `git pull --rebase origin main`, then run `pytest` if you touched `scripts/` or `tests/`.
4. **Description:** what changed, how you checked it, and any decision that affects another module.
5. **Review:** wait for the audit comment and read it before merging.
6. **Merge with squash**, then delete the branch.
7. **Never commit** data, `.env`, keys, or anything under `NASA_Data_Sources/` and `External_Data_Sources/`.
8. Edit only the files of your task. Shared files (`README.md`, `CLAUDE.md`, `requirements.txt`, `.gitignore`) change in small pull requests; add lines to `requirements.txt` at the end.
9. A notebook has one owner. Run it top to bottom and commit it with its outputs.
