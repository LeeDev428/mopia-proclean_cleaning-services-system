# Find PostgreSQL bin directory and add to PATH
$pgVersions = @("16", "15", "14", "13", "12", "11", "10")
$found = $false

foreach ($version in $pgVersions) {
    $pgPath = "C:\Program Files\PostgreSQL\$version\bin"
    if (Test-Path $pgPath) {
        $env:PATH += ";$pgPath"
        Write-Host "Added PostgreSQL $version to PATH"
        $found = $true
        break
    }
}

if (-not $found) {
    Write-Host "PostgreSQL bin directory not found in common locations"
}

# Display current PATH
Write-Host "PATH now contains: $($env:PATH)"

# Add virtual environment activation
Write-Host "Activating virtual environment..."
try {
    & "C:\Users\grafr\OneDrive\Desktop\mopia-cleaning-services\venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated successfully"
} catch {
    Write-Host "Failed to activate virtual environment: $_"
    Write-Host "Try running: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass"
}
