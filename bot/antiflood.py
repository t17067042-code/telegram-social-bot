from collections import defaultdict, deque
from time import monotonic


class AntiFlood:
    def __init__(self):
        self.events = defaultdict(deque)

    def hit(self, chat_id, user_id, limit, window):
        q = self.events[(chat_id, user_id)]
        now = monotonic()
        while q and now - q[0] > window:
            q.popleft()
        q.append(now)
        return len(q) >= limit

    def clear(self, chat_id, user_id):
        self.events.pop((chat_id, user_id), None)
