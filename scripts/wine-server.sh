#!/bin/bash
# Test helper: run the Windows ZPS 2.4 dedicated server under Wine on Linux.
#   wine-server.sh start|stop|cmd "..."|log
W=${ZPS24_WIN:-/mnt/ssd500/zps24-win-server}
PORT=${ZPS24_WIN_PORT:-27025}
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine-zps24} WINEDEBUG=-all
IP=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')
PW=$(cat ~/.config/zps24/rcon.pw)
case "$1" in
start)
	cd "$W" && rm -f zps/console.log
	setsid wine srcds.exe -console -game zps -condebug -insecure -port $PORT +ip $IP +sv_lan 1 +maxplayers 24 \
		+rcon_password "$PW" +map "${2:-zpo_cabin_outbreak_b8_com}" > /tmp/zps24-win.out 2>&1 &
	echo "starting on $IP:$PORT" ;;
stop)
	pkill -f '[s]rcds\.exe' ; sleep 2; WINEPREFIX=$WINEPREFIX wineserver -k 2>/dev/null; echo stopped ;;   # [s]: don't match this shell's own command line
cmd)
	shift; ZPS24_RCON_HOST=$IP ZPS24_RCON_PORT=$PORT python3 "$(dirname "$0")/../core/scripts/rcon.py" "$*" ;;
log)
	tail -${2:-40} "$W/zps/console.log" ;;
esac
