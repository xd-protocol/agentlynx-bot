import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class Poster:
    def __init__(self, twitter_env: dict[str, str]):
        self.env = {**os.environ, **twitter_env}

    def post_reply(self, tweet_id: str, text: str) -> bool:
        try:
            result = subprocess.run(["twitter", "reply", tweet_id, text], capture_output=True, text=True, env=self.env)
            if result.returncode != 0:
                logger.error("Failed to post reply: %s", result.stderr)
                return False
            data = json.loads(result.stdout)
            return data.get("ok", False)
        except Exception as e:
            logger.error("Error posting reply: %s", e)
            return False

    def check_auth(self) -> bool:
        try:
            result = subprocess.run(["twitter", "status", "--json"], capture_output=True, text=True, env=self.env)
            if result.returncode != 0:
                return False
            data = json.loads(result.stdout)
            return data.get("ok", False) and data.get("data", {}).get("authenticated", False)
        except Exception:
            return False
