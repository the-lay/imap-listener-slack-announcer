# IMAP Listener - Slack Announcer
[<img src="https://img.shields.io/badge/dockerhub-images-green.svg?logo=Docker">](https://hub.docker.com/r/thelay/imap-listener-slack-announcer/)
[<img src="https://img.shields.io/badge/github-repository-green.svg?logo=Github">](https://github.com/the-lay/imap-listener-slack-announcer)
[<img src="https://github.com/the-lay/imap-listener-slack-announcer/actions/workflows/dockerhub_publish.yml/badge.svg?branch=main">](https://github.com/the-lay/imap-listener-slack-announcer/actions/workflows/dockerhub_publish.yml)

This tool listens to a mailbox on an IMAP server and whenever there is a new unseen message,
publishes it to Slack channel of your choice. 

For ease of use, containerized [(Docker Hub)](https://hub.docker.com/r/thelay/imap-listener-slack-announcer/) 
and configured with environment variables (see `.env.sample` file).

If you are using mailgun to receive emails, you can also try an earlier version of this code, 
[the-lay/mailgun-slack-announcer](https://github.com/the-lay/mailgun-slack-announcer).

## Quick start

1. Create an `.env` file based on `.env.sample` from the repository
2. Run the container and pass env file with...  
    ... Docker:
    ```bash
    docker run -d -p 8000:80 --env-file .env thelay/imap-listener-slack-announcer:latest
    ```

    ... Docker Compose (forwarding output to port 8000): 
    ```docker-compose
    version: "3.7"
    services:
      email_listener:
        container_name: email_listener
        image: thelay/imap-listener-slack-announcer:latest
        restart: unless-stopped
        env_file:
          - .env
        ports:
          - "8000:80"
    ```

In addition to env variables defined in `.env`, the docker image can take advantage of base image 
[tiangolo/meinheld-gunicorn-flask-docker](https://github.com/tiangolo/meinheld-gunicorn-flask-docker)
and use
[its environment variables](https://github.com/tiangolo/meinheld-gunicorn-flask-docker#environment-variables).

## Message templating
Maybe one day? For now change template in `main.py`, `process_email()` method.
