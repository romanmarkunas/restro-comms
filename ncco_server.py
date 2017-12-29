"""This endpoint will serve NCCO objects required by Nexmo VAPI"""

import hug
import uuid
import requests
from booking_service import BookingService
from datetime import datetime
from base64 import urlsafe_b64encode
import os
import calendar
from jose import jwt

alreadyRun = false

class NCCOServer():

    APPLICATION_ID = "b75f58ba-f8ee-47fb-b0d0-a47ab23143c0"

    def __init__(self):
        self.conversation = str(uuid.uuid4())
        self.domain = "booktwotables.herokuapp.com"
        self.booking_service = BookingService()
        print("IN NCCO INIT: " + str(self.booking_service))
        self.call_id_and_customer_number = {}

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

    @hug.object.get('/remind')
    def make_remind_call(self):
        requests.post("https://api.nexmo.com/v1/calls", headers={"Authorization": "Bearer " + self.__generate_jwt()}, json={
            "to": [{
                "type": "phone",
                # "number": "447718650656"
                "number": "447426007676"
              }],
              "from": {
                "type": "phone",
                "number": "447418397022"
              },
              "answer_url": ["http://" + self.domain + "/remind"],
              "event_url": ["http://" + self.domain + "/event"]
        })

    def __generate_jwt(self):
        application_private_key = os.environ["PRIVATE_KEY"]
        token_payload = {
            "iat": calendar.timegm(datetime.utcnow().utctimetuple()),
            "application_id": NCCOServer.APPLICATION_ID,
            "jti": urlsafe_b64encode(os.urandom(64)).decode('utf-8')
        }

        return jwt.encode(
            claims=token_payload,
            key=application_private_key,
            algorithm='RS256')

    def remind_call_ncco(self):
        return [
            {
                "action": "talk",
                "voiceName": "Russell",
                "text": "Hi, this is Nexmo restaurant. We are just checking you are still ok for your reservation on HOURS, press 1 for yes or 2 to cancel?",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": ["http://" + self.domain + "/remind/input"]
            }
        ]

    @hug.object.post('/remind/input')
    def remind_input_response(self, body=None):
        print(str(body))
        dtmf = body["dtmf"]
        if dtmf == "1":
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Cool, look forward to seeing you soon.",
                }
            ]
        # else:
        #     # do cancel stuff

    @hug.object.post('/ncco/input')
    def ncco_input_response(self, body=None):
        print(str(body))
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

    @hug.object.post('/ncco/input/booking')
    def ncco_input_booking_response(self, body=None):
        print(str(body))
        booking_time = int(body["dtmf"])
        customer_number = self.call_id_and_customer_number[body["uuid"]]
        alternatives = []
        result = self.booking_service.book(hour=booking_time, pax=4, alternatives=alternatives, customer_number=customer_number)
        print("IN BOOKING: " + str(self.booking_service))

        if result:
            return [
                {
                    "action": "talk",
                    "voiceName": "Russell",
                    "text": "Fantastic, your booking has been successful.",
                }
            ]


    @hug.object.post('/event')
    def event_handler(self, request=None, body=None):
        self.call_id_and_customer_number[body["uuid"]] = body["from"]
        print("received event! : " + str(body) + str(request))

    @hug.object.get('/tables')
    def tables(self):
        print("IN TABLES: " + str(self.booking_service))
        return self.booking_service.get_tables()

    @hug.object.get("/hold-tune", output = hug.output_format.file)
    def hold_music(self):
        return open('static/bensound-thejazzpiano.mp3', mode='rb')

    @hug.object.get("/dashboard", output = hug.output_format.html)
    def dashboard(self):
        with open("static/dashboard.html") as page:
            return page.read()

if not alreadyRun:
    print("APP NAME:" + str(__name__))
    router = hug.route.API(__name__)
    router.object('/')(NCCOServer)
    alreadyRun = true
