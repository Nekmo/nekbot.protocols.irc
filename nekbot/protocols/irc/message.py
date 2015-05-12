from nekbot.protocols import Message
from nekbot.protocols.irc.utils import remove_sharp
from nekbot.protocols.irc.user import UserIRC

__author__ = 'nekmo'


class MessageIRC(Message):
    def __init__(self, server, event):
        self.server = server
        self.event = event
        body = event.arguments[0]
        user = UserIRC(server, event.source)
        super(MessageIRC, self).__init__(server.protocol, body, user)

    def get_group_chat_id(self):
        return '%s@%s' % (remove_sharp(self.event.target), self.server.domain)

    @property
    def is_groupchat(self):
        if self.is_private:
            return False
        elif self.is_public:
            return True
        else:
            raise NotImplementedError('Improperly implementation of is_groupchat.')

    @property
    def is_from_me(self):
        return self.server.connection.get_nickname() == self.user.username

    @property
    def is_private(self):
        return self.event.type in ['privmsg', 'privnotice']

    @property
    def is_public(self):
        return self.event.type in ['pubmsg']

    def _copy(self):
        return self.__class__(self.server, self.event)
