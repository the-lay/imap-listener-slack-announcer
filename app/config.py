from functools import lru_cache
import pydantic


class Settings(pydantic.BaseSettings):

    # IMAP connection parameters
    smtp_host: str
    smtp_port: int = 993
    smtp_user: str
    smtp_pass: str

    # Application parameters
    mailbox: str = "INBOX"
    imap_session_duration: int
    retry_history: int = 3
    retry_interval: int = 30
    restart_supress: int = 300

    # Slack parameters
    slack_api_token: str
    slack_channel: str
    administrator_id: str
    unfurl_links: bool = False
    unfurl_media: bool = False

    class Config:
        env_file = "../.env"  # for local development
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


config = get_settings()
