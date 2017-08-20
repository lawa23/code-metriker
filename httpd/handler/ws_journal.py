#!/usr/bin/python3
# coding: utf-8

import asyncio
import aiohttp
import subprocess
import locale
import json
import time

from aiohttp import web

from httpd.utils import log


class JournalHandler(object):

    def __init__(self, ws):
        self.ws = ws
        self.queue = asyncio.Queue()

    async def shutdown(self):
        await self.queue.put("shutdown")

    def sync_log(self):
        asyncio.ensure_future(self._sync_log())

    async def _shutdown(self):
        self.p.kill()
        await self.p.wait()

    async def _sync_log(self):
        cmd = ["journalctl", "-n", "500",  "-f", "-o", "json"]
        self.p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        while True:
            async for line in self.p.stdout:
                if not self.queue.empty():
                    cmd = self.queue.get()
                    if cmd == "shutdown":
                        self._shutdown()
                        return
                eline = line.decode(locale.getpreferredencoding(False))
                d = json.loads(eline)
                data = dict()
                data['data-log-entry'] = d
                try:
                    ret = self.ws.send_json(data)
                except RuntimeError:
                    self._shutdown()
                    return
                if ret: await ret
        return await self.p.wait()


    def sync_info(self):
        cmd = "journalctl -o json"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, _ = p.communicate()
        p_status = p.wait()
        output = output.decode("utf-8").rstrip()
        set_comm = set()
        for line in output.split("\n"):
            data = json.loads(line)
            if '_COMM' in data:
                set_comm.add(data['_COMM'])
        data = dict()
        data['data-info'] = dict()
        data['data-info']['list-comm'] = list(set_comm)
        self.ws.send_json(data)


async def handle(request):
    peername = request.transport.get_extra_info('peername')
    host = port = "unknown"
    if peername is not None:
        host, port = peername[0:2]
    log.debug("web journal socket request from {}[{}]".format(host, port))

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    jh = JournalHandler(ws)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
                await jh.shutdown()
                return ws
            if msg.data == 'info':
                jh.sync_info()
            elif msg.data == 'start':
                jh.sync_log()
            else:
                log.debug("unknown websocket command {}".format(str(msg.data)))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())
    return ws


