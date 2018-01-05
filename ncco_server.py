"""This endpoint will serve NCCO objects required by Nexmo VAPI"""

import hug
import requests
from booking_service import BookingService
from datetime import datetime
from base64 import urlsafe_b64encode
from threading import Thread
import os
import calendar
from jose import jwt
from call import CallState, Call, NccoBuilder
from ncco_helper import NCCOHelper


class NCCOServer:

    EVENT = "/event"

    REMIND_INPUT = "/remind/input"
    REMIND_START = "/remind/start"

    NCCO_INPUT = "/ncco/input"

    WAITING_INPUT = "/waiting/input"
    WAITING_START = "/waiting/start"

    APPLICATION_ID = "b75f58ba-f8ee-47fb-b0d0-a47ab23143c0"
    SIGN_OFF = ", thank you good bye."

    def __init__(self):
        self.lvn = "447418397022"
        self.manager_lvn = "447426007676"
        self.domain = "http://booktwotables.herokuapp.com"
        self.booking_service = BookingService()
        self.uuid_to_lvn = {}
        self.outbound_uuid_to_booking = {}
        self.calls = {}

    @hug.object.get('/ncco')
    def start_call(self, request):
        lvn = request.params['from']
        number_insight_json = NCCOHelper.get_call_info(lvn)
        caller_name = number_insight_json.get("caller_name", "")
        call = Call(user_lvn=lvn, state=CallState.CHOOSE_ACTION, is_mobile=number_insight_json["original_carrier"] == "mobile")
        self.calls[request.params['conversation_uuid']] = call
        return NccoBuilder().customer_call_greeting(caller_name).with_input(
            self.domain + NCCOServer.NCCO_INPUT
        ).build()

    @hug.object.post(NCCO_INPUT)
    def ncco_input_response(self, body=None):
        dtmf = body['dtmf']
        uuid = body['conversation_uuid']
        call = self.calls[uuid]

        if dtmf == "0" or dtmf == "0#":
            del self.calls[uuid]
            return [{
                "action": "record",
                "eventUrl": [self.domain + NCCOServer.EVENT]
            }, {
                "action": "connect",
                "eventUrl": [self.domain + NCCOServer.EVENT],
                "from": self.lvn,
                "endpoint": [{
                    "type": "phone",
                    "number": self.manager_lvn
                }]
            }]

        if call.get_state() == CallState.CHOOSE_ACTION:
            if dtmf == "1":
                return self.__switch_to_ask_time(call=call)
            elif dtmf == "2":
                return self.__do_cancel(customer_number=call.get_lvn(), uuid=uuid)
            elif dtmf == "3":
                return self.__do_cancel_and_reschedule(customer_number=call.get_lvn(), uuid=uuid)
        elif call.get_state() == CallState.BOOKING_ASK_TIME:
            time = int(dtmf)
            if time < 12 or time > 21:
                return self.__switch_to_ask_time(call=call)
            else:
                call.save_var('time', time)
                return self.__switch_to_ask_pax(call=call)
        elif call.get_state() == CallState.BOOKING_ASK_PAX:
            pax = int(dtmf)
            if pax < 1 or pax > 4:
                return self.__switch_to_ask_pax(call=call)
            
            booking_time = call.get_var('time')
            customer_number = call.get_lvn()
            alternatives = []
            result = self.booking_service.book(hour=booking_time, pax=pax, alternatives=alternatives, customer_number=customer_number)

            if result:
                if call.get_is_mobile:
                    NCCOHelper.send_sms(call.get_lvn(), "You booking for " + str(booking_time) + ":00 has been confirmed.")
                return NccoBuilder().book(str(booking_time)).build()
            elif not alternatives:
                self.booking_service.put_to_wait(hour=booking_time, pax=pax, customer_number=customer_number)
                return NccoBuilder().wait(str(booking_time)).build()
            else:
                call.set_state(CallState.BOOKING_CONFIRM_ALTERNATIVE)
                call.save_var('alternative', alternatives[0])
                call.save_var('pax', pax)
                call.save_var('hour', booking_time)
                return NccoBuilder().alternative(
                    hour=str(booking_time),
                    alternative_hour=str(self.booking_service.slot_to_hour(alternatives[0][0])),
                    pax=str(alternatives[0][1].pax)
                ).with_input(
                    self.domain + NCCOServer.NCCO_INPUT,
                    extra_params={
                        "timeOut": 7
                    }
                ).build()
        elif call.get_state() == CallState.BOOKING_CONFIRM_ALTERNATIVE:
            booking_time = call.get_var('hour')
            pax = int(call.get_var('pax'))
            customer_number = call.get_lvn()
            if dtmf == "1":
                self.booking_service.book(
                    hour=int(self.booking_service.slot_to_hour(call.get_var('alternative')[0])),
                    pax=int(call.get_var('alternative')[1].pax),
                    alternatives=[],
                    customer_number=customer_number
                )
                if call.get_is_mobile:
                    NCCOHelper.send_sms(call.get_lvn(), "You booking for " + str(booking_time) + ":00 has been confirmed.")
                return NccoBuilder().book(str(booking_time)).build()
            if dtmf == "2":
                self.booking_service.put_to_wait(hour=booking_time, pax=pax, customer_number=customer_number)
                return NccoBuilder().wait(str(booking_time)).build()

    def __do_cancel(self, customer_number, uuid):
        cancellable_results = self.booking_service.find_bookings(customer_number)
        # ASSUMPTION we will always cancel the first booking for a particular customer.
        self.booking_service.cancel(cancellable_results[0][1].id)
        return self.__cancel_triggered(
            customer_number=customer_number,
            uuid=uuid,
            slot=cancellable_results[0][0]
        )

    def __do_cancel_and_reschedule(self, customer_number, uuid):
        cancellable_results = self.booking_service.find_bookings(customer_number)
        # ASSUMPTION we will always cancel the first booking for a particular customer.
        self.booking_service.cancel(cancellable_results[0][1].id)
        return self.__cancel_and_reschedule_triggered(
            customer_number=customer_number,
            uuid=uuid,
            slot=cancellable_results[0][0]
        )

    def __cancel_and_reschedule_triggered(self, customer_number, slot, uuid):
        number_insight_json = NCCOHelper.get_call_info(customer_number)
        if number_insight_json["original_carrier"] == "mobile":
            NCCOHelper.send_sms(customer_number, "Your booking for " + str(self.booking_service.slot_to_hour(int(slot))) + " has been cancelled.")
        Thread(target=self.call_waiting_customers(slot)).start()
        call = self.calls[uuid]
        call.set_state(CallState.BOOKING_ASK_TIME)
        return NccoBuilder().cancel_and_reschedule(str(slot)).with_input(
                    self.domain + NCCOServer.NCCO_INPUT,
                    extra_params={
                        "submitOnHash": True,
                        "timeOut": 15
                    }).build()

    def __cancel_triggered(self, customer_number, slot, uuid):
        number_insight_json = NCCOHelper.get_call_info(customer_number)
        print(str(number_insight_json))
        print(str(number_insight_json["original_carrier"]['network_type']))
        if number_insight_json["original_carrier"]['network_type'] == "mobile":
            print("Sending cancel SMS")
            NCCOHelper.send_sms(customer_number, "Your booking for " + str(self.booking_service.slot_to_hour(int(slot))) + ":00 has been cancelled.")
        Thread(target=self.call_waiting_customers, args=(slot, )).start()
        self.calls.pop(uuid, None)
        return NccoBuilder().cancel(str(slot)).build()

    def __switch_to_ask_time(self, call):
        call.set_state(CallState.BOOKING_ASK_TIME)
        return NccoBuilder().select_time().with_input(
            self.domain + NCCOServer.NCCO_INPUT,
            extra_params={
                "submitOnHash": True,
                "timeOut": 15
            }
        ).build()

    def __switch_to_ask_pax(self, call):
        call.set_state(CallState.BOOKING_ASK_PAX)
        return NccoBuilder().select_pax().with_input(
            self.domain + NCCOServer.NCCO_INPUT
        ).build()

    def call_waiting_customers(self, slot):
        print("Searching in wait list for slot: " + str(slot))
        wait_list = self.booking_service.get_wait_list()
        for customer_waiting in wait_list:
            alternatives = self.booking_service.generate_alternatives(
                slot=customer_waiting[0],
                booking=self.booking_service.get_booking(
                    pax=customer_waiting[1].pax,
                    lvn=customer_waiting[1].customer_number
                )
            )
            for alt in alternatives:
                if alt[0] == slot:
                    response = requests.post(
                        "https://api.nexmo.com/v1/calls",
                        headers={"Authorization": "Bearer " + self.__generate_jwt()},
                        json={
                            "to": [{
                                "type": "phone",
                                "number": str(customer_waiting[1].customer_number)
                            }],
                            "from": {
                                "type": "phone",
                                "number": self.lvn
                            },
                            "answer_url": [self.domain + NCCOServer.WAITING_START + "?slot=" + str(slot) + "&pax=" + str(alt[1].pax)],
                            "event_url": [self.domain + NCCOServer.EVENT]
                        })
                    uuid = response.json()["conversation_uuid"]
                    print("Customers booking ID: " + str(customer_waiting[1].id))
                    print("Customers UUID: " + uuid)
                    return

    @hug.object.get(WAITING_START)
    def start_waiting_call(self, request=None, slot=None, pax=None):

        return [
            {
                "action": "talk",
                "voiceName": "Russell",
                "text": "Hi there it's Two Tables, a booking slot " \
                        "for " + str(pax) + " people at " + str(self.booking_service.slot_to_hour(int(slot))) + " hours has become free, " \
                        "press 1 to accept or 2 to pass",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": [self.domain + NCCOServer.WAITING_INPUT]
            }
        ]

    @hug.object.post(WAITING_INPUT)
    def waiting_call_input_response(self, body=None):
        dtmf = body["dtmf"]
        uuid = body["uuid"]

        customer_number = self.uuid_to_lvn[uuid]
        self.uuid_to_lvn.pop(uuid, "")

        def get_slot_using_customer_number(val):
            return val[1].customer_number == customer_number

        index = self.booking_service.wait_list.find(get_slot_using_customer_number)

        if dtmf == "1":
            alternatives = []

            print("Waiting customers UUID for DTMF: " + uuid)

            slot_booking = self.booking_service.get_wait_list()[index]

            self.booking_service.book(slot_booking[0], slot_booking[1].pax, slot_booking[1].customer_number, alternatives)
            self.booking_service.remove_from_wait_list(index)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Stupendous, you booking for " + str(self.booking_service.slot_to_hour(slot_booking[0])) + " hours has been confirmed, " \
                            "we look forward to seeing you soon" + NCCOServer.SIGN_OFF
                }
            ]

        elif dtmf == "2":
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Got it! I'll call if something else gets free",
                }
            ]

    @hug.object.post('/remind/trigger')
    def remind_trigger_call(self, body=None):
        booking_id = int(body["id"])
        booking = self.booking_service.find(booking_id)[1]
        response = requests.post(
            "https://api.nexmo.com/v1/calls",
            headers={"Authorization": "Bearer " + self.__generate_jwt()},
            json={
                "to": [{
                    "type": "phone",
                    "number": str(booking.customer_number)
                }],
                "from": {
                    "type": "phone",
                    "number": self.lvn
                },
                "answer_url": [self.domain + NCCOServer.REMIND_START],
                "event_url": [self.domain + NCCOServer.EVENT]
            })
        uuid = response.json()["conversation_uuid"]
        self.outbound_uuid_to_booking[uuid] = booking_id

    def __generate_jwt(self):
        return jwt.encode(
            claims={
                "iat": calendar.timegm(datetime.utcnow().utctimetuple()),
                "application_id": NCCOServer.APPLICATION_ID,
                "jti": urlsafe_b64encode(os.urandom(64)).decode('utf-8')
            },
            key=os.environ["PRIVATE_KEY"],
            algorithm='RS256')

    @hug.object.get(REMIND_START)
    def remind_start_ncco(self, conversation_uuid=None):
        booking_id = self.outbound_uuid_to_booking[conversation_uuid]
        time = self.booking_service.find(booking_id)[0]
        return NccoBuilder().remind(str(time)).with_input(
            self.domain + NCCOServer.REMIND_INPUT
        ).build()

    @hug.object.post(REMIND_INPUT)
    def remind_input_response(self, body = None):
        dtmf = body["dtmf"]
        uuid = body["conversation_uuid"]
        if dtmf == "1":
            return NccoBuilder().remind_confirmed().build()
        elif dtmf == "2":
            booking_id = self.outbound_uuid_to_booking[uuid]
            booking = self.booking_service.cancel(booking_id)
            return self.__cancel_triggered(
                customer_number=booking[1].customer_number,
                uuid=uuid,
                slot=int(self.booking_service.hour_to_slot(booking[0]))
            )
        else:
            return self.remind_start_ncco(uuid)

    @hug.object.post(EVENT)
    def event_handler(self, request=None, body=None):
        uuid = body["uuid"]
        print("received event! : " + str(body) + str(request))
        if body["direction"] == "inbound":
            self.uuid_to_lvn[uuid] = body["from"]
            print("Inbound event UUID is: " + uuid + " and " + "from is: " + body["from"])
        elif body["direction"] == "outbound":
            self.uuid_to_lvn[uuid] = body["to"]
            print("Outbound event UUID is: " + uuid + " and " + "to is: " + body["to"])

    @hug.object.get('/tables')
    def tables(self):
        return self.booking_service.get_tables()

    @hug.object.get('/waitlist')
    def wait_list(self):
        return self.booking_service.get_wait_list_json()

    @hug.object.get("/dashboard", output = hug.output_format.html)
    def dashboard(self):
        with open("static/dashboard.html") as page:
            return page.read()

    @hug.object.get("/manager")
    def change_manager_number(self, number=None):
        self.manager_lvn = str(number)
        return {"action": "changed manager number to " + str(number)}


router = hug.route.API(__name__)
router.object('/')(NCCOServer)
