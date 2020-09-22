from __future__ import annotations

from enum import Enum, unique
from pathlib import Path
from random import uniform
from statistics import median, stdev
from typing import Iterable, Dict, List

CARD_RANGE = range(1, 11)


@unique
class Operation(Enum):
    label: str

    MUL = "x"
    DIV = ":"

    def func(self, left, right):
        if self == Operation.MUL:
            return left * right
        else:
            return left / right

    def __init__(self, label):
        self.label = label

    def __str__(self):
        return self.label


class Card:
    right: int
    op: Operation
    left: int

    def __init__(self, left: int, op: Operation, right: int):
        self.left = left
        self.op = op
        self.right = right

    def answer(self) -> int:
        return self.op.func(self.left, self.right)

    def __str__(self) -> str:
        return " ".join([str(self.left), str(self.op), str(self.right)])

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, o: Card) -> bool:
        return self.left == o.left \
               and self.op == o.op \
               and self.right == o.right

    def __hash__(self) -> int:
        return hash((self.left, self.op, self.right))

    @staticmethod
    def generate(selected_tables: Iterable[int], operations=Operation) -> Iterable[Card]:
        for op in operations:
            for left in CARD_RANGE:
                for right in selected_tables:
                    if op == Operation.MUL:
                        yield Card(left, op, right)
                    else:
                        yield Card(left * right, op, right)


class CardStats:
    _serialVersion: int
    _sum_time: Dict[Card, float]
    _num_errors: Dict[Card, int]
    _num_correct: Dict[Card, int]

    def __init__(self):
        self._num_correct = {}
        self._num_errors = {}
        self._sum_time = {}
        self._serialVersion = 1

    def num_correct(self, card: Card) -> int:
        if card in self._num_correct:
            return self._num_correct[card]
        else:
            return 0

    def num_errors(self, card: Card) -> int:
        if card in self._num_errors:
            return self._num_errors[card]
        else:
            return 0

    def sum_time(self, card: Card) -> float:
        if card in self._sum_time:
            return self._sum_time[card]
        else:
            return 0

    def add_correct_answer(self, card: Card, time: float) -> None:
        if card in self._num_correct:
            self._sum_time[card] += time
            self._num_correct[card] += 1
        else:
            self._sum_time[card] = time
            self._num_correct[card] = 1

    def add_error(self, card: Card) -> None:
        if card in self._num_errors:
            self._num_errors[card] += 1
        else:
            self._num_errors[card] = 1

    def answer_time_avg(self, card: Card) -> float:
        if self.num_correct(card) == 0:
            return 0
        return self.sum_time(card) / self.num_correct(card)

    def error_rate(self, card: Card) -> float:
        if self.num_correct(card) == 0 and self.num_errors(card) == 0:
            return 0
        return float(self.num_errors(card)) / float(self.num_errors(card) + self.num_correct(card))

    def median_answer_time_avg(self, selection: Iterable[Card]) -> (float, float):
        answer_times = list(map(lambda card: self.answer_time_avg(card), selection))
        return median(answer_times), stdev(answer_times)

    def median_error_rate(self, selection: Iterable[Card]) -> (float, float):
        error_nrs = list(map(lambda card: self.error_rate(card), selection))
        return median(error_nrs), stdev(error_nrs)

    def get_error_score(self, card: Card, med_err: float, sigma_err: float) -> int:
        card_err = self.error_rate(card)
        if card_err == 0 or card_err > med_err + sigma_err:
            return 1
        if card_err < med_err - sigma_err:
            return -1
        else:
            return 0

    def get_timed_score(self, card: Card, med_time: float, sigma_time: float) -> int:
        card_time = self.sum_time(card)
        if card_time == 0 or card_time > med_time + sigma_time:
            return 1
        elif card_time < med_time - sigma_time:
            return -1
        else:
            return 0

    def get_weight(self, card: Card, med_err: float, sigma_err: float, med_time: float, sigma_time: float) -> int:
        sum_score = self.get_timed_score(card, med_time, sigma_time) + self.get_error_score(card, med_err, sigma_err)
        return 1 + (2 + sum_score) ^ 2

    def select_for_test(self, num_select: int, selected_tables: Iterable[int], operations=Operation) -> List[Card]:
        selection = []
        available = list(Card.generate(selected_tables, operations))
        (med_err, sigma_err) = self.median_error_rate(available)
        (med_time, sigma_time) = self.median_answer_time_avg(available)
        card_weights: Dict[Card, float] = dict(
            map(lambda c: (c, self.get_weight(c, med_err, sigma_err, med_time, sigma_time)), available))

        while len(selection) < num_select:
            sum_weights = 0.0
            for card in card_weights.keys():
                sum_weights += card_weights[card]
            weight_pointer = uniform(0, sum_weights)
            it = iter(card_weights.keys())
            while weight_pointer >= 0:
                card = next(it)
                weight_pointer -= card_weights[card]
            selection.append(card)
            del card_weights[card]

        return selection

    def __repr__(self) -> str:
        return repr(self.__dict__)


class CardStatsLoader:

    @staticmethod
    def load(file_name: Path) -> CardStats:
        if file_name.exists():
            import pickle
            with open(str(file_name), 'rb') as handle:
                return pickle.load(handle)
        else:
            return CardStats()

    @staticmethod
    def store(file_name: Path, stats: CardStats) -> None:
        import pickle
        file_name.parent.mkdir(parents=True, exist_ok=True)
        with open(str(file_name), "wb+") as handle:
            pickle.dump(stats, handle, protocol=pickle.HIGHEST_PROTOCOL)


class SelectionsLoader:
    @staticmethod
    def load(file_name: Path) -> List[int]:
        if file_name.exists():
            import pickle
            with open(str(file_name), 'rb') as handle:
                return pickle.load(handle)
        else:
            return list(CARD_RANGE)

    @staticmethod
    def store(file_name: Path, selections: Iterable[int]) -> None:
        import pickle
        file_name.parent.mkdir(parents=True, exist_ok=True)
        with open(str(file_name), "wb+") as handle:
            pickle.dump(selections, handle, protocol=pickle.HIGHEST_PROTOCOL)
