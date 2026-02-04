import asyncio
import json
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import psutil

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
CHANNEL_ID = os.getenv("CHANNEL_ID")
MONITOR_MESSAGE_ID = os.getenv("MONITOR_MESSAGE_ID")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "10"))
MESSAGE_ID_FILE = os.getenv("MESSAGE_ID_FILE", "monitor_message.json")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
BOT = commands.Bot(command_prefix=COMMAND_PREFIX, intents=INTENTS)

_last_net = None
_last_net_time = None


def _bar(percent: float, length: int = 10) -> str:
    filled = int(round((percent / 100.0) * length))
    filled = max(0, min(length, filled))
    return "[" + "█" * filled + "░" * (length - filled) + "]"


def _gb(value: float) -> str:
    return f"{value / (1024 ** 3):.2f} GB"


def _mbps(bytes_per_sec: float) -> str:
    return f"{(bytes_per_sec * 8) / 1_000_000:.2f} MBit/s"


def _load_message_id() -> str | None:
    if MONITOR_MESSAGE_ID:
        return MONITOR_MESSAGE_ID
    if not os.path.exists(MESSAGE_ID_FILE):
        return None
    try:
        with open(MESSAGE_ID_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return str(data.get("message_id")) if data.get("message_id") else None
    except (OSError, json.JSONDecodeError):
        return None


def _save_message_id(message_id: int) -> None:
    try:
        with open(MESSAGE_ID_FILE, "w", encoding="utf-8") as handle:
            json.dump({"message_id": message_id}, handle)
    except OSError:
        pass


def _net_speeds() -> tuple[float, float]:
    global _last_net, _last_net_time
    now = datetime.utcnow().timestamp()
    counters = psutil.net_io_counters()

    if _last_net is None or _last_net_time is None:
        _last_net = counters
        _last_net_time = now
        return 0.0, 0.0

    elapsed = max(0.1, now - _last_net_time)
    down_bps = (counters.bytes_recv - _last_net.bytes_recv) / elapsed
    up_bps = (counters.bytes_sent - _last_net.bytes_sent) / elapsed

    _last_net = counters
    _last_net_time = now
    return down_bps, up_bps


async def _gather_stats():
    cpu_total = await asyncio.to_thread(psutil.cpu_percent, 1.0)
    cpu_per_core = await asyncio.to_thread(psutil.cpu_percent, 1.0, True)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    down_bps, up_bps = _net_speeds()

    return {
        "cpu_total": cpu_total,
        "cpu_per_core": cpu_per_core,
        "mem": mem,
        "swap": swap,
        "down_bps": down_bps,
        "up_bps": up_bps,
    }


def _build_embed(stats: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🖥 Monitoring Linux VM",
        description="Live-Systeminformationen",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="〽️ CPU-Gesamtauslastung",
        value=f"{_bar(stats['cpu_total'])} {stats['cpu_total']:.2f}%",
        inline=False,
    )

    core_lines = []
    for idx, pct in enumerate(stats["cpu_per_core"]):
        core_lines.append(f"C{idx:02d}: {_bar(pct)} {pct:.2f}%")
    embed.add_field(name="📊 CPU-Kerne", value="\n".join(core_lines), inline=False)

    mem = stats["mem"]
    mem_text = (
        f"Genutzt: {_gb(mem.used)} / Frei: {_gb(mem.available)} / Total: {_gb(mem.total)}\n"
        f"Auslastung: {_bar(mem.percent)} {mem.percent:.2f}%"
    )
    embed.add_field(name="🎟 RAM", value=mem_text, inline=False)

    swap = stats["swap"]
    swap_text = (
        f"Genutzt: {_gb(swap.used)} / Frei: {_gb(swap.free)} / Total: {_gb(swap.total)}\n"
        f"Auslastung: {_bar(swap.percent)} {swap.percent:.2f}%"
    )
    embed.add_field(name="🗂️ Swap", value=swap_text, inline=False)

    net_text = f"↓ {_mbps(stats['down_bps'])} | ↑ {_mbps(stats['up_bps'])}"
    embed.add_field(name="🌐 Netzwerk", value=net_text, inline=False)

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    uptime_text = str(uptime).split(".")[0]

    try:
        load1, load5, load15 = os.getloadavg()
        load_text = f"{load1:.2f}, {load5:.2f}, {load15:.2f}"
    except OSError:
        load_text = "n/a"

    disk = psutil.disk_usage("/")
    disk_text = (
        f"Genutzt: {_gb(disk.used)} / Frei: {_gb(disk.free)} / Total: {_gb(disk.total)}\n"
        f"Auslastung: {_bar(disk.percent)} {disk.percent:.2f}%"
    )

    embed.add_field(name="💾 Disk (/)", value=disk_text, inline=False)
    embed.add_field(name="⏱️ Uptime", value=uptime_text, inline=True)
    embed.add_field(name="📈 Load (1/5/15)", value=load_text, inline=True)

    embed.set_footer(text=datetime.now().strftime("heute um %H:%M Uhr"))
    return embed


async def _get_target_channel():
    if not CHANNEL_ID:
        return None
    try:
        target_id = int(CHANNEL_ID)
    except ValueError:
        return None

    channel = BOT.get_channel(target_id)
    if channel is None:
        channel = await BOT.fetch_channel(target_id)
    return channel


@BOT.command(name="monitor")
async def monitor_command(ctx: commands.Context):
    stats = await _gather_stats()
    embed = _build_embed(stats)

    target_channel = await _get_target_channel()
    if target_channel:
        await target_channel.send(embed=embed)
        if ctx.channel.id != target_channel.id:
            await ctx.send("Monitoring wurde im Ziel-Channel gepostet.")
    else:
        await ctx.send(embed=embed)


@tasks.loop(seconds=UPDATE_INTERVAL)
async def monitor_loop():
    channel = await _get_target_channel()
    if channel is None:
        return

    stats = await _gather_stats()
    embed = _build_embed(stats)

    message = None
    message_id_str = _load_message_id()
    if message_id_str:
        try:
            message = await channel.fetch_message(int(message_id_str))
        except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
            message = None

    if message:
        await message.edit(embed=embed)
    else:
        new_message = await channel.send(embed=embed)
        _save_message_id(new_message.id)


@BOT.event
async def on_ready():
    print(f"Eingeloggt als {BOT.user}")
    if CHANNEL_ID and not monitor_loop.is_running():
        monitor_loop.start()


def main():
    if not TOKEN:
        raise SystemExit("Bitte DISCORD_TOKEN als Umgebungsvariable setzen.")
    BOT.run(TOKEN)


if __name__ == "__main__":
    main()
