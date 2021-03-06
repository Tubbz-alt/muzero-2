import typing
from abc import ABC, abstractmethod

import numpy as np

from utils.game_utils import GameState
from utils.selfplay_utils import GameHistory
from utils import DotDict

from AlphaZero.implementations.DefaultAlphaZero import DefaultAlphaZero
from AlphaZero.AlphaMCTS import MCTS as AlphaZeroMCTS
from MuZero.implementations.DefaultMuZero import DefaultMuZero
from MuZero.implementations.BlindMuZero import BlindMuZero
from MuZero.MuMCTS import MuZeroMCTS


class Player(ABC):

    def __init__(self, game, arg_file: typing.Optional[str] = None, name: str = "", parametric: bool = False) -> None:
        self.game = game
        self.player_args = arg_file
        self.parametric = parametric
        self.histories = list()
        self.history = GameHistory()
        self.name = name

    def bind_history(self, history: GameHistory) -> None:
        self.history = history

    def refresh(self, hard_reset: bool = False) -> None:
        if hard_reset:
            self.histories = list()
            self.history.refresh()
        else:
            self.histories.append(self.history)
            self.history = GameHistory()

    def observe(self, state: GameState) -> None:
        self.history.capture(state, np.array([]), 0, 0)

    def clone(self):
        return self.__class__(self.game, self.player_args)

    @abstractmethod
    def act(self, state: GameState) -> int:
        """
        Method that should be implemented as an agent-specific action-selection method.
        :param state: GameState Data structure containing the specifics of the current environment state.
        :return: int Integer action to be performed in the environment.
        """


class DefaultAlphaZeroPlayer(Player):

    def __init__(self, game, arg_file: typing.Optional[str] = None, name: str = "") -> None:
        super().__init__(game, arg_file, name, parametric=True)
        if self.player_args is not None:
            self.args = DotDict.from_json(self.player_args)

            self.model = DefaultAlphaZero(self.game, self.args.net_args, self.args.architecture)
            self.search_engine = AlphaZeroMCTS(self.game, self.model, self.args.args)
            self.name = self.args.name

    def set_variables(self, model, search_engine, name):
        self.model = model
        self.search_engine = search_engine
        self.name = name

    def refresh(self, hard_reset: bool = False):
        super().refresh()
        self.search_engine.clear_tree()

    def act(self, state: GameState) -> int:
        pi, _ = self.search_engine.runMCTS(state, self.history, temp=0)
        return np.argmax(pi).item()


class DefaultMuZeroPlayer(Player):

    def __init__(self, game, arg_file: typing.Optional[str] = None, name: str = "") -> None:
        super().__init__(game, arg_file, name, parametric=True)
        if self.player_args is not None:
            self.args = DotDict.from_json(self.player_args)

            self.model = DefaultMuZero(self.game, self.args.net_args, self.args.architecture)
            self.search_engine = MuZeroMCTS(self.game, self.model, self.args.args)
            self.name = self.args.name

    def set_variables(self, model, search_engine, name):
        self.model = model
        self.search_engine = search_engine
        self.name = name

    def refresh(self, hard_reset: bool = False):
        super().refresh()
        self.search_engine.clear_tree()

    def observe(self, state: GameState) -> None:
        self.history.capture(state, np.array([]), 0, 0)

    def act(self, state: GameState) -> int:
        pi, _ = self.search_engine.runMCTS(state, self.history, temp=0)
        return np.argmax(pi).item()


class BlindMuZeroPlayer(Player):

    def __init__(self, game, nested_config: typing.Optional[DotDict] = None, name: str = "") -> None:
        super().__init__(game, nested_config.file, name, parametric=True)
        if self.player_args is not None:
            self.args = DotDict.from_json(self.player_args)

            self.model = BlindMuZero(self.game, self.args.net_args, self.args.architecture, nested_config.refresh_freq)
            self.model.bind(self.history.actions)

            self.search_engine = MuZeroMCTS(self.game, self.model, self.args.args)
            self.name = self.args.name

    def set_variables(self, model, search_engine, name):
        self.model = model
        self.search_engine = search_engine
        self.name = name

    def refresh(self, hard_reset: bool = False):
        super().refresh()
        self.search_engine.clear_tree()
        self.model.reset()
        self.model.bind(self.history.actions)

    def observe(self, state: GameState) -> None:
        self.history.capture(state, np.array([]), 0, 0)

    def act(self, state: GameState) -> int:
        pi, _ = self.search_engine.runMCTS(state, self.history, temp=0)
        return np.argmax(pi).item()


class RandomPlayer(Player):
    name: str = "Random"

    def act(self, state: GameState) -> int:
        mass_valid = self.game.getLegalMoves(state)
        return np.random.choice(len(mass_valid), p=mass_valid / np.sum(mass_valid))


class DeterministicPlayer(Player):
    name: str = "Deterministic"

    def act(self, state: GameState) -> int:
        mass_valid = self.game.getLegalMoves(state)
        indices = np.ravel(np.where(mass_valid == 1))
        return indices[0]


class ManualPlayer(Player):
    name: str = "Manual"

    def __init__(self, game, config: typing.Optional[str] = None) -> None:
        super().__init__(game, config)
        self.name = input("Input a player name: ")

    def act(self, state: GameState) -> int:
        mass_valid = self.game.getLegalMoves(state)
        indices = np.ravel(np.where(mass_valid == 1))

        move = None
        while move is None:
            print("Available actions:", indices)
            move_str = input("Input an integer indicating a move:")
            if move_str.isdigit() and int(move_str) in indices:
                move = int(move_str)

        return move

