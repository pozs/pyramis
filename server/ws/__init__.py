import base64
import hashlib
from typing import Any


# Credit: https://gist.github.com/gpiffault/c462466bd644080a92e3430692a22784

def ws_accept(key: Any) -> str:
    if isinstance(key, str):
        key = key.encode('ascii')
    return base64.standard_b64encode(hashlib.sha1(
        key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    ).digest()).decode('ascii')


def ws_read_frame(rfile) -> str | bytes | None:
    preamble = rfile.read(2)
    if len(preamble) < 2:
        return None
    mask = preamble[1] >> 7
    length = preamble[1] & 0x7f
    if length == 126:
        length = int.from_bytes(rfile.read(2), 'big')
    elif length == 127:
        length = int.from_bytes(rfile.read(4), 'big')
    if mask:
        mask_key = rfile.read(4)
    data = rfile.read(length)
    if mask:
        data = bytes([data[i] ^ mask_key[i % 4] for i in range(len(data))])
    if preamble[0] & 0xf == 1:
        data = data.decode('utf-8')
    return data


def ws_encode_frame(msg: str | bytes) -> bytes:
    # Setting fin to 1
    preamble = 1 << 7
    if isinstance(msg, str):
        preamble |= 1
        msg = msg.encode('utf-8')
    else:
        preamble |= 2
    frame = bytes([preamble])
    if len(msg) <= 125:
        frame += bytes([len(msg)])
    elif len(msg) < 2 ** 16:
        frame += bytes([126])
        frame += len(msg).to_bytes(2, 'big')
    else:
        frame += bytes([127])
        frame += len(msg).to_bytes(4, 'big')
    frame += msg
    return frame
