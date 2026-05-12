# rhel-vuln — RHEL 脆弱性調査 Web アプリ

RHEL の **メジャー / マイナーバージョン** と **対象月 (YYYY-MM)** を指定すると、
その月に初回リリースされた **RHSA (Red Hat Security Advisory)** を
[Red Hat Security Data API](https://access.redhat.com/hydra/rest/securitydata/) から取得し、
JSON で返す Web アプリケーションです。

- 言語/FW: Python 3.11+ / FastAPI
- 公開: REST API (`GET /api/rhsa`) と 簡易 HTML UI (`/`)
- 認証: 不要 (Red Hat Security Data API は公開エンドポイント)

## クイックスタート

```bash
git clone https://github.com/batoer-0605/rhel-vuln.git
cd rhel-vuln
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

ブラウザで以下を開く:

- HTML UI: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/docs>
- ヘルスチェック: <http://localhost:8000/healthz>

### API 例

```bash
# RHEL 8.4 で 2024年9月 にリリースされた RHSA
curl 'http://localhost:8000/api/rhsa?major=8&minor=4&month=2024-09' | jq

# RHEL 9 メジャー全体
curl 'http://localhost:8000/api/rhsa?major=9&month=2024-09&mode=major' | jq '.count'
```

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | セットアップ手順書 (環境構築〜起動〜トラブルシュート) |
| [docs/USAGE.md](docs/USAGE.md) | 利用手順書 (UI / API の使い方、サンプル、FAQ) |

## テスト

```bash
pip install -r requirements.txt
pytest -q
```

## ライセンス

社内利用向け。再配布時は別途検討してください。
