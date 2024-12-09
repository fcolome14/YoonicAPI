#!/usr/bin/env bash
# wait-for-it.sh: waits for a given service to be available

# Usage: wait-for-it.sh host:port [-t timeout] -- command arg1 arg2 ...

# Default timeout is 30 seconds
TIMEOUT=30
WAIT_FOR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    *:* )
      WAIT_FOR="$1"
      shift
      ;;
    -t)
      TIMEOUT="$2"
      shift 2
      ;;
    --)
      shift
      COMMAND="$@"
      break
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

# Check if the WAIT_FOR variable is set (must be host:port)
if [[ -z "$WAIT_FOR" ]]; then
  echo "Usage: wait-for-it.sh host:port [-t timeout] -- command"
  exit 1
fi

# Split WAIT_FOR into host and port
HOST=$(echo "$WAIT_FOR" | cut -d':' -f1)
PORT=$(echo "$WAIT_FOR" | cut -d':' -f2)

# Function to check if the host is available
check_host() {
  nc -z -v -w5 "$HOST" "$PORT" &> /dev/null
  return $?
}

# Wait for the service to be available
echo "Waiting for $WAIT_FOR to be available..."

SECONDS=0
until check_host; do
  if [[ $SECONDS -ge $TIMEOUT ]]; then
    echo "Timeout reached. $WAIT_FOR is still not available."
    exit 1
  fi
  sleep 1
done

echo "$WAIT_FOR is available. Executing the command..."
exec $COMMAND
