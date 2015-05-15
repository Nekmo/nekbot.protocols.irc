__author__ = 'nekmo'

class NickservIdentify(object):
    def __init__(self, auth):
        self.auth = auth

    def __call__(self, server):
        server.connection.privmsg('NickServ', 'IDENTIFY %s' % self.auth['password'])