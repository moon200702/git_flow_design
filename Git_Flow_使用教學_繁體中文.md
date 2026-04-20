# Safe Commit Guard - Git Flow 完整使用教學

## 📖 目錄

1. [概述](#概述)
2. [安裝設置](#安裝設置)
3. [Git Flow 工作流程](#git-flow-工作流程)
4. [SCG 功能詳解](#scg-功能詳解)
5. [實戰案例](#實戰案例)
6. [常見問題](#常見問題)
7. [最佳實踐](#最佳實踐)

---

## 概述

### 什麼是 Safe Commit Guard？

Safe Commit Guard (SCG) 是一個**本機端策略引擎**，透過 Git hooks 在 commit 和 push 之前**自動阻止高風險變更**。

**主要功能：**
- ✅ 偵測危險檔案（.env、.key 等）
- ✅ 掃描機密資訊（API 密鑰、令牌等）
- ✅ 檢查提交訊息中的敏感數據
- ✅ 識別異常大型變更
- ✅ 識別可疑的 Base64 編碼字符串

### 為什麼在 Git Flow 中使用 SCG？

| 場景 | SCG 的作用 |
|------|----------|
| 開發分支 | 防止洩漏機密到版本控制 |
| 功能分支 | 在合併前檢查代碼質量 |
| 發佈分支 | 確保發佈代碼的安全性 |
| Hotfix 分支 | 快速修復時的安全檢查 |
| 推送到遠程 | 最後的防線，阻止推送高風險提交 |

---

## 安裝設置

### 第 1 步：克隆專案

```bash
git clone <your-repo-url>
cd git_flow_design
```

### 第 2 步：建立虛擬環境（推薦）

**Linux / macOS：**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)：**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 第 3 步：安裝 Safe Commit Guard

```bash
# 安裝到虛擬環境
pip install -e .

# 或使用 bootstrap 腳本
./scripts/bootstrap.sh
```

### 第 4 步：安裝 Git Hooks

```bash
# 複製 hooks 到 .git/hooks
cp hooks/pre-commit .git/hooks/pre-commit
cp hooks/commit-msg .git/hooks/commit-msg
cp hooks/pre-push .git/hooks/pre-push

# 設置為可執行
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg
chmod +x .git/hooks/pre-push
```

### 第 5 步：驗證安裝

```bash
# 測試 SCG 是否正常運作
scg scan staged --format text

# 預期結果：
# SCG: no findings (如果沒有問題)
```

✅ **安裝完成！**

### 🔧 常見安裝問題及解決方案

#### 問題 1: pip install -e . 失敗
**錯誤訊息：**
```
error: Multiple top-level packages discovered in a flat-layout: 
       ['hooks', 'source', 'safe_commit_guard']
```

**原因：** 虛擬環境創建失敗時留下的多餘文件

**解決方案：**
```bash
# 1. 清理多餘目錄
rm -rf source/

# 2. 重新創建虛擬環境
rm -rf .venv
python3 -m venv .venv

# 3. 啟動虛擬環境
source .venv/bin/activate

# 4. 安裝
pip install -e .
```

#### 問題 2: 找不到 scg 命令
**錯誤訊息：**
```
command not found: scg
```

**原因：** 未啟動虛擬環境

**解決方案：**
```bash
# 確保已啟動虛擬環境（看命令行前綴）
(.venv) jack@computer:~/git_flow_design$

# 如果沒有 (.venv) 前綴，執行：
source .venv/bin/activate

# 確認安裝
scg --help
```

#### 問題 3: 運行測試時模組找不到
**解決方案：**
```bash
# 1. 啟動虛擬環境
source .venv/bin/activate

# 2. 安裝 pytest
pip install pytest

# 3. 運行測試
python3 -m pytest tests/
```

---

## Git Flow 工作流程

### Git Flow 概述

Git Flow 是一個分支管理模型，包含 5 種分支類型：

```
main (主分支)
├── develop (開發分支)
│   ├── feature/* (功能分支)
│   ├── release/* (發佈分支)
│   └── hotfix/* (緊急修復分支)
```

### 分支用途

| 分支 | 用途 | 何時建立 | 何時合併 |
|------|------|--------|--------|
| main | 生產環境代碼 | 初始化 | 只合併 release 和 hotfix |
| develop | 開發版本 | 初始化 | 功能完成時 |
| feature/* | 新功能開發 | 從 develop | 開發完成後回到 develop |
| release/* | 發佈準備 | 從 develop | 發佈完成後回到 main 和 develop |
| hotfix/* | 緊急修復 | 從 main | 修復完成後回到 main 和 develop |

---

## SCG 功能詳解

### 1️⃣ Pre-commit Hook（提交前檢查）

**觸發時機：** 執行 `git commit` 時

**檢查內容：**
- 已暫存的檔案名稱
- 已暫存的代碼變更
- 檔案內容中的機密

**行為：**
```
❌ 發現 critical 級別問題 → 阻止 commit
⚠️  發現 high 級別問題 → 建立確認閘門（180 秒 TTL）
✅ 無問題 → 允許 commit
```

**使用場景（功能分支開發）：**
```bash
# 在功能分支上進行開發
git checkout -b feature/add-user-auth

# 編輯文件
echo "API_KEY=sk-1234567890" > config.env
git add config.env

# 嘗試提交
git commit -m "feat: add user auth"

# 結果：
# ❌ SCG findings:
# - [critical] file.risky at config.env: Risky file type/name staged
# ❌ COMMIT BLOCKED
```

### 2️⃣ Commit-msg Hook（提交訊息檢查）

**觸發時機：** 在編輯提交訊息後，但在提交前

**檢查內容：**
- 提交訊息中是否包含敏感模式（token=、password= 等）

**行為：**
```
❌ 發現敏感數據 → 阻止 commit
✅ 無敏感數據 → 允許 commit
```

**使用場景（提交訊息錯誤）：**
```bash
# 嘗試提交包含密鑰的訊息
git commit -m "fix: updated token=abc123xyz"

# 結果：
# ❌ SCG findings:
# - [critical] commitmsg.sensitive: Sensitive data pattern in commit message
# ❌ COMMIT BLOCKED
```

### 3️⃣ Pre-push Hook（推送前檢查）

**觸發時機：** 執行 `git push` 時

**檢查內容：**
- 即將推送的所有提交
- 每個提交的訊息和代碼變更
- 所有檔案內容

**行為：**
```
❌ 發現任何 critical 或 high 級別問題 → 阻止推送
✅ 無問題 → 允許推送
```

**使用場景（推送功能分支）：**
```bash
# 完成功能開發並推送
git push origin feature/add-user-auth

# SCG 檢查所有提交...

# 可能的結果：
# ✅ 全部通過 → 推送成功
# ❌ 發現問題 → 推送被阻止
```

### 4️⃣ 閘門系統（Confirm/Rollback）

當檢測到 **high 級別但沒有 critical 級別的問題**時，SCG 會建立一個**確認閘門**。

**閘門用途：**
- 給開發者時間審查發現
- 允許有意識地進行風險操作
- TTL 防止無期限有效

**閘門命令：**

```bash
# 確認閘門（允許此提交/推送）
scg confirm --id <gate_id>

# 結果：gate confirmed ✅

# 或者回滾（撤銷已暫存的變更）
scg rollback --id <gate_id>

# 結果：staged area rolled back ✅
```

---

## 實戰案例

### 案例 1：功能分支開發

#### 場景：添加新的用戶認證功能

```bash
# 1️⃣ 建立功能分支
git checkout develop
git pull origin develop
git checkout -b feature/user-auth

# 2️⃣ 開發功能
mkdir -p src/auth
cat > src/auth/login.py << 'EOF'
def authenticate(username, password):
    # 認證邏輯
    return True
EOF

# 3️⃣ 提交代碼
git add src/auth/login.py
git commit -m "feat: add user authentication module"

# ✅ SCG 檢查 - 無問題，提交成功

# 4️⃣ 推送到遠程
git push origin feature/user-auth

# ✅ SCG 檢查 - 無問題，推送成功

# 5️⃣ 建立 Pull Request
# 在 GitHub 上建立 PR，合併回 develop
```

**SCG 作用：** 防止開發者意外提交包含敏感訊息的代碼

---

### 案例 2：配置檔案錯誤

#### 場景：開發者不小心提交了 .env 檔案

```bash
# 1️⃣ 在功能分支開發
git checkout -b feature/config-setup

# 2️⃣ 建立環境配置（應該在 .gitignore 中）
cat > .env << 'EOF'
DATABASE_URL=postgres://user:pass@localhost/db
API_KEY=sk-123456789abcdef
SECRET_TOKEN=xyz789abc
EOF

git add .env
git commit -m "feat: add environment configuration"

# ❌ SCG 阻止提交：
# SCG findings:
# - [critical] file.risky at .env: Risky file type/name staged
# 
# SCG: no findings (在 critical 級別)
# ❌ COMMIT BLOCKED

# 3️⃣ 正確做法：使用 .env.example
git reset HEAD .env
git checkout .env  # 捨棄此檔案

cat > .env.example << 'EOF'
DATABASE_URL=postgres://user:pass@localhost/db
API_KEY=<your-api-key>
SECRET_TOKEN=<your-secret>
EOF

git add .env.example
git commit -m "feat: add environment config template"

# ✅ SCG 檢查通過，提交成功
```

**SCG 作用：** 防止意外提交敏感檔案

---

### 案例 3：發佈分支檢查

#### 場景：準備 v1.0.0 發佈

```bash
# 1️⃣ 從 develop 建立發佈分支
git checkout develop
git pull origin develop
git checkout -b release/1.0.0

# 2️⃣ 準備發佈（更新版本號、CHANGELOG 等）
echo "1.0.0" > version.txt
cat > CHANGELOG.md << 'EOF'
# Changelog

## [1.0.0] - 2026-04-20

### Added
- User authentication module
- Configuration management
- Error handling improvements

### Fixed
- Security vulnerabilities
EOF

git add version.txt CHANGELOG.md
git commit -m "chore: prepare v1.0.0 release"

# ✅ SCG 檢查通過

# 3️⃣ 推送發佈分支
git push origin release/1.0.0

# ✅ SCG 再次檢查，無問題

# 4️⃣ 建立 PR 回到 main
# GitHub PR: merge release/1.0.0 into main
# - SCG 再次檢查
# - 代碼審查
# - 批准並合併

# 5️⃣ 打標籤
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# 6️⃣ 同步回 develop
git checkout develop
git pull origin develop
git merge release/1.0.0
git push origin develop
```

**SCG 作用：** 確保發佈代碼的完整性和安全性

---

### 案例 4：緊急修復

#### 場景：生產環境發現 bug，需要快速修復

```bash
# 1️⃣ 從 main 建立 hotfix 分支
git checkout main
git pull origin main
git checkout -b hotfix/security-patch

# 2️⃣ 修復 bug
cat > src/auth/security.py << 'EOF'
# 安全修復程式碼
import hashlib

def secure_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()
EOF

git add src/auth/security.py
git commit -m "fix: apply security patch for authentication"

# ✅ SCG 檢查通過

# 3️⃣ 推送修復
git push origin hotfix/security-patch

# ✅ SCG 檢查通過

# 4️⃣ 建立 PR 回到 main（緊急）
# PR 標題：[HOTFIX] Security patch for auth module

# 5️⃣ 同時建立 PR 回到 develop
# 確保修復也應用到開發分支

# 6️⃣ 合併並更新版本
git checkout main
git merge hotfix/security-patch
git tag -a v1.0.1 -m "Hotfix: security patch"
git push origin main v1.0.1

# 7️⃣ 清理本地分支
git branch -d hotfix/security-patch
```

**SCG 作用：** 確保緊急修復不會引入新的安全問題

---

### 案例 5：高熵令牌檢測

#### 場景：開發者不小心提交了高熵字符串（可能是令牌）

```bash
# 開發代碼
echo "api_response = fetch_with_token('aB1xY9zQ4k7mNpR2vW5tUsXyZ8a9b')" >> app.py
git add app.py

git commit -m "feat: add API call with token"

# ❌ SCG 警告：
# SCG findings:
# - [high] secret.entropy at app.py:5: High-entropy token detected
# 
# SCG gate required. Confirm within TTL: scg confirm --id abc123def456

# 有兩個選擇：

# 選擇 1️⃣ ：確認（如果確實是安全的）
scg confirm --id abc123def456

# ✅ gate confirmed
# ✅ commit 成功

# 選擇 2️⃣ ：回滾（如果需要修改）
scg rollback --id abc123def456

# ✅ staged area rolled back
# 修改代碼，移除敏感令牌
echo "api_response = fetch_with_token(get_token())" >> app.py
git add app.py
git commit -m "feat: add API call with secure token"

# ✅ commit 成功
```

**SCG 作用：** 偵測並警告可疑的高熵字符串

---

### 案例 6：大型變更檢測

#### 場景：執行大規模重構，生成大量變更

```bash
# 重構大型模組
git checkout -b feature/major-refactor

# 重寫 500+ 行代碼
# ... 編輯多個檔案 ...

git add -A
git commit -m "refactor: reorganize module structure"

# ⚠️ SCG 警告：
# SCG findings:
# - [high] diff.too_large at staged-diff: Large patch detected (850 added lines)
# 
# SCG gate required. Confirm within TTL: scg confirm --id xyz789abc

# 評估是否合理...

# 選擇 1️⃣ ：確認（大型重構是計畫中的）
scg confirm --id xyz789abc

# ✅ gate confirmed
# ✅ commit 成功

# 選擇 2️⃣ ：分割提交（更好的做法）
scg rollback --id xyz789abc

# ✅ staged area rolled back

# 分割成多個更小的提交：
git add src/module1.py
git commit -m "refactor: reorganize module1"
# ✅ 第一個 commit

git add src/module2.py
git commit -m "refactor: reorganize module2"
# ✅ 第二個 commit

# 這樣每個提交都更容易審查
```

**SCG 作用：** 建議開發者分割大型變更以提高代碼審查效率

---

## 常見問題

### Q1：為什麼我的提交被阻止了？

**A：** 檢查 SCG 的輸出信息：

```bash
# 查看詳細的發現列表
scg scan staged --format json

# 可能的原因：
# 1. 提交了敏感檔案（.env、.key 等）
# 2. 代碼中有機密信息（密鑰、令牌等）
# 3. 提交訊息包含敏感數據
# 4. 變更太大（> 800 行）
# 5. 包含可疑的 Base64 字符串
```

### Q2：如何跳過 SCG 檢查？

**A：** ⚠️ **不推薦！** 但如果必要：

```bash
# 跳過 pre-commit hook
git commit -m "..." --no-verify

# ⚠️ 風險：這會跳過 pre-commit 檢查
# ✅ 仍然會在 pre-push 時檢查

# 如果真的需要跳過，必須指定原因：
git commit -m "... [SKIP-SCG: reason for skipping]" --no-verify
```

### Q3：我需要提交敏感檔案怎麼辦？

**A：** 正確的做法：

```bash
# 方案 1️⃣ ：建立 .gitignore
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
git add .gitignore
git commit -m "chore: add .gitignore"

# 方案 2️⃣ ：使用 git-crypt 加密敏感檔案
git-crypt init
echo ".env filter=git-crypt diff=git-crypt" >> .gitattributes
git add .env .gitattributes
git commit -m "chore: add encrypted .env"

# 方案 3️⃣ ：使用環境變數或秘密管理服務
# 不要將敏感資料提交到版本控制
```

### Q4：什麼是 gate？我應該確認還是回滾？

**A：** Gate 用於高風險但可能合法的變更：

```
確認 (confirm)     → 我已審查，這是安全的
回滾 (rollback)   → 撤銷已暫存的變更，我需要修改代碼
```

**決策樹：**

```
是否是故意的變更？
├─ 是 → 確認 (confirm)
│       └─ commit/push 成功
└─ 否 → 回滾 (rollback)
        └─ 修改代碼
        └─ 重新 add
        └─ 重新 commit
```

### Q5：Gate 過期了怎麼辦？

**A：** Gate 有 180 秒的 TTL，過期後需要重新提交：

```bash
# 嘗試確認已過期的 gate
scg confirm --id abc123

# ❌ gate expired

# 解決方案：重新進行變更
git reset  # 取消暫存
# 重新進行修改並提交
git add ...
git commit ...

# 系統會建立新的 gate
```

### Q6：如何查看 SCG 的規則配置？

**A：** 查看策略檔案：

```bash
# 查看預設規則
cat safe_commit_guard/policy/rules.json

# 自定義規則
cat > custom_rules.json << 'EOF'
{
  "risky_extensions": [".env", ".key", ".pem"],
  "risky_filenames": [".env", ".env.local", ".aws"],
  "secret_patterns": [
    "token=\\w+",
    "password=\\w+",
    "api_key=\\w+"
  ],
  "entropy_threshold": 4.2,
  "min_entropy_length": 20,
  "max_added_lines": 800,
  "confirm_ttl_seconds": 180
}
EOF

# 使用自定義規則
scg scan staged --policy-file custom_rules.json
```

### Q7：如何在團隊中強制使用 SCG？

**A：** 幾種方式：

```bash
# 方式 1️⃣ ：在專案中提交 hooks
# （所有隊員克隆後自動啟用）
git add hooks/
git commit -m "chore: add SCG hooks"

# 方式 2️⃣ ：在 README 中記錄設置步驟
# （參考本教學的「安裝設置」部分）

# 方式 3️⃣ ：在 CI/CD 管道中驗證
# （在合併前檢查）
scg scan pre-push --local-sha $HEAD --remote-sha $BASE

# 方式 4️⃣ ：建立團隊策略
# 在 .github/CONTRIBUTING.md 中說明要求
```

---

## 最佳實踐

### 1️⃣ 提交訊息規範

```bash
# ❌ 不好：
git commit -m "fix bug"
git commit -m "token=abc123 update"

# ✅ 好：
git commit -m "fix: correct authentication logic in login module"
git commit -m "feat: add new API endpoint for user profile"
git commit -m "docs: update API documentation"
```

**規則：**
- 使用清晰的動詞（feat, fix, docs, refactor 等）
- 簡短的標題（< 50 字符）
- 不包含敏感信息

### 2️⃣ 分割大型變更

```bash
# ❌ 不好：一次提交 800+ 行
git add -A
git commit -m "refactor: major refactoring"

# ✅ 好：分多次提交
git add src/module1.py
git commit -m "refactor: reorganize module1"

git add src/module2.py
git commit -m "refactor: reorganize module2"

git add tests/
git commit -m "test: add tests for reorganized modules"
```

**優點：**
- 更容易審查
- 更容易追蹤問題
- 更容易回滾特定變更

### 3️⃣ 使用功能分支

```bash
# ❌ 不好：直接在 develop 上工作
git checkout develop
# ... 編輯檔案 ...
git commit -m "..."

# ✅ 好：建立功能分支
git checkout -b feature/my-feature
# ... 編輯檔案 ...
git commit -m "..."
git push origin feature/my-feature
# 建立 PR 進行代碼審查
```

**優點：**
- 主分支保持穩定
- 便於代碼審查
- 支持並行開發

### 4️⃣ 定期同步主分支

```bash
# 在長期功能分支上，定期同步 develop
git checkout feature/my-feature
git fetch origin
git merge origin/develop

# 如果有衝突，解決衝突並提交
# 這樣可以及早發現集成問題
```

### 5️⃣ 代碼審查清單

進行代碼審查時，檢查：

- ✅ 沒有敏感信息（密鑰、令牌、密碼）
- ✅ 沒有危險的檔案（.env、.key、.pem）
- ✅ 提交訊息清晰且描述性強
- ✅ 變更在合理範圍內（不是一次性的 1000+ 行）
- ✅ 有相應的測試
- ✅ 文檔已更新
- ✅ 遵循項目代碼風格

### 6️⃣ 開發工作流程示例

```bash
# 1️⃣ 初始化
git clone <repo>
cd git_flow_design
source .venv/bin/activate  # 啟用虛擬環境

# 2️⃣ 開始新功能
git checkout -b feature/new-feature

# 3️⃣ 開發迭代
# ... 編輯檔案 ...
git add src/
git commit -m "feat: add new feature part 1"

# ... 編輯更多檔案 ...
git add tests/
git commit -m "test: add tests for new feature"

# 4️⃣ 本地測試
python3 -m pytest tests/

# 5️⃣ 推送
git push origin feature/new-feature

# 6️⃣ 建立 PR 並等待審查
# SCG 會檢查提交...

# 7️⃣ 代碼審查反饋
# ... 根據反饋修改 ...
git add ...
git commit -m "fix: address review feedback"
git push origin feature/new-feature

# 8️⃣ 合併
# PR 被批准並合併到 develop

# 9️⃣ 清理本地分支
git checkout develop
git pull origin develop
git branch -d feature/new-feature
```

---

## 故障排除

### 問題 1：Hook 沒有執行

**診斷：**
```bash
# 檢查 hook 是否存在
ls -la .git/hooks/pre-commit
ls -la .git/hooks/commit-msg
ls -la .git/hooks/pre-push

# 檢查是否可執行
file .git/hooks/pre-commit
```

**解決方案：**
```bash
# 重新安裝 hooks
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

cp hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg

cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### 問題 2：scg 命令找不到

**診斷：**
```bash
which scg
scg --version
```

**解決方案：**
```bash
# 確保已安裝
pip install -e .

# 檢查虛擬環境
source .venv/bin/activate
which scg

# 如果還是不行，使用完整路徑
python3 -m safe_commit_guard.cli scan staged
```

### 問題 3：假陽性（誤報）

**情況：** 合法的代碼被標記為有問題

**解決方案：**
```bash
# 方案 1️⃣ ：確認並提交
scg confirm --id <gate_id>

# 方案 2️⃣ ：自定義規則
# 修改 safe_commit_guard/policy/rules.json
# 調整閾值或模式

# 方案 3️⃣ ：與團隊討論
# 報告誤報，討論是否需要調整規則
```

---

## 快速參考

### 常用命令

```bash
# 掃描已暫存的變更
scg scan staged --format text

# 掃描已暫存的變更（JSON 格式）
scg scan staged --format json

# 掃描提交訊息
scg scan commit-msg --msg-file .git/COMMIT_EDITMSG

# 掃描將要推送的提交
scg scan pre-push --local-sha HEAD --remote-sha origin/develop

# 確認高風險變更
scg confirm --id <gate_id>

# 回滾已暫存的變更
scg rollback --id <gate_id>
```

### 分支命令

```bash
# 建立功能分支
git checkout -b feature/<feature-name>

# 建立發佈分支
git checkout -b release/<version>

# 建立 hotfix 分支
git checkout -b hotfix/<issue-name>

# 推送分支
git push origin <branch-name>

# 刪除本地分支
git branch -d <branch-name>

# 刪除遠程分支
git push origin --delete <branch-name>
```

---

## 總結

**Safe Commit Guard 在 Git Flow 中的作用：**

| 階段 | SCG 檢查 | 目的 |
|------|---------|------|
| 本地開發 | pre-commit | 防止不安全的提交 |
| 提交訊息 | commit-msg | 防止敏感資訊洩漏 |
| 準備推送 | pre-push | 最後防線檢查 |
| Code Review | 手動檢查 | 確保無遺漏 |

**核心原則：**
- ✅ 永遠不要在版本控制中提交敏感信息
- ✅ 使用 .gitignore 排除敏感檔案
- ✅ 定期同步主分支
- ✅ 分割大型變更為小型提交
- ✅ 進行代碼審查
- ✅ 使用清晰的提交訊息

**記住：** SCG 是**防御工具，不是替代品**。最好的安全來自於：
1. 開發人員的意識
2. 良好的編碼習慣
3. 代碼審查
4. 自動化工具（如 SCG）

---

## 延伸資源

- [Git Flow 詳細指南](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
- [Safe Commit Guard 文檔](../README.md)
- [Git Hooks 文檔](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [最佳實踐指南](../docs/best-practices.md)

---

**最後更新：** 2026-04-20  
**版本：** 1.0  
**語言：** 繁體中文  
**狀態：** ✅ 完成
