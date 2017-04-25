import telepot.aio
from telepot.aio.delegate import (per_chat_id, create_open,
                                  pave_event_space, per_callback_query_origin)
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot import glance
import aiohttp
import asyncio
import async_timeout
import json
from enum import Enum
from operator import itemgetter
from io import BytesIO

from typing import Tuple


from .logs import logger
from .dbs import add_reco, add_feedback
from .utils import get_chunks

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
        logger.info((content_type, chat_type, chat_id))

        if content_type == 'text' and msg['text'] == '/id':
            await self.sender.sendMessage('Your id is: *{}*'.format(chat_id),
                                          parse_mode='Markdown')
        elif content_type != 'photo':
            await self.sender.sendMessage('send a picture to get it recognized',
                                          parse_mode='Markdown')

        else:
            file_id = sorted(msg['photo'], key=image_size)[-1]['file_id']
            await self.sender.sendMessage('Starting reco ...')
            img = BytesIO()
            await self.bot.download_file(file_id, img)
            resp = await self.req(img, 'FR')

            is_error = False
            if resp['state'] in {'OCR_ERROR', 'PRODUCTS_AREA_NOT_DETECTED', 'STORE_NOT_DETECTED'}:
                msg = 'An error occurred during the recognition : *%s*' % resp['state'].replace('_', ' ').lower()
                is_error = True
            elif resp['state'] == 'FAILURE':
                msg = 'An internal error happened :('
                is_error = True
            else:
                add_reco(chat_id, resp, img)
                msg = WisdeatBot.pretty_print_reco(resp)

            logger.info(msg)
            for chunk in get_chunks(msg, 4000):
                await self.sender.sendMessage(chunk, parse_mode='Markdown')

            if not is_error:
                _ = await self.sender.sendMessage(
                    'How would you rate the recognition ?',
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[
                            InlineKeyboardButton(text='\u2600', callback_data='1'),
                            InlineKeyboardButton(text='\u2600' * 2, callback_data='2'),
                            InlineKeyboardButton(text='\u2600' * 3, callback_data='3')]
                        ]))

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
        store = '*{type_store}* {city} - {zipcode} - {address}'.format(
                    type_store=resp['result']['store']['store_type'].title(),
                    **resp['result']['store'])
        products = ['*Products*:']
        for product in resp['result']['products']:
            products.append('\n - *{name}*:'.format(name=product['raw']['name'].replace('*', '')))
            if product['valid']:
                products.append('\t ({score:.2f}){brand_name} - {name} ({price:.2f})'.format(
                    **product['valid'], brand_name=product['valid']['brand']['name'] or ''))
                for match in product['matches'][:1]:
                    products.append('\t ({score:.2f}){brand_name} - {name} ({price:.2f})'.format(
                        **match, brand_name=match['brand']['name'] or ''))
        return '\n'.join([store] + products)


class RecoManager(telepot.aio.helper.CallbackQueryOriginHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_callback_query(self, msg):
        query_id, from_id, feedback = glance(msg, flavor='callback_query')
        add_feedback(from_id, feedback)
        logger.info('{}: {}'.format(from_id, feedback))

        await self.editor.editMessageText('Thanks for your feedback!', reply_markup=None)
        self.close()

    async def on__idle(self, event):
        await self.editor.editMessageText('', reply_markup=None)
        self.close()


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
                per_chat_id(), create_open, WisdeatBot, loop, user, timeout=10),
            pave_event_space()(
                per_callback_query_origin(), create_open, RecoManager, timeout=120),
        ], loop=loop)


