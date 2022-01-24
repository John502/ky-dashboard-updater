"""
.. currentmodule:: kydashboardupdater.gdh2auth.gdh2auth
.. moduleauthor:: John Murner <jmurner@geo-comm.com>

"""
import requests

class GDH2Auth:

    def __init__(self, realm=None, user=None, secret=None, client_id=None, client_secret=None, token=None):

        self.session = requests.Session()
        self.token = token if token is not None else None
        self.realm = realm
        self.user = user
        self.secret = secret
        self.client_id = client_id
        self.client_secret = client_secret

    def get_session(self):
        """
        Returns a session with Bearer header access header

        """

        self.token = self.access_token()

        #Update Headers
        self.session.headers.update({'Authorization': 'Bearer {0}'.format(self.token)})
        self.session.headers.update({'Cache-Control': 'no-cache'})

        return self.session

    def request_token(self):
        """
        Returns a JSON Web Token as a string

        param: GDH2Auth: self

        return str: JWT
        """

        url = r'https://geocomm.auth0.com/oauth/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = {
            "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
            "username": self.user,
            "password": self.secret,
            "audience": "https://gdh.geocomm.cloud",
            "scope": "openid profile email",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "realm": self.realm
        }

        res = requests.post(url, data=body, headers=headers)

        if res.status_code == 200:
            data = res.json()
            return data['access_token']
        else:
            return None


    def access_token(self):
        """
        Return a the token from GDH2

        """
        return self.request_token() if self.token is None else self.token



