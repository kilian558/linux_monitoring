# Linux Monitoring Discord Bot

Ein Discord Bot, der Live-Systeminformationen (CPU, RAM, Swap, Netzwerk) ausgibt.

## Voraussetzungen (Linux)
- Python 3.10+
- Git
- Node.js + npm
- pm2 (`npm i -g pm2`)

## Installation
1. Repo klonen:
   `git clone https://github.com/kilian558/linux_monitoring.git`
2. Abhängigkeiten installieren:
   `pip install -r requirements.txt`
3. Bot-Token setzen:
   - In der `.env` Datei `DISCORD_TOKEN` eintragen
   - Optional `COMMAND_PREFIX` anpassen
   - Optional `CHANNEL_ID` setzen (Ziel-Channel für die Ausgabe)

## Start mit pm2
- Start: `pm2 start ecosystem.config.js`
- Logs: `pm2 logs linux-monitor-bot`
- Neustart: `pm2 restart linux-monitor-bot`
- Stop: `pm2 stop linux-monitor-bot`
- Autostart aktivieren: `pm2 startup` und danach `pm2 save`

## Bot-Befehl
- `!monitor`
