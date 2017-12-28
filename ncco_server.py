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
        return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE1MTQ0OTM4MTQsImp0aSI6ImM1YTE1YTQwLWVjMGYtMTFlNy1hZTQ0LTlmMTI5OWZiMGJhMCIsImFwcGxpY2F0aW9uX2lkIjoiZWM2MGVmMTMtNTkxOS00NTI3LWJlMDktNjg3NTU4OWIzYWIyIn0.hEMlE1anO3eq8UYFdZJP2SLOBI14ng-lE7YoZakR-VLeuIMRz3nvg1y8w-RQ6BKVwcxRpyRyNyf7l3B3kNO0FKMXM_yfO-Wa_X3Uch8xeiS67qliTCWMneWnli0e57XvbL8T1KVFfA54rURoNHoMxOZOFMH85AUUEEiWIucgxRIeh8PVKFLdTd2acgOoxzBaNrNicSsgDE75XQqb-B6oL357p1Ku7gwnqXmnFQupt5Ino-YfDv3yXuX5_GUUOJblhwgCtEmrMFpZ0C6JLTKMoZcsN4D1ZwKzWyjWfuIJtjJSO81fRq0Jg2RtxR2lQuHSI3qFz-1JznOrlFVEmDFu4A"

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
              "answer_url": ["http://" + self.domain + "/remind"],
              "event_url": ["http://" + self.domain + "/event"]
        })

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
