# WinRM接続設定手順書

## 概要

このドキュメントでは、Windows Remote Management (WinRM) を使用してリモートPCに接続するための設定手順を説明します。

## 対象PC

| PC名 | IPアドレス | 用途 | OS |
|------|------------|------|----|
| EPS50 | 192.168.1.57 | 勤怠用 | Windows 10 Pro |
| WIN-ND0QPM2D7G1 | 192.168.1.58 | 統合用 | Windows Server 2019 Essentials |

## 前提条件

- Windows 10/11 または Windows Server
- 管理者権限
- ネットワーク接続が可能
- Python 3.13以上

## 接続先PC側の設定

### 1. WinRMサービスの有効化

**管理者権限でPowerShellを開き、以下を実行：**

```powershell
# WinRMサービスの有効化
winrm quickconfig
```

**期待される出力：**
```
WinRM サービスは、既にこのコンピューターで実行されています。
このコンピューター上でのリモート管理には、WinRM が既に設定されています。
```

### 2. ファイアウォールルールの作成

```powershell
# WinRM用のファイアウォールルールを作成
netsh advfirewall firewall add rule name="WinRM-HTTP-In" dir=in action=allow protocol=TCP localport=5985
```

**期待される出力：**
```
OK
```

### 3. TrustedHosts設定

```powershell
# すべてのホストを信頼する設定
Set-Item WSMan:\localhost\Client\TrustedHosts -Value '*' -Force
```

### 4. WinRM設定の確認

```powershell
# WinRM設定を確認
winrm get winrm/config
```

**重要な設定項目：**
- `TrustedHosts = *`
- `AllowRemoteAccess = true`
- `HTTP = 5985`

### 5. ユーザーアカウントの確認

```powershell
# 利用可能なユーザーアカウントを確認
net user

# 管理者グループのメンバーを確認
net localgroup administrators
```

## 接続元PC側の設定

### 1. Python仮想環境の作成

```powershell
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1
```

### 2. 必要なパッケージのインストール

```powershell
# requirements.txtからインストール
pip install -r requirements.txt
```

**重要：** `pywinrm`パッケージは`import winrm`で使用します。

### 3. 認証情報の設定

```powershell
# 認証情報設定スクリプトを実行
python setup_credentials.py
```

**入力項目：**
- ユーザー名: 接続先PCのユーザー名
- パスワード: 接続先PCのパスワード

## 接続テスト

### 1. 個別PCの接続テスト

```powershell
# EPS50（勤怠PC）の接続テスト
python -m tests.test_eps50_connection

# WIN-ND0QPM2D7G1（統合PC）の接続テスト
python -m tests.test_integration_connection
```

### 2. 認証情報のテスト

```powershell
# 認証情報のテスト
python test_auth.py
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. ModuleNotFoundError: No module named 'pywinrm'

**原因：** パッケージ名とモジュール名が異なる

**解決方法：**
```python
# 誤り
import pywinrm

# 正しい
import winrm
```

#### 2. 認証エラー: "the specified credentials were rejected by the server"

**原因：** ユーザー名またはパスワードが間違っている

**解決方法：**
1. 接続先PCでユーザーアカウントを確認
2. 正しいユーザー名とパスワードで認証情報を再設定

#### 3. 接続タイムアウト

**原因：** ファイアウォール設定が不適切

**解決方法：**
1. 接続先PCでファイアウォールルールを確認
2. ポート5985が開放されているか確認

#### 4. TrustedHostsエラー

**原因：** TrustedHosts設定が不適切

**解決方法：**
```powershell
Set-Item WSMan:\localhost\Client\TrustedHosts -Value '*' -Force
```

## セキュリティ考慮事項

### 1. 認証情報の管理

- 認証情報ファイル（`credentials.json`）は適切に保護する
- パスワードは強固なものを使用する
- 定期的にパスワードを変更する

### 2. ネットワークセキュリティ

- ファイアウォール設定を適切に行う
- 不要なポートは開放しない
- ネットワークアクセスを制限する

### 3. アクセス制御

- 必要最小限のユーザーアカウントのみを使用
- 管理者権限は必要時のみ使用
- アクセスログを定期的に確認

## 運用上の注意点

### 1. 接続確認

定期的に接続テストを実行して、リモート接続が正常に動作することを確認する。

### 2. ログ監視

接続エラーや認証エラーのログを監視し、異常を早期に発見する。

### 3. バックアップ

設定ファイルや認証情報のバックアップを定期的に取得する。

## 参考情報

### 関連ドキュメント

- [WinRM公式ドキュメント](https://docs.microsoft.com/ja-jp/windows/win32/winrm/portal)
- [PowerShellリモート管理](https://docs.microsoft.com/ja-jp/powershell/scripting/overview-remoting)

### コマンドリファレンス

```powershell
# WinRM設定確認
winrm get winrm/config

# WinRMサービス状態確認
Get-Service WinRM

# ファイアウォールルール確認
netsh advfirewall firewall show rule name="WinRM-HTTP-In"

# TrustedHosts確認
Get-Item WSMan:\localhost\Client\TrustedHosts
```

---

**作成日：** 2025年7月13日  
**更新日：** 2025年7月13日  
**作成者：** システム管理者 