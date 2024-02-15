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
import programs.nmha_witness as Witness
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FILE_PATH = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(f'{FILE_PATH}\\config.ini')
PROGRAM_NAME = config['PROGRAM']['name']
PROGRAM_IP = config['PROGRAM']['ip']
PROGRAM_PORT = config['PROGRAM']['port']
PROGRAM_URL = f'https://{PROGRAM_IP}:{PROGRAM_PORT}'
PROGRAM_USERNAME = config['PROGRAM']['username']
PROGRAM_PASSWORD = config['PROGRAM']['password']
NMS_IP = config['NMS']['ip']
NMS_PORT = int(config['NMS']['port'])
LOG_PATH = f'{FILE_PATH}\\{config["LOGS"]["path"]}'
LOG_NAME = 'nmha.log'
DAYS_OF_BACKUP_LOGS = int(config['LOGS']['days'])

WITNESS_LOGIN_API = '/rest/v2/login/sessions'
WITNESS_EVENT_API = '/api/createEvent'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if os.path.isdir(LOG_PATH) is False:
    os.makedirs(LOG_PATH)
log_handler = logging.handlers.TimedRotatingFileHandler(
    f'{LOG_PATH}\\{LOG_NAME}',
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

def request_api(uri, method, **kwargs):
    """Sends an HTTP request to the designated Witness API endpoint.

    Args:
        witness_uri (String): The address of the specific Witness endpoint to
        be used.
        method (String): The request method type.

    Returns:
        Reponse object: The object containing the content of the response from
        the server.
    """
    server_address = f'{PROGRAM_URL}{uri}'
    response = None
    try:
        response = requests.request(method, server_address, **kwargs,
                                    timeout=120)
    except requests.exceptions.RequestException as error:
        logger.error('Error in request to %s server: %s', PROGRAM_NAME, error)
        response = requests.Response()
        response.status_code = 404
    return response

def create_authorization_header(program_session):
    """Takes the response from the login endpoint and creates a header
    containing the given bearer token.

    Args:
        witness_session (JSON): The session data returned by the
        request_witness_api function.

    Returns:
        Dictionary: Contains a single entry: the bearer token of the relevant
        session.
    """
    logger.info('Received %s authorization', PROGRAM_NAME)
    bearer_token = program_session.json()['token']
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

def login_to_program(login_details):
    """Calls the relevant functions to login to the Witness server and returns
    the bearer token.

    Returns:
        Dictionary: Contains a single entry: the bearer token of the relevant
        session.
    """
    response = request_api(
            login_details['url'],
            'POST',
            verify=False,
            json=login_details['data'])
    if not response:
        logger.error('Failed to login to Witness server.')
        return None
    response_code = check_response_code(response)
    if response_code != 200:
        logger.error('Failed to login to Witness server.')
        return None
    authorization_header = create_authorization_header(response)
    return authorization_header

def process_nms_message(data, program, authorization_header):
    decoded_message = data.decode().strip('\r')
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    event_api = program.get_event_api()
    event_data = program.create_event(decoded_message, timestamp,
                                      authorization_header)
    response = request_api(event_api, 'POST', verify=False,
                           headers=event_data[0], json=event_data[1])
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

    program = Witness.WitnessProgram(PROGRAM_USERNAME, PROGRAM_PASSWORD)
    login_details = program.get_login_details()
    authorization_header = login_to_program(login_details)

    nms_socket = connect_to_nms_server()
    while True:
        message = nms_socket.recv(1024)
        if not authorization_header:
            authorization_header = login_to_program(login_details)
        if not message:
            logger.error('Connection to NMS server lost.')
            logger.info('Attempting to reconnect.')
            nms_socket = connect_to_nms_server()
        elif authorization_header:
            response = process_nms_message(message, program,
                                           authorization_header)
            response_code = check_response_code(response)
            if response_code == 401:
                logger.info('Reauthenticating...')
                authorization_header = login_to_program(login_details)
                response = process_nms_message(message, program,
                                           authorization_header)
                response_code = check_response_code(response)
            if response_code != 200:
                logger.error('Unhandled error, message not forwarded.')

if __name__ == '__main__':
    main()
