# Safe Commit Guard (MVP)

MVP implementation for multi-layer local protections:

- `pre-commit`: scan staged files and staged diff
- `commit-msg`: scan commit message
- `pre-push`: scan outgoing commit range

## Install

```bash
python -m pip install -e .
cp hooks/pre-commit .git/hooks/pre-commit
cp hooks/commit-msg .git/hooks/commit-msg
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push
```

## CLI

```bash
scg scan staged --format text
scg scan commit-msg --msg-file .git/COMMIT_EDITMSG
scg scan pre-push --local-sha <sha> --remote-sha <sha>
scg confirm --id <gate_id>
scg rollback --id <gate_id>
```

Configuration is loaded from `safe_commit_guard/policy/rules.json`.
