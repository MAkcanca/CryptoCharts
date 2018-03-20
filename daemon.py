# Xrp/btc ETH/BTC NEO/BTC LTC/BTC NEO/ETH XRP/ETH ETH/LTC
import logging
import socketIO_client
from socketIO_client.transports import get_response
from socketIO_client.parsers import get_byte, _read_packet_text, parse_packet_text
import time
from requests.exceptions import ConnectionError
from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_socketio import send, emit
from threading import Thread


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


FIELDS = {'TYPE': 0x0, 'MARKET': 0x0, 'FROMSYMBOL': 0x0, 'TOSYMBOL': 0x0, 'FLAGS': 0x0, 'PRICE': 0x1, 'BID': 0x2,
          'OFFER': 0x4, 'LASTUPDATE': 0x8, 'AVG': 0x10, 'LASTVOLUME': 0x20, 'LASTVOLUMETO': 0x40, 'LASTTRADEID': 0x80,
          'VOLUMEHOUR': 0x100, 'VOLUMEHOURTO': 0x200, 'VOLUME24HOUR': 0x400, 'VOLUME24HOURTO': 0x800,
          'OPENHOUR': 0x1000, 'HIGHHOUR': 0x2000, 'LOWHOUR': 0x4000, 'OPEN24HOUR': 0x8000, 'HIGH24HOUR': 0x10000,
          'LOW24HOUR': 0x20000, 'LASTMARKET': 0x40000}


# extra function to support XHR1 style protocol
def _new_read_packet_length(content, content_index):
    packet_length_string = ''
    while get_byte(content, content_index) != ord(':'):
        byte = get_byte(content, content_index)
        packet_length_string += chr(byte)
        content_index += 1
    content_index += 1
    return content_index, int(packet_length_string)


def new_decode_engineIO_content(content):
    content_index = 0
    content_length = len(content)
    while content_index < content_length:
        try:
            content_index, packet_length = _new_read_packet_length(
                content, content_index)
        except IndexError:
            break
        content_index, packet_text = _read_packet_text(
            content, content_index, packet_length)
        engineIO_packet_type, engineIO_packet_data = parse_packet_text(
            packet_text)
        yield engineIO_packet_type, engineIO_packet_data


def new_recv_packet(self):
    params = dict(self._params)
    params['t'] = self._get_timestamp()
    response = get_response(
        self.http_session.get,
        self._http_url,
        params=params,
        **self._kw_get)
    for engineIO_packet in new_decode_engineIO_content(response.content):
        engineIO_packet_type, engineIO_packet_data = engineIO_packet
        yield engineIO_packet_type, engineIO_packet_data


setattr(socketIO_client.transports.XHR_PollingTransport, 'recv_packet', new_recv_packet)

logging.basicConfig(level=logging.DEBUG)


def on_m_response(data):
    data_type = data[0:data.find("~")]
    unpackedCurrent = {}
    currentField = 0
    if data_type == "5":
        valArray = data.split("~")
        mask = valArray[len(valArray) - 1]
        maskInt = int(mask, 16)
        for var in FIELDS:
            if FIELDS[var] == 0:
                unpackedCurrent[var] = valArray[currentField]
                currentField += 1
            elif maskInt&FIELDS[var]:
                if var == 'LASTMARKET':
                    unpackedCurrent[var] = valArray[currentField]
                else:
                    unpackedCurrent[var] = float(valArray[currentField])
                currentField += 1
        if unpackedCurrent['FROMSYMBOL'] == "XRP" and unpackedCurrent['TOSYMBOL'] == "BTC":
            socketio.emit('xrp-btc', data)
        if unpackedCurrent['FROMSYMBOL'] == "ETH" and unpackedCurrent['TOSYMBOL'] == "BTC":
            socketio.emit('eth-btc', data)
        if unpackedCurrent['FROMSYMBOL'] == "NEO" and unpackedCurrent['TOSYMBOL'] == "BTC":
            socketio.emit('neo-btc', data)
        if unpackedCurrent['FROMSYMBOL'] == "LTC" and unpackedCurrent['TOSYMBOL'] == "BTC":
            socketio.emit('ltc-btc', data)
        if unpackedCurrent['FROMSYMBOL'] == "NEO" and unpackedCurrent['TOSYMBOL'] == "ETH":
            socketio.emit('neo-eth', data)
        if unpackedCurrent['FROMSYMBOL'] == "XRP" and unpackedCurrent['TOSYMBOL'] == "ETH":
            socketio.emit('xrp-eth', data)
        if unpackedCurrent['FROMSYMBOL'] == "ETH" and unpackedCurrent['TOSYMBOL'] == "LTC":
            socketio.emit('eth-ltc', data)


def start():
    try:
        thread = Thread(target=socketio.run, args=(app,))
        thread.start()
        socket = socketIO_client.SocketIO('https://streamer.cryptocompare.com')
        socket.emit('SubAdd', {
            'subs': ['5~CCCAGG~XRP~BTC', '5~CCCAGG~ETH~BTC', '5~CCCAGG~NEO~BTC', '5~CCCAGG~LTC~BTC', '5~CCCAGG~NEO~ETH',
                     '5~CCCAGG~XRP~ETH', '5~CCCAGG~ETH~LTC']})
        socket.on('m', on_m_response)
        socket.wait()
    except:
        logging.warning('The server is down. Restarting in 10 seconds.')
        time.sleep(10)
        start()


start()
