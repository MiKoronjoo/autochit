import re

from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.filters import group, private

from pymongo import MongoClient
from pymongo.collection import Collection, ObjectId

mongo_client = MongoClient('localhost', 27017)
db = mongo_client.autochit
words_table: Collection = db.words
offers_table: Collection = db.offers

client = Client('autochit')
POSTFIX = '*'
ADMIN_ID = 69529223  # miko


def add_word(en: str, fa: str, short=False):
    words_table.update_one(dict(en=en), {'$set': dict(en=en, fa=fa, short=short)}, upsert=True)


def add_offer(en: str, fa: str, msg: Message):
    inserted = offers_table.insert_one(dict(en=en, fa=fa, cid=msg.chat.id, mid=msg.message_id))
    assert inserted.acknowledged, 'no acknowledge from database'
    return inserted.inserted_id


def load_offer(oid: str):
    return offers_table.find_one(dict(_id=ObjectId(oid)))


def delete_offer(oid: str):
    return offers_table.delete_one(dict(_id=ObjectId(oid)))


def standard(text: str):
    for c in '_-#@.,\'"*;،:؛؟?!/\\)(}{[]<>':
        text = text.replace(c, ' ')
    text = text.replace('ي', 'ی').replace('ك', 'ک')
    return text


def check_words(text: str):
    text = standard(text)
    text_words = text.split()
    temp = []
    for word in words_table.find():
        search_area = text_words if word['short'] else text
        if word['en'] in search_area:
            temp.append(word['fa'] + POSTFIX)
    result = []
    for x in temp:
        if x not in result:
            result.append(x)
    return result


def IKM2D(data) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, cbd) for text, cbd in row] for row in data])


@client.on_message(filters=group)
def on_message(bot: Client, msg: Message):
    if msg.forward_from is not None:
        return

    text = msg.text or msg.caption
    if text:
        res = check_words(text)
        if res:
            bot.send_message(msg.chat.id, '\n'.join(res), reply_to_message_id=msg.message_id)


@client.on_message(filters=private)
def on_message_private(bot: Client, msg: Message):
    if msg.text:
        text = msg.text.replace('ي', 'ی').replace('ك', 'ک').strip()
        matched = re.findall(r'^/add\s+"(\w+)"\s+"(\w+)"$', text)
        if matched:
            en = matched[0][0]
            fa = matched[0][1]
            found = words_table.find_one(dict(en=en))
            prv = f"\nموجود:\n{found['en']} -> {found['fa']}" if found else ''
            try:
                oid = add_offer(en, fa, msg)
            except AssertionError:
                bot.send_message(msg.chat.id, "Something's wrong, I can feel it!")
            else:
                bot.send_message(ADMIN_ID, f'{msg.from_user.mention}\nپیشنهاد:\n{en} -> {fa}' + prv, 'html',
                                 reply_markup=IKM2D([[('بلند', f'LONG_{oid}'), ('کوتاه', f'SHORT_{oid}')],
                                                     [('رد کردن', f'REJECT_{oid}')]]))
                bot.send_message(msg.chat.id, 'ممنون. منتظر تایید مدیر باشید')


@client.on_callback_query()
def handle_callback_query(bot: Client, query: CallbackQuery):
    if not query.data or query.from_user.id != ADMIN_ID:
        return

    cmd, oid = query.data.split('_')
    offer = load_offer(oid)
    if cmd == 'REJECT':
        bot.send_message(offer['cid'], 'این پیشنهادتون رد شد!', reply_to_message_id=offer['mid'])
        delete_offer(oid)
        query.message.edit_text(query.message.text + f"\n\nرد شد!\n[USER](tg://user?id={offer['cid']})", 'md')
    elif cmd in ('LONG', 'SHORT'):
        add_word(offer['en'], offer['fa'], cmd == 'SHORT')
        bot.send_message(offer['cid'], 'این پیشنهادتون تایید شد!', reply_to_message_id=offer['mid'])
        delete_offer(oid)
        query.message.edit_text(query.message.text + f"\n\nتایید شد!\n[USER](tg://user?id={offer['cid']})", 'md')


client.run()
