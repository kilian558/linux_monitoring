module.exports = {
  apps: [
    {
      name: "linux-monitor-bot",
      script: "monitor_bot.py",
      interpreter: "python3",
      env: {
        DISCORD_TOKEN: "",
        COMMAND_PREFIX: "!"
      }
    }
  ]
};
