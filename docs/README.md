# Architecture Reference Docs

Interactive HTML reference files for each week of the AI-First Application Development bootcamp.
Click any component to see detailed explanation, code examples, and team sign-off notes.
All files include a navigation bar to switch between weeks and the CI/CD pipeline reference.

## Files

| File | Week | Contents |
|---|---|---|
| `week1_architecture.html` | Week 1 | config.py contract — ENVIRONMENT switch, make_call(), _Response, bug fix |
| `week2_architecture.html` | Week 2 | Prompt testing harness — HarnessRunner, variants, inputs, scorer, JSONL schema |
| `week3_architecture.html` | Week 3 | Stateful chatbot — MessageHistory, TokenTracker, Summarizer, config.py, streaming |
| `cicd_pipeline.html` | All weeks | GitHub Actions CI/CD pipeline, branch protection, developer workflow |

## Usage

Open any file directly in a browser — no server needed. All files are self-contained HTML.
Navigation bar at the top links all files together.

## Conventions

- One architecture file per week — created after the lab from real code
- cicd_pipeline.html updated whenever the pipeline changes
- All files committed to docs/ and version-controlled alongside the code
- File naming: `weekN_architecture.html`
