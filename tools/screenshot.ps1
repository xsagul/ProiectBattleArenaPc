# Save the primary screen to a PNG, optionally several times.
#   screenshot.ps1 <out.png> [delay seconds before each shot, comma separated: "20,28,36" writes out_1.png, out_2.png, ...]
param([string]$out, [string]$delays = "")
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
function Shot([string]$path) {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save($path)
    $g.Dispose(); $bmp.Dispose()
}
if ($delays -eq "") { Shot $out; exit }
$t0 = Get-Date
$i = 0
foreach ($d in $delays.Split(",")) {
    $i++
    $wait = [double]$d - ((Get-Date) - $t0).TotalSeconds
    if ($wait -gt 0) { Start-Sleep -Milliseconds ([int]($wait * 1000)) }
    Shot ($out -replace "\.png$", "_$i.png")
}
