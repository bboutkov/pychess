
import os
import re
import json
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from html.parser import HTMLParser
import base64

from pychess import VERSION
from pychess.Utils.const import FISCHERRANDOMCHESS
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAny, toSAN

# import pdb
# def _(p):
#     return p
# VERSION = '1.0'
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context


# Abstract class to download a game from the Internet
class InternetGameInterface:
    # Internal
    def __init__(self):
        self.id = None
        self.userAgent = 'PyChess %s' % VERSION

    def get_game_id(self):
        return self.id

    def json_field(self, data, path):
        if data is None:
            return None
        keys = path.split('/')
        value = data
        for key in keys:
            if key in value:
                value = value[key]
            else:
                return ''
        if value is None:
            return ''
        else:
            return value

    def read_data(self, response):
        # Check
        if response is None:
            return None
        bytes = response.read()

        # Decode
        cs = response.info().get_content_charset()
        if not cs is None:
            data = bytes.decode(cs)
        else:
            try:
                data = bytes.decode('utf-8')
            except:
                try:
                    data = bytes.decode('latin-1')
                except:
                    data = ''

        # Result
        return data.replace("\r", '')

    # External
    def get_description(self):
        pass

    def get_test_links(self):
        pass

    def assign_game(self, url):
        pass

    def download_game(self):
        pass


# Lichess.org
class InternetGameLichess(InternetGameInterface):
    def get_description(self):
        return 'Lichess.org -- %s' % _('Download link')

    def get_test_links(self):
        return [('http://lichess.org/CA4bR2b8/black/analysis#12', True),    # Game in advanced position
                ('https://lichess.org/CA4bR2b8', True),                     # Canonical address
                ('https://lichess.org/game/export/CA4bR2b8', True),         # Download link
                ('http://fr.lichess.org/@/thibault', False),                # Not a game (user page)
                ('http://lichess.org/blog', False),                         # Not a game (page)
                ('http://lichess.dev/ABCD1234', False),                     # Not a game (wrong ID)
                ('https://LICHESS.org/nGhOUXdP?p=0', True),                 # Variant game with parameter
                ('https://lichess.org/nGhOUXdP?p=0#3', True)]               # Variant game with parameter and anchor

    def assign_game(self, url):
        # Parse the provided URL to retrieve the ID
        rxp = re.compile('^https?:\/\/([\S]+\.)?lichess\.(org|dev)\/(game\/export\/)?([a-z0-9]+)\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is None:
            return False

        # Extract the identifier
        id = str(m.group(4))
        if len(id) != 8:
            return False
        else:
            self.id = id
            return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download (possible error 404)
        url = 'http://lichess.org/game/export/%s?literate=1' % self.id
        response = urlopen(url)
        return self.read_data(response)


# ChessGames.com
class InternetGameChessgames(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.computer = False

    def get_description(self):
        return 'ChessGames.com -- %s' % _('Download link')

    def get_test_links(self):
        return [('http://www.chessgames.com/perl/chessgame?gid=1075462&comp=1', True),          # With computer analysis
                ('http://www.chessgames.com/perl/chessgame?gid=1075463', True),                 # Without computer analysis
                ('http://www.CHESSGAMES.com/perl/chessgame?gid=1075463&comp=1#test', True),     # Without computer analysis but requested in URL
                ('http://www.chessgames.com/perl/chessgame?gid=1234567890', False)]             # Not a game

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.chessgames.com', 'chessgames.com']:
            return False

        # Read the arguments
        args = urllib.parse.parse_qs(parsed.query)
        if 'gid' in args:
            gid = args['gid'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                self.computer = ('comp' in args) and (args['comp'][0] == '1')
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # First try with computer analysis
        url = 'http://www.chessgames.com/pgn/pychess.pgn?gid=' + self.id
        if self.computer:
            response = urlopen(url + '&comp=1')
            pgn = self.read_data(response)
            if 'NO SUCH GAME' in pgn:
                self.computer = False
            else:
                return pgn

        # Second try without computer analysis
        if not self.computer:
            response = urlopen(url)
            pgn = self.read_data(response)
            if 'NO SUCH GAME' in pgn:
                return None
            else:
                return pgn


# FicsGames.org
class InternetGameFicsgames(InternetGameInterface):
    def get_description(self):
        return 'FicsGames.org -- %s' % _('Download link')

    def get_test_links(self):
        return [('https://www.ficsgames.org/cgi-bin/show.cgi?ID=451813954;action=save', True),      # Normal game
                ('https://www.ficsgames.org/cgi-bin/show.cgi?ID=qwertz;action=save', True),         # Invalid identifier (not numeric)
                ('https://www.ficsgames.org/cgi-bin/show.cgi?ID=0#anchor', False),                  # Invalid identifier (null)
                ('https://www.ficsgames.org/about.html', False)]                                    # Not a game

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.ficsgames.org', 'ficsgames.org'] or not 'show' in parsed.path.lower():
            return False

        # Read the arguments
        args = urllib.parse.parse_qs(parsed.query)
        if 'ID' in args:
            gid = args['ID'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        url = 'http://ficsgames.org/cgi-bin/show.cgi?ID=%s;action=save' % self.id
        response = urlopen(url)
        pgn = self.read_data(response)
        if 'not found in GGbID' in pgn:
            return None
        else:
            return pgn


# ChessTempo.com
class InternetGameChesstempo(InternetGameInterface):
    def get_description(self):
        return 'ChessTempo.com -- %s' % _('Download link')

    def get_test_links(self):
        return [('https://chesstempo.com/gamedb/game/2046457', True),               # Game
                ('https://chesstempo.com/gamedb/game/2046457/foo/bar/123', True),   # Game with additional path
                ('https://www.chesstempo.com/gamedb/game/2046457?p=0#tag', True),   # Game with additional parameters
                ('http://chesstempo.com', False)]                                   # Not a game

    def assign_game(self, url):
        # Parse the provided URL to retrieve the ID
        rxp = re.compile('^https?:\/\/(\S+\.)?chesstempo\.com\/gamedb\/game\/(\d+)\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is None:
            return False

        # Extract the identifier
        gid = str(m.group(2))
        if gid.isdigit() and gid != '0':
            self.id = gid
            return True
        else:
            return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        url = 'http://chesstempo.com/requests/download_game_pgn.php?gameids=%s' % self.id
        req = Request(url, headers = { 'User-Agent': self.userAgent })  # Else a random game is retrieved
        response = urlopen(req)
        pgn = self.read_data(response)
        if len(pgn) <= 128:
            return None
        else:
            return pgn


# Chess24.com
class InternetGameChess24(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.use_an = True  # True to rebuild a readable PGN

    def get_description(self):
        return 'Chess24.com -- %s' % _('HTML parsing')

    def get_test_links(self):
        return [('https://chess24.com/en/game/DQhOOrJaQKS31LOiOmrqPg#anchor', True)]    # Game with anchor

    def assign_game(self, url):
        # Parse the provided URL to retrieve the ID
        rxp = re.compile('^https?:\/\/chess24\.com\/[a-z]+\/(analysis|game|download-game)\/([a-z0-9\-_]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is None:
            return False

        # Extract the identifier
        gid = str(m.group(2))
        if len(gid) == 22:
            self.id = gid
            return True
        else:
            return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download the page
        url = 'https://chess24.com/en/game/%s' % self.id
        req = Request(url, headers = { 'User-Agent': self.userAgent })  # Else HTTP 403 Forbidden
        response = urlopen(req)
        pgn = self.read_data(response)

        # Extract the JSON of the game
        lines = pgn.split("\n")
        for line in lines:
            line = line.strip()
            pos1 = line.find('.initGameSession({')
            pos2 = line.find('});')
            if -1 in [pos1, pos2]:
                continue

            # Read the game from JSON
            bourne = json.loads(line[pos1+17:pos2+1])
            game = self.json_field(bourne, 'chessGame')
            moves = self.json_field(game, 'moves')
            if None in [game, moves]:
                continue

            # Build the header of the PGN file
            result = self.json_field(game, 'meta/Result')
            pgn = '[Event "%s"]\n[Site "%s"]\n[Date "%s"]\n[Round "%s"]\n[White "%s"]\n[WhiteElo "%s"]\n[Black "%s"]\n[BlackElo "%s"]\n[Result "%s"]\n' % (
                        self.json_field(game, 'meta/Event'),
                        self.json_field(game, 'meta/Site'),
                        self.json_field(game, 'meta/Date'),
                        self.json_field(game, 'meta/Round'),
                        self.json_field(game, 'meta/White/Name'),
                        self.json_field(game, 'meta/White/Elo'),
                        self.json_field(game, 'meta/Black/Name'),
                        self.json_field(game, 'meta/Black/Elo'),
                        result)

            # Build the PGN
            board = LBoard(variant=FISCHERRANDOMCHESS)
            head_complete = False
            for move in moves:
                # Info from the knot
                kid = self.json_field(move, 'knotId')
                if kid is None:
                    break
                kmove = self.json_field(move, 'move')

                # FEN initialization
                if kid == 0:
                    kfen = self.json_field(move, 'fen')
                    if kfen is None:
                        break
                    kfen = kfen.replace('\/', '/')
                    try:
                        board.applyFen(kfen)
                    except:
                        return None
                    pgn += '[Variant "Fischerandom"]\n[SetUp "1"]\n[FEN "%s"]\n\n{ %s }\n' % (kfen, url)
                    head_complete = True
                else:
                    if not head_complete:
                        return None

                    # Execution of the move
                    if kmove is None:
                        break
                    try:
                        if self.use_an:
                            kmove = parseAny(board, kmove)
                            pgn += toSAN(board, kmove) + ' '
                            board.applyMove(kmove)
                        else:
                            pgn += kmove + ' '
                    except:
                        return None

            # Final result
            pgn += result
            return pgn
        return None


# 365chess.com
class InternetGame365chess(InternetGameInterface):
    def get_description(self):
        return '365chess.com -- %s' % _('HTML parsing')

    def get_test_links(self):
        return [('https://www.365chess.com/view_game.php?g=4187437#anchor', True),      # Game 1/2-1/2 for special chars
                ('https://www.365chess.com/view_game.php?g=1234567890', False)]         # Not a game

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.365chess.com', '365chess.com'] or not 'view_game' in parsed.path.lower():
            return False

        # Read the arguments
        args = urllib.parse.parse_qs(parsed.query)
        if 'g' in args:
            gid = args['g'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        url = 'https://www.365chess.com/view_game.php?g=%s' % self.id
        response = urlopen(url)
        pgn = self.read_data(response)

        # Played moves
        game = {}
        pos1 = pgn.find(".ApplyPgnMoveText('")
        pos2 = pgn.find("')", pos1)
        if not -1 in [pos1, pos2]:
            game['_pgn'] = pgn[pos1+19:pos2]

        # Header
        lines = pgn.split("\n")
        for line in lines:
            line = line.strip()

            if line.startswith('<tr><td><h1>') and line.endswith('</h1></td></tr>'):
                rxp = re.compile('^([\w\-\s]+) \(([0-9]+)\) vs\. ([\w\-\s]+) \(([0-9]+)\)$', re.IGNORECASE)
                m = rxp.match(line[12:-15])
                if m is None:
                    game['White'] = _('Unknown')
                    game['Black'] = _('Unknown')
                else:
                    game['White'] = str(m.group(1))
                    game['WhiteElo'] = str(m.group(2))
                    game['Black'] = str(m.group(3))
                    game['BlackElo'] = str(m.group(4))
                continue

            if line.startswith('<tr><td><h2>') and line.endswith('</h2></td></tr>'):
                list = line[12:-15].split(' &middot; ')
                game['Event'] = list[0]
                game['Opening'] = list[1]
                game['Result'] = list[2].replace('&frac12;', '1/2')
                continue

        # Rebuild the PGN game
        pgn = ''
        for e in game:
            if e[:1] != '_':
                pgn += '[%s "%s"]\n' % (e, game[e])
        pgn += '\n%s' % game['_pgn']
        return pgn


# ChessPastebin.com
class InternetGameChesspastebin(InternetGameInterface):
    def get_description(self):
        return 'ChessPastebin.com -- %s' % _('HTML parsing')

    def get_test_links(self):
        return [('https://www.chesspastebin.com/2018/12/29/anonymous-anonymous-by-george-2/', True),    # Game
                ('https://www.chesspastebin.com', False)]                                               # Homepage

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.chesspastebin.com', 'chesspastebin.com']:
            return False

        # Any page is valid
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        response = urlopen(self.id)
        pgn = self.read_data(response)

        # Definition of the parser
        class chesspastebinparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.last_tag = None
                self.pgn = None

            def handle_starttag(self, tag, attrs):
                self.last_tag = tag.lower()

            def handle_data(self, data):
                if self.pgn is None and self.last_tag == 'div':
                    if '[Event "' in data:
                        self.pgn = data

        # Read the PGN
        parser = chesspastebinparser()
        parser.feed(pgn)
        return parser.pgn


# ChessBomb.com
class InternetGameChessbomb(InternetGameInterface):
    def get_description(self):
        return 'ChessBomb.com -- %s' % _('HTML parsing')

    def get_test_links(self):
        return [('https://www.chessbomb.com/arena/2019-katowice-chess-festival-im/04-Kubicka_Anna-Sliwicka_Alicja', True),  # Game
                ('https://www.chessbomb.com/arena/2019-bangkok-chess-open', False)]                                         # Not a game (arena)

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.chessbomb.com', 'chessbomb.com']:
            return False

        # Any page is valid
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        req = Request(self.id, headers = { 'User-Agent': self.userAgent })  # Else HTTP 403 Forbidden
        response = urlopen(req)
        pgn = self.read_data(response)

        # Definition of the parser
        class chessbombparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.last_tag = None
                self.json = None

            def handle_starttag(self, tag, attrs):
                self.last_tag = tag.lower()

            def handle_data(self, data):
                if self.json is None and self.last_tag == 'script':
                    pos1 = data.find('cbConfigData')
                    if pos1 == -1:
                        return
                    pos1 = data.find('"', pos1)
                    pos2 = data.find('"', pos1+1)
                    if not -1 in [pos1, pos2]:
                        try:
                            self.json = base64.b64decode(data[pos1+1:pos2]).decode().strip()
                            self.json = json.loads(self.json)
                        except:
                            self.json = None
                            return

        # Get the JSON
        parser = chessbombparser()
        parser.feed(pgn)
        if parser.json is None:
            return None

        # Interpret the JSON
        header = self.json_field(parser.json, 'gameData/game')
        room = self.json_field(parser.json, 'gameData/room')
        moves = self.json_field(parser.json, 'gameData/moves')
        if None in [header, room, moves]:
            return None

        game = {}
        game['Event'] = self.json_field(room, 'name')
        game['Site'] = self.json_field(room, 'officialUrl')
        game['Date'] = self.json_field(header, 'startAt')[:10]
        game['Round'] = self.json_field(header, 'roundSlug')
        game['White'] = self.json_field(header, 'white/name')
        game['WhiteElo'] = self.json_field(header, 'white/elo')
        game['Black'] = self.json_field(header, 'black/name')
        game['BlackElo'] = self.json_field(header, 'black/elo')
        game['Result'] = self.json_field(header, 'result')

        game['_pgn'] = ''
        for move in moves:
            move = self.json_field(move, 'cbn')
            pos1 = move.find('_')
            if pos1 == -1:
                break
            game['_pgn'] += move[pos1+1:] + ' '

        # Rebuild the PGN game
        if len(game['_pgn']) == 0:
            return None
        pgn = ''
        for e in game:
            if e[:1] != '_':
                pgn += '[%s "%s"]\n' % (e, game[e])
        pgn += '\n%s%s' % (game['_pgn'], game['Result'])
        return pgn


# Generic
class InternetGameGeneric(InternetGameInterface):
    def get_description(self):
        return 'Generic -- %s' % _('Various techniques')

    def get_test_links(self):
        return []

    def assign_game(self, url):
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        response = urlopen(self.id)
        mime = response.info().get_content_type().lower()
        if mime != 'application/x-chess-pgn':
            return None
        else:
            return self.read_data(response)


# Interface
chess_providers = [InternetGameLichess(),
                   InternetGameChessgames(),
                   InternetGameFicsgames(),
                   InternetGameChesstempo(),
                   InternetGameChess24(),
                   InternetGame365chess(),
                   InternetGameChesspastebin(),
                   InternetGameChessbomb(),
                   InternetGameGeneric()]

# Get the list of chess providers
def get_internet_game_providers():
    list = [cp.get_description() for cp in chess_providers]
    list.sort()
    return list

# Retrieve a game from a URL
def get_internet_game_as_pgn(url):
    # Check the format
    if url is None:
        return None
    p = urlparse(url.strip())
    if '' in [p.scheme, p.netloc, p.path]:
        return 0

    # Download a game for each provider
    for prov in chess_providers:
        if prov.assign_game(url):
            try:
                pgn = prov.download_game()
            except:
                pgn = None
            if pgn is None:
                continue

            # Verify that it starts with the correct magic character (ex.: "<" denotes an HTML content, "[" a chess game, etc...)
            pgn = pgn.strip()
            if not pgn.startswith('['):
                 return None

            # Extract the first game
            pos = pgn.find("\n\n[")
            if pos != -1:
                pgn = pgn[:pos]

            # Return the PGN with the local crlf
            return pgn.replace("\n", os.linesep)
    return None


# print(get_internet_game_as_pgn(''))
