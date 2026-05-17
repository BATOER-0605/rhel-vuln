# セットアップ手順書

本書は `rhel-vuln` を初めて動かすための手順を、前提環境からトラブルシュートまで網羅したものです。

---

## 1. 前提環境

| 項目 | 要件 |
|---|---|
| OS | Linux / macOS / Windows (WSL2 推奨) |
| Python | **3.12 系** (推奨: **3.12.13**) — `python --version` で確認 |
| pip | 24 以上を推奨 (`python -m pip install --upgrade pip`) |
| ネットワーク | `https://access.redhat.com` への HTTPS 到達性 |
| メモリ | 256 MB 以上で十分 |
| ディスク | 約 100 MB (依存パッケージ含む) |

> `pyproject.toml` は `requires-python = ">=3.12,<3.13"` で 3.12 系のみを公式サポートとしています。
> 3.11 以下では `pip install` が失敗します。

> プロキシ環境下の場合は別途「9. トラブルシュート」を参照してください。

---

## 2. リポジトリ取得

```bash
git clone https://github.com/batoer-0605/rhel-vuln.git
cd rhel-vuln
```

特定ブランチを取得する場合:

```bash
git fetch origin claude/rhel-vulnerability-app-njZF1
git checkout claude/rhel-vulnerability-app-njZF1
```

---

## 2.5. Python 3.12.13 の導入 (pyenv 推奨)

システム標準の Python が 3.12 系でない場合は、`pyenv` でリポジトリ専用に固定するのが安全です。

```bash
# pyenv 未導入なら https://github.com/pyenv/pyenv-installer を参照

pyenv install 3.12.13            # 既にあればスキップされます
cd rhel-vuln
pyenv local 3.12.13              # .python-version を作成し当該ディレクトリで固定
python --version                  # => Python 3.12.13
```

> `pyenv local` が出力する `.python-version` ファイルは個人のローカル設定なので
> 通常はコミットしません (リポジトリでは `.gitignore` に含めるか、必要に応じて
> チームで取り扱いを決めてください)。

Windows の場合は [pyenv-win](https://github.com/pyenv-win/pyenv-win) または公式
インストーラから 3.12.13 を入れてください。

---

## 3. 仮想環境の作成と有効化

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Windows (cmd.exe)

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

仮想環境を抜けるときは `deactivate` を実行します。

---

## 4. 依存パッケージのインストール

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

インストールされる主なライブラリ:

- `fastapi`, `uvicorn[standard]` — Web フレームワーク / ASGI サーバ
- `httpx` — 非同期 HTTP クライアント
- `pydantic` — リクエスト/レスポンスのスキーマ
- `jinja2` — HTML テンプレート
- `pytest`, `pytest-asyncio`, `respx` — テスト

---

## 5. 起動方法

開発用 (ホットリロード有効):

```bash
uvicorn app.main:app --reload --port 8000
```

本番想定 (複数ワーカー):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

バックグラウンド起動 (Linux):

```bash
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

---

## 6. 動作確認

### 6.1 ヘルスチェック

```bash
curl http://localhost:8000/healthz
# => {"status":"ok","version":"0.1.0"}
```

### 6.2 Swagger UI (OpenAPI)

ブラウザで以下を開きます:

- <http://localhost:8000/docs> — Swagger UI
- <http://localhost:8000/redoc> — ReDoc
- <http://localhost:8000/openapi.json> — 生 OpenAPI スキーマ

Swagger UI 上から `/api/rhsa` を直接実行できます。

### 6.3 HTML UI

ブラウザで <http://localhost:8000/> を開き、Major / Minor / Month を入力して「検索」。

### 6.4 API スモークテスト

```bash
curl 'http://localhost:8000/api/rhsa?major=8&minor=4&month=2024-09' | head
```

---

## 7. テスト実行

```bash
pytest -q
```

`tests/` 配下のユニットテストが実行されます。Red Hat API の呼び出しは `respx` で
モックされるため、ネットワークなしでも完走します。

カバレッジを取りたい場合:

```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

## 8. Docker Compose での起動 (推奨)

リポジトリ直下に `Dockerfile` / `docker-compose.yml` / `.dockerignore` を同梱しています。
ローカルに Python を入れずに **`docker compose` だけで** 起動できます。

### 8.1 前提
- Docker Engine 20.10+ / Docker Desktop
- Compose plugin (`docker compose version` で `v2` 以上)

### 8.2 起動

```bash
docker compose up -d --build
```

- `-d`: バックグラウンド起動
- `--build`: 初回 or `requirements.txt` / `app/` 変更時に再ビルド
- ホスト側ポートを変更したい場合: `APP_PORT=18000 docker compose up -d`

### 8.3 動作確認

```bash
docker compose ps
curl http://localhost:8000/healthz
# => {"status":"ok","version":"0.1.0"}
```

ヘルスチェックは Compose に組み込み済みで、`STATUS` が `Up (healthy)` になれば OK。

### 8.4 ログ確認 / 停止 / 再起動

```bash
docker compose logs -f app   # ログ追従
docker compose restart app   # 再起動
docker compose down          # 停止 & コンテナ削除
docker compose down -v       # ボリュームも削除 (本アプリは未使用)
```

### 8.5 一時的にコンテナ内で `pytest` を流す

```bash
docker compose run --rm --entrypoint "" app \
  sh -c "pip install pytest pytest-asyncio respx && pytest -q"
```

### 8.6 構成

| ファイル | 役割 |
|---|---|
| `Dockerfile` | `python:3.12.13-slim` ベース、非 root (`appuser`) で `uvicorn` を起動 |
| `docker-compose.yml` | サービス `app` を定義。ポート公開、ヘルスチェック、`restart: unless-stopped` |
| `.dockerignore` | `tests/`, `docs/`, `.git/`, キャッシュ類を除外しビルドコンテキストを軽量化 |

---

## 9. トラブルシュート

### Python バージョンが 3.12 系でない

`python --version` が `Python 3.12.x` でない場合、`pip install` が
`requires-python = ">=3.12,<3.13"` で失敗します。「2.5. Python 3.12.13 の導入」を
参照して `pyenv` で 3.12.13 を入れてください。

### `access.redhat.com` に到達できない

```bash
curl -I 'https://access.redhat.com/hydra/rest/securitydata/csaf.json?after=2024-09-01&before=2024-09-02'
```

`HTTP/2 200` が返らない場合はネットワーク/プロキシ/DNS を確認してください。

### プロキシ環境

`httpx` は `HTTPS_PROXY` / `HTTP_PROXY` を尊重します:

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export HTTP_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

### ポート競合

`uvicorn ... --port 8001` などで別ポートを指定してください。

### 502 Bad Gateway が返る

サーバが Red Hat API に到達できなかった場合の応答です。`app.log` または
コンソールに出力された警告 (`Red Hat API request failed (attempt N/3)`) を確認し、
ネットワーク到達性 / プロキシ設定を見直してください。

### 0 件しか返らない

`mode=minor` で対象月にその minor 向けの EUS/AUS リリースが無いケースが該当します。
`mode=major` で再実行して結果を確認してください。
