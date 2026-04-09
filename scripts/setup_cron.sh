#!/bin/bash
# Install cron job for agentlynx-bot pipeline (every 2 hours)

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$SCRIPT_DIR/.venv/bin/python"
PIPELINE="$SCRIPT_DIR/run_pipeline.py"
LOG="$SCRIPT_DIR/logs/pipeline.log"

mkdir -p "$SCRIPT_DIR/logs"

# Add cron entry
CRON_LINE="0 */2 * * * cd $SCRIPT_DIR && $VENV $PIPELINE >> $LOG 2>&1"

(crontab -l 2>/dev/null | grep -v "run_pipeline.py"; echo "$CRON_LINE") | crontab -

echo "Cron job installed:"
echo "  $CRON_LINE"
echo ""
echo "Don't forget to start the Telegram bot as a background service:"
echo "  nohup $VENV $SCRIPT_DIR/run_telegram.py >> $SCRIPT_DIR/logs/telegram.log 2>&1 &"
