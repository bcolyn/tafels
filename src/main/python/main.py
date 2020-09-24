from time import time
from enum import Enum, auto
from pathlib import Path
from random import shuffle
from typing import Iterable, List, Dict
from appdirs import user_state_dir

from PySide2.QtCore import Slot, Qt, QTimer
from PySide2.QtMultimedia import QSound
from PySide2.QtWidgets import QMainWindow, QApplication, QDesktopWidget, QPushButton, QListWidgetItem, QMessageBox

from generated.main_ui import Ui_MainWindow
from tables import Card, CardStatsLoader, CardStats, SelectionsLoader, Operation

TEST_SIZE = 20
TEST_DURATION_MSEC = 1000 * 60 * 2


class GameState(Enum):
    SETUP = auto()
    PRACTICE = auto()
    TESTING = auto()


class TafelsMainWindow(QMainWindow, Ui_MainWindow):
    test_timed_out: bool
    card_stats: CardStats
    cards_todo: List[Card]
    state: GameState
    test_timer: QTimer
    question_start_time: float
    test_answers: Dict[Card, int]

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.state = GameState.SETUP
        self.hook_events()
        self.enable_controls()
        self.question.setAlignment(Qt.AlignRight)
        self.sound_ok = QSound(":/sound/sound/ok.wav")
        self.sound_error = QSound(":/sound/sound/error.wav")
        self.test_timed_out = False
        self.card_stats = CardStatsLoader.load(self.get_stats_file())
        self.apply_selections(SelectionsLoader.load(self.get_selections_file()))
        print(self.card_stats)

    def hook_events(self):
        for pb in self.numpad_controls():
            pb.clicked.connect(self.numpad_click)
        self.pb_clear.clicked.connect(self.clear_answer)
        self.pb_submit.clicked.connect(self.check_answer)
        self.pb_stop.clicked.connect(self.stop_all)
        self.pb_test.clicked.connect(self.start_test)
        self.pb_practice.clicked.connect(self.start_practice)
        self.answer.returnPressed.connect(self.check_answer)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def numpad_controls(self) -> Iterable[QPushButton]:
        return [self.pushButton_1, self.pushButton_2, self.pushButton_3, self.pushButton_4, self.pushButton_5,
                self.pushButton_6, self.pushButton_7, self.pushButton_8, self.pushButton_9, self.pushButton_0]

    def enable_controls(self):
        for pb in self.numpad_controls():
            pb.setEnabled(self.is_running())
        self.pb_clear.setEnabled(self.is_running())
        self.pb_submit.setEnabled(self.is_running())
        self.answer.setEnabled(self.is_running())
        self.pb_stop.setEnabled(self.is_running())
        self.pb_practice.setEnabled(self.state == GameState.SETUP)
        self.pb_test.setEnabled(self.state == GameState.SETUP)
        self.lst_selection.setEnabled(self.state == GameState.SETUP)

    def is_running(self):
        return self.state == GameState.TESTING or self.state == GameState.PRACTICE

    def get_selection(self) -> Iterable[int]:
        selection = []
        for i in range(0, self.lst_selection.count()):
            item: QListWidgetItem = self.lst_selection.item(i)
            if item.checkState() == Qt.Checked:
                selection.append(int(item.text()))
        return selection

    def apply_selections(self, selection: Iterable[int]):
        for i in range(0, self.lst_selection.count()):
            item: QListWidgetItem = self.lst_selection.item(i)
            if int(item.text()) in selection:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

    @Slot()
    def clear_answer(self):
        self.answer.setText("")

    @Slot()
    def numpad_click(self):
        sender = self.sender()
        self.answer.setText(self.answer.text() + sender.text())

    @Slot()
    def start_test(self):
        SelectionsLoader.store(self.get_selections_file(), self.get_selection())
        self.state = GameState.TESTING
        self.test_timed_out = False
        self.enable_controls()
        self.cards_todo = list(self.card_stats.select_for_test(TEST_SIZE, self.get_selection()))
        shuffle(self.cards_todo)
        self.show_question_or_feedback()
        self.feedback.setText("")
        self.test_answers = {}

        self.test_timer = QTimer(self)
        self.test_timer.timeout.connect(self.test_timeout)
        self.test_timer.setInterval(TEST_DURATION_MSEC)
        self.test_timer.setSingleShot(True)
        self.test_timer.start()
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(len(self.cards_todo))

    @Slot()
    def start_practice(self):
        print("starting practice")
        SelectionsLoader.store(self.get_selections_file(), self.get_selection())
        self.state = GameState.PRACTICE
        self.test_timed_out = False
        self.enable_controls()
        self.cards_todo = list(Card.generate(self.get_selection()))
        shuffle(self.cards_todo)
        self.show_question_or_feedback()
        self.feedback.setText("")
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(len(self.cards_todo))

    @Slot()
    def stop_all(self):
        print("stopping")
        self.state = GameState.SETUP
        self.enable_controls()
        self.progressBar.setValue(0)
        if self.state == GameState.TESTING:
            self.test_timer.stop()
            del self.test_timer
            self.test_timed_out = False

    @Slot()
    def test_timeout(self):
        self.test_timed_out = True

    def show_test_results(self):
        print(self.test_answers)
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setText(self.generate_report())
        msgBox.exec()

    def current_card(self):
        return self.cards_todo[-1]

    @Slot()
    def check_answer(self):
        try:
            answer = int(self.answer.text())
        except ValueError:
            self.clear_answer()
            return
        stop_time = time()
        if answer == self.current_card().answer():
            self.correct_answer(stop_time)
        else:
            self.wrong_answer()

    def correct_answer(self, stop_time):
        time_delta = stop_time - self.question_start_time
        print(" %s took %f" % (self.current_card(), time_delta))
        self.card_stats.add_correct_answer(self.current_card(), time_delta)
        self.save_stats()
        if self.state == GameState.PRACTICE:
            self.sound_ok.play()
            self.next_card()
        elif self.state == GameState.TESTING:
            self.test_answers[self.current_card()] = int(self.answer.text())
            self.next_card()

    def next_card(self):
        self.cards_todo.pop()
        self.progressBar.setValue(1 + self.progressBar.maximum() - len(self.cards_todo))
        self.show_question_or_feedback()

    def wrong_answer(self):
        self.card_stats.add_error(self.current_card())
        print(" %s wrong answer %s" % (str(self.current_card()), self.answer.text()))
        self.save_stats()
        if self.state == GameState.PRACTICE:
            self.sound_error.play()
            self.style_feedback()
            self.feedback.setText(" " + self.answer.text() + " ")
            self.answer.setText("")
        elif self.state == GameState.TESTING:
            self.test_answers[self.current_card()] = int(self.answer.text())
            self.next_card()

    def style_feedback(self, color=Qt.red, strikeout=True):
        font = self.question.font()
        font.setStrikeOut(strikeout)
        self.feedback.setFont(font)
        palette = self.feedback.palette()
        palette.setColor(self.feedback.foregroundRole(), color)
        self.feedback.setPalette(palette)

    def show_question_or_feedback(self):
        if len(self.cards_todo) == 0 or self.test_timed_out:
            if self.state == GameState.PRACTICE:
                self.style_feedback(Qt.green, False)
                self.feedback.setText("Klaar!")
            else:
                self.show_test_results()
            self.question.setText("")
            self.answer.setText("")
            self.stop_all()
        else:
            self.question.setText(str(self.current_card()) + " =")
            self.answer.setText("")
            self.answer.setFocus()
            self.feedback.setText("")
            self.question_start_time = time()

    def generate_report(self) -> str:
        correct_answers = 0
        for (card, my_answer) in self.test_answers.items():
            correct_answer = card.answer()
            if my_answer == correct_answer:
                correct_answers += 1
        report = "<h1>"
        report += "Resultaat toets = %d / %d" % (correct_answers, TEST_SIZE)
        report += "<img src='%s'></img>" % self.get_report_icon(correct_answers / TEST_SIZE)
        report += " </h1>\n<br>"
        for (card, my_answer) in self.test_answers.items():
            correct_answer = card.answer()
            if my_answer == correct_answer:
                report += "<font size='6' color='green'>%s = %d</font><br>\n" % (str(card), my_answer)
            else:
                report += "<font size='6' color='red'>%s&nbsp;=&nbsp;<s>%s</s>&nbsp;</font>" \
                          "<font size='6'>%d</font><br>\n" % (str(card), str(my_answer), correct_answer)
        return report

    @staticmethod
    def get_report_icon(score: float) -> str:
        if score == 1.0:
            return ":/icons/icons/emoji/1F3C6.svg"  # prize
        elif score >= 0.9:
            return ":/icons/icons/emoji/1F600.svg"  # :D
        elif score >= 0.8:
            return ":/icons/icons/emoji/1F642.svg"  # :-)
        elif score >= 0.6:
            return ":/icons/icons/emoji/1F610.svg"  # :-|
        else:
            return ":/icons/icons/emoji/1F61F.svg"  # :-(

    @staticmethod
    def get_stats_file() -> Path:
        dir = user_state_dir("tafels")
        return Path(dir, "cardstate.dat")

    @staticmethod
    def get_selections_file() -> Path:
        dir = user_state_dir("tafels")
        return Path(dir, "selections.dat")

    def save_stats(self):
        CardStatsLoader.store(self.get_stats_file(), self.card_stats)


if __name__ == '__main__':
    app = QApplication([])
    window = TafelsMainWindow()
    window.resize(100, 100)  # pack it
    window.show()
    window.center()
    app.exec_()
