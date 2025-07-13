# Windows PowerShell での TrustedHosts 設定手順のまとめ

このドキュメントでは、Windows 環境の PowerShell Remoting (WinRM) において、管理サーバーから他のPC（管理対象サーバー）へリモート接続する際に必要な TrustedHosts の設定方法をまとめます。

## TrustedHosts とは？

TrustedHosts は、PowerShell リモート処理（WinRM）において、接続元のコンピューター（管理サーバー）が、接続先のリモートコンピューター（管理対象サーバー）を信頼するかどうかを定義する設定です。この設定がないと、セキュリティ上の理由からリモート接続が拒否される場合があります。

## これまでのエラーと原因

これまでの試行では、以下のようなエラーが発生しました。

### Get-Item WSMan:\localhost\Client\TrustedHosts での「パスが存在しない」エラー:

**原因**: TrustedHosts の設定を保存するレジストリキー (HKLM:\SOFTWARE\Microsoft\WSMan\Client) がまだ存在していなかったため。

### Set-Item WSMan:\localhost\Client\TrustedHosts や Set-WSManInstance での「接続先に接続できません」エラー:

**原因**: WSMan:\ プロバイダーが、ローカルの WinRM 設定ストア（レジストリ）にアクセスまたは書き込みできなかったため。これは、上記レジストリキーの欠落が根本原因である可能性が高いです。

### Set-ItemProperty -Path HKLM:\SOFTWARE\Microsoft\WSMan\Client での「パスが存在しない」エラー:

**原因**: やはり Client レジストリキーが欠落していたため。

これらのエラーは、TrustedHosts の設定を格納するレジストリパスが、初期状態では存在しないために発生していました。

## 管理サーバー (送信側) の設定手順

TrustedHosts を設定するには、以下の手順を管理者権限の PowerShell で実行します。

### 1. PowerShell を管理者として実行します。

Windows の検索バーで「PowerShell」と入力し、表示された「Windows PowerShell」を右クリックし、「管理者として実行」を選択します。

### 2. 必要なレジストリキーを作成します。

TrustedHosts の設定を格納する Client レジストリキーが欠落している場合があるため、まずこのキーを作成します。

```powershell
New-Item -Path HKLM:\SOFTWARE\Microsoft\WSMan -Name Client -Force
```

このコマンドは、`HKLM:\SOFTWARE\Microsoft\WSMan` の下に Client という新しいキーを作成します。`-Force` パラメーターは、キーが既に存在する場合でもエラーにならず、処理を続行させます。

### 3. TrustedHosts の値を設定します。

次に、管理したい他のPCのホスト名（またはIPアドレス）を TrustedHosts に設定します。

```powershell
Set-ItemProperty -Path HKLM:\SOFTWARE\Microsoft\WSMan\Client -Name TrustedHosts -Value "管理対象PCのホスト名1,管理対象PCのホスト名2,..."
```

`-Value` には、信頼するリモートPCのホスト名、IPアドレス、または完全修飾ドメイン名（FQDN）をカンマ区切りで指定します。

**例**:
```powershell
Set-ItemProperty -Path HKLM:\SOFTWARE\Microsoft\WSMan\Client -Name TrustedHosts -Value "EPS50,WIN-ND0QPM2D7G1"
```

## 管理対象PC (受信側) の設定手順

リモートから操作される側のPC（管理対象PC）でも、WinRMが正しく動作するように設定が必要です。以下の手順を、各管理対象PCで管理者権限のPowerShellで実行します。

### 1. 共通管理者アカウントの作成

リモート操作には、管理サーバーと管理対象PC間で共通の管理者権限を持つアカウントを使用することが推奨されます。まだ作成していない場合は、各管理対象PCに同じユーザー名とパスワードの管理者アカウントを作成してください。

### 2. WinRM の有効化

WinRMサービスを有効にし、ファイアウォール設定を自動的に構成します。

```powershell
winrm quickconfig
```

実行すると、変更の確認を求められる場合がありますので、`y` を入力して進めます。

もし「ネットワーク接続の種類が Public に設定されているため、WinRM ファイアウォール例外は機能しません」というエラーが出た場合は、次のステップに進んでください。

### 3. ネットワークプロファイルを「プライベート」に変更 (エラーが出た場合)

`winrm quickconfig` でエラーが出た場合、ネットワークプロファイルが「パブリック」になっている可能性があります。

1. **設定を開く**: Windowsキー + Iキー を同時に押して、設定ウィンドウを開きます。
2. **「ネットワークとインターネット」を選択**: 左側のメニューから「ネットワークとインターネット」をクリックします。
3. **接続中のネットワークを選択**: 現在接続しているネットワーク（通常は「イーサネット」または「Wi-Fi」）をクリックします。
4. **ネットワークプロファイルの種類の変更**: 「ネットワーク プロファイルの種類」という項目を探し、「プライベート」を選択します。

設定変更後、再度 `winrm quickconfig` を実行してください。

## 設定の確認

設定が正しく行われたことを確認するには、以下のコマンドを実行します。

```powershell
Get-ItemProperty -Path HKLM:\SOFTWARE\Microsoft\WSMan\Client -Name TrustedHosts
```

このコマンドの出力で、設定したホスト名が表示されれば、TrustedHosts の設定は完了です。

## まとめ

この手順により、管理サーバーは指定されたリモートPCとの PowerShell リモート接続を信頼し、タスクスケジューラの操作など、様々なリモート管理タスクを実行できるようになります。 