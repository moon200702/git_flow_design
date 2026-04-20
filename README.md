# Safe Commit Guard (MVP)

Safe Commit Guard 是一個本機多層防護工具，針對 AI 加速開發情境提供：

- `pre-commit`: 掃描 staged files + staged diff
- `commit-msg`: 掃描 commit message 洩漏
- `pre-push`: 掃描即將推送的 commit range
- `confirm/rollback`: 針對 high-risk 變更做確認與 staged rollback

## 1) Clone 後建立開發環境

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

## 2) 安裝 Git hooks

```bash
cp hooks/pre-commit .git/hooks/pre-commit
cp hooks/commit-msg .git/hooks/commit-msg
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push
```

> Windows 可用 Git Bash 執行上面三個 `cp`/`chmod`，或手動複製到 `.git/hooks/`。

## 3) CLI 使用方式

```bash
scg scan staged --format text
scg scan commit-msg --msg-file .git/COMMIT_EDITMSG
scg scan pre-push --local-sha <sha> --remote-sha <sha>
scg confirm --id <gate_id>
scg rollback --id <gate_id>
```

預設規則檔：`safe_commit_guard/policy/rules.json`。

## 4) 快速測試（你 clone 到 PC 後建議先跑）

### A. 內建 smoke tests

```bash
./scripts/smoke_test.sh
```

### B. 手動測試 commit-msg 阻擋

```bash
echo 'fix: token=abcd1234' > /tmp/COMMIT_EDITMSG
scg scan commit-msg --msg-file /tmp/COMMIT_EDITMSG --format text
# 預期：exit code = 1，且顯示 commitmsg.sensitive
```

### C. 手動測試 staged risky file 阻擋

```bash
echo 'A=B' > .env
git add .env
scg scan staged --format text
# 預期：exit code = 1，且顯示 file.risky
```

## 5) pre-commit framework 整合（可選）

專案附帶 `.pre-commit-config.yaml`（local hook 範例），你可以再加入 gitleaks/detect-secrets 進一步強化。
