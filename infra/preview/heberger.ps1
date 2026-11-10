# Héberge XPASS derrière des tunnels publics pour un test (le PC doit rester allumé).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $Root "docker-compose.yml"))) { $Root = Split-Path -Parent $PSScriptRoot }
Set-Location $Root
$Preview = Join-Path $Root "infra\preview"
New-Item -ItemType Directory -Force -Path $Preview | Out-Null

function Set-EnvKey([string]$Path, [string]$Key, [string]$Value) {
    $lines = @(Get-Content -LiteralPath $Path)
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^$([regex]::Escape($Key))=") {
            $found = $true
            "$Key=$Value"
        } else { $line }
    }
    if (-not $found) { $out += "$Key=$Value" }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, (($out -join "`n").TrimEnd() + "`n"), $utf8)
}

function Add-CorsOrigin([string]$Path, [string]$Origin) {
    $lines = @(Get-Content -LiteralPath $Path)
    $out = foreach ($line in $lines) {
        if ($line -match "^CORS_ORIGINS=(.*)$") {
            $current = $Matches[1]
            if ($current -notlike "*$Origin*") { "CORS_ORIGINS=$current,$Origin" } else { $line }
        } else { $line }
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, (($out -join "`n").TrimEnd() + "`n"), $utf8)
}

function Find-Cloudflared {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}

$cf = Find-Cloudflared
if (-not $cf) {
    Write-Host "Installation de cloudflared..."
    try {
        winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $cf = Find-Cloudflared
    } catch { $cf = $null }
}
if (-not $cf) {
    $exe = Join-Path $Preview "cloudflared.exe"
    if (-not (Test-Path $exe)) {
        Write-Host "Téléchargement de cloudflared..."
        Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $exe
    }
    $cf = $exe
}

Write-Host "Démarrage de la passerelle locale..."
docker compose -f docker-compose.yml -f docker-compose.preview.yml up -d preview

function Start-Tunnel([string]$Name, [int]$Port) {
    $log = Join-Path $Preview "$Name.log"
    Get-Process cloudflared -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*localhost:$Port*" -or $_.CommandLine -like "*127.0.0.1:$Port*"
    } | Out-Null
    $outLog = Join-Path $Preview "$Name.out.log"
    $proc = Start-Process -FilePath $cf -ArgumentList @("tunnel","--url","http://127.0.0.1:$Port","--protocol","http2","--no-autoupdate") -RedirectStandardError $log -RedirectStandardOutput $outLog -PassThru -WindowStyle Hidden
    $url = $null
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $log) {
            $text = Get-Content -LiteralPath $log -Raw -ErrorAction SilentlyContinue
            if ($text -match "https://[a-z0-9-]+\.trycloudflare\.com") {
                $url = $Matches[0]
                break
            }
        }
        if ($proc.HasExited) { throw "Le tunnel $Name s'est arrêté. Voir $log" }
    }
    if (-not $url) { throw "Pas d'URL pour le tunnel $Name. Voir $log" }
    return $url
}

Write-Host "Ouverture des tunnels publics..."
# App client servie sous /client sur le même tunnel que les portails (Caddy :3080).
$site = Start-Tunnel "site" 3080
$auth = Start-Tunnel "auth" 8080
$app = "$site/client"

$urlsPath = Join-Path $Preview ".urls"
@(
    "PREVIEW_SITE_URL=$site",
    "PREVIEW_APP_URL=$app",
    "PREVIEW_AUTH_URL=$auth"
) | Set-Content -LiteralPath $urlsPath -Encoding ascii

Set-EnvKey (Join-Path $Root ".env") "PREVIEW_AUTH_URL" $auth
Set-EnvKey (Join-Path $Root ".env") "PREVIEW_SITE_URL" $site
Set-EnvKey (Join-Path $Root ".env") "PREVIEW_APP_URL" $app
Set-EnvKey (Join-Path $Root ".env") "OIDC_ISSUER" "$auth/realms/xpass"
Set-EnvKey (Join-Path $Root ".env") "API_PUBLIC_URL" $site
Set-EnvKey (Join-Path $Root ".env") "APP_PUBLIC_URL" $app
Set-EnvKey (Join-Path $Root ".env") "PORTALS_PUBLIC_URL" $site
Set-EnvKey (Join-Path $Root ".env") "MEDIA_BASE_URL" "$site/xpass-public"
Add-CorsOrigin (Join-Path $Root ".env") $site

$local = Join-Path $Root "apps\portals\.env.local"
Set-EnvKey $local "PORTALS_PUBLIC_URL" $site
Set-EnvKey $local "APP_PUBLIC_URL" $app
Set-EnvKey $local "OIDC_ISSUER" "http://localhost:8080/realms/xpass"
Set-EnvKey $local "OIDC_ISSUER_PUBLIC" "$auth/realms/xpass"
Set-EnvKey $local "NEXT_PUBLIC_MEDIA_BASE_URL" "$site/xpass-public"

Write-Host "Mise à jour de Keycloak et de l'API..."
docker compose up -d keycloak
for ($i = 0; $i -lt 40; $i++) {
    $st = docker inspect -f "{{.State.Health.Status}}" xpass-keycloak-1 2>$null
    if ($st -eq "healthy") { break }
    Start-Sleep -Seconds 3
}
# recreate (pas restart) : recharge OIDC_ISSUER / URLs publiques du .env
docker compose up -d --force-recreate api worker scheduler
Start-Sleep -Seconds 5

$apply = Get-Content -LiteralPath (Join-Path $Preview "apply_urls.py") -Raw
$apply | docker compose exec -T `
    -e PREVIEW_SITE_URL=$site `
    -e PREVIEW_APP_URL=$app `
    -e PREVIEW_AUTH_URL=$auth `
    -e KC_PASS=admin-dev-only `
    api python -

Write-Host "SITE=$site"
Write-Host "APP=$app"
Write-Host "AUTH=$auth"
Write-Host "GOOGLE_REDIRECT=$auth/realms/xpass/broker/google/endpoint"
