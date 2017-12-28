"""This endpoint will serve NCCO objects required by Nexmo VAPI"""

import hug
import uuid
import requests
from booking_service import BookingService

class NCCOServer():

    def __init__(self, domain):
        self.conversation = str(uuid.uuid4())
        self.domain = domain
        self.booking_service = BookingService()
        self.jwt = self.get_jwt()

    def get_jwt(application_id="none", keyfile="jwt.txt") :
        return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE1MTQ0MTY2MTUsImp0aSI6IjA3ZGUwOTgwLWViNWMtMTFlNy1hZGM4LWI1NDYyYzJmZGQ3MiIsImFwcGxpY2F0aW9uX2lkIjoiYjc1ZjU4YmEtZjhlZS00N2ZiLWIwZDAtYTQ3YWIyMzE0M2MwIn0.l2kGG1j7jybCWquQirJi4I_EF4Ys6cag6Zi_N7DltkB0f9zv3KakMGIw_T7bmT0hvTa_lkmeHlnPglgJP-c1plY6JoinoQC8pdWz5oEynJkZXqZNLtQkAB16i5sNxVOFPID97A_jw1Wc5l66nikJEWkseAw2kYbDKOz1Ag8g_gP75cek2z4ynguQbuO7kXCgwaTi0pqXwmEXl471I6ub04K1Ht8iqaLLAX6XhoxT00-YReFFM83y7f_3bAtlculT3iiigVFATgWRWe8fJOI4o7bWuNIw35K_49cXS05IwJ_0ILVHp2NkjJDsU9Sw_0Qh9XT9YU6fczuGQG2lIei2Nw"

    def start_call(self):
        return [
            {
                "action" : "talk",
                "text" : "Thanks for calling book two tables! Please hold on"
            },
            # {
            #     "action" : "conversation",
            #     "name" : self.conversation,
            #     "startOnEnter" : "false",
            #     # Music: https://www.bensound.com
            #     "musicOnHoldUrl" : [ self.domain + "/hold-tune" ]
            # }
            {
                "action": "connect",
                "endpoint": [
                    {
                        "content-type": "audio/l16;rate=16000",
                        "headers": {
                            "aws_key": "AKIAJQ3CX2DGX64WONXQ",
                            "aws_secret": "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"
                        },
                        "type": "websocket",
                        "uri": "wss://lex-us-east-1.nexmo.com/bot/BookTwoTables/alias/BookBot_no_cancel/user/BookTwoTables/content"
                    }
                ],
                "eventUrl": [ self.domain + "/event"]
            }
        ]

    # def ivr(self):
    #     return [{
    #             "action" : "conversation",
    #             "name" : self.conversation,
    #             "startOnEnter" : "true",
    #             "endOnExit" : "true"
    #     }]

    def stt_websocket(self):
        return [{
                "action" : "conversation",
                "name" : self.conversation,
                "startOnEnter" : "false"
                # actually web socket is avr
                # add hook after socket joined to do IVR
        }]

    def make_remind_call(self):
        r = requests.post("https://api.nexmo.com/v1/calls", json={
            "to": [{
                "type": "phone",
                # "number": "447718650656"
                "number": "447426007676"
              }],
              "from": {
                "type": "phone",
                "number": "447418397022"
              },
              "answer_url": ["https://nexmo-community.github.io/ncco-examples/first_call_talk.json"],
              "event_url": [self.domain + "/event"]
        }, headers={
            "Authorization": "Bearer " + self.jwt
        })

        print(str(r))
        print(self.domain + "/remind")

    def remind_call_ncco(self):
        return [
            {
                "action" : "talk",
                "text" : "You have been hacked by russian hackers"
            }
        ]

    def event_handler(self, request=None, body=None):
        print("received event! : " + str(body) + str(request))

    def tables(self):
        return self.booking_service.get_tables()

    @hug.get("/hold-tune", output = hug.output_format.file)
    def hold_music(**kwargs):
        return open('static/bensound-thejazzpiano.mp3', mode='rb')

    @hug.get("/dashboard", output = hug.output_format.html)
    def dashboard(**kwargs):
        with open("static/dashboard.html") as page:
            return page.read()

ncco_server = NCCOServer("booktwotables.herokuapp.com")
router = hug.route.API(__name__)
router.get('/ncco')(ncco_server.start_call)
# router.get('/ivr')(ncco_server.ivr)
router.get('/websocket')(ncco_server.stt_websocket)
router.post('/event')(ncco_server.event_handler)
router.get('/tables')(ncco_server.tables)
router.get('/remind')(ncco_server.remind_call_ncco)

ncco_server.make_remind_call()
