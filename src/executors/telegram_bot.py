"""
Telegram Bot Executor.

Commands:
    /analyze <symbol> [mode] [st_bar]
    /status

Example:
    /analyze BTC-USD fast
    /analyze ETH-USD thorough 1h
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.agents.graph import run_pipeline
from src.core.utils import get_telegram_token, load_config, setup_logging
from src.reporters.executive_report import write_report_to_disk

logger = logging.getLogger(__name__)


class RegimeBot:
    """Telegram bot for regime analysis"""

    def __init__(self, token: str, config_path: str = "config/settings.yaml"):
        self.token = token
        self.config = load_config(config_path)
        self.allowed_user_ids = set(self.config.get("telegram", {}).get("allowed_user_ids", []))
        self.rate_limit = {}

    def _is_allowed(self, user_id: int) -> bool:
        """Check if user is in allowlist"""
        if not self.allowed_user_ids:
            # If no allowlist, allow all (development mode)
            logger.warning("No allowed_user_ids configured - allowing all users")
            return True
        return user_id in self.allowed_user_ids

    def _check_rate_limit(self, user_id: int, seconds: int = 30) -> bool:
        """Check if user exceeded rate limit"""
        now = datetime.utcnow()
        last_request = self.rate_limit.get(user_id)

        if last_request and (now - last_request).total_seconds() < seconds:
            return False

        self.rate_limit[user_id] = now
        return True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🤖 Crypto Regime Analysis Bot\n\n"
            "Commands:\n"
            "/analyze <symbol> [mode] [st_bar] - Run regime analysis\n"
            "/status - Check bot status\n\n"
            "Example:\n"
            "/analyze BTC-USD fast\n"
            "/analyze ETH-USD thorough 1h"
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id

        if not self._is_allowed(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return

        await update.message.reply_text(
            f"✅ Bot is running\n"
            f"User ID: {user_id}\n"
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /analyze command.

        Usage: /analyze <symbol> [mode] [st_bar]
        """
        user_id = update.effective_user.id

        # Check authorization
        if not self._is_allowed(user_id):
            await update.message.reply_text("❌ Unauthorized. Contact administrator.")
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            return

        # Check rate limit
        rate_limit_seconds = self.config.get("telegram", {}).get("rate_limit_seconds", 30)
        if not self._check_rate_limit(user_id, rate_limit_seconds):
            await update.message.reply_text(
                f"⏳ Rate limit exceeded. Please wait {rate_limit_seconds}s between requests."
            )
            return

        # Parse arguments
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ Usage: /analyze <symbol> [mode] [st_bar]\n\n"
                "Example: /analyze BTC-USD fast"
            )
            return

        symbol = args[0].upper()
        mode = args[1].lower() if len(args) > 1 else "fast"
        st_bar = args[2] if len(args) > 2 else None

        if mode not in ["fast", "thorough"]:
            await update.message.reply_text("❌ Mode must be 'fast' or 'thorough'")
            return

        # Start analysis
        await update.message.reply_text(
            f"🔄 Starting analysis for {symbol} (mode={mode})...\n"
            "This may take 30-60 seconds."
        )

        try:
            # Run pipeline
            final_state = await asyncio.to_thread(
                run_pipeline,
                symbol=symbol,
                mode=mode,
                st_bar=st_bar,
                config_path="config/settings.yaml",
            )

            # Write report
            report_path = await asyncio.to_thread(write_report_to_disk, final_state)

            # Get results
            exec_report = final_state.get("exec_report")
            judge_report = final_state.get("judge_report")

            if not exec_report:
                await update.message.reply_text("❌ Analysis failed: No report generated")
                return

            # Check validation
            if judge_report and not judge_report.valid:
                error_msg = "⚠️ Analysis completed with validation errors:\n"
                error_msg += "\n".join(f"- {e}" for e in judge_report.errors[:3])
                await update.message.reply_text(error_msg)

            # Send summary
            summary = (
                f"✅ Analysis complete: {symbol}\n\n"
                f"**ST Regime:** {exec_report.st_regime.value}\n"
                f"**ST Strategy:** {exec_report.st_strategy}\n"
                f"**Confidence:** {exec_report.st_confidence:.1%}\n"
            )

            if exec_report.backtest_sharpe is not None:
                summary += f"\n**Backtest Sharpe:** {exec_report.backtest_sharpe:.2f}\n"
                summary += f"**Max Drawdown:** {exec_report.backtest_max_dd:.1%}\n"

            summary += f"\n📁 Artifacts: `{exec_report.artifacts_dir}`"

            await update.message.reply_text(summary, parse_mode="Markdown")

            # Send report file
            report_file = Path(report_path)
            if report_file.exists():
                await update.message.reply_document(
                    document=open(report_file, "rb"),
                    filename=f"{symbol}_report.md",
                    caption=f"📄 Full report for {symbol}",
                )

            logger.info(f"Analysis completed for {symbol} (user {user_id})")

        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Analysis failed: {str(e)}\n\n"
                "Check logs for details or try again later."
            )

    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram bot...")

        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set. Cannot start bot.")
            return

        # Create application
        app = Application.builder().token(self.token).build()

        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("analyze", self.analyze_command))

        # Start polling
        logger.info("Bot started. Press Ctrl+C to stop.")
        app.run_polling()


def main():
    """Main entry point"""
    setup_logging(level="INFO")

    token = get_telegram_token()

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        logger.error("Set it in .env file or export it in your shell")
        return

    bot = RegimeBot(token)
    bot.run()


if __name__ == "__main__":
    main()

