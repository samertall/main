"""Environment configuration; zero implicit sending in demo mode."""
import os


def setting(name, default=""):
    return os.environ.get(name, default)


def is_live():
    return setting("APP_MODE", "demo").lower() == "aws"


def can_send():
    return is_live() and setting("SEND_ENABLED", "0").lower() in {"1", "true", "yes"}


def region():
    return setting("AWS_REGION", "us-east-1")
