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

    def hold_music(self):
        return open('static/bensound-thejazzpiano.mp3', mode='rb')
