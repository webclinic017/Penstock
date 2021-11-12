import webbrowser
import json
import logging
import requests
from rauth import OAuth1Service, OAuth1Session

import common.config as config

log = logging.getLogger(__name__)

class EtradeInterface(object):
    def __init__(self, token_file_name, base_url):
        self.base_url = base_url
        self.get_session(token_file_name)

    def get_session(self, token_file_name):
        try:
            with open(token_file_name) as token_file:
                token_data = json.load(token_file)
                self.session = OAuth1Session(
                    consumer_key=config.etrade_consumer_key,
                    consumer_secret=config.etrade_consumer_secret,
                    **token_data
                )
                if not self.get_accounts():
                    self.session = self.oauth(token_file_name)

        except FileNotFoundError:
            log.debug('No token file found, running oauth...')
            return self.oauth(token_file_name)

    def oauth(self, token_file_name):
        etrade = OAuth1Service(
            name="etrade",
            consumer_key=config.etrade_consumer_key,
            consumer_secret=config.etrade_consumer_secret,
            request_token_url="https://api.etrade.com/oauth/request_token",
            access_token_url="https://api.etrade.com/oauth/access_token",
            authorize_url="https://us.etrade.com/e/t/etws/authorize?key={}&token={}",
            base_url="https://api.etrade.com")

        # Step 1: Get OAuth 1 request token and secret
        request_token, request_token_secret = etrade.get_request_token(
            params={"oauth_callback": "oob", "format": "json"})

        # Step 2: Go through the authentication flow. Login to E*TRADE.
        # After you login, the page will provide a text code to enter.
        authorize_url = etrade.authorize_url.format(etrade.consumer_key, request_token)
        webbrowser.open(authorize_url)
        print(f'Go to this url if on headless: {authorize_url}')
        text_code = input("Please accept agreement and enter text code from browser: ")

        # Step 3: Exchange the authorized request token for an authenticated OAuth 1 session
        response = etrade.get_access_token(
            request_token,
            request_token_secret,
            params={"oauth_verifier": text_code}
        )
        access_tokens = {
            'access_token': response[0],
            'access_token_secret': response[1]
        }

        with open(token_file_name, 'w') as token_file:
            json.dump(access_tokens, token_file)

        return OAuth1Session(
            consumer_key=config.etrade_consumer_key,
            consumer_secret=config.etrade_consumer_secret,
            **access_tokens
        )

    def main_menu(self):
        menu_items = {"1": "Market Quotes",
                    "2": "Account List",
                    "3": "Exit"}

        while True:
            print("")
            options = menu_items.keys()
            for entry in options:
                print(entry + ")\t" + menu_items[entry])
            selection = input("Please select an option: ")
            if selection == "1":
                log.debug('Market')
            elif selection == "2":
                log.debug('Accounts')
                print(self.get_accounts())
            elif selection == "3":
                log.debug('Quitting...')
                break
            else:
                print("Unknown Option Selected!")

    def get_accounts(self):
        url = self.base_url + '/v1/accounts/list.json'
        response = self.session.get(url)
        if response.status_code == 401:
            return None
        if response is not None and response.status_code == 200:
            parsed = json.loads(response.text)
            log.debug("Response Body: %s", json.dumps(parsed, indent=4, sort_keys=True))
            data = response.json()

        return response