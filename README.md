# Safe Commit Guard (MVP)

Safe Commit Guard 是一個本機端 policy engine，透過 Git hooks 在 commit/push 前阻擋高風險變更。

## 功能

- `pre-commit`: 掃描 staged files + staged diff
- `commit-msg`: 掃描 commit message 洩漏
- `pre-push`: 掃描即將推送的 commit range
- `confirm/rollback`: 針對 high-risk 變更做確認與 staged rollback

## 快速開始

### Linux / macOS

```bash
git clone <your-repo-url>
cd git_flow_design
./scripts/bootstrap.sh
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
git clone <your-repo-url>
cd git_flow_design
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

## 安裝 hooks

```bash
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

預設規則檔：`safe_commit_guard/policy/rules.json`。

## 測試

```bash
./scripts/smoke_test.sh
```

也可手動檢查：

```bash
echo 'fix: token=abcd1234' > /tmp/COMMIT_EDITMSG
scg scan commit-msg --msg-file /tmp/COMMIT_EDITMSG --format text
```
