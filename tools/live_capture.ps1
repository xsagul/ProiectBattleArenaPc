# Passive capture of the UDP traffic between the live client and Riot's game server.
# Uses Windows' own pktmon (no driver install, nothing touches the game process).
# Must run elevated. Start it BEFORE the loading screen; press Enter between / after matches.
#
# Only a stopped capture is whole: pktmon keeps one 16 MB buffer per CPU and writes a buffer to the
# file when it fills or at stop [measured: a copy of the running file held a third of the datagrams].
# So each Enter stops, converts to .pcapng and starts a new file; q + Enter stops for good.
#
# -All = every protocol, first 96 bytes of each packet (addresses + sizes, no contents): who moved how much,
# for the lobby / patcher / game as a whole. A match recorded this way cannot be decoded (payload cut).
param([string]$Out = (Join-Path $PSScriptRoot '..\data\live'), [switch]$All)

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not (New-Object Security.Principal.WindowsPrincipal $id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Not elevated: pktmon needs an Administrator PowerShell.' -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force $Out | Out-Null
$Out = (Resolve-Path $Out).Path

while ($true) {
    $etl = Join-Path $Out ($(if ($All) { 'all_' } else { 'live_' }) + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.etl')
    pktmon stop | Out-Null
    pktmon filter remove | Out-Null
    if (-not $All) { pktmon filter add LoLGameUdp -t UDP | Out-Null }
    # nics only = each packet once; pkt-size 0 = whole packet; flags 0x10 = raw packet only
    pktmon start --capture --comp nics --pkt-size $(if ($All) { 96 } else { 0 }) --flags 0x10 --file-name $etl --file-size 2048
    if ($LASTEXITCODE -ne 0) { Write-Host 'pktmon start failed.' -ForegroundColor Red; exit 1 }

    Write-Host ''
    Write-Host "Capturing $(if ($All) { 'all traffic (headers only)' } else { 'UDP' }) to $etl" -ForegroundColor Green
    $answer = Read-Host 'Between matches (never during one): Enter = save and keep capturing, q + Enter = save and stop'

    pktmon stop
    pktmon filter remove | Out-Null
    $pcap = [IO.Path]::ChangeExtension($etl, '.pcapng')
    pktmon etl2pcap $etl --out $pcap
    Write-Host "Saved: $pcap" -ForegroundColor Green
    if ($answer -eq 'q') { break }
}
