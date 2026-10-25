[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>SLMS Host Alert</text><text>Workstation LAB-PC-04 has 94% RAM usage!</text></binding></visual></toast>")
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml

try {
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("com.slms.dashboard").Show($toast)
    Write-Host "SUCCESS: Toast sent via com.slms.dashboard"
} catch {
    Write-Host "ERROR with com.slms.dashboard: $($_.Exception.Message)"
}
