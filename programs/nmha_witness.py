class WitnessProgram:
    WITNESS_LOGIN_API = '/rest/v2/login/sessions'
    WITNESS_EVENT_API = '/api/createEvent'

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_login_details(self):
        """Creates and returns a dictionary containing the required parameters to
        access the Witness login endpoint.

        Returns:
            Dictionary: Contains the required parameters to access the Witness
            login endpoint.
        """
        login_data = {
            'username': self.username,
            'password': self.password,
            'setCookie': False
        }
        return {'data': login_data, 'url': self.WITNESS_LOGIN_API}

    def get_event_api(self):
        return self.WITNESS_EVENT_API

    def _create_event_body(self, event_message, timestamp):
        """Formats the body of the NMS event to forward to the Witness server,
        adding a timestamp.

        Args:
            event_message (String): The decoded message from the NMS server.

        Returns:
            Dictionary: Contains a timestamp and the message from the NMS,
            formatted to match the Witness API.
        """
        event_body = ''
        if event_message.count('-') == 2:
            source, caption, description = event_message.split('-')
            event_body = {'timestamp': timestamp,
                          'source': source,
                          'caption': caption,
                          'description': description}
        else:
            event_body = {'timestamp': timestamp,
                          'description': event_message}
        return event_body

    def create_event(self, event_message, timestamp, authorization_header):
        """Calls functions to format the NMS message and forward it to the Witness
        server.

        Args:
            event_message (String): The decoded message from the NMS server.
            witness_authorization_header (Dictionary): The bearer token for the
            Witness session.

        Returns:
            Response object: The object containing the content of the response from
            the server.
        """
        header = authorization_header
        header['Content-type'] = 'application/json'
        event_body = self._create_event_body(event_message, timestamp)
        return [header, event_body]
