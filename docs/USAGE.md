# 利用手順書

`rhel-vuln` の使い方を、Web UI / REST API の両面で説明します。

---

## 1. 概要

本ツールは、指定した RHEL のバージョン (Major.Minor) と対象月 (YYYY-MM) に対して、
**その月に初回リリースされた RHSA (Red Hat Security Advisory)** を一覧で取得します。

- 入力: `major`, `minor` (任意), `month`, `mode` (任意)
- 出力: 該当 RHSA の `rhsa_id`, `severity`, `released_on`, `cves`, `title`,
  `affected_packages`, `rhsa_url` などを含む JSON

データソースは Red Hat 公式の Security Data API です。

---

## 2. Web UI からの利用手順

1. ブラウザで <http://localhost:8000/> を開く
2. フォームに入力する:
   - **Major**: RHEL メジャーバージョン (例: `8`, `9`)
   - **Minor**: RHEL マイナーバージョン (例: `4`)。空欄可
   - **Month**: 対象月 (例: `2024-09`)
   - **Mode**:
     - `auto` (空欄): Minor が指定されていれば `minor`、なければ `major`
     - `minor`: `.elX_Y` 個別マイナー + 汎用 `.elX` を該当扱い
     - `major`: メジャー X 全体 (`.elX*`) を該当扱い
3. 「**検索**」を押下
4. 結果が表として表示されます。
   - 列: `RHSA / Severity / Released / Title / CVEs`
   - 各 `RHSA` は `https://access.redhat.com/errata/{ID}` へのリンクです
5. 「**レスポンス JSON を表示**」を開くと、API そのものの JSON を確認できます

> Severity に応じて色分けされます (Critical=赤, Important=橙, Moderate=青, Low=緑)

---

## 3. REST API からの利用手順

### 3.1 エンドポイント

```
GET /api/rhsa
```

### 3.2 クエリパラメータ

| パラメータ | 型 | 必須 | 例 | 説明 |
|---|---|:---:|---|---|
| `major` | int | ✓ | `8` | RHEL メジャーバージョン (5〜99) |
| `minor` | int | – | `4` | RHEL マイナーバージョン (0〜99) |
| `month` | string | ✓ | `2024-09` | 対象月 `YYYY-MM` |
| `mode` | enum | – | `minor` / `major` | フィルタモード |

`mode` を省略した場合、`minor` の指定があれば `minor`、なければ `major` になります。

### 3.3 curl サンプル

```bash
# RHEL 8.4 の 2024年9月分
curl 'http://localhost:8000/api/rhsa?major=8&minor=4&month=2024-09' | jq

# RHEL 9 メジャー全体
curl 'http://localhost:8000/api/rhsa?major=9&month=2024-09&mode=major' | jq

# 件数だけ確認
curl -s 'http://localhost:8000/api/rhsa?major=8&minor=10&month=2024-09' | jq '.count'

# CVE 一覧だけ抽出
curl -s 'http://localhost:8000/api/rhsa?major=8&minor=4&month=2024-09' \
  | jq -r '.results[].cves[]' | sort -u

# 月次レポートをファイル保存
curl -s 'http://localhost:8000/api/rhsa?major=9&minor=2&month=2024-09' \
  > rhel-9.2-2024-09.json
```

### 3.4 レスポンス JSON

```json
{
  "query": { "major": 8, "minor": 4, "month": "2024-09", "mode": "minor" },
  "count": 12,
  "results": [
    {
      "rhsa_id": "RHSA-2024:6500",
      "title": "Moderate: openssl EUS update for 8.4",
      "severity": "Moderate",
      "released_on": "2024-09-15T00:00:00Z",
      "cves": ["CVE-2024-3333"],
      "bugzilla_ids": ["2300002"],
      "affected_packages": ["openssl-1.1.1k-12.el8_4.x86_64"],
      "resource_url": "https://access.redhat.com/hydra/rest/securitydata/csaf/RHSA-2024:6500.json",
      "rhsa_url": "https://access.redhat.com/errata/RHSA-2024:6500"
    }
  ]
}
```

#### フィールド説明

| フィールド | 型 | 説明 |
|---|---|---|
| `query.major` | int | リクエストされたメジャー |
| `query.minor` | int / null | リクエストされたマイナー |
| `query.month` | string | リクエストされた対象月 |
| `query.mode` | string | 実際に適用されたモード |
| `count` | int | `results` の件数 |
| `results[].rhsa_id` | string | RHSA-YYYY:NNNN 形式の ID |
| `results[].title` | string | RHSA の synopsis |
| `results[].severity` | string | `Critical` / `Important` / `Moderate` / `Low` |
| `results[].released_on` | string | ISO8601 のリリース日時 |
| `results[].cves` | string[] | 紐付く CVE 一覧 |
| `results[].bugzilla_ids` | string[] | 紐付く Bugzilla ID 一覧 |
| `results[].affected_packages` | string[] | リリースされた NVR 一覧 (`.elX_Y` 等) |
| `results[].resource_url` | string | 元 CSAF JSON へのリンク |
| `results[].rhsa_url` | string | Red Hat Errata ページへのリンク |

### 3.5 ステータスコード

| Code | 意味 |
|---|---|
| 200 | 正常終了 (0 件でも 200) |
| 422 | 入力バリデーションエラー (例: `month=2024-13`) |
| 502 | Red Hat API 疎通失敗 (3 回までリトライ後) |

---

## 4. モード解説

実装は **`released_packages` のパッケージ NVR タグ** をもとに該当判定します。

| モード | 判定ルール |
|---|---|
| `mode=major` | `.elX` で始まる NVR を含む RHSA を該当扱い |
| `mode=minor` | (A) `.elX_Y` を含む、または (B) 他の `.elX_Z` (Z≠Y) が一切無く `.elX` を含む RHSA を該当扱い |

- **(A)** は EUS / AUS 向け minor 固有のリリースを拾います
- **(B)** は GA ストリーム向けリリース (例: `.el8`) が指定 minor (例 8.4) にも適用される事実を反映しています
- 他 minor 専用 (`.el8_6` だけ) の RHSA は 8.4 の検索からは除外されます

---

## 5. 典型ユースケース

### 5.1 月次脆弱性レポートを作る

```bash
for v in 8.4 8.10 9.2 9.4; do
  major=${v%.*}; minor=${v#*.}
  curl -s "http://localhost:8000/api/rhsa?major=${major}&minor=${minor}&month=2024-09" \
    > "report-${v}-2024-09.json"
done
```

### 5.2 重大度 Critical のみ抽出

```bash
curl -s 'http://localhost:8000/api/rhsa?major=8&minor=4&month=2024-09' \
  | jq '.results[] | select(.severity=="Critical")'
```

### 5.3 BI ツール (CSV) への取り込み

```bash
curl -s 'http://localhost:8000/api/rhsa?major=8&minor=4&month=2024-09' \
  | jq -r '.results[] | [.rhsa_id, .severity, .released_on, (.cves|join("|"))] | @csv' \
  > rhsa.csv
```

---

## 6. 制限事項

- **判定根拠**: `released_packages` が空の RHSA (パッケージリストが API から取得不能なケース)
  は検出できません。Red Hat 側のメタデータ不備が原因です。
- **対象月**: Red Hat API の `released_on` に依存します。RHSA の **後日訂正リリース**
  (revision) は別 ID で再採番されることが多いため、最新版だけが返ります。
- **レート制限**: Red Hat Security Data API には控えめなレート制限があります。
  本ツールは月単位でリスト 1 回呼び出し + 必要に応じてページングするだけのため、
  通常利用では問題になりません。短時間に多数のリクエストを送る場合は呼び出し側で間隔を空けてください。
- **CVE フィルタ非対応**: 本ツールは CVE 単位ではなく RHSA 単位での検索を行います。
  CVE 単位での詳細は `resource_url` 先の CSAF JSON を参照してください。

---

## 7. FAQ / トラブルシュート

### Q. 0 件しか返らない
- `mode` を `major` に切り替えて再実行。それでも 0 件なら、その月にその major
  向けの RHSA がリリースされていない可能性があります。
- `month` の値が `YYYY-MM` 形式か再確認 (`2024-9` は 422 になります)。

### Q. 502 Bad Gateway
- サーバが Red Hat API に到達できていません。`docs/SETUP.md` の
  「9. トラブルシュート」を参照してください。

### Q. JSON 表示が崩れる
- `curl ... | jq` の `jq` がインストールされていない場合は `curl -s ... | python -m json.tool` でも代替可能です。

### Q. 認証が必要?
- 不要です。Red Hat Security Data API は公開エンドポイントで、認証ヘッダは送りません。
