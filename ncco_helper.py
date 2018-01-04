import nexmo
import os


class NCCOHelper(object):

    @staticmethod
    def get_caller_name(caller_name):
        """Returns caller name if true or empty string if false"""
        return caller_name if caller_name else ""

    @staticmethod
    def get_call_info(customer_number):
        """Returns json response from number insight advanced call"""
        demo_api_key = os.environ["DEMO_API_KEY"]
        demo_api_secret = os.environ["DEMO_API_SECRET"]
        client = nexmo.Client(key=demo_api_key, secret=demo_api_secret)
        return client.get_advanced_number_insight(number=customer_number)

    @staticmethod
    def send_sms(customer_number, text):
        demo_api_key = os.environ["DEMO_API_KEY"]
        demo_api_secret = os.environ["DEMO_API_SECRET"]
        client = nexmo.Client(key=demo_api_key, secret=demo_api_secret)
        client.send_message({
            'from': 'Two tables',
            'to': customer_number,
            'text': text,
        })
