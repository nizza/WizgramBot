import telepot.aio
from telepot.aio.delegate import (per_chat_id, create_open,
                                  pave_event_space)
import aiohttp
import asyncio
import async_timeout
import json
from enum import Enum
from operator import itemgetter
from io import BytesIO
from typing import Tuple

image_size = itemgetter('file_size')


class API(Enum):
    SUCCESS_LOGIN = 200
    SUCCESS_RECO = 202


class NoAuthError(Exception):
    pass


class RecoFailedError(Exception):
    pass


class WisdeatBot(telepot.aio.helper.ChatHandler):

    url = 'http://api.wisdeat.com:5990/v1'
    login_url = '{}/login'.format(url)
    upload_url = '{}/receipt/upload'.format(url)
    status_url = '{}/task/recognition/status'.format(url)

    def __init__(self, seed_tuple, loop, user, **kwargs):
        """

        Args:
            seed_tuple (Tuple[UserHandler, dict, int]): bot, message, seed
            loop (asyncio.AbstractEventLoop):
            user (dict): the user email and password
            **kwargs:
        """
        super().__init__(seed_tuple, **kwargs)
        self.loop = loop
        self.user = user

    async def on_chat_message(self, msg):

        content_type, chat_type, chat_id = telepot.glance(msg)
        print(content_type, chat_type, chat_id)

        if content_type == 'photo':
            file_id = sorted(msg['photo'], key=image_size)[-1]['file_id']
            await self.sender.sendMessage('Starting reco ...')
            img = BytesIO()
            await self.bot.download_file(file_id, img)
            resp = await self.req(img, 'FR')
            msg = WisdeatBot.pretty_print_reco(resp)

        else:
            msg = 'send a picture to get it recognized'

        # "Markdown"
        await self.sender.sendMessage(msg, parse_mode='Markdown')
        self.close()

    @staticmethod
    async def get_task(session, task_id, timeout):
        with async_timeout.timeout(timeout):
            resp = await session.get(WisdeatBot.status_url,
                                     params={'task_id': task_id})
        resp = await resp.json()
        return resp

    @staticmethod
    async def recognize_receipt(session, img, country,
                                timeout=10):

        img.seek(0)
        with async_timeout.timeout(timeout):
            files = {'file': img}
            resp = await session.post(WisdeatBot.upload_url, data=files,
                                      params={'country': country})
        status = resp.status
        resp = await resp.json()
        return status, resp

    async def login(self, session, timeout=10):
        with async_timeout.timeout(timeout):
            resp = await session.post(WisdeatBot.login_url,
                                      data=json.dumps(self.user))
        status = resp.status
        resp = await resp.json()
        return status, resp

    async def req(self, img, country, timeout=10):
        async with aiohttp.ClientSession(loop=self.loop) as session:
            status, resp = await self.login(session, timeout=timeout)
            if status != API.SUCCESS_LOGIN.value:
                raise NoAuthError(resp['message'])

            status, resp = await WisdeatBot.recognize_receipt(session, img, country, timeout)
            if not status == API.SUCCESS_RECO.value:
                raise RecoFailedError(resp['message'])

            task_id = resp['task_id']
            for i in range(0, 10):
                resp = await WisdeatBot.get_task(session, task_id, timeout)
                if resp['state'] not in {'STARTED', 'PENDING', 'PROGRESS'}:
                    break
                await asyncio.sleep(1)
            else:
                raise RecoFailedError()
        return resp

    @staticmethod
    def pretty_print_reco(resp):
        store = '*{store_type}* {city} - {zipcode} - {address}'.format(**resp['result']['store'])
        products = ['*Products*:']
        for product in resp['result']['products']:
            products.append('\n - *{name}*:'.format(**product['raw']))
            for match in product['matches'][:2]:
                products.append('\t ({score:.2f}) {brand_name} - {name} ({price:.2f})'.format(
                    **match, brand_name=match['brand']['name']))
        return '\n'.join([store] + products)


class UserHandler(telepot.aio.DelegatorBot):

    def __init__(self, token, loop, email, password, **kwargs):
        """

        Args:
            token (str): the Bot token
            loop (asyncio.AbstractEventLoop): the asyncio loop
            email (str): the Wisdeat API user email
            password (str): the Wisdeat API user password
            **kwargs:
        """
        user = {
            'email': email,
            'password': password
        }
        super().__init__(token,  [
            pave_event_space()(
                per_chat_id(), create_open, WisdeatBot, loop, user, timeout=10)
        ], loop=loop)


