import random
from random import uniform
from unittest import TestCase

from tables import Operation, Card, CardStats, CARD_RANGE


class TestOperation(TestCase):
    def test_to_str(self):
        self.assertEqual(str(Operation.MUL), "x")
        self.assertEqual(str(Operation.DIV), ":")

    def test_func(self):
        self.assertEqual(Operation.MUL.func(4, 2), 8)
        self.assertEqual(Operation.DIV.func(4, 2), 2)


class TestCard(TestCase):
    def test_to_str(self):
        card = Card(2, Operation.MUL, 4)
        self.assertEqual(str(card), "2 x 4")

    def test_value(self):
        card = Card(2, Operation.MUL, 4)
        self.assertEqual(card.answer(), 8)
        card = Card(20, Operation.DIV, 4)
        self.assertEqual(card.answer(), 5)

    def test_generator(self):
        table_of_2 = list(Card.generate([2]))
        self.assertEqual(table_of_2[0], Card(1, Operation.MUL, 2))
        self.assertEqual(table_of_2[4], Card(5, Operation.MUL, 2))
        self.assertEqual(table_of_2[14], Card(10, Operation.DIV, 2))
        self.assertEqual(table_of_2[19], Card(20, Operation.DIV, 2))

        all_tables = list(Card.generate(range(1, 11)))
        self.assertEqual(len(all_tables), 200)
        self.assertEqual(all_tables[0], Card(1, Operation.MUL, 1))
        self.assertEqual(all_tables[42], Card(5, Operation.MUL, 3))
        self.assertEqual(all_tables[55], Card(6, Operation.MUL, 6))
        self.assertEqual(all_tables[100], Card(1, Operation.DIV, 1))
        self.assertEqual(all_tables[132], Card(12, Operation.DIV, 3))
        self.assertEqual(all_tables[199], Card(100, Operation.DIV, 10))


def fill_stats(selections):
    stats = CardStats()
    cards = list(Card.generate(selections))
    for card in cards:
        num_times = int(uniform(1, 10))
        num_err = int(uniform(0, 2))

        for i in range(0, num_times):
            time = abs(random.gauss(3.0, 2.0))
            stats.add_correct_answer(card, time)
        for i in range(0, num_err):
            stats.add_error(card)
    return stats


class TestCardStats(TestCase):
    def test_add_error(self):
        stats = CardStats()
        stats.add_error(Card(2, Operation.MUL, 2))
        c = Card(2, Operation.MUL, 2)
        self.assertEqual(stats.num_errors(c), 1)
        stats.add_error(Card(2, Operation.MUL, 2))
        c = Card(2, Operation.MUL, 2)
        self.assertEqual(stats.num_errors(c), 2)
        self.assertEqual(stats.error_rate(c), 1.0)
        stats.add_correct_answer(c, 5.0)
        self.assertAlmostEqual(stats.error_rate(c), 2.0 / 3.0)

    def test_add_timed_result(self):
        stats = CardStats()
        card = Card(10, Operation.DIV, 10)
        stats.add_correct_answer(card, 4.0)
        stats.add_correct_answer(card, 8.0)
        self.assertEqual(stats.sum_time(card), 12.0)
        self.assertEqual(stats.num_correct(card), 2)
        self.assertEqual(stats.answer_time_avg(card), 6.0)

    def test_median_answer_time_avg(self):
        stats = CardStats()
        for c in Card.generate([1], [Operation.DIV]):
            if c.left % 2 == 0:
                stats.add_correct_answer(c, 4.0)
            else:
                stats.add_correct_answer(c, 8.0)
        stats.add_correct_answer(Card(10, Operation.DIV, 1), 4.0)
        median, stddev = stats.median_answer_time_avg(Card.generate([1], [Operation.DIV]))
        self.assertEqual(median, 6.0)
        self.assertAlmostEqual(stddev, 2.1081851067789197)

    def test_median_error_rate(self):
        stats = CardStats()
        for c in Card.generate([1], [Operation.DIV]):
            stats.add_correct_answer(c, 4.0)
            stats.add_correct_answer(c, 8.0)
            stats.add_error(c)
        stats.add_error(Card(1, Operation.DIV, 1))
        median, stddev = stats.median_error_rate(Card.generate([1], [Operation.DIV]))
        self.assertAlmostEqual(median, 0.3333333333333333)
        self.assertAlmostEqual(stddev, 0.052704627669472995)

    def test_select_for_test_blank(self):
        stats = CardStats()
        test = stats.select_for_test(20, [1])
        self.assertEqual(len(set(test)), 20)
        print(test)

        test = stats.select_for_test(20, CARD_RANGE)
        self.assertEqual(len(set(test)), 20)
        print(test)

    def test_select_for_test_filled(self):
        stats = fill_stats([1])
        test = stats.select_for_test(20, [1])
        self.assertEqual(len(set(test)), 20)
        print(test)

    def test_serialization(self):
        stats = fill_stats(CARD_RANGE)
        import pickle
        ser = pickle.dumps(stats)
        loaded = pickle.loads(ser)
        self.assertIsNot(stats, loaded)
        self.assertEqual(stats._sum_time, loaded._sum_time)
        self.assertEqual(stats._num_errors, loaded._num_errors)
        self.assertEqual(stats._num_correct, loaded._num_correct)
        self.assertEqual(stats._serialVersion, loaded._serialVersion)
