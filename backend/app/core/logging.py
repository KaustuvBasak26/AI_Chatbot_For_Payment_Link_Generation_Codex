import logging
import re


class SecretRedactionFilter(logging.Filter):
    patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
        re.compile(r"(?i)(x-llm-api-key|authorization|razorpay_key_secret|webhook_secret)(\s*[:=]\s*)[^\s,}]+"),
    )

    @classmethod
    def redact(cls, value: str) -> str:
        redacted = value
        for pattern in cls.patterns:
            if pattern.groups >= 2:
                redacted = pattern.sub(r"\1\2[REDACTED]", redacted)
            else:
                redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.redact(str(record.msg))
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(self.redact(arg) if isinstance(arg, str) else arg for arg in record.args)
            elif isinstance(record.args, dict):
                record.args = {key: self.redact(value) if isinstance(value, str) else value for key, value in record.args.items()}
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SecretRedactionFilter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
