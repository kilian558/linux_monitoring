module.exports = {
  apps: [
    {
      name: "linux-monitor-bot",
      script: "monitor_bot.py",
      interpreter: "python3",
      cwd: __dirname,
      env_file: ".env",
      cron_restart: "30 4 * * *",
      env: {
        COMMAND_PREFIX: "!"
      }
    }
  ]
};
