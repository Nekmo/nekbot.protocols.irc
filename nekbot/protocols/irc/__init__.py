from collections import defaultdict
from logging import getLogger
from irc import bot
from nekbot import settings
from nekbot.protocols import Protocol
from nekbot.utils.auth import AuthAddress, UserPassword
import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr


"""A simple example bot.

This is an example bot that uses the SingleServerIRCBot class from
irc.bot.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.

The known commands are:

    stats -- Prints some channel information.

    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.

    die -- Let the bot cease to exist.

    dcc -- Let the bot invite you to a DCC CHAT connection.
"""

__author__ = 'nekmo'


logger = getLogger('nekbot.protocols.irc')

def normalize_roomname(name):
    if not name.startswith('#'):
        return '#' + name
    return name


class ServerBot(irc.bot.SingleServerIRCBot):
    def __init__(self, groupchats_list, username, realname, server, port=6667):
        self.groupchats_list = groupchats_list
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], username, realname)

    def input_message(self, channel, event):
        MessageIRC(self, msg)

    def on_nicknameinuse(self, channel, event):
        channel.nick(channel.get_nickname() + "_")

    def on_welcome(self, channel, event):
        for groupchat in self.groupchats_list:
            channel.join(groupchat)

    def on_privmsg(self, channel, event):
        self.input_message()
        # self.do_command(e, e.arguments[0])

    def on_pubmsg(self, channel, event):
        a = event.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            pass
            # self.do_command(e, a[1].strip())
        return

    def on_dccmsg(self, channel, event):
        # non-chat DCC messages are raw bytes; decode as text
        text = event.arguments[0].decode('utf-8')
        channel.privmsg("You said: " + text)

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
                [normalize_roomname(addr.user) for addr in self._groupchats_by_server[str(server)]],  # rooms
                auth['username'],  # username
                auth.get('realname', auth['username']),  # Realname
                server.host,  # hostname without port
                server.port if server.port else 6667  # server port
            )
            self.servers.append(serverbot)

    def run(self):
        for server in self.servers:
            server.start()