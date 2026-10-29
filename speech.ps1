param([string]$InputPath, [string]$OutputPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$payload = Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($payload.timing_path) {
    Add-Type -ReferencedAssemblies ([System.Speech.Synthesis.SpeechSynthesizer].Assembly.Location) -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Speech.Synthesis;
public class StoryWord {
    public double seconds;
    public int position;
    public int length;
}
public class StorySpeechTiming {
    public List<StoryWord> Words = new List<StoryWord>();
    public void Progress(object sender, SpeakProgressEventArgs e) {
        lock (Words) {
            Words.Add(new StoryWord { seconds=e.AudioPosition.TotalSeconds,
                position=e.CharacterPosition, length=e.CharacterCount });
        }
    }
    public void Attach(SpeechSynthesizer speaker) { speaker.SpeakProgress += Progress; }
}
'@
    $timing = New-Object StorySpeechTiming
}
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = $speaker.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'pt-BR' }
    if (-not $voices) { throw 'Nenhuma voz pt-BR instalada no Windows.' }
    $speaker.SelectVoice(($voices | Select-Object -First 1).VoiceInfo.Name)
    $speaker.Rate = if ($payload.rate -eq 1) { 1 } else { 0 }
    # An explicit PCM format keeps SAPI progress positions on the WAV clock.
    # The default negotiated format produced events beyond the recorded audio.
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,
        [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono)
    $speaker.SetOutputToWaveFile($OutputPath, $format)
    if ($timing) { $timing.Attach($speaker) }
    $speaker.Speak([string]$payload.text)
    if ($timing) {
        ConvertTo-Json -InputObject @($timing.Words.ToArray()) -Depth 4 |
            Set-Content -LiteralPath ([string]$payload.timing_path) -Encoding UTF8
    }
} finally {
    $speaker.Dispose()
}
