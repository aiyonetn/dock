#!/bin/sh
# Waypoint güncelleyici. Kullanıcı çift tıklar; yapay zekâ bu dosyayı kendisi çalıştırmaz.
# Kurulum bu dosyayı çalışırken değiştirir; bu yüzden her şey tek blok olarak okunur.
# İndirme ayrı yapılır: `curl | sh` indirme başarısız olsa da başarılı görünürdü.
{
    cd "$(dirname "$0")/.." || exit 1
    script=$(curl -fsSL "${WAYPOINT_INSTALL_URL:-https://raw.githubusercontent.com/1eren0/WaypointSkill/main/install.sh}") || script=
    if [ -z "$script" ] && [ -z "${WAYPOINT_INSTALL_URL:-}" ] && command -v gh >/dev/null 2>&1; then
        # Gizli repo: GitHub CLI girişiyle indir
        script=$(gh api repos/1eren0/WaypointSkill/contents/install.sh -H "Accept: application/vnd.github.raw") || script=
    fi
    if [ -n "$script" ] && printf '%s\n' "$script" | sh; then
        printf '\n%s\n' 'Bitti. Bu pencereyi kapatıp yapay zekâya "güncelledim" yaz.'
    else
        printf '\n%s\n' 'Güncelleme OLMADI. Yukarıdaki hatayı kopyalayıp yapay zekâya göster.'
    fi
    exit
}
