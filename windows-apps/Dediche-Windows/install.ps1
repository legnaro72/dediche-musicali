param([string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'DedicheMusicaliApps'))
$ErrorActionPreference = 'Stop'
$edge = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (!$edge) { throw 'Microsoft Edge non trovato. Installare Edge e riprovare.' }
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
        $shortcut.TargetPath = $edge
        $profile = Join-Path $InstallRoot "profiles/$($app.Id)"
        $shortcut.Arguments = "--app=$($app.Url) --user-data-dir=`"$profile`" --no-first-run"
        $shortcut.IconLocation = "$iconPath,0"
        $shortcut.Description = $app.Name
        $shortcut.Save()
    }
    Write-Output "Installata: $($app.Name)"
}
Write-Output "Collegamenti creati sul Desktop e nel menu Start."
