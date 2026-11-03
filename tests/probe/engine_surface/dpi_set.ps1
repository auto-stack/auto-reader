param(
    [Parameter(Mandatory=$true)][string]$Target  # e.g. "150%" — the tier to select
)
# dpi_set.ps1 — 经 UIA 驱动 设置>系统>屏幕 的缩放下拉选择目标档位。
# 消息级操作（SelectionPattern），不移动物理鼠标——不干扰 SendInput 门。
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$winCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, 'ApplicationFrameWindow')
$wins = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $winCond)
$settings = $null
foreach ($w in $wins) {
    if ($w.Current.Name -match '设置|Settings') { $settings = $w; break }
}
if (-not $settings) { Write-Output 'NO-SETTINGS-WINDOW'; exit 2 }

# 找值匹配当前档位或名称含「缩放/scale」的组合框——Win11 缩放下拉的 Value
# 形如 "192% (自定义)"，子项为各档位 ListItem。
$cbs = $settings.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::ComboBox)))
$scale = $null
foreach ($c in $cbs) {
    $v = ''
    try {
        $vp = $c.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
        $v = $vp.Current.Value
    } catch {
        $sel = $null
        try {
            $sp = $c.GetCurrentPattern([System.Windows.Automation.SelectionPattern]::Pattern)
            $selArr = $sp.Current.GetSelection()
            if ($selArr.Length -gt 0) { $v = $selArr[0].Current.Name }
        } catch { $v = $c.Current.Name }
    }
    Write-Output ("CB: name=[" + $c.Current.Name + "] value=[" + $v + "]")
    if ($v -match '%') { $scale = $c; $scaleV = $v }
}
if (-not $scale) { Write-Output 'NO-SCALE-COMBO'; exit 2 }
Write-Output ("SCALE-CURRENT: " + $scaleV)

# 展开 → 选目标档位
$ec = $scale.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
$ec.Expand()
Start-Sleep -Milliseconds 800
$items = $scale.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::ListItem)))
if ($items.Count -eq 0) {
    $items = $scale.FindAll([System.Windows.Automation.TreeScope]::Children,
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::ListItem)))
}
$hit = $null
foreach ($i in $items) {
    if ($i.Current.Name -match [regex]::Escape($Target)) { $hit = $i; break }
}
if (-not $hit) {
    Write-Output ("TARGET-NOT-FOUND: " + $Target + " among " + $items.Count + " items")
    $ec.Collapse()
    exit 3
}
$selPat = $hit.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
$selPat.Select()
Write-Output ("SELECTED: " + $hit.Current.Name)
Start-Sleep -Milliseconds 1200
try { $ec.Collapse() } catch {}
Write-Output 'OK'
