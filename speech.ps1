param([string]$InputPath, [string]$OutputPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$payload = Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8 | ConvertFrom-Json
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = $speaker.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'pt-BR' }
    if (-not $voices) { throw 'Nenhuma voz pt-BR instalada no Windows.' }
    $speaker.SelectVoice(($voices | Select-Object -First 1).VoiceInfo.Name)
    $speaker.Rate = if ($payload.rate -eq 1) { 1 } else { 0 }
    $speaker.SetOutputToWaveFile($OutputPath)
    $speaker.Speak([string]$payload.text)
} finally {
    $speaker.Dispose()
}
