# Task Management Dashboard

複数PCのタスクスケジューラを一元管理するWebダッシュボードです。

## 主な機能

### ✅ 実装済み機能
- **PC情報表示**: 管理対象PCのシステム情報、リソース使用状況、タスク数の表示
- **タスク管理**: タスクの一覧表示、作成、編集、削除、有効/無効切り替え
- **実行結果ログ**: 詳細な検索・フィルター機能、エラーコード表示、AI分析結果表示、CSVエクスポート
- **サマリーレポート**: タスク成功率、エラー発生件数の可視化
- **管理者設定**: PC設定、通知設定、エラーコード管理

### 🔄 開発中機能
- **AIエラー分析**: Gemini APIを使用したエラーログの自動分析
- **通知機能**: Google Chatへのエラー通知
- **手動実行機能**: タスクの即時実行

## Setup

### 1. WinRM接続設定

**重要：** リモートPCに接続する前に、WinRM接続設定が必要です。

詳細な設定手順は以下を参照してください：
- [クイックスタートガイド](docs/クイックスタートガイド.md) - 5分で設定完了
- [WinRM接続設定手順書](docs/WinRM接続設定手順書.md) - 詳細な手順とトラブルシューティング

### 2. 環境構築

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 必要なライブラリをインストール
pip install -r requirements.txt
```

### 3. 認証情報設定

```bash
# 認証情報を設定
python setup_credentials.py
```

## How to Run

### 接続テスト

```bash
# 個別PCの接続テスト
python -m tests.test_eps50_connection
python -m tests.test_integration_connection
```

### アプリケーション起動

```bash
# Streamlitアプリを起動
streamlit run app.py
```

## プロジェクトディレクトリ構成

このプロジェクトは、以下のディレクトリ構造で管理することを推奨します。

```
task-dashboard/
│
├── .streamlit/
│   └── config.toml         # (オプション) Streamlitのテーマや詳細設定
│
├── core/
│   ├── __init__.py         # coreをPythonパッケージとして認識させるためのファイル
│   ├── config_manager.py     # 設定ファイル(config.json)を管理するモジュール
│   ├── db_manager.py         # データベース(logs.db)を管理するモジュール
│   ├── task_manager.py       # リモートPCのタスクを操作するコアロジック
│   ├── notification_manager.py # Google Chatへの通知モジュール
│   └── ai_analyzer.py        # Gemini APIと連携するエラー分析モジュール
│
├── data/                     # (追加) 開発用のデータフォルダ
│   ├── config.json         # 開発用の設定ファイル
│   └── logs.db             # 開発用のデータベースファイル
│
├── docs/                     # (追加) ドキュメントフォルダ
│   ├── 1_requirements.md
│   ├── 2_system_design.md
│   ├── 3_module_design.md
│   └── 4_development_guide.md
│
├── logs/                     # (追加) ログファイルフォルダ
│   └── .gitkeep            # Gitでフォルダを追跡するためのファイル
│
├── tests/                    # (追加) テストファイルフォルダ
│   ├── test_core_modules.py
│   ├── test_task_manager.py
│   ├── test_notification_manager.py
│   └── test_ai_analyzer.py
│
├── app.py                    # Streamlitアプリケーション本体（起動スクリプト）
│
├── requirements.txt          # プロジェクトに必要なPythonライブラリ一覧
│
└── README.md                 # プロジェクトの概要やセットアップ方法を記述する文書
```

## 各ファイル/フォルダの役割

| 名前 | 役割 |
|------|------|
| `task-dashboard/` | プロジェクトのルートフォルダ。 |
| `.streamlit/config.toml` | （オプション）Streamlitのテーマ（色など）や、サーバーのポート番号といった詳細な設定を記述するファイルです。 |
| `core/` | システムのバックエンドロジックを格納する心臓部です。UI (app.py) から独立させることで、コードの見通しが良くなり、テストや修正がしやすくなります。 |
| `data/` | (追加) 開発中に使用する設定ファイルやデータベースファイルを格納します。本番運用時はNAS上のファイルを参照します。 |
| `docs/` | (追加) 要件定義書や設計書（画面設計、DB設計など）といった、プロジェクト関連のドキュメントを格納します。 |
| `logs/` | (追加) アプリケーション実行時に生成されるログファイルを格納します。エラーログ、アクセスログ、デバッグログなどが保存されます。 |
| `tests/` | (追加) 各モジュールのテストファイルを格納します。単体テスト、統合テストなどが含まれます。 |
| `app.py` | ユーザーが直接操作するWebインターフェースを定義する、Streamlitアプリケーションのメインファイルです。このファイルを実行してダッシュボードを起動します。 |
| `requirements.txt` | このプロジェクトを動かすために必要なPythonライブラリをリストアップしたファイルです。新しい環境にシステムを移行する際に、`pip install -r requirements.txt`コマンドで一括インストールできます。 |
| `README.md` | プロジェクトの概要、セットアップ手順、起動方法、注意事項などを記述する説明書です。 |

## データと設定ファイルの配置について

開発中と本番運用時で、参照するファイルの場所を切り替えます。

- **開発中**: プロジェクト内の `data/` フォルダにあるファイルを参照してテストを行います。
- **本番運用時**: `app.py`内のパス設定を書き換え、NAS上の以下のファイルを参照するようにします。
  - 設定ファイル: `\\nas-server\config\config.json`
  - データベースファイル: `\\nas-server\data\logs.db`

## requirements.txt の内容例

```
streamlit
pandas
plotly
pywinrm
requests
google-generativeai
```

