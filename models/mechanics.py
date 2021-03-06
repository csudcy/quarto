from models.parts import Board, Piece


class GameStateError(Exception):
    pass


class Game:
    def __init__(self):
        self.player_a = None
        self.player_b = None
        self.events = []

        self.remaining_pieces = []
        self.board = None
        self.next_piece = None
        self.__init_game()
        self.winner = None

    def join_game(self, player):
        if self.player_a is None:
            self.player_a = player
        elif self.player_b is None:
            if self.player_a == player:
                raise GameStateError('Player already in game')
            self.player_b = player
        else:
            raise GameStateError('Game already full')

    def to_dict(self):
        return {
            'player_a': self.player_a.to_dict() if self.player_a else None,
            'player_b': self.player_b.to_dict() if self.player_b else None,
            'winner': self.winner.to_dict() if self.winner else None,
            'events': [
                event.to_dict() for event in self.events
            ]
        }

    @classmethod
    def from_dict(cls, in_dict):
        game = cls()
        if in_dict['player_a'] is not None:
            game.player_a = Player.from_dict(in_dict['player_a'])
        if in_dict['player_b'] is not None:
            game.player_b = Player.from_dict(in_dict['player_b'])
        for event_dict in in_dict['events']:
            event = Event.from_dict(event_dict)
            game.apply_event(event)
        return game

    @property
    def turn(self):
        return len(self.events)

    def __init_game(self):
        self.board = Board()
        for value in range(1 << 4):
            self.remaining_pieces.append(
                Piece(value)
            )

    def apply_event(self, event):
        # ok, the game goes through two different types of moves
        # and in rotation around the players... sooo

        # move 0, 4, 8 & so on is player 1 picking a piece for player 2
        # move 1, 5, 9, etc player 2 chosing where to place a piece
        # 2, 6, 10 player 2 picking a piece for player 1
        # 3, 7, 11 player 1 placing a piece.
        # so:

        if self.winner is not None:
            raise GameStateError("Player has already won")

        if self.player_a is None or self.player_b is None:
            raise GameStateError("Missing players")

        if self.turn % 4 in (0, 3):
            if event.player != self.player_a:
                raise GameStateError("Illegal player")
        else:
            if event.player != self.player_b:
                raise GameStateError("Illegal player")

        event.move.validate(self)
        victory = event.move.apply(self)
        self.events.append(
            event
        )
        if victory:
            self.winner = event.player

    def check_win(self, x, y):
        # Check if we've just won a game, based on having added
        # a piece to position x, y
        for winning_sets in self.board.get_rows(x, y):
            pieces = []
            for _x, _y in winning_sets:
                last_piece = self.board.get(_x, _y)
                if last_piece is None:
                    break
                pieces.append(last_piece)
            if (
                len(pieces) == 4 and
                Piece.overlap(*pieces)
            ):
                return True
        return False


class Event:
    def __init__(self, player, move):
        self.player = player
        self.move = move

    def to_dict(self):
        return {
            'player': self.player.to_dict(),
            'move': self.move.to_dict()
        }

    @classmethod
    def from_dict(self, in_dict):
        return Event(
            Player.from_dict(in_dict['player']),
            Move.from_dict(in_dict['move'])
        )


class Player:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other_player):
        return self.name == other_player.name

    def to_dict(self):
        return {
            'name': self.name
        }

    @classmethod
    def from_dict(cls, in_dict):
        return cls(
            in_dict['name']
        )


class Move:
    def validate(self):
        raise NotImplemented()

    def apply(self):
        raise NotImplemented()

    @classmethod
    def from_dict(cls, in_dict):
        if in_dict['type'] == 'PickingMove':
            return PickingMove.from_dict(in_dict)
        elif in_dict['type'] == 'PlacementMove':
            return PlacementMove.from_dict(in_dict)
        else:
            raise GameStateError('Cannot determine the type of move')


class PickingMove(Move):
    def __init__(self, piece):
        self.piece = piece

    def to_dict(self):
        return {
            'type': 'PickingMove',
            'piece': self.piece.to_dict()
        }

    @classmethod
    def from_dict(cls, in_dict):
        return cls(
            Piece.from_dict(in_dict['piece'])
        )

    def validate(self, game):
        if game.turn % 2 == 1:
            raise GameStateError("Illegal move")
        if self.piece not in game.remaining_pieces:
            raise GameStateError("Illegal piece choice")
        return

    def apply(self, game):
        game.next_piece = self.piece
        game.remaining_pieces.remove(self.piece)


class PlacementMove(Move):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_dict(self):
        return {
            'type': 'PlacementMove',
            'x': self.x,
            'y': self.y,
        }

    @classmethod
    def from_dict(cls, in_dict):
        return cls(
            in_dict['x'],
            in_dict['y']
        )

    def validate(self, game):
        if game.turn % 2 == 0:
            raise GameStateError("Illegal move")
        if game.board.get(
            self.x,
            self.y,
        ) is not None:
            raise GameStateError("Illegal placement choice")
        return

    def apply(self, game):
        game.board.put(
            game.next_piece,
            self.x,
            self.y
        )
        game.next_piece = None
        return game.check_win(self.x, self.y)
