"""This script forwards the events sent over NMS TCP/IP sockets to the http API
of Witness (or related products)."""
import os
import logging
import logging.handlers
import datetime
import socket
import time
import configparser
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config = configparser.ConfigParser()
config.read('config.ini')
WITNESS_IP = config['WITNESS']['ip']
WITNESS_PORT = config['WITNESS']['port']
WITNESS_URL = f'https://{WITNESS_IP}:{WITNESS_PORT}'
WITNESS_USERNAME = config['WITNESS']['username']
WITNESS_PASSWORD = config['WITNESS']['password']
NMS_IP = config['NMS']['ip']
NMS_PORT = int(config['NMS']['port'])
LOG_PATH = config['LOGS']['path']
LOG_NAME = 'wit_sec.log'
DAYS_OF_BACKUP_LOGS = int(config['LOGS']['days'])

WITNESS_LOGIN_API = '/rest/v2/login/sessions'
WITNESS_EVENT_API = '/api/createEvent'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if os.path.isdir(LOG_PATH) is False:
    os.makedirs(LOG_PATH)
log_handler = logging.handlers.TimedRotatingFileHandler(
    f'{LOG_PATH}/{LOG_NAME}',
    when='midnight',
    backupCount=DAYS_OF_BACKUP_LOGS
    )
log_handler.suffix = '%Y%m%d'
logger_format = logging.Formatter('%(asctime)s;%(levelname)s;%(message)s',
                                  '%H:%M:%S')
log_handler.setFormatter(logger_format)
logger.addHandler(log_handler)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)

def get_witness_login_details():
    """Creates and returns a dictionary containing the required parameters to
    access the Witness login endpoint.

    Returns:
        Dictionary: Contains the required parameters to access the Witness
        login endpoint.
    """
    login_details = {
        'username': WITNESS_USERNAME,
        'password': WITNESS_PASSWORD,
        'setCookie': False
    }
    return login_details

def request_witness_api(witness_uri, method, **kwargs):
    """Sends an HTTP request to the designated Witness API endpoint.

    Args:
        witness_uri (String): The address of the specific Witness endpoint to
        be used.
        method (String): The request method type.

    Returns:
        Reponse object: The object containing the content of the response from
        the server.
    """
    server_address = f'{WITNESS_URL}{witness_uri}'
    response = None
    try:
        response = requests.request(method, server_address, **kwargs,
                                    timeout=120)
    except requests.exceptions.RequestException as error:
        logger.error('Error in request to Witness server: %s', error)
    return response

def create_witness_authorization_header(witness_session):
    """Takes the response from the login endpoint and creates a header
    containing the given bearer token.

    Args:
        witness_session (JSON): The session data returned by the
        request_witness_api function.

    Returns:
        Dictionary: Contains a single entry: the bearer token of the relevant
        session.
    """
    logger.info('Received Witness authorization')
    bearer_token = witness_session.json()['token']
    header = {'Authorization': f'Bearer {bearer_token}'}
    return header

def check_response_code(response):
    """Checks the response code from a given request, logging it's result and
    returning the code.

    Args:
        response (Response object): A request Response object returned from a
        request call.

    Returns:
        Int: The response code for the given request call.
    """
    response_code = response.status_code
    if response_code == 200:
        logger.debug('Request successful.')
    else:
        logger.error('Request error, response code: %s.', response_code)
    return response_code

def login_to_witness():
    """Calls the relevant functions to login to the Witness server and returns
    the bearer token.

    Returns:
        Dictionary: Contains a single entry: the bearer token of the relevant
        session.
    """
    login_details = get_witness_login_details()
    response = request_witness_api(
            WITNESS_LOGIN_API,
            'POST',
            verify=False,
            json=login_details)
    if not response:
        logger.error('Failed to login to Witness server.')
        return None
    response_code = check_response_code(response)
    if response_code != 200:
        logger.error('Failed to login to Witness server.')
        return None
    witness_authorization_header = create_witness_authorization_header(
        response)
    return witness_authorization_header

def create_generic_event_body(event_message):
    """Formats the body of the NMS event to forward to the Witness server,
    adding a timestamp.

    Args:
        event_message (String): The decoded message from the NMS server.

    Returns:
        Dictionary: Contains a timestamp and the message from the NMS,
        formatted to match the Witness API.
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
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

def create_generic_witness_event(event_message, witness_authorization_header):
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
    header = witness_authorization_header
    header['Content-type'] = 'application/json'
    event_body = create_generic_event_body(event_message)
    response = request_witness_api(
        WITNESS_EVENT_API,
        'POST',
        verify=False,
        headers=header,
        json=event_body)
    return response

def process_nms_message(data, witness_authorization_header):
    """Decodes the message from the NMS server and calls the function to
    forward it to the Witness server. If not logged in to the Witness server,
    attempts to reconnect.

    Args:
        data (Bytes object): The message from the NMS server.
        witness_authorization_header (Dictionary): The bearer token for the
        Witness session.

    Returns:
        Response object: The object containing the content of the response from
        the server.
    """
    decoded_message = data.decode().strip('\r')
    if witness_authorization_header:
        response = create_generic_witness_event(decoded_message,
                                                witness_authorization_header)
    return response

def connect_to_nms_server():
    """Using the set NMS IP and port, opens a client socket to listen to the
    NMS server, then returns that socket.

    Returns:
        Socket object: The socket created by the function.
    """
    server_address = (NMS_IP, NMS_PORT)
    nms_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.info('Connecting to NMS Server at %s, port %s...', NMS_IP, NMS_PORT)
    while nms_socket.connect_ex(server_address) != 0:
        time.sleep(10)
    logger.info('Connection established.')
    return nms_socket

def main():
    """Logs in to the Witness Server then opens the TCP/IP client socket and
    begins listening on the client socket. Continuosly listens to the NMS
    server and sends received messages to the processing function. If the
    Witness session expires, it attempts to create a new one. If the socket
    disconnects, it attempts to reconnect.
    """
    authorization_header = login_to_witness()

    nms_socket = connect_to_nms_server()
    while True:
        message = nms_socket.recv(1024)
        if not authorization_header:
            authorization_header = login_to_witness()
        if not message:
            logger.error('Connection to NMS server lost.')
            logger.info('Attempting to reconnect.')
            nms_socket = connect_to_nms_server()
        else:
            response = process_nms_message(message, authorization_header)
            response_code = check_response_code(response)
            if response_code == 401:
                logger.info('Reauthenticating...')
                authorization_header = login_to_witness()
                response = process_nms_message(message, authorization_header)
                response_code = check_response_code(response)
            if response_code != 200:
                logger.error('Unhandled error, message not forwarded.')

if __name__ == '__main__':
    main()
