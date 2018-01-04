from enum import Enum, unique


@unique
class CallState(Enum):
    STARTED = "started"
    CHOOSE_ACTION = "action"
    BOOKING_ASK_TIME = "ask_time"
    BOOKING_ASK_PAX = "ask_pax"
    BOOKING_DO = "do_booking"
    CANCELLING = "cancel"


class Call:

    def __init__(self, user_lvn, state=CallState.STARTED):
        self.user_lvn = str(user_lvn)
        self.state = state
        self.saved_vars = {}

    def get_lvn(self):
        return self.user_lvn

    def get_state(self):
        return self.state

    def get_state_val(self):
        return str(self.state.value)

    def set_state(self, state):
        self.state = state

    def save_var(self, key, val):
        self.saved_vars[key] = val

    def get_var(self, key):
        return self.saved_vars[key]


class NccoBuilder:

    def __init__(self):
        self.ncco = []

    def customer_call_greeting(self):
        self.ncco.append(NccoBuilder.__talk(
            "Thanks for calling Two Tables. Please key in 1 for booking or 2 "
            "for cancelling."
        ))
        return self

    def select_time(self):
        self.ncco.append(NccoBuilder.__talk(
            "Excellent, please enter the time between 12 and 21 hours followed "
            "by the hash key."
        ))
        return self

    def select_pax(self):
        self.ncco.append(NccoBuilder.__talk(
            "Please enter number of guests between 1 and 4"
        ))
        return self

    def cancel(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "Thanks for letting us know! Your reservation for" + hour + "pm was"
            "cancelled. You should receive confirmation SMS soon. Bye!",
            barge_in=False
        ))
        return self

    def book(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "Fantastic, your booking has been successful, we'll see you "
            "at " + hour + " pm. Bye!",
            barge_in=False
        ))
        return self

    def wait(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "I'm sorry, but " + hour + " pm is currently full, you've been "
            "added to the waiting list and we'll call you immediately once the "
            "slot becomes available. Bye!",  # TODO - better propose other time
            barge_in=False
        ))
        return self

    def with_input(self, loc, extra_params=None):
        self.ncco.append(NccoBuilder.__input(loc, extra_params=extra_params))
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
    def __input(loc, extra_params=None):
        ncco = {
            "action": "input",
            "eventUrl": [loc],
            "timeOut": 15
        }

        if extra_params is not None:
            ncco.update(extra_params)

        return ncco
