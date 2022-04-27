import logging
import os
import requests
import threading
from typing import Any, Union, Optional

from eth_account import Account, messages
from eth_account.signers.local import LocalAccount
from eth_typing import URI
from web3 import HTTPProvider
from web3._utils.request import make_post_request
from web3.types import RPCEndpoint, RPCResponse
from web3 import Web3


def get_default_endpoint() -> URI:
    return URI(
        os.environ.get("FLASHBOTS_HTTP_PROVIDER_URI", "https://relay.flashbots.net")
    )


class FlashbotProvider(HTTPProvider):
    logger = logging.getLogger("web3.providers.FlashbotProvider")

    def __init__(
        self,
        signature_account: LocalAccount,
        endpoint_uri: Optional[Union[URI, str]] = None,
        request_kwargs: Optional[Any] = None,
        session: Optional[Any] = None,
    ):
        _endpoint_uri = endpoint_uri or get_default_endpoint()
        super().__init__(_endpoint_uri, request_kwargs, session)
        self.signature_account = signature_account

    def send_request(self, endpoint_uri, request_data, headers, method):
        try:
            response = requests.post(
                endpoint_uri, request_data, headers=headers, timeout=2
            ).json()

            print(response)
        except Exception as error:
            print(error)

    def make_request(self, method: RPCEndpoint, params: Any):
        self.logger.debug(
            "Making request HTTP. URI: %s, Method: %s", self.endpoint_uri, method
        )
        request_data = self.encode_rpc_request(method, params)

        message = messages.encode_defunct(
            text=Web3.keccak(text=request_data.decode("utf-8")).hex()
        )
        signed_message = Account.sign_message(
            message, private_key=self.signature_account.privateKey.hex()
        )

        headers = self.get_request_headers() | {
            "X-Flashbots-Signature": f"{self.signature_account.address}:{signed_message.signature.hex()}"
        }

        threads = []

        threads.append(threading.Thread(target=self.send_request, args=(self.endpoint_uri, request_data, headers, method)))
        threads.append(threading.Thread(target=self.send_request, args=("https://api.edennetwork.io/v1/bundle", request_data, headers, method)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
