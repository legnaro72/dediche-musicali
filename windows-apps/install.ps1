param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'DedicheMusicaliApps'),
    [string]$BrowserPath = '',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$browser = $null
if ($BrowserPath) {
    if (!(Test-Path -LiteralPath $BrowserPath -PathType Leaf)) {
        throw "Browser non trovato nel percorso indicato: $BrowserPath"
    }
    if ([IO.Path]::GetFileName($BrowserPath) -notin @('msedge.exe', 'chrome.exe')) {
        throw 'Specificare il percorso di msedge.exe oppure chrome.exe.'
    }
    $browser = (Resolve-Path -LiteralPath $BrowserPath).Path
} else {
    foreach ($exe in @('msedge.exe', 'chrome.exe')) {
        $candidates = @()
        foreach ($key in @(
            "HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\$exe",
            "HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\$exe",
            "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\$exe"
        )) {
            if (Test-Path -LiteralPath $key) {
                $value = (Get-Item -LiteralPath $key).GetValue('')
                if ($value) { $candidates += [Environment]::ExpandEnvironmentVariables($value).Trim('"') }
            }
        }
        $command = Get-Command $exe -CommandType Application -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command[0].Source }
        $relative = if ($exe -eq 'msedge.exe') { 'Microsoft\Edge\Application' } else { 'Google\Chrome\Application' }
        foreach ($root in @(${env:ProgramW6432}, ${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)) {
            if ($root) { $candidates += Join-Path $root "$relative\$exe" }
        }
        $browser = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if ($browser) { break }
    }
}
if (!$browser) {
    throw 'Edge e Chrome non trovati. Installare uno dei due, oppure eseguire install.ps1 -BrowserPath "C:\percorso\chrome.exe" se installato in una cartella personalizzata.'
}
Write-Output "Browser: $browser"
if ($CheckOnly) { return }
$apps = @(
    @{ Id='ddgpilli'; Name='DDGPilli - Sito'; Url='https://legnaro72.github.io/dediche-musicali/' },
    @{ Id='ddgpilli-admin'; Name='DDGPilli - Admin'; Url='https://ddgpilli.streamlit.app/' },
    @{ Id='ff'; Name='Dediche FF - Sito'; Url='https://legnaro72.github.io/dediche-musicali-ff/' },
    @{ Id='ff-admin'; Name='Dediche FF - Admin'; Url='https://dediche-musicali-ff.streamlit.app/' }
)
Add-Type -AssemblyName System.Drawing
$desktop = [Environment]::GetFolderPath('Desktop')
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Dediche musicali'
New-Item -ItemType Directory -Path $InstallRoot,$menu -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($app in $apps) {
    $source = Join-Path $PSScriptRoot "assets/$($app.Id).png"
    $iconPath = Join-Path $InstallRoot "$($app.Id).ico"
    $sourceImage = [Drawing.Image]::FromFile($source)
    $bitmap = New-Object Drawing.Bitmap 256,256
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    $memory = New-Object IO.MemoryStream
    try {
        $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.DrawImage($sourceImage, 0, 0, 256, 256)
        $bitmap.Save($memory, [Drawing.Imaging.ImageFormat]::Png)
        $png = $memory.ToArray()
        $writer = New-Object IO.BinaryWriter ([IO.File]::Create($iconPath))
        try {
            # ICO directory followed by a PNG-compressed 256px image.
            $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]1)
            $writer.Write([byte]0); $writer.Write([byte]0); $writer.Write([byte]0); $writer.Write([byte]0)
            $writer.Write([uint16]1); $writer.Write([uint16]32)
            $writer.Write([uint32]$png.Length); $writer.Write([uint32]22); $writer.Write($png)
        } finally { $writer.Dispose() }
    } finally {
        $memory.Dispose(); $graphics.Dispose(); $bitmap.Dispose(); $sourceImage.Dispose()
    }
    foreach ($folder in @($desktop, $menu)) {
        $shortcut = $shell.CreateShortcut((Join-Path $folder "$($app.Name).lnk"))
        $shortcut.TargetPath = $browser
        $profile = Join-Path $InstallRoot "profiles/$($app.Id)"
        $shortcut.Arguments = "--app=$($app.Url) --user-data-dir=`"$profile`" --no-first-run"
        $shortcut.IconLocation = "$iconPath,0"
        $shortcut.Description = $app.Name
        $shortcut.Save()
    }
    Write-Output "Installata: $($app.Name)"
}
Write-Output "Collegamenti creati sul Desktop e nel menu Start."
