import asyncio
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
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))

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
        timestamp=datetime.now(),
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
    if MONITOR_MESSAGE_ID:
        try:
            message_id = int(MONITOR_MESSAGE_ID)
            message = await channel.fetch_message(message_id)
        except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
            message = None

    if message:
        await message.edit(embed=embed)
    else:
        await channel.send(embed=embed)


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
