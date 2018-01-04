"""This endpoint will serve NCCO objects required by Nexmo VAPI"""

import hug
import requests
from booking_service import BookingService
from datetime import datetime
from base64 import urlsafe_b64encode
from threading import Thread
import os
import nexmo
import calendar
from jose import jwt
from call import CallState, Call, NccoBuilder


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
        call = Call(user_lvn=request.params['from'], state=CallState.CHOOSE_ACTION)
        self.calls[request.params['conversation_uuid']] = call
        return NccoBuilder().customer_call_greeting().with_input(
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
                call.set_state(CallState.BOOKING_ASK_TIME)
                return NccoBuilder().select_time().with_input(
                    self.domain + NCCOServer.NCCO_INPUT,
                    extra_params={
                        "submitOnHash": True,
                        "timeOut": 15
                    }
                ).build()
            elif dtmf == "2":
                return self.__do_cancel(customer_number=call.get_lvn(), uuid=uuid)
            elif dtmf == "3":
                self.__do_cancel(customer_number=call.get_lvn(), uuid=uuid)
        elif call.get_state() == CallState.BOOKING_ASK_TIME:
            call.save_var('time', int(dtmf))
            call.set_state(CallState.BOOKING_ASK_PAX)
            return NccoBuilder().select_pax().with_input(
                self.domain + NCCOServer.NCCO_INPUT
            ).build()
        elif call.get_state() == CallState.BOOKING_ASK_PAX:
            pax = int(dtmf)
            booking_time = call.get_var('time')
            customer_number = call.get_lvn()
            alternatives = []
            result = self.booking_service.book(hour=booking_time, pax=pax, alternatives=alternatives, customer_number=customer_number)
            del self.calls[uuid]

            if result:
                return NccoBuilder().book(str(self.booking_service.hour_to_slot(booking_time))).build()
            else:
                self.booking_service.put_to_wait(hour=booking_time, pax=pax, customer_number=customer_number)
                return NccoBuilder().wait(str(self.booking_service.hour_to_slot(booking_time))).build()

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
        NCCOServer.send_sms(customer_number, "Your booking for " + str(slot) + " has been cancelled.")
        Thread(target=self.call_waiting_customers(self.booking_service.slot_to_hour(slot))).start()
        call = self.calls[uuid]
        call.set_state(CallState.BOOKING_ASK_TIME)
        return NccoBuilder().cancel_and_reschedule(str(slot)).with_input(
                    self.domain + NCCOServer.NCCO_INPUT,
                    extra_params={
                        "submitOnHash": True,
                        "timeOut": 15
                    }).build()

    def __cancel_triggered(self, customer_number, slot, uuid):
        NCCOServer.send_sms(customer_number, "Your booking for " + str(slot) + " has been cancelled.")
        Thread(target=self.call_waiting_customers(self.booking_service.slot_to_hour(slot))).start()
        self.calls.pop(uuid, None)
        return NccoBuilder().cancel(str(slot)).build()

    @staticmethod
    def send_sms(customer_number, text):
        demo_api_key = os.environ["DEMO_API_KEY"]
        demo_api_secret = os.environ["DEMO_API_SECRET"]
        client = nexmo.Client(key=demo_api_key, secret=demo_api_secret)
        client.send_message({
            'from': 'Two tables',
            'to': customer_number,
            'text': text,
        })

    def call_waiting_customers(self, freed_up_slot_in_correct_format):
        wait_list = self.booking_service.get_wait_list()
        for customer_waiting in wait_list:
            customer_waiting_slot_in_correct_format = self.booking_service.slot_to_hour(customer_waiting[0])
            if customer_waiting_slot_in_correct_format == freed_up_slot_in_correct_format:
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
                        "answer_url": [self.domain + NCCOServer.WAITING_START],
                        "event_url": [self.domain + NCCOServer.EVENT]
                    })
                uuid = response.json()["conversation_uuid"]
                print("Customers booking ID: " + str(customer_waiting[1].id))
                print("Customers UUID: " + uuid)
                break

    @hug.object.get(WAITING_START)
    def start_waiting_call(self, request=None):

        customer_number = request.params["to"]

        def get_slot_using_customer_number(val):
            return val[1].customer_number == customer_number

        index = self.booking_service.wait_list.find(get_slot_using_customer_number)
        slot_booking = self.booking_service.get_wait_list()[index]

        return [
            {
                "action": "talk",
                "voiceName": "Russell",
                "text": "Hi there it's Two Tables with tremendous news, a booking slot " \
                        "for " + str(slot_booking[0]) + "pm has become free, " \
                        "press 1 to accept or 2 to remove yourself from the waiting list?",
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
        self.uuid_to_lvn.pop(uuid)

        def get_slot_using_customer_number(val):
            return val[1].customer_number == customer_number

        index = self.booking_service.wait_list.find(get_slot_using_customer_number)

        if dtmf == "1":
            alternatives = []

            print("Waiting customers UUID for DTMF: " + uuid)

            slot_booking = self.booking_service.get_wait_list()[index]

            self.booking_service.book(slot_booking[0], 4, slot_booking[1].customer_number, alternatives)
            self.booking_service.remove_from_wait_list(index)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Stupendous, you booking for " + str(slot_booking[0]) + " pm has been confirmed, " \
                            "we look forward to seeing you soon" + NCCOServer.SIGN_OFF
                }
            ]

        elif dtmf == "2":
            self.booking_service.remove_from_wait_list(index)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We have now successfully removed you from the waiting list, " \
                            "but we hope to see you soon, thanks you good bye",
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
                slot=int(booking[0])
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

    @hug.object.post("/blah")
    def blah(self, pax=None):
        alternatives = []
        self.booking_service.book(20, int(pax), "1234", alternatives)

    @hug.object.post("/blah1")
    def blah1(self, request=None, body=None):
        alternatives = []
        self.booking_service.book(18, 4, "12344", alternatives)

    @hug.object.get('/tables')
    def tables(self):
        return self.booking_service.get_tables()

    @hug.object.get("/dashboard", output = hug.output_format.html)
    def dashboard(self):
        with open("static/dashboard.html") as page:
            return page.read()

    @hug.object.get("/manager")
    def change_manager_number(self, number=None):
        self.manager_lvn = str(number)
        return {"action": "changed manager number to " + str(number)}

# If customer selects reschedule then cancel the booking and redirect to new booking flow

router = hug.route.API(__name__)
router.object('/')(NCCOServer)
