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

            # {
            #     "action" : "conversation",
            #     "name" : self.conversation,
            #     "startOnEnter" : "false",
            #     # Music: https://www.bensound.com
            #     "musicOnHoldUrl" : [ self.domain + "/hold-tune" ]
            # }
            # {
            #     "action": "connect",
            #     "endpoint": [
            #         {
            #             "content-type": "audio/l16;rate=16000",
            #             "headers": {
            #                 "aws_key": "AKIAJQ3CX2DGX64WONXQ",
            #                 "aws_secret": "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"
            #             },
            #             "type": "websocket",
            #             "uri": "wss://lex-us-east-1.nexmo.com/bot/BookTwoTables/alias/BookBot_no_cancel/user/BookTwoTables/content"
            #         }
            #     ],
            #     "eventUrl": ["http://" + self.domain + "/event"]
            # }
        ]

    # def ivr(self):
    #     return [{
    #             "action" : "conversation",
    #             "name" : self.conversation,
    #             "startOnEnter" : "true",
    #             "endOnExit" : "true"
    #     }]

    # def stt_websocket(self):
    #     return [{
    #             "action" : "conversation",
    #             "name" : self.conversation,
    #             "startOnEnter" : "false"
    #             # actually web socket is avr
    #             # add hook after socket joined to do IVR
    #     }]

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

            t = Thread(target=self.call_next_customer_in_waiting_list)
            t.start()

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

    def call_next_customer_in_waiting_list(self):
        print("we made it!")


    @hug.object.post('/ncco/input/booking')
    def ncco_input_booking_response(self, body=None):
        uuid = body["uuid"]
        booking_time = int(body["dtmf"])
        customer_number = self.uuid_to_lvn[uuid]
        alternatives = []
        print("Booking table @" + str(booking_time) + " for LVN " + str(customer_number))
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
