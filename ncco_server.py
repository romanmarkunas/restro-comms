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

    APPLICATION_ID = "b75f58ba-f8ee-47fb-b0d0-a47ab23143c0"

    def __init__(self):
        self.lvn = "447418397022"
        self.domain = "booktwotables.herokuapp.com"
        self.booking_service = BookingService()
        self.uuid_to_lvn = {}
        self.outbound_uuid_to_booking = {}

    @hug.object.get('/ncco')
    def start_call(self):
        return [
            {
                "action" : "talk",
                "text" : "Thanks for calling Nexmo restaurant. Please select from the following options, 1 for booking or 2 for cancelling.",
                "voiceName": "Russell",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": ["http://" + self.domain + "/ncco/input"]
            }
        ]

    @hug.object.post('/ncco/input')
    def ncco_input_response(self, body=None):
        dtmf = body["dtmf"]
        if dtmf == "1":
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Excellent, please enter the time you'd like in the 24 hour format followed by the hash key.",
                    "bargeIn": True
                },
                {
                    "action": "input",
                    "submitOnHash": True,
                    "timeOut": 10,
                    "eventUrl": ["http://" + self.domain + "/ncco/input/booking"]
                }
            ]
        elif dtmf == "2":
            customer_number = self.uuid_to_lvn[body["uuid"]]
            cancellable_results = self.booking_service.find_bookings(customer_number)
            # Currently we will always cancel the first booking.
            self.booking_service.cancel(cancellable_results[0][1].id)

            NCCOServer.send_cancel_sms(customer_number)

            Thread(target=self.call_next_customer_in_waiting_list(self.booking_service.slot_to_hour(cancellable_results[0][0]))).start()

            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We're sorry to hear you are cancelling, an SMS has been sent to confirm we have cancelled your booking."
                }
            ]

    @staticmethod
    def send_cancel_sms(customer_number):
        demo_api_key = os.environ["DEMO_API_KEY"]
        demo_api_secret = os.environ["DEMO_API_SECRET"]
        client = nexmo.Client(key=demo_api_key, secret=demo_api_secret)
        client.send_message({
            'from': 'Nexmo restaurant',
            'to': customer_number,
            'text': 'Your booking has been successfully cancelled.',
        })

    def call_next_customer_in_waiting_list(self, freed_up_slot_in_correct_format):
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
                            "answer_url": ["http://" + self.domain + "/ncco/input/waiting-list/booking"],
                            "event_url": ["http://" + self.domain + "/event/outbound"]
                        })
                    uuid = response.json()["conversation_uuid"]
                    self.outbound_uuid_to_booking[uuid] = customer_waiting[1].id

    @hug.object.post('/ncco/input/waiting-list/booking')
    def ncco_input_waiting_list_booking(self):
        return [
            {
                "action": "talk",
                "voiceName": "Russell",
                "text": "Hi there, a booking slot has become free, press 1 to accept or 2 to remove yourself from the waiting list?",
                "bargeIn": True
            },
            {
                "action": "input",
                "timeOut": 10,
                "eventUrl": ["http://" + self.domain + "/ncco/input/waiting-list/booking/input"]
            }
        ]

    @hug.object.post('/ncco/input/waiting-list/booking/input')
    def ncco_input_waiting_list_booking_input(self, body=None):
        dtmf = body["dtmf"]
        uuid = body["uuid"]
        if dtmf == "1":
            booking_id = self.outbound_uuid_to_booking[uuid]
            self.outbound_uuid_to_booking.pop(uuid, None)
            wait_list = self.booking_service.get_wait_list()

            for customer_waiting in wait_list:
                customer_waiting_slot = self.booking_service.slot_to_hour(customer_waiting[0])
                customer_waiting_booking = customer_waiting[1]
                if customer_waiting_booking.id == booking_id:
                    self.booking_service.book(customer_waiting_slot, customer_waiting_booking)
                    return [
                        {
                            "action": "talk",
                            "voiceName": "Russell",
                            "text": "Stupendous you booking has been confirmed, we look forward to seeing you.",
                        }
                    ]

        elif dtmf == "2":
            # ASSUMPTION there is only ever one in the wait list for now.
            self.booking_service.remove_from_wait_list(0)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We have now successfully removed you from the waiting list.",
                }
            ]

    @hug.object.post('/ncco/input/booking')
    def ncco_input_booking_response(self, body=None):
        uuid = body["uuid"]
        booking_time = int(body["dtmf"])
        customer_number = self.uuid_to_lvn[uuid]
        alternatives = []
        print("Booking table @" + str(booking_time) + " for LVN " + str(customer_number))  # TODO
        result = self.booking_service.book(hour=booking_time, pax=4, alternatives=alternatives, customer_number=customer_number)

        if result:
            self.uuid_to_lvn.pop(uuid, None)
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Fantastic, your booking has been successful.",
                }
            ]
        else:
            booking = self.booking_service.put_to_wait(hour=booking_time, pax=4, customer_number=customer_number)
            self.outbound_uuid_to_booking[uuid] = booking.id
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "We're really sorry but that slot is currently full, you've been added to the waiting list and we'll call you once the slot becomes free.",
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
                "answer_url": ["http://" + self.domain + "/remind/start"],
                "event_url": ["http://" + self.domain + "/event"]
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

    @hug.object.get('/remind/start')
    def remind_start_ncco(self, conversation_uuid = None): # why Nexmo do not provide uuid here?
        booking_id = self.outbound_uuid_to_booking[conversation_uuid]
        time = self.booking_service.find(booking_id)[0]
        return [{
            "action": "talk",
            "voiceName": "Russell",
            "text": "Hi, this is book two tables. Just checking you are still "\
                    "OK for your reservation at " + str(time) + " hours? "\
                    "Press 1 for yes, 2 for cancel or any other key to repeat.",
            "bargeIn": True
        },
        {
            "action": "input",
            "eventUrl": ["http://" + self.domain + "/remind/input"]
        }]

    @hug.object.post('/remind/input')
    def remind_input_response(self, body = None):
        dtmf = body["dtmf"]
        uuid = body["conversation_uuid"]
        if dtmf == "1":
            return [{
                "action": "talk",
                "voiceName": "Russell",
                "text": "Cool, looking forward to see you soon.",
            }]
        elif dtmf == "2":
            booking_id = self.outbound_uuid_to_booking[uuid]
            self.booking_service.cancel(booking_id)
            return [{
                "action": "talk",
                "voiceName": "Russell",
                "text": "Thanks! Your booking has been cancelled"
            }]
        else:
            return self.remind_start_ncco(uuid)

    @hug.object.post('/event')
    def event_handler(self, request=None, body=None):
        print("received event! : " + str(body) + str(request))
        self.uuid_to_lvn[body["uuid"]] = body["from"]

    @hug.object.post('/event/outbound')
    def event_handler(self, request=None, body=None):
        print("received event! : " + str(body) + str(request))

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
