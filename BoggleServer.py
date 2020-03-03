from http.server import BaseHTTPRequestHandler, HTTPServer

import json
import cgi
import time
import secrets
import string
import random

gameID = 1
SAVED = {}
timekeeper = {}
class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(201)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    # GET sends back the game info to the user
    def do_GET(self):

        # get specific ID requested by client
        getID = requestID(self.path)
        keyID = str(getID)

        global SAVED, timekeeper

        # The ID given by user doesn't exist        
        if len(SAVED) > getID or (getID < 0) :
            send_boggle_response(self, 404, {'message' : "No such game found"})
            return

        # Get data POSTed by client previously
        game = SAVED[keyID]
        timing = time.time() - timekeeper[keyID]
        game['time_left'] = game['duration'] - int(timing)

        # Sends the game info back to user in JSON object
        send_boggle_response(self, 200, game)    
        return

    # PUT method lets user put a word
    def do_PUT(self):
        global gameID, SAVED, timekeeper
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))

        # refuse to receive non-json content
        if ctype != 'application/json':
            send_boggle_response(self, 400, {'message': "Content should be of JSON object"})    
            return

        # read the message and convert it into a python dictionary
        # store dictionary in variable 'gamerequest'
        length = int(self.headers.get('content-length'))
        gamerequest = json.loads(self.rfile.read(length))

        # get specific ID requested by client
        getID = requestID(self.path)
        keyID = str(getID)

        # Get data POSTed by client previously
        data = SAVED[keyID]

        # Get time left for the particular game
        timing = time.time() - timekeeper[keyID]


        # The ID given by user doesn't exist
        if len(SAVED) > getID or getID < 0 :
            send_boggle_response(self, 404, {'message': "Invalid ID"}) 
        
        # Wrong Token provided
        elif gamerequest['token'] != data['token']:
            send_boggle_response(self, 400, {'message': "Incorrect Token"})

        # Outdated Game. Client has used up the duration of game
        elif timing >= data['duration']:
            send_boggle_response(self, 400, 
                {'message' : "Times Up! Game is no longer available", 'points_earned' : data['points']}) 
            del SAVED[keyID]

        # Check if compulsory keys 'token' and 'word' exists 
        elif keyExist(gamerequest, 'token') and keyExist(gamerequest, 'word'):
            
            # Is a valid word
            if isValidWord(gamerequest['word']) == 1 and isCorrectWord(gamerequest['word'], data['board'].replace(' ', '')): 
                gamerequest['id'] = getID
                gamerequest['token'] = data['token']
                gamerequest['board'] = data['board']
                gamerequest['points'] = data['points'] + len(gamerequest['word'])
                gamerequest['time_left'] = data['duration'] - int(timing)
                gamerequest['duration'] = data['duration']

                # Returns json object to client
                send_boggle_response(self, 200, gamerequest)

                # Update data
                timekeeper['time'] = time.time()     
                SAVED[keyID] = gamerequest

            else :
                # Word not found in dictionary
                gamerequest['time_left'] = data['duration'] - int(timing)

                send_boggle_response(self, 400, {'message' : "Wrong word!"})
                SAVED[keyID] = gamerequest
        else :
            # If the user did not include the compulsory fields
            gamereuqest['time_left'] = data['duration'] - int(timing)

            send_boggle_response(self, 400, {'message' : "Invalid Input!"})
            SAVED[keyID] = gamerequest
        return

    def do_POST(self):
        global gameID, SAVED, timekeeper
        ctype , pdict = cgi.parse_header(self.headers.get('content-type'))

        # refuse to receive non-json content
        if ctype != 'application/json':
            send_boggle_response(self, 400, {'message': "Content should be of JSON object"})    
            return

        # read the message and convert it into a python dictionary
        # store dictionary in variable 'message'
        length = int(self.headers.get('content-length'))
        message = json.loads(self.rfile.read(length))
        
        # check if the received object contains key 'token' and 'random'
        if keyExist(message, 'duration') and keyExist(message, 'random'):

            # Generate a random board if random is true
            # else generate based on input
            if message['random'] :
                # Generate a new random board
                message['board'] = generateNewBoard()

            if not keyExist(message, 'board'):
                with open('test_board.txt', 'r') as testboard:
                    message['board'] = testboard.readline().replace('\n', '')

            # Generate a new game ID and new game token
            message['id'] = gameID
            message['token'] = secrets.token_hex(16)

            del message['random']

            # send the JSON object back
            send_boggle_response(self, 201, message)    

            # Keep track of the points
            message['points'] = 0
            message['time_left'] = message['duration']
            timekeeper[str(gameID)] = time.time()

            # Store data for future references
            SAVED[str(gameID)] = message

            # Increment counter for new games 
            gameID = gameID + 1

            return

        else :
            # Keys not found
            send_boggle_response(self, 400, {'message' : "Invalid Input!"})
            return

def send_boggle_response(self, code, message):
    self.send_response(code)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps(message).encode())

def generateNewBoard():
    letters = string.ascii_uppercase + '*'
    myString = ''.join(random.choice(letters) for i in range(16))
    mylist = list(myString)
    newboard = ', '.join(mylist)
    return newboard

def isValidWord(word):
    # Open the dictionary and check if
    # word exists in dictionary
    myfile = open("dictionary.txt", "r")
    file_contents = myfile.read()

    # Return 1 if word found in dictionary
    # else return 0
    flag = 0
    for line in file_contents.split('\n'):
        if word == line:
            flag = 1            
    return flag

def isCorrectWord(word, mystring):
    map = []
    board = mystring.split(',') # Put board as an array
    wordarray = list(word.upper()) # Word by client

    # Initalize key value pairs
    for letter in board :
        map.append(letter)

    result = True
    
    # Loop through all the characters of the word given
    for i in range(len(wordarray) - 1):
        found = []

        # Find all occurrences of the same letter
        # The board can have more than one occurence 
        # of the same letter
        for gameindex in range(16):
            if map[gameindex] == wordarray[i]:
                # The list, found, contains indexes
                # of the same letter at a particular iteration
                found.append(gameindex) 

        # The letter in the word is not found on board
        # Cannot form word on board
        if len(found) == 0 :
            return False
        
        recursion = nextLetterInBoard(found, map, wordarray, i)
        result = result and recursion
    
    return result

def nextLetterInBoard(letterList, board, word, ptr):
    values = [-5, -4, -3, -1, 1, 3, 4, 5]

    if len(letterList) == 0:
        return True

    else :
        letter = letterList.pop(0)
        nextletterFound = False

        for value in values:
            # Ensure that it doesnt go out of bounds
            if letter + value < 0 or  letter + value > 15:
                continue
            elif letter % 4 == 0 and (value == -1 or value == -5 or value == 3):
                continue
            elif (letter == 3 or letter == 7 or letter == 11 or letter == 15) and (value == 3 or value == 1 or value == 5):
                continue
            
            # Check if the next letter can be 
            # formed from the board
            if board[letter + value] == word[ptr + 1] or board[letter + value] == '*':
                nextletterFound = True
                break

    # There could be the same letters at different indexes
    # Check if the word can be formed from the different starting indexes
    return nextletterFound or nextLetterInBoard(letterList, board, word, ptr)

def keyExist(dict, key):
    return key in dict.keys()

def requestID(currentpath):
    pathdir = currentpath.split('/')
    return int(pathdir[2])

def run(server_class=HTTPServer, handler_class=Server, port=9000):
    server_address = ('localhost', port)
    httpd = server_class(server_address, handler_class)
    
    print ('Starting httpd on port %d...' % port)
    httpd.serve_forever()
    
if __name__ == "__main__":
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()