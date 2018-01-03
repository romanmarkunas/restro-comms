"""This endpoint will serve NCCO objects required by Nexmo VAPI"""

import hug
import uuid as uuid_generator
import requests
from booking_service import BookingService
from datetime import datetime
from base64 import urlsafe_b64encode
from threading import Thread
import os
import nexmo
import calendar
from jose import jwt

class NCCOServer():

    EVENT = "/event"

    REMIND_INPUT = "/remind/input"
    REMIND_START = "/remind/start"

    NCCO_INPUT = "/ncco/input"
    NCCO_INPUT_BOOKING = '/ncco/input/booking'

    WAITING_INPUT = "/waiting/input"
    WAITING_START = "/waiting/start"

    APPLICATION_ID = "b75f58ba-f8ee-47fb-b0d0-a47ab23143c0"
    SIGN_OFF = ", thank you good bye."

    def __init__(self):
        self.nexmo_client = nexmo.Client(
            application_id = NCCOServer.APPLICATION_ID, # change to env var
            private_key = os.environ["PRIVATE_KEY"],
            key = os.environ["DEMO_API_KEY"],
            secret = os.environ["DEMO_API_SECRET"]
        )
        self.lvn = "447418397022"
        self.conference_id = "conference" + self.lvn + str(uuid_generator.uuid4())
        self.domain = "http://booktwotables.herokuapp.com"
        self.ws_call = None

        self.booking_service = BookingService()
        self.uuid_to_lvn = {}
        self.outbound_uuid_to_booking = {}
        self.waiting_lvn_to_slot_and_booking = {}

    @hug.object.get('/ncco')
    def start_call(self, request = None):
        from_lvn = str(request.get_param("from"))
        self.nexmo_client.create_call({
            "to": [{"type": "phone", "number": "447982968924"}],
            "from": {"type": "phone", "number": self.lvn},
            "answer_url": ["http://booktwotables.herokuapp.com/conference-joiner"]
        })

        if from_lvn == "447426007676":
            print("HEY BOSS!!")
            return [
              {
                "action": "talk",
                "text": "Welcome to a Nexmo moderated conference",
                "voiceName": "Amy"
              },
              {
                "action": "conversation",
                "name": "nexmo-conference-moderated",
                "startOnEnter": "false",
                "musicOnHoldUrl": ["https://nexmo-community.github.io/ncco-examples/assets/voice_api_audio_streaming.mp3"]
              }
            ]
        elif from_lvn == "447982968924":
            print("WOAH!")
            return [
              {
                "action": "conversation",
                "name": "nexmo-conference-moderated",
                "record": "true",
                "endOnExit": "true"
              }
            ]
        # from_lvn = str(request.get_param("from"))
        # print("IN NCCO: from = " + from_lvn)
        # if from_lvn != self.lvn:
        #     print("CREATING CALL TO MYSELF!")
        #     self.nexmo_client.create_call({
        #         "to": [{"type": "phone", "number": "447982968924"}],
        #         "from": {"type": "phone", "number": self.lvn},
        #         "answer_url": [self.domain + "/conference-joiner" + "?start=true"]
        #     })
        #     # self.nexmo_client.create_call({
        #     #     "to": [{"type": "phone", "number": self.lvn}],
        #     #     "from": {"type": "phone", "number": self.lvn},
        #     #     "answer_url": [self.domain + "/conference-joiner" + "?start=false"]
        #     # })
        #     return [{
        #         "action": "talk",
        #         "text": "Thanks for calling Two Tables. Please hold on",
        #         "voiceName": "Russell"
        #     },
        #     {
        #         "action": "conversation",
        #         "name": self.conference_id, # TODO - add state object to track each customer call
        #         "startOnEnter": "false",
        #         "endOnExit": "true",
        #         "eventUrl": [self.domain + "/event"],
        #         "musicOnHoldUrl": [self.domain + "/hold-tune" ] # https://www.bensound.com
        #     }]
        # else:
        #     print("ANSWERING WITH PROPER IVR!")
        #     return self.start_call_ivr()

        # {
        #     "action": "talk",
        #     "text": ("Thanks for calling Nexmo restaurant. I am Russell, your "
        #              "booking assistant. You can also type 9 9 and hashkey to "
        #              "speak with real person. How can I help?"),
        #     "voiceName": "Russell",
        #     "bargeIn": True
        # },
        #     {
        #         "action": "input",
        #         "eventUrl": [self.domain + "/ncco/input"]
        #     }

    @hug.object.post("/conference-joiner")
    def join_conference(self):
        # print("IN JOINER! start = " + str(start))
        # return [{
        #     "action": "conversation",
        #     "name": self.conference_id,
        #     "startOnEnter": str(start).lower(),
        #     "endOnExit": str(start).lower()
        #     # "musicOnHoldUrl": [self.domain + "/hold-tune" ] # https://www.bensound.com
        # }]
        return [
          {
            "action": "conversation",
            "name": "nexmo-conference-moderated",
            "record": "true",
            "endOnExit": "true"
          }
        ]

    @hug.object.get("/booking-ivr")
    def start_call_ivr(self):
        print("INSIDE IVR")
        return [
            {
                "action": "talk",
                "text": "Thanks for calling Two Tables. Please select from the following options, " \
                        "1 for booking or 2 for cancelling.",
                "voiceName": "Russell",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": [self.domain + NCCOServer.NCCO_INPUT]
            }
        ]

    @hug.object.post(NCCO_INPUT)
    def ncco_input_response(self, body=None):
        dtmf = body["dtmf"]
        if dtmf == "1":
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Excellent, please enter the time you'd like in the 24 hour" \
                            "format followed by the hash key.",
                    "bargeIn": True
                },
                {
                    "action": "input",
                    "submitOnHash": True,
                    "timeOut": 10,
                    "eventUrl": [self.domain + NCCOServer.NCCO_INPUT_BOOKING]
                }
            ]
        elif dtmf == "2":
            customer_number = self.uuid_to_lvn[body["uuid"]]
            cancellable_results = self.booking_service.find_bookings(customer_number)
            cancelled_slot = str(cancellable_results[0][0])
            # ASSUMPTION we will always cancel the first booking for a particular customer.
            self.booking_service.cancel(cancellable_results[0][1].id)

            self.send_sms(customer_number, "Your booking for " + cancelled_slot + "pm has been cancelled.")

            Thread(target=self.call_waiting_customers(self.booking_service.slot_to_hour(cancellable_results[0][0]))) \
                .start()

            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We're sorry to hear you are cancelling your reservation " \
                            "for" + str(cancellable_results[0][0]) + " pm, an SMS " \
                            "has been sent to confirm we have cancelled your booking, but we hope to " \
                             "see you real soon" + NCCOServer.SIGN_OFF
                }
            ]

    def send_sms(self, customer_number, text):
        self.nexmo_client.send_message({
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
                        "answer_url": ["http://" + self.domain + NCCOServer.WAITING_START],
                        "event_url": ["http://" + self.domain + NCCOServer.EVENT]
                    })
                uuid = response.json()["conversation_uuid"]
                print("Customers booking ID: " + str(customer_waiting[1].id))
                print("Customers UUID: " + uuid)
                break

    @hug.object.get(WAITING_START)
    def start_waiting_call(self, request=None):

        customer_number = request.params["to"]
        waiting_slot_booking = self.waiting_lvn_to_slot_and_booking[customer_number]
        return [
            {
                "action": "talk",
                "voiceName": "Russell",
                "text": "Hi there it's Two Tables with tremendous news, a booking slot " \
                        "for " + str(waiting_slot_booking[0]) + "pm has become free, " \
                        "press 1 to accept or 2 to remove yourself from the waiting list?",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": ["http://" + self.domain + NCCOServer.WAITING_INPUT]
            }
        ]

    @hug.object.post(WAITING_INPUT)
    def waiting_call_input_response(self, body=None):
        dtmf = body["dtmf"]

        if dtmf == "1":
            alternatives = []
            uuid = body["uuid"]
            print("Waiting customers UUID for DTMF: " + uuid)

            customer_number = self.uuid_to_lvn[uuid]
            self.uuid_to_lvn.pop(uuid)

            slot_booking = self.waiting_lvn_to_slot_and_booking[customer_number]
            self.waiting_lvn_to_slot_and_booking.pop(customer_number)

            self.booking_service.book(slot_booking[0], 4, slot_booking[1].customer_number, alternatives)
            self.booking_service.remove_from_wait_list(0)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Stupendous, you booking for " + str(slot_booking[0]) + " pm has been confirmed, " \
                            "we look forward to seeing you soon" + NCCOServer.SIGN_OFF
                }
            ]

        elif dtmf == "2":
            # ASSUMPTION there is only ever one in the wait list for now.
            self.booking_service.remove_from_wait_list(0)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We have now successfully removed you from the waiting list, " \
                            "but we hope to see you soon, thanks you good bye",
                }
            ]

    @hug.object.post(NCCO_INPUT_BOOKING)
    def ncco_input_booking_response(self, body=None):
        uuid = body["uuid"]
        booking_time = int(body["dtmf"])
        customer_number = self.uuid_to_lvn[uuid]
        alternatives = []
        result = self.booking_service.book(hour=booking_time, pax=4, alternatives=alternatives, customer_number=customer_number)

        if result:
            print("Booking table @" + str(booking_time) + " for LVN " + str(customer_number))
            self.uuid_to_lvn.pop(uuid, None)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Fantastic, your booking has been successful, we'll " \
                            "see you at " + str(self.booking_service.hour_to_slot(booking_time)) + " pm. "\
                            "Thank you good bye."
                }
            ]
        else:
            print("Added to waiting list for @" + str(booking_time) + " for LVN " + str(customer_number))
            slot_booking = self.booking_service.put_to_wait(hour=booking_time, pax=4, customer_number=customer_number)
            self.waiting_lvn_to_slot_and_booking[customer_number] = slot_booking
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We're deeply saddened but this time "\
                            "at " + str(self.booking_service.hour_to_slot(booking_time)) + " pm is currently " \
                            "full, you've been added to the waiting list and we'll call you immediately once the " \
                            "slot becomes free" + NCCOServer.SIGN_OFF
                }
            ]

    @hug.object.post('/remind/trigger')
    def remind_trigger_call(self, body = None):
        booking_id = int(body["id"])
        booking = self.booking_service.find(booking_id)[1]
        response = requests.post(
            "https://api.nexmo.com/v1/calls",
            headers = { "Authorization": "Bearer " + self.__generate_jwt() },
            json = {
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
            claims = {
                "iat": calendar.timegm(datetime.utcnow().utctimetuple()),
                "application_id": NCCOServer.APPLICATION_ID,
                "jti": urlsafe_b64encode(os.urandom(64)).decode('utf-8')
            },
            key = os.environ["PRIVATE_KEY"],
            algorithm = 'RS256')

    @hug.object.get(REMIND_START)
    def remind_start_ncco(self, conversation_uuid = None): # why Nexmo do not provide uuid here?
        booking_id = self.outbound_uuid_to_booking[conversation_uuid]
        time = self.booking_service.find(booking_id)[0]
        return [{
            "action": "talk",
            "voiceName": "Russell",
            "text": "Hi, this is Two Tables. Just checking you are still " \
                    "ok for your reservation at " + str(time) + " pm? " \
                    "Press 1 for yes, 2 for cancel or any other key to repeat.",
            "bargeIn": True
        },
            {
                "action": "input",
                "eventUrl": [self.domain + NCCOServer.REMIND_INPUT]
            }]

    @hug.object.post(REMIND_INPUT)
    def remind_input_response(self, body = None):
        dtmf = body["dtmf"]
        uuid = body["conversation_uuid"]
        if dtmf == "1":
            return [{
                "action": "talk",
                "voiceName": "Russell",
                "text": "Outstanding, we look forward to seeing you soon" + NCCOServer.SIGN_OFF
            }]
        elif dtmf == "2":
            booking_id = self.outbound_uuid_to_booking[uuid]
            self.booking_service.cancel(booking_id)
            return [{
                "action": "talk",
                "voiceName": "Russell",
                "text": "We are devastated but your booking has now been cancelled" + NCCOServer.SIGN_OFF
            }]
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

    @hug.object.get("/hold-tune", output = hug.output_format.file)
    def hold_music(self):
        return open('static/bensound-thejazzpiano.mp3', mode='rb')

    @hug.object.get("/dashboard", output = hug.output_format.html)
    def dashboard(self):
        with open("static/dashboard.html") as page:
            return page.read()

router = hug.route.API(__name__)
router.object('/')(NCCOServer)
