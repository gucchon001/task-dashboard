# 作成者でタスクを絞り込むスクリプト（修正版）
# 使用方法: .\filter_tasks_by_author_fixed.ps1 [作成者名]

param(
    [string]$AuthorFilter = ""
)

Write-Host "=== 作成者別タスク絞り込み ===" -ForegroundColor Green
Write-Host ""

# ルート直下のタスクを取得
$rootTasks = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }

if ($AuthorFilter) {
    # 特定の作成者で絞り込み
    Write-Host "作成者 '$AuthorFilter' で絞り込み中..." -ForegroundColor Yellow
    $filteredTasks = $rootTasks | Where-Object { $_.Author -like "*$AuthorFilter*" }
    Write-Host "絞り込み結果: $($filteredTasks.Count)件" -ForegroundColor Green
    # 結果を表示
    if ($filteredTasks.Count -gt 0) {
        Write-Host ""
        Write-Host "=== 詳細情報 ===" -ForegroundColor Green
        $filteredTasks | Select-Object TaskName, TaskPath, Author, State, NextRunTime, LastRunTime, Description | Format-Table -AutoSize
    } else {
        Write-Host "該当するタスクが見つかりませんでした。" -ForegroundColor Red
    }
} else {
    # 作成者別にグループ化して表示
    Write-Host "作成者別統計:" -ForegroundColor Yellow
    $authorGroups = $rootTasks | Group-Object Author | Sort-Object Count -Descending
    foreach ($group in $authorGroups) {
        Write-Host ""
        Write-Host "作成者: $($group.Name) ($($group.Count)件)" -ForegroundColor Cyan
        $group.Group | Select-Object TaskName, State, NextRunTime | Format-Table -AutoSize
    }
    Write-Host ""
    Write-Host "=== 詳細情報 ===" -ForegroundColor Green
    $rootTasks | Select-Object TaskName, TaskPath, Author, State, NextRunTime, LastRunTime, Description | Format-Table -AutoSize
}

Write-Host ""
Write-Host "使用方法:" -ForegroundColor Yellow
Write-Host ".\\filter_tasks_by_author_fixed.ps1                    # 全作成者を表示"
Write-Host ".\\filter_tasks_by_author_fixed.ps1 'Administrator'    # Administratorで絞り込み"
Write-Host ".\\filter_tasks_by_author_fixed.ps1 'WIN-ND0QPM2D7G1' # 特定PCで絞り込み"