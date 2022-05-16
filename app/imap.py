# Heavily based on:
# https://github.com/bondar-aleksandr/telegram_email_checker/blob/main/utils/imap_api.py

import asyncio
from datetime import datetime
from email import message_from_bytes
from email.message import Message
from email.policy import default as default_policy
from typing import Optional, Tuple, List, Dict, NamedTuple
from collections import namedtuple

import aioimaplib

from config import config


seq_date = namedtuple("seq_date", "seq date")
seq_msg = namedtuple("seq_msg", "seq msg")


class ImapError(Exception):
    pass


class CredentialsErrors(ImapError):
    pass


class MailboxError(ImapError):
    pass


class ServerError(ImapError):
    pass


class ImapWorker:
    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection: Optional[aioimaplib.IMAP4_SSL] = None

    @property
    def state(self) -> str:
        _state = self.connection.get_state()
        return _state if _state else "UNKNOWN"

    async def connect(self):
        self.connection = aioimaplib.IMAP4_SSL(
            host=self.host,
            port=self.port,
            timeout=5,
        )

        try:
            await self.connection.wait_hello_from_server()

            await self.connection.login(user=self.user, password=self.password)
            if self.state != "AUTH":
                raise CredentialsErrors

            await self.connection.select(mailbox=config.mailbox)
            if self.state != "SELECTED":
                raise MailboxError

        except asyncio.exceptions.TimeoutError:
            print(f"Unable to connect to IMAP server {self.host}:{self.port}!")
        except CredentialsErrors:
            print(f"Wrong credentials!")
        except MailboxError:
            print(f"Mailbox {config.mailbox} can not be selected!")

    async def disconnect(self):
        try:

            if self.connection.has_pending_idle():
                self.connection.idle_done()

            await self.connection.close()
            await self.connection.logout()

        except asyncio.exceptions.TimeoutError:
            print("Timeout during IMAP disconnection!")
        except aioimaplib.Abort:
            print(f"Can't disconnect session in state {self.state}!")

    async def run(self, process_message_func):

        while True:
            # Start IMAP session
            await self.connect()
            start_time = datetime.now()

            while True:
                # Check for idle loop maximum session duration
                if (datetime.now() - start_time).seconds > config.imap_session_duration:
                    break

                # Get new messages and process them
                await self._get_new_messages(process_message_func)

                # Handle connection
                try:
                    idle_task = await self.connection.idle_start(timeout=60)
                    await self.connection.wait_server_push()
                    self.connection.idle_done()
                    await asyncio.wait_for(idle_task, timeout=5)
                except asyncio.exceptions.TimeoutError:
                    raise ConnectionError("Connection to IMAP server is lost!")
                except aioimaplib.Abort as e:
                    raise ServerError(e.args)

            # Finish IMAP session
            await self.disconnect()

    async def _get_new_messages(self, process_message_func) -> None:
        try:
            seq_list, n_messages = await self._search_messages("UNSEEN")
            print(f"Found {n_messages} new messages!")
            if n_messages > 0:
                seq_msg_list = await self._fetch_message_bodies(seq_list)
                await process_message_func(seq_msg_list)
        except asyncio.exceptions.TimeoutError:
            raise ConnectionError("Timeout occurred!")
        except aioimaplib.Abort:
            raise ServerError("Unexpected server response")

    async def _search_messages(self, lookup_rule: str) -> Tuple[List, int]:
        lookup = await self.connection.search(lookup_rule)

        if lookup.result == "OK":
            msg_nums_str = lookup.lines[0].decode()
            msg_nums_list = msg_nums_str.split()
            n_messages = len(msg_nums_list)
            return msg_nums_list, n_messages
        else:
            raise ServerError(
                f"Search for {lookup_rule} failed with result {lookup.result}!"
            )

    async def _fetch_message_bodies(self, seq_list: List[str]) -> List[NamedTuple]:
        result = []
        for seq in seq_list:
            response = await self.connection.fetch(
                message_set=seq, message_parts="(RFC822)"
            )
            if response.result == "OK":
                msg = message_from_bytes(response.lines[1], policy=default_policy)
                result.append(seq_msg(seq, msg))
            else:
                raise ServerError(
                    f"Error during fetching {seq} body, server returned {response.result}!"
                )

        return result

    async def _process_messages(
        self, seq_msg_list: List[NamedTuple], func, func_kwargs: Dict
    ) -> None:
        for element in seq_msg_list:
            element: seq_msg
            print("Processing message... ", end="")

            # Go through the message
            for part in element.msg.walk():
                part: Message
                content_type = part.get_content_type()

                if content_type.startswith("text"):
                    text = part.get_payload()
                    if part["Content-Transfer-Encoding"] == "base64":
                        text = part.get_payload(decode=True).decode()
                    func(text, **func_kwargs)

                elif content_type == "application":
                    pl = part.get_payload(decode=True)
                    func(pl, **func_kwargs)

            # Mark message as seen
            await self.connection.store(element.seq, "+FLAGS", "\\Seen")

            print("Finished.")
