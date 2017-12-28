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
        return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE1MTQ0ODI0NjcsImp0aSI6IjVhOWVhMjMwLWViZjUtMTFlNy1iY2I2LWMxYzdjMTAxNTk4YiIsImFwcGxpY2F0aW9uX2lkIjoiZWM2MGVmMTMtNTkxOS00NTI3LWJlMDktNjg3NTU4OWIzYWIyIn0.af8BPfK0U3j2aVL-G09rzwBfqBSlbQ0dJwLP9r20dR-WplEcGNsYRo3rnO2zi_y3fLin9GsrxF9DjcUQNgLDS6eobF7_buna3xdomqTyTe5dTNCdmsSkMhUKhpQ2tqVocJHfHOq1V_pJamDn6wwO7ZzMe97IhU9dKQbtZ4fCYq4_rvv3k1ZsoiqbHjouay8NyevMSM7yTxrI-kvn3ZtfNexATBdygJ4vbbERT2KUptu9PXoSXu65HBokRaDSCam1rDLHd8ORDD9Az7MffI51bEoV34SNdE70fxwt9Hi5iot9AVg14vX2DS90mmk-TwGcgUIaz-Y2pB5YoKElm-bIDQ"

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
        r = requests.post("https://api.nexmo.com/v1/calls", headers={"Authorization": "Bearer " + self.jwt}, json={
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
              "answer_url": [self.domain + "/remind"],
              "event_url": [self.domain + "/event"]
        })

        print(str(r))
        print(self.domain + "/remind")

    def remind_call_ncco(self):
        return [
                        {
                            "action": "talk",
                            "voiceName": "Russell",
                            "text": "Hi, this is Russell. Youre booking is about to expire"
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
