module.exports = {
  apps: [
    {
      name: "linux-monitor-bot",
      script: "monitor_bot.py",
      interpreter: "python3",
      cwd: __dirname,
      env_file: ".env",
      env: {
        COMMAND_PREFIX: "!"
      }
    }
  ]
};
