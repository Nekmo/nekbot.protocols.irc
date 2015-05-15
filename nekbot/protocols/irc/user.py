from irc.client import NickMask
from nekbot.protocols import User
from nekbot.protocols.base.user import Users

__author__ = 'nekmo'


class UserIRC(User):
    def __init__(self, server, user):
        user = NickMask(user)
        # user.nick
        # user.userhost
        # user.host
        # user.user
        self.server = server
        self._id = None
        User.__init__(self, server.protocol, user.nick)

    def send_message(self, body, notice=False):
        if notice:
            method = self.server.connection.notice
        else:
            method = self.server.connection.privmsg
        method(self.username, self.protocol.prepare_message(body))

    @property
    def id(self):
        return self._id

    def get_id(self):
        if self._id:
            return self._id
        if self.username in self.server.users_by_username:
            self._id = self.server.users_by_username[self.username].id
            return self._id
        if not self.server.get_identified(self.username):
            self._id = None
        else:
            self._id = '%s@%s' % (self.username, self.server.domain)
        self.server.users_by_username[self.username] = self
        return self._id


class UsersIRC(Users):
    def __init__(self, server):
        self.server = server
        super(UsersIRC, self).__init__(server.protocol)