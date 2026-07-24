# Project Instructions

## Graphify

This project has a knowledge graph at graphify-out/ with structural relationships between files.

Rules:
- Always consult graphify first, before reading the raw codebase. When graphify-out/graph.json exists, run `graphify query "<question>"` for codebase questions before Grep/Glob/Read-ing source files. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- After every prompt that changes the codebase, run `graphify update .` before ending the turn, so the graph is never stale (AST-only, no API cost).

## Project wiki

This project maintains a hand-written wiki at graphify-out/wiki/.

Rules:
- After any change to the codebase, update the relevant wiki page(s) so they stay accurate -- not just a changelog, but every page that describes what changed.
- After any change, add an entry to graphify-out/wiki/changelog.md (newest entry on top) with the date, a one-paragraph summary of the prompt that triggered the change, and a bullet list of what actually changed.
- Treat the documentation as written for a future session with no memory of this one, not shorthand notes to yourself.

## Commit messages

Rules:
- At the end of every prompt that changed the codebase, commit the changes locally -- do not wait to be asked. Stage the relevant files (check `git status` first for anything unexpected rather than a blind `-A`) and commit with a concise, imperative-mood subject line (~70 chars) plus bullet points for anything non-obvious.
- After the local commit, ask a plain yes/no question about pushing to the remote. Do not push without an explicit yes.

## Tests

Rules:
- Run the existing test suite before considering a task done, if one exists.
- Prefer adding a test for new, non-trivial logic, but do not let missing test infrastructure block finishing a small, low-risk change.

## Dependencies

Rules:
- Flag before adding a new dependency rather than adding it silently -- say what it is, why it is needed, and let the user confirm before installing it.
- Prefer a dependency already in use elsewhere in the project over introducing a new one that does the same job.

## Developer OS integration

This project is tracked by Developer OS. Its knowledge graph, wiki, and a RAG-source file live in `graphify-out/`, generated and kept updated by Developer OS's "Analyze" feature.

Rules:
- `graphify-out/wiki/` and `graphify-out/rag-records.json` follow the same conventions described above for the project wiki -- `rag-records.json` uses the same `{id, module, text}` record shape Developer OS's own app-knowledge does.
- After a meaningful update to `rag-records.json`, remember Developer OS has a "Bake Knowledge" action on this project's card that syncs it into its own searchable knowledge base -- re-run it if you want Developer OS's assistant grounded in the latest content. This is a manual step, not automatic.
