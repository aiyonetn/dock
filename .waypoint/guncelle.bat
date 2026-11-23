@echo off
rem Waypoint guncelleyici. Kullanici cift tiklar; yapay zeka bu dosyayi kendisi calistirmaz.
rem Kurulum bu dosyayi calisirken degistirir; bu yuzden her sey tek satirda.
rem Once herkese acik adres denenir; repo gizliyse GitHub CLI girisiyle indirilir.
rem iex icinde kurulumun "exit 1"i calismaz; basariyi kurulumun koydugu $global:WaypointBasarili soyler.
cd /d "%~dp0.." && powershell -NoProfile -Command "$u = if ($env:WAYPOINT_INSTALL_URL) { $env:WAYPOINT_INSTALL_URL } else { 'https://raw.githubusercontent.com/1eren0/WaypointSkill/main/install.ps1' }; $s = try { irm $u } catch { if (-not $env:WAYPOINT_INSTALL_URL -and (Get-Command gh -ErrorAction SilentlyContinue)) { gh api repos/1eren0/WaypointSkill/contents/install.ps1 -H 'Accept: application/vnd.github.raw' | Out-String } }; if (-not $s) { Write-Host 'Waypoint indirilemedi. Repo gizliyse GitHub CLI kurup gh auth login ile giris yapin.'; exit 1 }; $global:WaypointBasarili = $false; $s | iex; if (-not $global:WaypointBasarili) { exit 1 }" && (echo. & echo Bitti. Bu pencereyi kapatip yapay zekaya "guncelledim" yaz.) || (echo. & echo Guncelleme OLMADI. Yukaridaki hatayi kopyalayip yapay zekaya goster.) & pause & exit /b
