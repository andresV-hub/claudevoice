import time


class Conversation:

    def __init__(self, timeout=90):
        self.timeout = timeout
        self.active = False
        self.last_activity = 0

    def activate(self):
        self.active = True
        self.touch()

    def deactivate(self):
        self.active = False

    def touch(self):
        self.last_activity = time.time()

    def expired(self):
        if not self.active:
            return True

        return (
            time.time() - self.last_activity
            > self.timeout
        )

    def should_accept_without_wake_word(self):
        if self.expired():
            self.deactivate()
            return False

        self.touch()
        return True

    def reset(self):
        self.active = False
        self.last_activity = 0