from logging import getLogger
from nekbot.protocols import GroupChat
from nekbot.protocols.base.group_chat import GroupChats
from nekbot.protocols.irc.user import UserIRC, UsersIRC
from nekbot.protocols.irc.utils import remove_sharp

__author__ = 'nekmo'

logger = getLogger('nekbot.protocols.irc.group_chat')

class GroupChatIRC(GroupChat):
    def __init__(self, server, channel, name):
        name = remove_sharp(name)
        self.channel = channel
        self.server = server
        self.users = UsersIRC(self.server)
        id_groupchat = '%s@%s' % (name, self.server.domain)
        GroupChat.__init__(self, server.protocol, name, id_groupchat)

    def get_users(self, override=True):
        users = UsersIRC(self.server)
        for user in self.channel.users():
            user = UserIRC(self.server, user)
            users[str(user)] = user
        if override:
            self.users = users
        logger.debug('Users in %s: %s' % (self.name, ', '.join(users)))
        return users

    @property
    def bot(self):
        return UserIRC(self.server, self.server.connection.get_nickname())

    def send_message(self, body):
        self.server.connection.privmsg('#' + self.name,
                                       self.protocol.prepare_message(body))


class GroupChatsIRC(GroupChats):
    pass