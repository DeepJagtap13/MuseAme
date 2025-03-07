# Change directory to your Flask project
cd C:\Users\xyz\Desktop\theog\bhai2

# Activate virtual environment
.venv\Scripts\activate

# Start Flask app in the background
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "app.py"

# Wait for Flask to start
Start-Sleep -Seconds 5

# Start ngrok
Start-Process -NoNewWindow -FilePath "ngrok" -ArgumentList "http 5000"

# Wait for ngrok to initialize
Start-Sleep -Seconds 5

# Retry fetching ngrok URL up to 10 times
$ngrokUrl = $null
for ($i = 1; $i -le 10; $i++) {
    Start-Sleep -Seconds 2
    try {
        $ngrokUrl = (Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels").tunnels[0].public_url
        if ($ngrokUrl) { break }  # Exit loop if URL is found
    } catch {
        Write-Output "Waiting for ngrok to start... ($i/10)"
    }
}

if (-not $ngrokUrl) {
    Write-Output "❌ Failed to get ngrok URL. Is ngrok running?"
    exit
}

# Bitly API Key (REPLACE WITH YOUR NEW API TOKEN)
$bitlyApiKey = "YOUR_BITLY_API_KEY"

# Existing Bitly Short Link
$bitlyShortLink = "bit.ly/museame"

# Update Bitly with the new ngrok URL
$body = @{ long_url = $ngrokUrl } | ConvertTo-Json -Compress
$headers = @{ "Authorization" = "Bearer $bitlyApiKey"; "Content-Type" = "application/json" }

Invoke-RestMethod -Uri "https://api-ssl.bitly.com/v4/bitlinks/$bitlyShortLink" -Method PATCH -Body $body -Headers $headers

# Output the updated short link
Write-Output "✅ Your Flask app is always accessible at: https://$bitlyShortLink"

# Keep the script running (optional)
Start-Sleep -Seconds 999999
