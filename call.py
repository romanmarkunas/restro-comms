from enum import Enum, unique


@unique
class CallState(Enum):
    STARTED = "started"
    CHOOSE_ACTION = "action"
    BOOKING_ASK_TIME = "ask_time"
    BOOKING_ASK_PAX = "ask_pax"
    BOOKING_DO = "do_booking"


class Call:

    def __init__(self, user_lvn, state=CallState.STARTED):
        self.user_lvn = str(user_lvn)
        self.state = state

    def get_lvn(self):
        return self.user_lvn

    def get_state(self):
        return self.state

    def get_state_val(self):
        return str(self.state.value)

    def set_state(self, state):
        self.state = state


class NccoBuilder:

    def __init__(self):
        self.ncco = []

    def customer_call_greeting(self):
        self.ncco.append(NccoBuilder.__talk(
            "Thanks for calling Two Tables. Please key in 1 for booking or 2 "
            "for cancelling."))
        return self

    def with_input(self, loc, method="GET", call=None):
        self.ncco.append(NccoBuilder.__input(loc=loc, method=method, call=call))
        return self

    def build(self):
        return self.ncco

    @staticmethod
    def __talk(text, barge_in=True):
        return {
            "action": "talk",
            "text": text,
            "voiceName": "Russell",
            "bargeIn": barge_in
        }

    @staticmethod
    def __input(loc, method=None, call=None):
        event_url = loc
        if call is not None:
            event_url += "?state=" + call.get_state_val()

        ncco = {
            "action": "input",
            "eventUrl": [event_url]
        }
        if method is not None:
            ncco["eventMethod"] = method

        return ncco
