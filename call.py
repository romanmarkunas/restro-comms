from enum import Enum, unique


@unique
class CallState(Enum):
    STARTED = "started"
    CHOOSE_ACTION = "action"
    BOOKING_ASK_TIME = "ask_time"
    BOOKING_ASK_PAX = "ask_pax"
    BOOKING_DO = "do_booking"
    BOOKING_CONFIRM_ALTERNATIVE = "alternative"
    CANCELLING = "cancel"
    REMINDING = "remind"

class Call:

    def __init__(self, user_lvn, state=CallState.STARTED, is_mobile=True):
        self.user_lvn = str(user_lvn)
        self.state = state
        self.saved_vars = {}
        self.is_mobile = is_mobile

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

    def get_is_mobile(self):
        return self.is_mobile


class NccoBuilder:

    def __init__(self):
        self.ncco = []

    def customer_call_greeting(self, name):
        self.ncco.append(NccoBuilder.__talk(
            "Thanks for calling Two Tables " + name + ". Please key in 1 for booking 2 "
            "for cancelling or 3 to reschedule. Alternatively press 0 and hash key any time"
            "during this call to speak to manager"
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
            "Thanks for letting us know! Your reservation for" + hour + " was "
            "cancelled. Bye!",
            barge_in=False
        ))
        return self

    def cancel_and_reschedule(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "Thanks for letting us know! Your reservation for" + hour + " was "
            "cancelled. Please enter the new time between 12 and 21 hours followed "
            "by the hash key!",
            barge_in=False
        ))
        return self

    def book(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "Fantastic, your booking has been successful, we'll see you "
            "at " + hour + " hours. Bye!",
            barge_in=False
        ))
        return self

    def wait(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "I'm sorry, but " + hour + " hours is currently full, you've been "
            "added to the waiting list and we'll call you immediately once the "
            "slot becomes available. Bye!",  # TODO - better propose other time
            barge_in=False
        ))
        return self

    def alternative(self, hour, alternative_hour, pax):
        self.ncco.append(NccoBuilder.__talk(
            "I'm sorry, but " + hour + " hours is currently full. Best "
            "alternative I can provide is table for " + pax + " people "
            "at " + alternative_hour + " hours. Press 1 to confirm, 2 to "
            "join wait list or 0 to speak with manager"
        ))
        return self

    def remind(self, hour):
        self.ncco.append(NccoBuilder.__talk(
            "Hi, this is Two Tables. Just checking you are still ok for your "
            "reservation at " + hour + " hours? Press 1 for yes, 2 for cancel "
            "or any other key to repeat."
        ))
        return self

    def remind_confirmed(self):
        self.ncco.append(NccoBuilder.__talk(
            "Outstanding, we look forward to seeing you soon. Bye!",
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
            "timeOut": 3
        }

        if extra_params is not None:
            ncco.update(extra_params)

        return ncco
