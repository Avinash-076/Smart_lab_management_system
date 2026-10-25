[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null

$n1 = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('com.slms.dashboard')
Write-Host "Setting for com.slms.dashboard: $($n1.Setting)"

$n2 = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe')
Write-Host "Setting for PowerShell: $($n2.Setting)"
