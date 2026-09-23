# Start the reserved public media tunnel required by Buffer publishing.
$ApiPort = "8000"
$NgrokDomain = "perceptually-homocentric-lindy.ngrok-free.dev"
$ExpectedBaseUrl = "https://$NgrokDomain"

if (-not (Get-Command "ngrok" -ErrorAction SilentlyContinue)) {
    throw "ngrok is required for Buffer media publishing."
}
try {
    $config = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/media/config" -TimeoutSec 5
} catch {
    throw "AURA is not responding on http://127.0.0.1:$ApiPort. Start the API first."
}
if (-not $config.configured -or $config.base_url.TrimEnd('/') -ne $ExpectedBaseUrl) {
    throw "Set MEDIA_PUBLIC_BASE_URL=$ExpectedBaseUrl in the root .env and restart AURA."
}

Write-Host "[aura] Starting the Buffer media tunnel at https://$NgrokDomain -> http://localhost:$ApiPort"
Write-Host "[aura] Keep this terminal running while Buffer is in use."
& ngrok http "--url=$NgrokDomain" $ApiPort
