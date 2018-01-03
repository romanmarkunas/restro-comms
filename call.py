from enum import Enum, unique


@unique
class CallState(Enum):
    STARTED = "started"
    BOOKING_ASK_TIME = "ask_time"
    BOOKING_ASK_PAX = "ask_pax"
    BOOKING_DO = "do_booking"


class Call:

    def __init__(self, state=CallState.STARTED):
        self.state = state

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state
