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
        return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE1MTQ0OTY1MjgsImp0aSI6IjE3NjQ4OWYwLWVjMTYtMTFlNy05NDhhLWZmYmEwYWE2ZWM4YyIsImFwcGxpY2F0aW9uX2lkIjoiZWM2MGVmMTMtNTkxOS00NTI3LWJlMDktNjg3NTU4OWIzYWIyIn0.MA6QU2I_87igNs7gwwHzwQbd_J7e-pj3IkH4KDuaG_41nMX7E5diwNEWT54Ud5Tp0crzILhXxOpFFO5WgBO0nkGL7cL_-pPaETBQBXEDl6fYlDpPsKmOWlQgM2OJsOTw0i86fz2JIdD9F_zZyjQpUPA-9sWdkDx5xBScZHxnUEXgfjvA0zjQbgxdW7C3fbZFvHS0I3bZrp-k8rYOzU4e7rzOXzD7axicA0wtp-N6l06XTSkTKelDYpakS0zNBPjffyn2W52OZtt5DNpy3gvdgB09WGkCGeqvmwZgrmXne-gFq1U-agM-x_E3u5mXkvBk3X8C539vrD4dlOk9-kZD8Q"

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
        requests.post("https://api.nexmo.com/v1/calls", headers={"Authorization": "Bearer " + self.jwt}, json={
            "to": [{
                "type": "phone",
                "number": "447718650656"
                # "number": "447426007676"
              }],
              "from": {
                "type": "phone",
                # "number": "447418397022"
                  "number": "447520635826"
              },
              "answer_url": ["http://" + self.domain + "/remind"],
              "event_url": ["http://" + self.domain + "/event"]
        })

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

    def remind_input_response(self, body=None):
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
router.post('/remind/input')(ncco_server.remind_input_response)

ncco_server.make_remind_call()
