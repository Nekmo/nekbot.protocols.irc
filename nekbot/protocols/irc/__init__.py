# coding=utf-8
from collections import defaultdict
from logging import getLogger

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, NickMask
import threading

from nekbot import settings
from nekbot.core.commands.temp import TempRegex, TempTimeout, CancelTemp
from nekbot.protocols import Protocol
from nekbot.protocols.irc.group_chat import GroupChatsIRC, GroupChatIRC
from nekbot.protocols.irc.message import MessageIRC
from nekbot.protocols.irc.user import UserIRC
from nekbot.protocols.irc.utils import add_sharp, remove_sharp
from nekbot.utils.auth import AuthAddress
from nekbot.utils.modules import get_module


"""
"""

__author__ = 'nekmo'

logger = getLogger('nekbot.protocols.irc')

irc.client.ServerConnection.buffer_class.errors = 'replace'

class ServerBot(irc.bot.SingleServerIRCBot):
    def __init__(self, protocol, groupchats_list, username, realname, server, port=6667):
        self.on_start = []
        self.identified_command = None
        self.users_by_username = {}  # Usuarios en el servidor conocidos.
        self.groupchats = {}  # {'groupchat': <Groupchat object>}
        self.groupchats_list = groupchats_list  # ['groupchat1', 'groupchat2']
        self.protocol = protocol
        self.domain = server
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], username, realname)

    def input_message(self, event):
        logger.debug('Incoming message: %s' % event.arguments[0])
        self.protocol.propagate('message', MessageIRC(self, event))

    def _execute_identified_command(self, username, command=None, result=None):
        if command is None:
            command = self.identified_command
        if result is None:
            result = settings.IDENTIFIED_COMMANDS[command]
        self.connection.send_raw(command % username)
        pattern = result[0].format(username=username)
        temp = TempRegex(self.protocol, pattern, timeout=6, no_raise=True)
        for msg in temp.read():
            if isinstance(msg, TempTimeout): break
            if msg == CancelTemp: break
            if msg.server != self: continue
            temp.done()
            return msg
        return False

    def _get_identified_command(self):
        for command, result in settings.IDENTIFIED_COMMANDS.items():
            if self._execute_identified_command(self.connection.get_nickname(), command, result) is not False:
                logger.debug('Identified Command for %s: %s' % (self.domain, command))
                self.identified_command = command
                return result
        logger.info('Identified Command unknown for server %s' % self.domain)
        self.identified_command = False
        return False

    def get_identified_command(self):
        l = threading.Thread(target=self._get_identified_command)
        l.start()

    def get_identified(self, username):
        """IRC no tiene una forma sencilla de comprobar si un usuario está autenticado.
        Intentar descubrirlo.
        """
        if self.identified_command is False:
            # No hay un comando conocido para saber si el usuario está conectado
            return False
        if self.identified_command is None:
            return False
            # self.get_identified_command()
        msg = self._execute_identified_command(username)
        if msg is False: return False
        result = settings.IDENTIFIED_COMMANDS[self.identified_command]
        if msg.match[0] == result[1]:
            return True
        return False

    def on_welcome(self, connection, event):
        self.get_identified_command()
        for on_start in self.on_start:
            on_start(self)
        for groupchat in self.groupchats_list:
            self.join_groupchat(add_sharp(groupchat))

    def join_groupchat(self, channel, key=''):
        self.connection.join(channel, key)

    def on_privmsg(self, connection, event):
        self.input_message(event)

    def on_pubmsg(self, connection, event):
        self.input_message(event)

    def on_privnotice(self, channel, event):
        self.input_message(event)

    def on_pubnotice(self, channel, event):
        self.input_message(event)

    def on_dccmsg(self, channel, event):
        # non-chat DCC messages are raw bytes; decode as text
        text = event.arguments[0].decode('utf-8')
        channel.privmsg("You said: " + text)

    def on_join(self, connection, event):
        if event.target not in self.groupchats:
            # Se está entrando a la sala por primera vez
            groupchat = GroupChatIRC(self, self.channels[event.target], event.target)
            self.groupchats[remove_sharp(event.target)] = groupchat
            self.protocol.groupchats[str(groupchat)] = groupchat
            groupchat.get_users()
        else:
            # Un usuario ha entrado a al sala
            user = NickMask(event.source)
            self.groupchats[remove_sharp(event.target)].users[str(user)] = user

    def on_part(self, connection, event):
        # {'source': u'nekmo!~nekmo@localhost.localdomain',
        # 'type': u'part', 'target': u'#testing', 'arguments': [u'Saliendo']}
        user = NickMask(event.source)
        del self.groupchats[remove_sharp(event.target)].users[str(user)]

    def on_mode(self, connection, event):
        pass

    def on_nicknameinuse(self, connection, event):
        connection.nick(connection.get_nickname() + "_")

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
            # if cmd == "disconnect":
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

    def close(self):
        self.connection.close()


class Irc(Protocol):
    features = ['notice', 'groupchats', 'wide_messages']
    user_class = UserIRC

    def __init__(self, nekbot):
        self.servers = []
        self._addresses = [AuthAddress(addr) for addr in settings.IRC_GROUPCHATS]  # groupchat@server
        self._groupchats_by_server = defaultdict(list)  # {server: [groupchat@server]}
        super(Irc, self).__init__(nekbot)

    def prepare_message(self, body):
        if not isinstance(body, (str, unicode)):
            body = unicode(body)
        try:
            body = body.decode('utf-8')
        except:
            pass
        return body

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
            if 'method' in auth:
                AuthMethod = get_module('nekbot.protocols.irc.auth.%s' % auth['method'])
                serverbot.on_start.append(AuthMethod(auth))
            self.servers.append(serverbot)

    def run(self):
        for server in self.servers:
            server.start()

    def close(self):
        for server in self.servers:
            server.close()
