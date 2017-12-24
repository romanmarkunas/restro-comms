"""This endpoint will serve NCCO objects required by Nexmo VAPI"""

import hug
import uuid

class NCCOServer():

    def __init__(self, domain):
        self.conversation = str(uuid.uuid4())
        self.domain = domain

    def start_call(self):
        return [
            {
                "action" : "talk",
                "text" : "Thanks for calling book two tables! Please hold on"
            },
            {
                "action" : "conversation",
                "name" : self.conversation,
                "startOnEnter" : "false",
                # Music: https://www.bensound.com
                "musicOnHoldUrl" : [ self.domain + "/hold-tune" ]
            }
        ]

    def ivr(self):
        return [{
                "action" : "conversation",
                "name" : self.conversation,
                "startOnEnter" : "true"
                "endOnExit" : "true"
        }]

    def stt_websocket(self):
        return [{
                "action" : "conversation",
                "name" : self.conversation,
                "startOnEnter" : "false"
        }]

    def hold_music(self):
        return open('static/bensound-thejazzpiano.mp3', mode='rb')

ncco_server = NCCOServer("booktwotables.heroku.com")
router = hug.route.API(__name__)
router.get('/ncco')(ncco_server.start_call)
router.get('/hold-tune', output = hug.output_format.file)(ncco_server.hold_music)
router.get('/ivr')(ncco_server.ivr)
router.get('/websocket')(ncco_server.stt_websocket)
