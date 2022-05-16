import asyncio
import time
from typing import List, NamedTuple
from email.utils import parsedate_to_datetime
from collections import deque

from config import config
from imap import ImapWorker, ImapError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


api = WebClient(token=config.slack_api_token)


async def process_email(seq_msg_list: List[NamedTuple]):

    for seq, msg in seq_msg_list:

        sender = ", ".join(msg.get_all("From"))
        recipients = ", ".join(msg.get_all("To"))
        timestamp = parsedate_to_datetime(msg["Date"])
        subject = msg["Subject"]

        body = ""
        attachments = []

        for part in msg.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            cdisposition = part.get("Content-Disposition")

            if ctype == "text/plain":
                body += payload.decode("utf-8")
            elif ctype != "multipart" and cdisposition is not None:
                attachments.append((part.get_filename(), payload))

        try:
            announcement = api.chat_postMessage(
                channel=config.slack_channel,
                text=f"📧📧📧\n"
                f"*Sender:* {sender}\n"
                f"*Recipients:* {recipients}\n"
                f"*Time:* {timestamp:%Y-%m-%d %H:%M:%S} UTC\n"
                f"*Subject:* {subject}",
                parse="full",
                unfurl_links=config.unfurl_links,
                unfurl_media=config.unfurl_media,
            )
            thread_ts = announcement.get("ts")

            api.chat_postMessage(
                channel=config.slack_channel,
                thread_ts=thread_ts,
                text=body,
                unfurl_links=config.unfurl_links,
                unfurl_media=config.unfurl_media,
            )

            for filename, attachment in attachments:
                api.files_upload(
                    channels=config.slack_channel,
                    thread_ts=thread_ts,
                    filename=filename,
                    file=attachment,
                )

        except SlackApiError as e:
            api.chat_postMessage(channel=config.slack_channel, text=e.response["error"])


async def shutdown(loop):
    print("Shutting down... ", end="")
    await worker.disconnect()

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.exceptions.CancelledError:
        pass

    loop.stop()
    print("Finished.")


async def supervisor(func):
    start_times = deque([float("-inf")], maxlen=config.retry_history)
    while True:
        start_times.append(time.monotonic())
        try:
            return await func(process_email)
        except ConnectionError as e:
            if min(start_times) > (time.monotonic() - config.retry_interval):
                await asyncio.sleep(config.restart_supress)
            else:
                print(f"Restarting...")
        except ImapError:
            await shutdown(loop=loop)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    worker = ImapWorker(
        config.smtp_host,
        config.smtp_port,
        config.smtp_user,
        config.smtp_pass,
    )

    loop.create_task(supervisor(worker.run))
    loop.run_forever()
