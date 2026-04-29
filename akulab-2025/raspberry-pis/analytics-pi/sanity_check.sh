#!/usr/bin/env bash
#
# sanity_check.sh
#
# One-shot system sanity check from Analytics Pi perspective.
# Checks: mounts, NTP sources on all Pis, recent audio files,
#         cron jobs, user services, disk space, health log freshness,
#         NAS reachability, and backup activity.
#
# Usage: ./sanity_check.sh
#        ./sanity_check.sh --no-color
#

set -euo pipefail

NO_COLOR=false
[[ "${1:-}" == "--no-color" ]] && NO_COLOR=true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.ini"

# ── helpers ──────────────────────────────────────────────────────────────────

read_config() {
  local section="$1" key="$2"
  awk -F= -v s="$section" -v k="$key" '
    $0 ~ "\\[" s "\\]" { in_s=1; next }
    in_s && $1 ~ k { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/ { in_s=0 }
  ' "$CONFIG_FILE"
}

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
if $NO_COLOR; then GREEN=''; YELLOW=''; RED=''; BOLD=''; RESET=''; fi

PASS=0; WARN=0; FAIL=0

pass()  { echo -e "${GREEN}  ✅ PASS${RESET}  $*"; PASS=$((PASS+1));  }
warn()  { echo -e "${YELLOW}  ⚠️  WARN${RESET}  $*"; WARN=$((WARN+1)); }
fail()  { echo -e "${RED}  ❌ FAIL${RESET}  $*"; FAIL=$((FAIL+1));  }
header(){ echo -e "\n${BOLD}══ $* ══${RESET}"; }

# ── read config ───────────────────────────────────────────────────────────────

CLOCKPI_IP=$(read_config "clockpi" "clockpi_ip")
CLOCKPI_USER=$(read_config "clockpi" "clockpi_user")
RECORDINGPI_IP=$(read_config "recordingpi" "recordingpi_ip")
RECORDINGPI_USER=$(read_config "recordingpi" "recordingpi_user")
ANALYTICSPI_USER=$(read_config "analyticspi" "analyticspi_user")
ANALYTICSPI_IP=$(read_config "analyticspi" "analyticspi_ip")
NAS_IP=$(read_config "nas" "nas_ip")
NAS_REMOTE_DIR=$(read_config "nas" "to_audio_dir")
LOCAL_RECORDING_MOUNT=$(read_config "analyticspi" "from_audio_dir")
LOCAL_NAS_MOUNT=$(read_config "analyticspi" "to_audio_dir")
REMOTE_AUDIO_DIR=$(read_config "recordingpi" "to_audio_dir")

POOLED_BASE="/home/${ANALYTICSPI_USER}/logs/pooled"
TODAY=$(date +%F)

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║        AukLab System Sanity Check - ${TODAY}   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo "  Clock Pi    : ${CLOCKPI_IP}"
echo "  Recording Pi: ${RECORDINGPI_IP}"
echo "  Analytics Pi: ${ANALYTICSPI_IP}"
echo "  NAS         : ${NAS_IP}"

# ── 1) Network reachability ───────────────────────────────────────────────────

header "1) Network Reachability"

for label_ip in "Clock Pi:${CLOCKPI_IP}" "Recording Pi:${RECORDINGPI_IP}" "NAS:${NAS_IP}"; do
  label="${label_ip%%:*}"; ip="${label_ip##*:}"
  if ping -c 1 -W 2 "$ip" &>/dev/null; then
    pass "$label ($ip) reachable"
  else
    fail "$label ($ip) NOT reachable"
  fi
done

# ── 2) Mounts ─────────────────────────────────────────────────────────────────

header "2) Mount Points"

if mountpoint -q "$LOCAL_RECORDING_MOUNT"; then
  pass "Recording Pi SSHFS mounted at $LOCAL_RECORDING_MOUNT"
else
  fail "Recording Pi NOT mounted at $LOCAL_RECORDING_MOUNT"
fi

if mountpoint -q "$LOCAL_NAS_MOUNT"; then
  pass "NAS NFS mounted at $LOCAL_NAS_MOUNT"
else
  fail "NAS NOT mounted at $LOCAL_NAS_MOUNT"
fi

# ── 3) Recent audio files ─────────────────────────────────────────────────────

header "3) Audio Files"

AUDIO_MAX_AGE_MIN=30  # expect a new file within this many minutes

check_audio_dir() {
  local label="$1" dir="$2"
  if [[ ! -d "$dir" ]]; then
    fail "$label: directory $dir not accessible"
    return
  fi
  local newest
  newest=$(find "$dir" -maxdepth 1 -name '*.wav' -printf '%T@ %p\n' 2>/dev/null \
           | sort -rn | head -1 | awk '{print $2}')
  if [[ -z "$newest" ]]; then
    fail "$label: no .wav files found in $dir"
    return
  fi
  local age_min
  age_min=$(( ( $(date +%s) - $(stat -c %Y "$newest") ) / 60 ))
  local fname; fname=$(basename "$newest")
  if (( age_min <= AUDIO_MAX_AGE_MIN )); then
    pass "$label: newest file '$fname' is ${age_min}m old"
  else
    warn "$label: newest file '$fname' is ${age_min}m old (expected < ${AUDIO_MAX_AGE_MIN}m)"
  fi
}

check_audio_dir "Recording Pi (via SSHFS)" "$LOCAL_RECORDING_MOUNT"
check_audio_dir "NAS (via NFS)"            "$LOCAL_NAS_MOUNT"

# Also check via SSH directly on Recording Pi
if ssh -o ConnectTimeout=5 -o BatchMode=yes "${RECORDINGPI_USER}@${RECORDINGPI_IP}" true 2>/dev/null; then
  newest_remote=$(ssh -o ConnectTimeout=5 "${RECORDINGPI_USER}@${RECORDINGPI_IP}" \
    "find '$REMOTE_AUDIO_DIR' -maxdepth 1 -name '*.wav' -printf '%T@ %p\n' 2>/dev/null \
     | sort -rn | head -1 | awk '{print \$2}'" 2>/dev/null || true)
  if [[ -n "$newest_remote" ]]; then
    age_min=$(ssh -o ConnectTimeout=5 "${RECORDINGPI_USER}@${RECORDINGPI_IP}" \
      "echo \$(( ( \$(date +%s) - \$(stat -c %Y '$newest_remote') ) / 60 ))" 2>/dev/null || echo "?")
    pass "Recording Pi local audio: $(basename "$newest_remote") is ${age_min}m old"
  else
    fail "Recording Pi: no .wav files found at $REMOTE_AUDIO_DIR"
  fi
else
  warn "Cannot SSH to Recording Pi ($RECORDINGPI_IP) — skipping direct audio check"
fi

# ── 4) NTP / Chrony sources ───────────────────────────────────────────────────

header "4) NTP / Chrony Sources"

check_chrony_client() {
  local label="$1" host="$2" user="$3"
  local out
  if [[ "$host" == "local" ]]; then
    out=$(chronyc sources -n 2>/dev/null || true)
  else
    out=$(ssh -o ConnectTimeout=5 -o BatchMode=yes "${user}@${host}" \
      "chronyc sources -n" 2>/dev/null || true)
  fi
  if [[ -z "$out" ]]; then
    warn "$label: could not reach chrony"
    return
  fi
  # Accept IP or hostname match for Clock Pi
  local selected
  selected=$(echo "$out" | awk '/^\^\*/ {print $2; exit}')
  if [[ -z "$selected" ]]; then
    fail "$label: no selected chrony source (no ^* line)"
  elif [[ "$selected" == "$CLOCKPI_IP" || "$selected" == *"clockpi"* ]]; then
    pass "$label: chrony using Clock Pi as source ($selected)"
  else
    warn "$label: chrony source is $selected (expected Clock Pi $CLOCKPI_IP)"
  fi
}

check_chrony_server() {
  local label="$1" host="$2" user="$3"
  local out
  out=$(ssh -o ConnectTimeout=5 -o BatchMode=yes "${user}@${host}" \
    "chronyc sources" 2>/dev/null || true)
  if [[ -z "$out" ]]; then
    warn "$label: could not reach chrony"
    return
  fi
  # Clock Pi uses a local reference (#* prefix = local clock like GPS/PPS)
  local selected
  selected=$(echo "$out" | awk '/^#\*/ {print $2; exit}')
  if [[ -n "$selected" ]]; then
    pass "$label: chrony locked to local reference clock ($selected) — GPS/PPS OK"
  else
    # Might also be using a network fallback (^*) if GPS not yet locked
    selected=$(echo "$out" | awk '/^\^\*/ {print $2; exit}')
    if [[ -n "$selected" ]]; then
      warn "$label: chrony using network source $selected (GPS/PPS not selected — is antenna locked?)"
    else
      fail "$label: chrony has no selected source at all"
    fi
  fi
}

check_chrony_client "Analytics Pi"  "local"           ""
check_chrony_client "Recording Pi"  "$RECORDINGPI_IP" "$RECORDINGPI_USER"
check_chrony_server "Clock Pi"      "$CLOCKPI_IP"     "$CLOCKPI_USER"

# ── 5) User services ──────────────────────────────────────────────────────────

header "5) Analytics Pi User Services"

for svc in mount_recording_pi.service mount_nas.service; do
  state=$(systemctl --user is-active "$svc" 2>/dev/null || echo "unknown")
  enabled=$(systemctl --user is-enabled "$svc" 2>/dev/null || echo "unknown")
  if [[ "$state" == "active" ]]; then
    pass "$svc is active (enabled=$enabled)"
  else
    # For one-shot style mount services, inactive after successful mount is OK
    # if the mountpoint is actually present
    if [[ "$svc" == "mount_recording_pi.service" ]] && mountpoint -q "$LOCAL_RECORDING_MOUNT"; then
      pass "$svc: inactive but mount confirmed present"
    elif [[ "$svc" == "mount_nas.service" ]] && mountpoint -q "$LOCAL_NAS_MOUNT"; then
      pass "$svc: inactive but mount confirmed present"
    else
      fail "$svc is $state (enabled=$enabled) and mount not present"
    fi
  fi
done

linger=$(loginctl show-user "$ANALYTICSPI_USER" 2>/dev/null | grep Linger | cut -d= -f2)
if [[ "$linger" == "yes" ]]; then
  pass "Linger enabled for $ANALYTICSPI_USER"
else
  fail "Linger NOT enabled for $ANALYTICSPI_USER (user services won't survive reboot without login)"
fi

# ── 6) Recording service on Recording Pi ─────────────────────────────────────

header "6) Recording Pi Service"

if ssh -o ConnectTimeout=5 -o BatchMode=yes "${RECORDINGPI_USER}@${RECORDINGPI_IP}" true 2>/dev/null; then
  rec_state=$(ssh -o ConnectTimeout=5 "${RECORDINGPI_USER}@${RECORDINGPI_IP}" \
    "systemctl is-active record_zoom.service" 2>/dev/null || echo "unknown")
  if [[ "$rec_state" == "active" ]]; then
    pass "record_zoom.service is active on Recording Pi"
  else
    fail "record_zoom.service is $rec_state on Recording Pi"
  fi

  disk_info=$(ssh -o ConnectTimeout=5 "${RECORDINGPI_USER}@${RECORDINGPI_IP}" \
    "df -h '$REMOTE_AUDIO_DIR' 2>/dev/null | tail -1" 2>/dev/null || true)
  if [[ -n "$disk_info" ]]; then
    use_pct=$(echo "$disk_info" | awk '{print $5}' | tr -d '%')
    if (( use_pct >= 90 )); then
      fail "Recording Pi disk $use_pct% full: $disk_info"
    elif (( use_pct >= 75 )); then
      warn "Recording Pi disk $use_pct% full: $disk_info"
    else
      pass "Recording Pi disk usage: ${use_pct}%"
    fi
  fi
else
  warn "Cannot SSH to Recording Pi — skipping service and disk checks"
fi

# ── 7) Cron jobs ──────────────────────────────────────────────────────────────

header "7) Cron Jobs (Analytics Pi)"

crontab_out=$(crontab -l 2>/dev/null || true)

check_cron() {
  local label="$1" pattern="$2"
  if echo "$crontab_out" | grep -qE "^[^#].*${pattern}"; then
    pass "Cron active: $label"
  else
    fail "Cron MISSING or commented: $label"
  fi
}

check_cron "backup_recordings"   "backup_recordings.py"
check_cron "health_snapshot"     "rpi_health_snapshot.py"
check_cron "mount_watchdog"      "mount_watchdog.sh"
check_cron "pool_logs/summaries" "pool_logs.sh"
check_cron "push_summaries"      "push_summaries.sh"

# ── 8) Health log freshness ───────────────────────────────────────────────────

header "8) Health Log Freshness (today = $TODAY)"

HEALTH_MAX_AGE_MIN=30

check_health_log() {
  local label="$1" pi_dir="$2"
  local log_file="${POOLED_BASE}/${pi_dir}/rpi_health_snapshot/${TODAY}_rpi_health.csv"
  if [[ ! -f "$log_file" ]]; then
    warn "$label: no health log for today at $log_file"
    return
  fi
  local age_min
  age_min=$(( ( $(date +%s) - $(stat -c %Y "$log_file") ) / 60 ))
  local lines
  lines=$(wc -l < "$log_file")
  if (( age_min <= HEALTH_MAX_AGE_MIN )); then
    pass "$label: health log updated ${age_min}m ago (${lines} rows)"
  else
    warn "$label: health log last updated ${age_min}m ago (stale?)"
  fi
}

check_health_log "Clock Pi"     "clockpi"
check_health_log "Recording Pi" "recordingpi"
check_health_log "Analytics Pi" "analyticspi"

# ── 9) Backup activity ────────────────────────────────────────────────────────

header "9) Backup Activity"

BACKUP_LOG="${POOLED_BASE}/analyticspi/backup_recordings/${TODAY}_backup_recordings.log"
if [[ ! -f "$BACKUP_LOG" ]]; then
  warn "No backup log for today at $BACKUP_LOG"
else
  age_min=$(( ( $(date +%s) - $(stat -c %Y "$BACKUP_LOG") ) / 60 ))
  errors=$(grep -c "ERROR\|FAIL\|error\|fail" "$BACKUP_LOG" 2>/dev/null || true)
  synced=$(grep -c "synced\|copied\|transferred" "$BACKUP_LOG" 2>/dev/null || true)
  if (( age_min <= 20 )); then
    if (( errors > 0 )); then
      warn "Backup log updated ${age_min}m ago but contains ${errors} error line(s)"
    else
      pass "Backup log updated ${age_min}m ago, ${errors} errors, ~${synced} sync events"
    fi
  else
    warn "Backup log last updated ${age_min}m ago (expected < 20m if cron is running)"
  fi
fi

# ── 10) Disk space (Analytics Pi) ────────────────────────────────────────────

header "10) Disk Space (Analytics Pi)"

df -h --output=target,pcent,avail / /home 2>/dev/null | tail -n +2 | while read -r mount pct avail; do
  pct_num=$(echo "$pct" | tr -d '%')
  if (( pct_num >= 90 )); then
    fail "Disk $mount is ${pct} full (${avail} free)"
  elif (( pct_num >= 75 )); then
    warn "Disk $mount is ${pct} full (${avail} free)"
  else
    pass "Disk $mount is ${pct} full (${avail} free)"
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────

TOTAL=$(( PASS + WARN + FAIL ))
echo ""
echo -e "${BOLD}══ Summary ══${RESET}"
echo -e "  Total checks : $TOTAL"
echo -e "  ${GREEN}Pass${RESET}  : $PASS"
echo -e "  ${YELLOW}Warn${RESET}  : $WARN"
echo -e "  ${RED}Fail${RESET}  : $FAIL"
echo ""

if (( FAIL > 0 )); then
  echo -e "${RED}System NOT fully healthy — ${FAIL} check(s) failed.${RESET}"
  exit 1
elif (( WARN > 0 )); then
  echo -e "${YELLOW}System mostly healthy — ${WARN} warning(s) to review.${RESET}"
  exit 0
else
  echo -e "${GREEN}System fully healthy. All checks passed.${RESET}"
  exit 0
fi
