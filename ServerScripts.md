## SH Scripts
**`start.sh` pattern** (adapt runtime — node, uvicorn, python, etc.):
```bash
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Already running (PID $(cat "$PID_FILE")). Use restart.sh to restart."
  exit 1
fi

cd "$DIR"
nohup {runtime command} > "$DIR/server.log" 2>&1 &
echo $! > "$PID_FILE"
echo "Started (PID $!). Logs: $DIR/server.log"
```

**`stop.sh` pattern** (same for all apps):
```bash
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "Not running (no PID file found)."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill -9 "$PID"
  rm -f "$PID_FILE"
  echo "Stopped (PID $PID)."
else
  echo "Process $PID not found. Cleaning up PID file."
  rm -f "$PID_FILE"
fi
```

**`restart.sh` pattern** (same for all apps):
```bash
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/stop.sh"
sleep 1
"$DIR/start.sh"
```

All three scripts must be made executable: `chmod +x start.sh stop.sh restart.sh`