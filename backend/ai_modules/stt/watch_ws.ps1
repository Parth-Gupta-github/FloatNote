$ErrorActionPreference = "Stop"

$uri = [System.Uri]"ws://127.0.0.1:8000/ws"
$ws = [System.Net.WebSockets.ClientWebSocket]::new()

Write-Host "Connecting to $uri ..."
$ws.ConnectAsync($uri, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
Write-Host "Connected. Waiting for diarization output..."

$buffer = New-Object byte[] 8192

try {
    while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        $stream = New-Object System.IO.MemoryStream

        do {
            $segment = New-Object System.ArraySegment[byte] -ArgumentList (, $buffer)
            $result = $ws.ReceiveAsync($segment, [Threading.CancellationToken]::None).GetAwaiter().GetResult()

            if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                Write-Host "Server closed the connection."
                break
            }

            $stream.Write($buffer, 0, $result.Count)
        } while (-not $result.EndOfMessage)

        if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
            break
        }

        $message = [Text.Encoding]::UTF8.GetString($stream.ToArray())
        Write-Host ""
        Write-Host "----- MESSAGE -----"
        try {
            $obj = $message | ConvertFrom-Json
            $speaker = if ($obj.speaker) { $obj.speaker } else { "unknown" }
            $source = if ($obj.source) { $obj.source } else { "unknown" }
            $duration = if ($obj.duration) { $obj.duration } else { 0 }
            Write-Host ("speaker={0} source={1} duration={2}s" -f $speaker, $source, $duration)
            Write-Host ("text: {0}" -f $obj.text)
            if ($obj.actions -and $obj.actions.Count -gt 0) {
                Write-Host ("actions: {0}" -f ($obj.actions -join "; "))
            }
            else {
                Write-Host "actions: []"
            }
        }
        catch {
            Write-Host $message
        }
    }
}
finally {
    if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        $ws.CloseAsync(
            [System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure,
            "done",
            [Threading.CancellationToken]::None
        ).GetAwaiter().GetResult()
    }
    $ws.Dispose()
}
