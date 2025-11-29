import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from enum import Enum
import json
import random


class TestStatus(Enum):
    NOT_STARTED = "не начат"
    IN_PROGRESS = "выполняется"
    COMPLETED = "завершен"
    EVALUATED = "оценен"


class QuestionType(Enum):
    SINGLE_CHOICE = "один вариант"
    MULTIPLE_CHOICE = "несколько вариантов"
    TEXT_ANSWER = "текстовый ответ"


class Student:
    def __init__(self, student_id, full_name, group, email=""):
        self.student_id = student_id
        self.full_name = full_name
        self.group = group
        self.email = email
        self.test_attempts = []

    def add_attempt(self, attempt):
        self.test_attempts.append(attempt)

    def get_attempts_count(self):
        return len(self.test_attempts)

    def to_dict(self):
        return {
            'student_id': self.student_id,
            'full_name': self.full_name,
            'group': self.group,
            'email': self.email
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['student_id'], data['full_name'], data['group'], data['email'])


class Question:
    def __init__(self, question_id, text, question_type, options=None, correct_answers=None, max_points=1):
        self.question_id = question_id
        self.text = text
        self.question_type = question_type
        self.options = options or []
        self.correct_answers = correct_answers or []
        self.max_points = max_points
        self.is_active = True

    def toggle_active(self):
        self.is_active = not self.is_active

    def check_answer(self, user_answers):
        if self.question_type == QuestionType.SINGLE_CHOICE:
            return user_answers[0] in self.correct_answers if user_answers else False
        elif self.question_type == QuestionType.MULTIPLE_CHOICE:
            return set(user_answers) == set(self.correct_answers)
        else:
            return True  # Для текстовых ответов проверка вручную

    def to_dict(self):
        return {
            'question_id': self.question_id,
            'text': self.text,
            'question_type': self.question_type.name,
            'options': self.options,
            'correct_answers': self.correct_answers,
            'max_points': self.max_points,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data):
        question = cls(
            data['question_id'],
            data['text'],
            QuestionType[data['question_type']],
            data['options'],
            data['correct_answers'],
            data['max_points']
        )
        question.is_active = data['is_active']
        return question


class Test:
    def __init__(self, test_id, title, subject, time_limit=60):
        self.test_id = test_id
        self.title = title
        self.subject = subject
        self.time_limit = time_limit  # в минутах
        self.questions = []
        self.is_active = True
        self.passing_score = 60  # минимальный процент для зачета

    def add_question(self, question):
        self.questions.append(question)

    def remove_question(self, question_id):
        self.questions = [q for q in self.questions if q.question_id != question_id]

    def get_active_questions(self):
        return [q for q in self.questions if q.is_active]

    def get_max_score(self):
        return sum(q.max_points for q in self.get_active_questions())

    def toggle_active(self):
        self.is_active = not self.is_active

    def to_dict(self):
        return {
            'test_id': self.test_id,
            'title': self.title,
            'subject': self.subject,
            'time_limit': self.time_limit,
            'questions': [q.to_dict() for q in self.questions],
            'is_active': self.is_active,
            'passing_score': self.passing_score
        }

    @classmethod
    def from_dict(cls, data):
        test = cls(data['test_id'], data['title'], data['subject'], data['time_limit'])
        test.questions = [Question.from_dict(q_data) for q_data in data['questions']]
        test.is_active = data['is_active']
        test.passing_score = data.get('passing_score', 60)
        return test


class TestAttempt:
    def __init__(self, attempt_id, student, test):
        self.attempt_id = attempt_id
        self.student = student
        self.test = test
        self.start_time = datetime.now()
        self.end_time = None
        self.status = TestStatus.NOT_STARTED
        self.answers = {}  # question_id -> ответы студента
        self.scores = {}  # question_id -> набранные баллы
        self.final_score = 0
        self.percentage = 0
        self.is_passed = False

    def start_attempt(self):
        self.status = TestStatus.IN_PROGRESS
        self.start_time = datetime.now()

    def submit_answer(self, question_id, answers):
        self.answers[question_id] = answers

        # Автопроверка для вопросов с выбором
        question = next((q for q in self.test.questions if q.question_id == question_id), None)
        if question and question.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
            if question.check_answer(answers):
                self.scores[question_id] = question.max_points
            else:
                self.scores[question_id] = 0

    def finish_attempt(self):
        self.status = TestStatus.COMPLETED
        self.end_time = datetime.now()
        self.calculate_score()

    def evaluate_attempt(self, manual_scores=None):
        self.status = TestStatus.EVALUATED
        if manual_scores:
            self.scores.update(manual_scores)
        self.calculate_score()

    def calculate_score(self):
        total_score = sum(self.scores.values())
        max_score = self.test.get_max_score()
        self.final_score = total_score
        self.percentage = (total_score / max_score * 100) if max_score > 0 else 0
        self.is_passed = self.percentage >= self.test.passing_score

    def get_duration(self):
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() / 60  # в минутах
        return 0

    def to_dict(self):
        return {
            'attempt_id': self.attempt_id,
            'student_id': self.student.student_id,
            'test_id': self.test.test_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status.name,
            'answers': self.answers,
            'scores': self.scores,
            'final_score': self.final_score,
            'percentage': self.percentage,
            'is_passed': self.is_passed
        }


class TestingSystem:
    def __init__(self, system_name):
        self.system_name = system_name
        self.students = []
        self.tests = []
        self.attempts = []
        self.next_student_id = 1
        self.next_test_id = 1
        self.next_attempt_id = 1
        self.next_question_id = 1
        self.load_data()

    def add_student(self, full_name, group, email=""):
        student = Student(self.next_student_id, full_name, group, email)
        self.students.append(student)
        self.next_student_id += 1
        self.save_data()
        return student

    def find_student_by_id(self, student_id):
        for student in self.students:
            if student.student_id == student_id:
                return student
        return None

    def find_students_by_group(self, group):
        return [s for s in self.students if s.group == group]

    def add_test(self, title, subject, time_limit=60):
        test = Test(self.next_test_id, title, subject, time_limit)
        self.tests.append(test)
        self.next_test_id += 1
        self.save_data()
        return test

    def find_test_by_id(self, test_id):
        for test in self.tests:
            if test.test_id == test_id:
                return test
        return None

    def delete_test(self, test_id):
        test = self.find_test_by_id(test_id)
        if test:
            # Проверяем, есть ли попытки прохождения теста
            test_attempts = [a for a in self.attempts if a.test.test_id == test_id]
            if test_attempts:
                messagebox.showwarning(
                    "Нельзя удалить",
                    f"Тест используется в {len(test_attempts)} попытках"
                )
                return False

            self.tests.remove(test)
            self.save_data()
            return True
        return False

    def add_question_to_test(self, test_id, text, question_type, options=None, correct_answers=None, max_points=1):
        test = self.find_test_by_id(test_id)
        if test:
            question = Question(self.next_question_id, text, question_type, options, correct_answers, max_points)
            test.add_question(question)
            self.next_question_id += 1
            self.save_data()
            return question
        return None

    def delete_question(self, test_id, question_id):
        test = self.find_test_by_id(test_id)
        if test:
            test.remove_question(question_id)
            self.save_data()
            return True
        return False

    def create_attempt(self, student_id, test_id):
        student = self.find_student_by_id(student_id)
        test = self.find_test_by_id(test_id)

        if student and test:
            # Проверяем, не превышено ли максимальное количество попыток (например, 3)
            student_attempts = [a for a in self.attempts if
                                a.student.student_id == student_id and a.test.test_id == test_id]
            if len(student_attempts) >= 3:
                messagebox.showwarning("Превышено", "Максимум 3 попытки на тест")
                return None

            attempt = TestAttempt(self.next_attempt_id, student, test)
            self.attempts.append(attempt)
            student.add_attempt(attempt)
            self.next_attempt_id += 1
            self.save_data()
            return attempt
        return None

    def get_student_attempts(self, student_id, test_id=None):
        if test_id:
            return [a for a in self.attempts if a.student.student_id == student_id and a.test.test_id == test_id]
        return [a for a in self.attempts if a.student.student_id == student_id]

    def get_test_statistics(self, test_id):
        test_attempts = [a for a in self.attempts if a.test.test_id == test_id and a.status == TestStatus.EVALUATED]
        if not test_attempts:
            return None

        total_attempts = len(test_attempts)
        passed_attempts = len([a for a in test_attempts if a.is_passed])
        avg_score = sum(a.percentage for a in test_attempts) / total_attempts
        avg_time = sum(a.get_duration() for a in test_attempts) / total_attempts

        return {
            'total_attempts': total_attempts,
            'passed_attempts': passed_attempts,
            'success_rate': (passed_attempts / total_attempts * 100) if total_attempts > 0 else 0,
            'avg_score': avg_score,
            'avg_time': avg_time
        }

    def save_data(self):
        data = {
            'students': [s.to_dict() for s in self.students],
            'tests': [t.to_dict() for t in self.tests],
            'attempts': [a.to_dict() for a in self.attempts],
            'counters': {
                'student': self.next_student_id,
                'test': self.next_test_id,
                'attempt': self.next_attempt_id,
                'question': self.next_question_id
            }
        }
        try:
            with open('testing_system_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def load_data(self):
        try:
            with open('testing_system_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.students = [Student.from_dict(s_data) for s_data in data['students']]
            self.tests = [Test.from_dict(t_data) for t_data in data['tests']]

            # Восстанавливаем попытки
            for attempt_data in data['attempts']:
                student = self.find_student_by_id(attempt_data['student_id'])
                test = self.find_test_by_id(attempt_data['test_id'])

                if student and test:
                    attempt = TestAttempt(attempt_data['attempt_id'], student, test)
                    attempt.start_time = datetime.fromisoformat(attempt_data['start_time'])
                    if attempt_data['end_time']:
                        attempt.end_time = datetime.fromisoformat(attempt_data['end_time'])
                    attempt.status = TestStatus[attempt_data['status']]
                    attempt.answers = attempt_data['answers']
                    attempt.scores = attempt_data['scores']
                    attempt.final_score = attempt_data['final_score']
                    attempt.percentage = attempt_data['percentage']
                    attempt.is_passed = attempt_data['is_passed']

                    self.attempts.append(attempt)
                    student.test_attempts.append(attempt)

            counters = data['counters']
            self.next_student_id = counters['student']
            self.next_test_id = counters['test']
            self.next_attempt_id = counters['attempt']
            self.next_question_id = counters['question']

        except FileNotFoundError:
            self.create_sample_data()
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            self.create_sample_data()

    def create_sample_data(self):
        # Создаем демо-студентов
        self.add_student("Иванов Алексей", "Группа 101", "ivanov@edu.ru")
        self.add_student("Петрова Мария", "Группа 101", "petrova@edu.ru")
        self.add_student("Сидоров Дмитрий", "Группа 102", "sidorov@edu.ru")

        # Создаем демо-тесты
        math_test = self.add_test("Математика - базовый уровень", "Математика", 45)
        prog_test = self.add_test("Основы программирования", "Информатика", 60)

        # Добавляем вопросы в математический тест
        self.add_question_to_test(
            math_test.test_id,
            "Чему равно 2 + 2 × 2?",
            QuestionType.SINGLE_CHOICE,
            ["6", "8", "10"],
            ["6"]
        )

        self.add_question_to_test(
            math_test.test_id,
            "Какие из перечисленных чисел являются простыми?",
            QuestionType.MULTIPLE_CHOICE,
            ["2", "4", "7", "9", "11"],
            ["2", "7", "11"]
        )

        self.add_question_to_test(
            math_test.test_id,
            "Сформулируйте теорему Пифагора",
            QuestionType.TEXT_ANSWER,
            max_points=3
        )

        # Добавляем вопросы в тест по программированию
        self.add_question_to_test(
            prog_test.test_id,
            "Что такое переменная в программировании?",
            QuestionType.SINGLE_CHOICE,
            ["Место в памяти для хранения данных", "Тип данных", "Функция"],
            ["Место в памяти для хранения данных"]
        )

        self.add_question_to_test(
            prog_test.test_id,
            "Какие языки программирования являются объектно-ориентированными?",
            QuestionType.MULTIPLE_CHOICE,
            ["Python", "C++", "Java", "HTML"],
            ["Python", "C++", "Java"]
        )


class TestingSystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система учета тестирования учащихся")
        self.root.geometry("1400x800")

        self.system = TestingSystem("Учебный портал")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.create_students_tab()
        self.create_tests_tab()
        self.create_questions_tab()
        self.create_attempts_tab()
        self.create_statistics_tab()

    def create_students_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Студенты")

        # Панель добавления студента
        add_frame = ttk.LabelFrame(tab, text="Добавить студента", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(add_frame, text="ФИО:").grid(row=0, column=0, sticky='w')
        self.student_name = ttk.Entry(add_frame, width=30)
        self.student_name.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Группа:").grid(row=1, column=0, sticky='w')
        self.student_group = ttk.Entry(add_frame, width=30)
        self.student_group.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Email:").grid(row=2, column=0, sticky='w')
        self.student_email = ttk.Entry(add_frame, width=30)
        self.student_email.grid(row=2, column=1, padx=5, pady=2)

        ttk.Button(add_frame, text="Добавить студента",
                   command=self.add_student).grid(row=3, column=1, pady=10)

        # Список студентов
        list_frame = ttk.LabelFrame(tab, text="Список студентов", padding=10)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        columns = ('ID', 'ФИО', 'Группа', 'Email', 'Попыток')
        self.students_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.students_tree.heading(col, text=col)

        self.students_tree.pack(fill='both', expand=True)

        ttk.Button(list_frame, text="Обновить список",
                   command=self.update_students_list).pack(pady=5)

        self.update_students_list()

    def create_tests_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Тесты")

        # Панель добавления теста
        add_frame = ttk.LabelFrame(tab, text="Создать тест", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(add_frame, text="Название:").grid(row=0, column=0, sticky='w')
        self.test_title = ttk.Entry(add_frame, width=30)
        self.test_title.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Предмет:").grid(row=1, column=0, sticky='w')
        self.test_subject = ttk.Entry(add_frame, width=30)
        self.test_subject.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Время (мин):").grid(row=2, column=0, sticky='w')
        self.test_time = ttk.Spinbox(add_frame, from_=5, to=180, width=28)
        self.test_time.grid(row=2, column=1, padx=5, pady=2)

        ttk.Button(add_frame, text="Создать тест",
                   command=self.add_test).grid(row=3, column=1, pady=10)

        # Список тестов
        list_frame = ttk.LabelFrame(tab, text="Список тестов", padding=10)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        columns = ('ID', 'Название', 'Предмет', 'Время', 'Вопросов', 'Статус')
        self.tests_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.tests_tree.heading(col, text=col)

        self.tests_tree.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill='x', pady=5)

        ttk.Button(btn_frame, text="Обновить список",
                   command=self.update_tests_list).pack(side='left', padx=5)

        self.test_status_btn = ttk.Button(btn_frame, text="Деактивировать",
                                          command=self.toggle_test_status)
        self.test_status_btn.pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Удалить тест",
                   command=self.delete_test).pack(side='left', padx=5)

        self.update_tests_list()

    def create_questions_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Вопросы")

        # Выбор теста
        test_frame = ttk.LabelFrame(tab, text="Выбор теста", padding=10)
        test_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(test_frame, text="Тест:").pack(side='left')
        self.test_selector = ttk.Combobox(test_frame, width=50)
        self.test_selector.pack(side='left', padx=5)
        self.test_selector.bind('<<ComboboxSelected>>', self.on_test_selected)

        # Панель добавления вопроса
        add_frame = ttk.LabelFrame(tab, text="Добавить вопрос", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(add_frame, text="Текст вопроса:").grid(row=0, column=0, sticky='w')
        self.question_text = scrolledtext.ScrolledText(add_frame, width=60, height=3)
        self.question_text.grid(row=0, column=1, padx=5, pady=2, columnspan=3)

        ttk.Label(add_frame, text="Тип вопроса:").grid(row=1, column=0, sticky='w')
        self.question_type = ttk.Combobox(add_frame, values=[t.value for t in QuestionType], width=20)
        self.question_type.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Баллы:").grid(row=1, column=2, sticky='w')
        self.question_points = ttk.Spinbox(add_frame, from_=1, to=10, width=5)
        self.question_points.grid(row=1, column=3, padx=5, pady=2)

        ttk.Button(add_frame, text="Добавить вопрос",
                   command=self.add_question).grid(row=2, column=3, pady=10)

        # Список вопросов
        list_frame = ttk.LabelFrame(tab, text="Вопросы теста", padding=10)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        columns = ('ID', 'Текст', 'Тип', 'Варианты', 'Правильные ответы', 'Баллы', 'Статус')
        self.questions_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)

        for col in columns:
            self.questions_tree.heading(col, text=col)

        self.questions_tree.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill='x', pady=5)

        ttk.Button(btn_frame, text="Обновить вопросы",
                   command=self.update_questions_list).pack(side='left', padx=5)

        self.question_status_btn = ttk.Button(btn_frame, text="Деактивировать",
                                              command=self.toggle_question_status)
        self.question_status_btn.pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Удалить вопрос",
                   command=self.delete_question).pack(side='left', padx=5)

        self.update_test_selector()

    def create_attempts_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Попытки")

        # Создание попытки
        create_frame = ttk.LabelFrame(tab, text="Новая попытка", padding=10)
        create_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(create_frame, text="Студент:").grid(row=0, column=0, sticky='w')
        self.attempt_student = ttk.Combobox(create_frame, width=30)
        self.attempt_student.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(create_frame, text="Тест:").grid(row=0, column=2, sticky='w')
        self.attempt_test = ttk.Combobox(create_frame, width=30)
        self.attempt_test.grid(row=0, column=3, padx=5, pady=2)

        ttk.Button(create_frame, text="Создать попытку",
                   command=self.create_attempt).grid(row=1, column=3, pady=5)

        # Список попыток
        list_frame = ttk.LabelFrame(tab, text="История попыток", padding=10)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        columns = ('ID', 'Студент', 'Тест', 'Начало', 'Завершение', 'Статус', 'Баллы', 'Процент', 'Результат')
        self.attempts_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.attempts_tree.heading(col, text=col)

        self.attempts_tree.pack(fill='both', expand=True)

        ttk.Button(list_frame, text="Обновить список",
                   command=self.update_attempts_list).pack(pady=5)

        self.update_attempt_selectors()
        self.update_attempts_list()

    def create_statistics_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Статистика")

        self.stats_text = scrolledtext.ScrolledText(tab, height=20, width=100)
        self.stats_text.pack(fill='both', expand=True, padx=10, pady=10)

        self.update_statistics()

    def update_statistics(self):
        stats = self.generate_statistics()
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)

    def generate_statistics(self):
        total_students = len(self.system.students)
        total_tests = len(self.system.tests)
        total_attempts = len(self.system.attempts)

        text = f"""
    СТАТИСТИКА СИСТЕМЫ ТЕСТИРОВАНИЯ 

Общее количество студентов: {total_students}
Общее количество тестов: {total_tests}
Общее количество попыток: {total_attempts}

Статистика по тестам:
"""

        for test in self.system.tests:
            stats = self.system.get_test_statistics(test.test_id)
            if stats:
                text += f"""
Тест: {test.title}
  Всего попыток: {stats['total_attempts']}
  Успешных: {stats['passed_attempts']}
  Успеваемость: {stats['success_rate']:.1f}%
  Средний балл: {stats['avg_score']:.1f}%
  Среднее время: {stats['avg_time']:.1f} мин
"""
            else:
                text += f"""
Тест: {test.title}
  Нет данных о попытках
"""

        # Топ студентов (только те, у кого есть оцененные попытки)
        text += "\nЛучшие студенты:\n"
        students_with_evaluated_attempts = [
            s for s in self.system.students
            if any(a.status == TestStatus.EVALUATED for a in s.test_attempts)
        ]

        if students_with_evaluated_attempts:
            top_students = sorted(students_with_evaluated_attempts,
                                  key=lambda s: sum(
                                      a.percentage for a in s.test_attempts if a.status == TestStatus.EVALUATED) / len(
                                      [a for a in s.test_attempts if a.status == TestStatus.EVALUATED]),
                                  reverse=True)[:5]

            for i, student in enumerate(top_students, 1):
                evaluated_attempts = [a for a in student.test_attempts if a.status == TestStatus.EVALUATED]
                avg_score = sum(a.percentage for a in evaluated_attempts) / len(evaluated_attempts)
                text += f"  {i}. {student.full_name} - {avg_score:.1f}% (попыток: {student.get_attempts_count()})\n"
        else:
            text += "  Нет данных о студентах с оцененными попытками\n"

        return text

    def add_student(self):
        name = self.student_name.get()
        group = self.student_group.get()
        email = self.student_email.get()

        if not name or not group:
            messagebox.showerror("Ошибка", "Заполните ФИО и группу")
            return

        self.system.add_student(name, group, email)
        self.update_students_list()
        self.update_attempt_selectors()

        self.student_name.delete(0, tk.END)
        self.student_group.delete(0, tk.END)
        self.student_email.delete(0, tk.END)

        messagebox.showinfo("Успех", "Студент добавлен")

    def update_students_list(self):
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)

        for student in self.system.students:
            self.students_tree.insert('', 'end', values=(
                student.student_id,
                student.full_name,
                student.group,
                student.email,
                student.get_attempts_count()
            ))

    def add_test(self):
        title = self.test_title.get()
        subject = self.test_subject.get()
        try:
            time_limit = int(self.test_time.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Время должно быть числом")
            return

        if not title or not subject:
            messagebox.showerror("Ошибка", "Заполните название и предмет")
            return

        self.system.add_test(title, subject, time_limit)
        self.update_tests_list()
        self.update_test_selector()
        self.update_attempt_selectors()

        self.test_title.delete(0, tk.END)
        self.test_subject.delete(0, tk.END)

        messagebox.showinfo("Успех", "Тест создан")

    def update_tests_list(self):
        for item in self.tests_tree.get_children():
            self.tests_tree.delete(item)

        for test in self.system.tests:
            status = "Активен" if test.is_active else "Неактивен"
            self.tests_tree.insert('', 'end', values=(
                test.test_id,
                test.title,
                test.subject,
                f"{test.time_limit} мин",
                len(test.get_active_questions()),
                status
            ))

    def toggle_test_status(self):
        selection = self.tests_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите тест")
            return

        test_id = int(self.tests_tree.item(selection[0])['values'][0])
        test = self.system.find_test_by_id(test_id)

        if test:
            test.toggle_active()
            self.system.save_data()
            self.update_tests_list()

            if test.is_active:
                self.test_status_btn.config(text="Деактивировать")
            else:
                self.test_status_btn.config(text="Активировать")

    def delete_test(self):
        selection = self.tests_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите тест")
            return

        test_id = int(self.tests_tree.item(selection[0])['values'][0])
        test_name = self.tests_tree.item(selection[0])['values'][1]

        confirm = messagebox.askyesno("Подтверждение", f"Удалить тест '{test_name}'?")

        if confirm:
            success = self.system.delete_test(test_id)
            if success:
                self.update_tests_list()
                self.update_test_selector()
                self.update_attempt_selectors()
                messagebox.showinfo("Успех", "Тест удален")

    def update_test_selector(self):
        tests = [f"{t.test_id}. {t.title}" for t in self.system.tests]
        self.test_selector['values'] = tests
        if tests:
            self.test_selector.set(tests[0])

    def on_test_selected(self, event):
        self.update_questions_list()

    def add_question(self):
        test_selection = self.test_selector.get()
        if not test_selection:
            messagebox.showerror("Ошибка", "Выберите тест")
            return

        test_id = int(test_selection.split('.')[0])
        text = self.question_text.get(1.0, tk.END).strip()
        question_type_name = self.question_type.get()
        points = int(self.question_points.get())

        if not text:
            messagebox.showerror("Ошибка", "Введите текст вопроса")
            return

        # Определяем тип вопроса
        question_type = None
        for qt in QuestionType:
            if qt.value == question_type_name:
                question_type = qt
                break

        if not question_type:
            messagebox.showerror("Ошибка", "Выберите тип вопроса")
            return

        self.system.add_question_to_test(test_id, text, question_type, max_points=points)
        self.update_questions_list()

        self.question_text.delete(1.0, tk.END)

        messagebox.showinfo("Успех", "Вопрос добавлен")

    def update_questions_list(self):
        for item in self.questions_tree.get_children():
            self.questions_tree.delete(item)

        test_selection = self.test_selector.get()
        if not test_selection:
            return

        test_id = int(test_selection.split('.')[0])
        test = self.system.find_test_by_id(test_id)

        if test:
            for question in test.questions:
                status = "Активен" if question.is_active else "Неактивен"
                options = ", ".join(question.options) if question.options else "-"
                correct_answers = ", ".join(question.correct_answers) if question.correct_answers else "-"

                self.questions_tree.insert('', 'end', values=(
                    question.question_id,
                    question.text[:50] + "..." if len(question.text) > 50 else question.text,
                    question.question_type.value,
                    options,
                    correct_answers,
                    question.max_points,
                    status
                ))

    def toggle_question_status(self):
        selection = self.questions_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите вопрос")
            return

        test_selection = self.test_selector.get()
        if not test_selection:
            return

        test_id = int(test_selection.split('.')[0])
        question_id = int(self.questions_tree.item(selection[0])['values'][0])

        test = self.system.find_test_by_id(test_id)
        if test:
            question = next((q for q in test.questions if q.question_id == question_id), None)
            if question:
                question.toggle_active()
                self.system.save_data()
                self.update_questions_list()

    def delete_question(self):
        selection = self.questions_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите вопрос")
            return

        test_selection = self.test_selector.get()
        if not test_selection:
            return

        test_id = int(test_selection.split('.')[0])
        question_id = int(self.questions_tree.item(selection[0])['values'][0])

        confirm = messagebox.askyesno("Подтверждение", "Удалить вопрос?")

        if confirm:
            success = self.system.delete_question(test_id, question_id)
            if success:
                self.update_questions_list()
                messagebox.showinfo("Успех", "Вопрос удален")

    def update_attempt_selectors(self):
        students = [f"{s.student_id}. {s.full_name} ({s.group})" for s in self.system.students]
        tests = [f"{t.test_id}. {t.title}" for t in self.system.tests if t.is_active]

        self.attempt_student['values'] = students
        self.attempt_test['values'] = tests

        if students:
            self.attempt_student.set(students[0])
        if tests:
            self.attempt_test.set(tests[0])

    def create_attempt(self):
        student_selection = self.attempt_student.get()
        test_selection = self.attempt_test.get()

        if not student_selection or not test_selection:
            messagebox.showerror("Ошибка", "Выберите студента и тест")
            return

        student_id = int(student_selection.split('.')[0])
        test_id = int(test_selection.split('.')[0])

        attempt = self.system.create_attempt(student_id, test_id)
        if attempt:
            messagebox.showinfo("Успех", f"Попытка #{attempt.attempt_id} создана")
            self.update_attempts_list()
            self.update_statistics()
        else:
            messagebox.showerror("Ошибка", "Не удалось создать попытку")

    def update_attempts_list(self):
        for item in self.attempts_tree.get_children():
            self.attempts_tree.delete(item)

        for attempt in self.system.attempts:
            start_time = attempt.start_time.strftime('%d.%m.%Y %H:%M')
            end_time = attempt.end_time.strftime('%d.%m.%Y %H:%M') if attempt.end_time else "-"
            result = "Зачет" if attempt.is_passed else "Незачет" if attempt.status == TestStatus.EVALUATED else "-"

            self.attempts_tree.insert('', 'end', values=(
                attempt.attempt_id,
                attempt.student.full_name,
                attempt.test.title,
                start_time,
                end_time,
                attempt.status.value,
                attempt.final_score,
                f"{attempt.percentage:.1f}%" if attempt.percentage > 0 else "-",
                result
            ))


def main():
    root = tk.Tk()
    app = TestingSystemApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()