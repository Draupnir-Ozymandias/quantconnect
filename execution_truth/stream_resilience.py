"""Declared BTC five-minute observation watchdogs; no execution claims."""
import json
import random

POLICY = {"schema_version": "qcrl.stream_resilience.v1",
          "initial_books_seconds": 10, "active_data_silence_seconds": 30,
          "stale_event_seconds": 5, "stale_flow_seconds": 10,
          "retry_base_seconds": 2, "retry_cap_seconds": 8,
          "retry_jitter": "equal_jitter"}


def retry_delay(connection, uniform=random.uniform):
    ceiling = min(POLICY["retry_cap_seconds"], POLICY["retry_base_seconds"] * 2**(connection - 1))
    return uniform(ceiling / 2, ceiling)


class DataWatchdog:
    def __init__(self, assets, started):
        self.assets, self.books = set(assets), set()
        self.started = self.last_data = started
        self.stale_since = None

    def reason(self, now, active):
        if self.books != self.assets and now - self.started >= POLICY["initial_books_seconds"]:
            return "initial_books_timeout"
        if active and now - self.last_data >= POLICY["active_data_silence_seconds"]:
            return "selected_book_data_silence"
        if active and self.stale_since is not None and now - self.stale_since >= POLICY["stale_flow_seconds"]:
            return "stale_timestamped_book_flow"
        return None

    def observe(self, raw, classes, now, receipt_epoch):
        try:
            data = json.loads(raw)
        except ValueError:
            return
        events = data if isinstance(data, list) else [data]
        relevant = []
        for event, cls in zip(events, classes):
            if cls["scope"] != "selected_market" or cls["event_type"] not in ("book", "price_change"):
                continue
            self.last_data = now
            if cls["event_type"] == "book":
                self.books.update(cls["asset_ids"])
            value = event.get("timestamp")
            if type(value) is int or (isinstance(value, str) and len(value) == 13 and value.isascii() and value.isdigit()):
                stamp = int(value)
                if 10**12 <= stamp < 10**13:
                    age = receipt_epoch - stamp / 1000
                    if age >= 0:
                        relevant.append(age)
        # Any fresh relevant event clears this diagnostic suspicion. Missing or
        # invalid timestamps are not evidence of freshness and do not clear it.
        if relevant:
            if any(age <= POLICY["stale_event_seconds"] for age in relevant):
                self.stale_since = None
            elif self.stale_since is None:
                self.stale_since = now
