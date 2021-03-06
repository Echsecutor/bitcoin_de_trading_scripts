"""
This module facilitates the details of the api connection.
See https://www.bitcoin.de/de/api/tapi/v2/docu

.. moduleauthor:: Sebastian Schmittner <sebastian@schmittner.pw> and Jan Schmidt


Copyright 2017-2018 Sebastian Schmittner

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import hashlib
import hmac
import logging
import time

import requests

logger = logging.getLogger(__name__)

class BaseQuerry(object):
    def __init__(self, name):
        """Each API should have a unique name"""
        self.name = name

    def query_url(self, url, headers=None):
        if headers:
            logger.debug("headers=%s", headers)
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error("Error getting info. Response %s", response.status_code)
            return None
        else:
            return response

    def query_json(self, url, headers=None):
        response = self.query_url(url, headers)
        if not response:
            return None

        try:
            return response.json()
        except Exception as ex:  #pylint: disable=W
            logger.error("Could not parse json: %s", ex)
            return None


class BCdeSession(BaseQuerry):
    """bitcoin.de API Wrapper"""
    def __init__(self, c_public_key, c_private_key, api_credits=20):
        super(BCdeSession, self).__init__("bitcoind.de")
        self.c_private_key = c_private_key
        self.c_public_key = c_public_key
        self.api_credits = api_credits
        self.C_API_URL = "https://api.bitcoin.de/v2"

    def generate_api_signature(self, method, url, nonce, post_params=None):
        """
        Generate and return X-API-SIGNATURE according to
        http://www.bitcoin.de/de/api/tapi/v2/docu
        """
        sorted_params = []
        if post_params:
            for key, val in post_params.items():
                sorted_params.append("{}={}".format(key, val))
            sorted_params.sort()
        query_string = "?".join(sorted_params)
        logger.debug("query_string: '%s' = %s", query_string, query_string.encode())
        hashed_query_string = hashlib.md5(query_string.encode()).hexdigest()
        hmac_data = "{}#{}#{}#{}#{}".format(
            method,
            url,
            self.c_public_key,
            nonce,
            hashed_query_string
            )
        logger.debug("hamc_data: %s", hmac_data)

        return hmac.new(
            self.c_private_key.encode(),
            msg=hmac_data.encode(),
            digestmod="sha256").hexdigest()

    def query(self, url, method="GET", post_params=None, headers=None):
        """
        method should be "GET", "POST", etc.
        return: request object
        """
        if not headers:
            headers = dict()

        if self.api_credits < 3:
            logger.warning(
                "Not enough api_credits (to high request frequency).\n"
                + "Sleeping for 3 seconds...")
            time.sleep(3)
        else:
            logger.debug("We have at least %s api_credits", self.api_credits)

        headers['X-API-KEY'] = self.c_public_key
        headers['X-API-NONCE'] = str(int(time.time()))
        headers['X-API-SIGNATURE'] = self.generate_api_signature(
            method, url, headers['X-API-NONCE'], post_params)

        response = super().query_json(url, headers=headers)

        if response:
            self.api_credits = response["credits"]
            logger.info("Credits left: %s", self.api_credits)

        return response

    def get_public_trade_history(self, since_tid=None, trading_pair="btceur"):
        """
        Query the btceur trade history and return the JSON answer.
        Return None on error.
        """
        url = self.C_API_URL + "/trades/history?trading_pair=" + trading_pair
        if since_tid:
            url += "&since_tid={}".format(since_tid)
            logger.debug("since_tid = %s", since_tid)

        return self.query(url)


class Shapeshift(BaseQuerry):
    """See https://info.shapeshift.io/api"""
    def __init__(self, api_key=None):
        super(Shapeshift, self).__init__("shapeshift")
        self.API_BASE_URL = "https://shapeshift.io"
        self.api_key = api_key
        "not yet used"

    def get_marketinfo(self, curIn="btc", curOut="eth"):
        """If none is given, return dict of all pairs"""
        url = self.API_BASE_URL + "/marketinfo/" + curIn + "_" + curOut
        response = self.query_json(url)

        if not response:
            return None
        elif "error" in response:
            logger.error("Error getting market info: %s", response["error"])
            return None

        return response

    def recent_tx(self, max_trans=50):
        """Get the most recent max_trans transactions. max_trans must be in [1,50]"""
        if max_trans not in range(51):
            logger.error("max_trans must be in [1, 50]. %s given.", max_trans)
            return None
        url = self.API_BASE_URL + "/recenttx/" + str(max_trans)
        return self.query_json(url)


class BitcoinCharts(BaseQuerry):
    """See https://bitcoincharts.com/about/markets-api/"""
    def __init__(self):
        super(BitcoinCharts, self).__init__("bitcoincharts")
        self.API_BASE_URL = "http://api.bitcoincharts.com/v1"

    def weighted_prices(self):
        """Get json of weighted prices in differen currencies"""
        url = self.API_BASE_URL + "/weighted_prices.json"
        return self.query_json(url)

    def market_data(self):
        url = self.API_BASE_URL + "/markets.json"
        return self.query_json(url)

    def historic_trade_data(self, symbol, starttime=None):
        """Get historic trade data. Symbol can be obtained from market_data. starttime is a Unixtimestamp.
        Returns a list of dicts
        The full history can be downloaded as gz cvs files from http://api.bitcoincharts.com/v1/csv/"""
        url = self.API_BASE_URL + "/trades.csv?symbol=" + symbol
        if starttime:
            url += r"&start=" + str(starttime)
        response = self.query_url(url)
        list_cvs = [
            [float(y) for y in x.split(",")]
            for x in response.split("\n")
        ]
        return [{
            "timestamp": x[0],
            "price": x[1],
            "amount": x[2]} for x in list_cvs
        ]


class XCrypto(BaseQuerry):
    """See https://x-crypto.com/_cc_api.php"""
    def __init__(self):
        super(XCrypto, self).__init__("xcrypto")
        self.API_BASE_URL = "https://x-crypto.com/api"

    def ticker(self, currency1="btc", currency2="eur"):
        url = self.API_BASE_URL + "/" + currency1 + "/" + currency2
        response = self.query_url(url)
        if not response:
            return None
        if "Error" in response.text:
            logger.error("Error while accessing data: %s", response.text)
        try:
            return response.json()
        except Exception as ex: #pylint: disable=W
            logger.error("Error converting response to json: %s", ex)
            return None

    def orderbook(self, currency1="btc", currency2="eur", maxlist=None):
        url = self.API_BASE_URL + "/orderbook/" + currency1 + "/" + currency2 + "/"
        url += maxlist or ""
        return self.query_json(url)

    def trades(self, currency1="btc", currency2="eur", maxtrades=None):
        url = self.API_BASE_URL + "/trades/" + currency1 + "/" + currency2
        url += maxtrades or ""
        return self.query_json(url)
