module.exports = {
  apps: [
    {
      name: "linux-monitor-bot",
      script: "run_bot.sh",
      interpreter: "bash",
      cwd: __dirname,
      env_file: ".env",
      cron_restart: "30 4 * * *",
      env: {
        COMMAND_PREFIX: "!"
      }
    }
  ]
};
