from collections import defaultdict
from logging import getLogger

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad

from nekbot import settings
from nekbot.protocols import Protocol
from nekbot.protocols.irc.group_chat import GroupChatsIRC, GroupChatIRC
from nekbot.protocols.irc.message import MessageIRC
from nekbot.protocols.irc.utils import add_sharp
from nekbot.utils.auth import AuthAddress


"""
"""

__author__ = 'nekmo'

logger = getLogger('nekbot.protocols.irc')

# event:
# {'source': u'nekmo!~nekmo@localhost.localdomain',
# 'type': 'pubmsg', 'target': u'#testing', 'arguments': [u'jugou']}
#
# channel:
# {'username': 'NekBot', 'reactor': <irc.client.Reactor object at 0x7f44c2cf9d50>,
# 'real_nickname': u'NekBot', 'handlers': {},
# 'buffer': <irc.buffer.DecodingLineBuffer object at 0x7f44c2cf9e50>,
# 'server_address': ('localhost', 6667), 'server': 'localhost',
#  '_saved_connect': args_and_kwargs(args=('localhost', 6667, 'NekBot', None),
# kwargs={'ircname': 'Nekbot Mirai IRC'}),
#  'connect_factory': <irc.connection.Factory object at 0x7f44c2fb6490>,
# 'socket': <socket._socketobject object at 0x7f44c5d118a0>, 'connected': True,
#  'real_server_name': u'irc.example.net', 'password': None, 'nickname': 'NekBot',
#  'port': 6667, 'ircname': 'Nekbot Mirai IRC',
# 'features': <irc.features.FeatureSet object at 0x7f44c2cf9e10>}



class ServerBot(irc.bot.SingleServerIRCBot):
    def __init__(self, protocol, groupchats_list, username, realname, server, port=6667):
        self.groupchats = {} # {'groupchat': <Groupchat object>}
        self.groupchats_list = groupchats_list
        self.protocol = protocol
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], username, realname)

    def input_message(self, event):
        self.protocol.propagate('message', MessageIRC(self, event))

    def on_nicknameinuse(self, channel, event):
        channel.nick(channel.get_nickname() + "_")

    def on_welcome(self, connection, event):
        for groupchat in self.groupchats_list:
            self.join_groupchat(add_sharp(groupchat))

    def on_privmsg(self, connection, event):
        self.input_message(event)
        # self.do_command(e, e.arguments[0])

    def on_pubmsg(self, connection, event):
        # self.send_pubmsg('#testing', 'Message')
        # connection.privmsg('Nekmo', 'Test')  # Mensaje privado
        # self.connection.privmsg('#testing', 'Test')
        self.input_message(event)
        a = event.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            pass
            # self.do_command(e, a[1].strip())
        return

    def on_dccmsg(self, channel, event):
        # non-chat DCC messages are raw bytes; decode as text
        text = event.arguments[0].decode('utf-8')
        channel.privmsg("You said: " + text)

    def join_groupchat(self, channel, key=''):
        self.connection.join(channel, key)

    def on_join(self, connection, event):
        groupchat = GroupChatIRC(self, self.channels[event.target], event.target, event.source)
        self.groupchats[str(groupchat)] = groupchat
        self.protocol.groupchats[str(groupchat)] = groupchat

    def on_dccchat(self, channel, event):
        if len(event.arguments) != 2:
            return
        args = event.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

            # def do_command(self, e, cmd):
            # nick = e.source.nick
            # c = self.connection
            #
            #     if cmd == "disconnect":
            #         self.disconnect()
            #     elif cmd == "die":
            #         self.die()
            #     elif cmd == "stats":
            #         for chname, chobj in self.channels.items():
            #             c.notice(nick, "--- Channel statistics ---")
            #             c.notice(nick, "Channel: " + chname)
            #             users = sorted(chobj.users())
            #             c.notice(nick, "Users: " + ", ".join(users))
            #             opers = sorted(chobj.opers())
            #             c.notice(nick, "Opers: " + ", ".join(opers))
            #             voiced = sorted(chobj.voiced())
            #             c.notice(nick, "Voiced: " + ", ".join(voiced))
            #     elif cmd == "dcc":
            #         dcc = self.dcc_listen()
            #         c.ctcp("DCC", nick, "CHAT chat %s %d" % (
            #             ip_quad_to_numstr(dcc.localaddress),
            #             dcc.localport))
            #     else:
            #         c.notice(nick, "Not understood: " + cmd)


class Irc(Protocol):
    def __init__(self, nekbot):
        self.servers = []
        self.groupchats = GroupChatsIRC(self)
        self._addresses = [AuthAddress(addr) for addr in settings.IRC_GROUPCHATS]  # groupchat@server
        self._groupchats_by_server = defaultdict(list)  # {server: [groupchat@server]}
        super(Irc, self).__init__(nekbot)

    def init(self):
        for address in self._addresses:
            self._groupchats_by_server[address.endpoint].append(address)
        for server, auth in settings.IRC_AUTHS.items():
            # El identificador es addr.user, pero en realidad es addr.groupchat. Esto es porque es una
            # clase abstraida para obtener user@host, donde user en realidad es el groupchat.
            server = AuthAddress(server)
            serverbot = ServerBot(
                self,  # protocol instance
                [addr.user for addr in self._groupchats_by_server[str(server)]],  # rooms
                auth['username'],  # username
                auth.get('realname', auth['username']),  # Realname
                server.host,  # hostname without port
                server.port if server.port else 6667  # server port
            )
            self.servers.append(serverbot)

    def run(self):
        for server in self.servers:
            server.start()