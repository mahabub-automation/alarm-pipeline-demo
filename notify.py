"""
Region-wise Telegram notifications.

Runs the full pipeline: process alarms, build the Excel report, then send
an overview, one message per region and the workbook to Telegram.

Usage:
    python notify.py --dry-run   print messages without sending
    python notify.py             send to Telegram
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from excel_report import build_report
from formatter import format_overview, format_region_message
from notifier import TelegramNotifier
from processor import process

# Stay well under Telegram's per-chat rate limit
SEND_DELAY_SECONDS = 1.2

# In production each region posts to its own team group.
# Map region names to chat IDs here; unmapped regions use TELEGRAM_CHAT_ID.
REGION_CHAT_IDS = {
    # "Dhaka North": "-1001234567890",
}


def build_messages(result):
    """Return a list of (region, text) pairs; region is None for the overview."""
    messages = [(None, format_overview(result))]
    for _, row in result["regions"].iterrows():
        messages.append((row["Region"], format_region_message(row, result)))
    return messages


def print_messages(messages):
    for _, text in messages:
        print("-" * 50)
        print(text)
    print("-" * 50)
    print(f"Dry run: {len(messages)} messages prepared, nothing sent.")


def send_messages(messages, report_path, token, default_chat):
    """Send every message and the report; return the number of failures."""
    failed = 0
    for region, text in messages:
        chat_id = REGION_CHAT_IDS.get(region, default_chat)
        if not TelegramNotifier(token, chat_id).send_message(text):
            failed += 1
            logging.error(f"Failed to send message for {region or 'overview'}")
        time.sleep(SEND_DELAY_SECONDS)

    if not TelegramNotifier(token, default_chat).send_document(
        report_path, caption="Full alarm report"
    ):
        failed += 1

    return failed


def main():
    parser = argparse.ArgumentParser(description="Send region-wise alarm notifications.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the messages instead of sending them")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")
    load_dotenv()

    result = process()
    report_path = build_report(result)
    messages = build_messages(result)
    logging.info(f"Prepared {len(messages)} messages and {report_path}")

    if args.dry_run:
        print_messages(messages)
        return 0

    token = os.getenv("TELEGRAM_TOKEN")
    default_chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not default_chat:
        logging.error("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        return 1

    failed = send_messages(messages, report_path, token, default_chat)
    logging.info(f"Finished: {len(messages) + 1 - failed} sent, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())