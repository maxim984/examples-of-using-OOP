import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from enum import Enum
import json


class OrderState(Enum):
    WAITING = "ожидает"
    ACCEPTED = "принят"
    COOKING = "готовится"
    DONE = "готов"
    FINISHED = "завершен"
    CANCELED = "отменен"


class PayState(Enum):
    NOT_PAID = "не оплачен"
    PAID = "оплачен"
    RETURNED = "возврат"


class Dish:
    def __init__(self, num, title, info, cost, group):
        self.num = num
        self.title = title
        self.info = info
        self.cost = cost
        self.group = group
        self.active = True

    def switch_active(self):
        self.active = not self.active

    def to_json(self):
        return {
            'num': self.num,
            'title': self.title,
            'info': self.info,
            'cost': self.cost,
            'group': self.group,
            'active': self.active
        }

    @classmethod
    def from_json(cls, data):
        item = cls(data['num'], data['title'], data['info'], data['cost'], data['group'])
        item.active = data['active']
        return item


class OrderLine:
    def __init__(self, dish, count=1, comment=""):
        self.dish = dish
        self.count = count
        self.comment = comment
        self.sum = dish.cost * count

    def change_count(self, new_count):
        self.count = new_count
        self.sum = self.dish.cost * new_count

    def __str__(self):
        return f"{self.dish.title} x{self.count} - {self.sum} руб."


class Client:
    def __init__(self, client_id, full_name, phone_num, mail=""):
        self.client_id = client_id
        self.full_name = full_name
        self.phone_num = phone_num
        self.mail = mail
        self.orders = []

    def add_order(self, order):
        self.orders.append(order)

    def orders_count(self):
        return len(self.orders)

    def to_json(self):
        return {
            'client_id': self.client_id,
            'full_name': self.full_name,
            'phone_num': self.phone_num,
            'mail': self.mail
        }

    @classmethod
    def from_json(cls, data):
        return cls(data['client_id'], data['full_name'], data['phone_num'], data['mail'])


class Order:
    def __init__(self, order_num, client):
        self.order_num = order_num
        self.client = client
        self.lines = []
        self.date = datetime.now()
        self.state = OrderState.WAITING
        self.pay_state = PayState.NOT_PAID
        self.total = 0.0
        self.comments = ""

    def add_dish(self, dish, count=1, comment=""):
        if not dish.active:
            raise ValueError(f"Блюдо '{dish.title}' не доступно")

        for line in self.lines:
            if line.dish.num == dish.num and line.comment == comment:
                line.change_count(line.count + count)
                self.calc_total()
                return

        new_line = OrderLine(dish, count, comment)
        self.lines.append(new_line)
        self.calc_total()

    def remove_dish(self, dish_num):
        self.lines = [line for line in self.lines if line.dish.num != dish_num]
        self.calc_total()

    def change_count(self, dish_num, new_count):
        for line in self.lines:
            if line.dish.num == dish_num:
                if new_count <= 0:
                    self.remove_dish(dish_num)
                else:
                    line.change_count(new_count)
                self.calc_total()
                return

    def calc_total(self):
        self.total = sum(line.sum for line in self.lines)

    def set_state(self, new_state):
        self.state = new_state

    def set_pay_state(self, new_pay_state):
        self.pay_state = new_pay_state

    def add_comment(self, text):
        self.comments = text

    def to_json(self):
        return {
            'order_num': self.order_num,
            'client_id': self.client.client_id,
            'lines': [
                {
                    'dish_num': line.dish.num,
                    'count': line.count,
                    'comment': line.comment
                } for line in self.lines
            ],
            'date': self.date.isoformat(),
            'state': self.state.name,
            'pay_state': self.pay_state.name,
            'total': self.total,
            'comments': self.comments
        }

    def get_info(self):
        lines_text = "\n".join([f"  - {line}" for line in self.lines])
        return f"""
Заказ #{self.order_num}
Клиент: {self.client.full_name}
Дата: {self.date.strftime('%d.%m.%Y %H:%M')}
Статус: {self.state.value}
Оплата: {self.pay_state.value}
Состав:
{lines_text}
Всего: {self.total} руб.
Примечания: {self.comments if self.comments else 'нет'}
        """


class Cafe:
    def __init__(self, cafe_name):
        self.cafe_name = cafe_name
        self.dishes = []
        self.clients = []
        self.orders = []
        self.next_order_num = 1
        self.next_client_num = 1
        self.next_dish_num = 1
        self.load()

    def new_dish(self, title, info, cost, group):
        dish = Dish(self.next_dish_num, title, info, cost, group)
        self.dishes.append(dish)
        self.next_dish_num += 1
        self.save()
        return dish

    def find_dish(self, dish_num):
        for dish in self.dishes:
            if dish.num == dish_num:
                return dish
        return None

    def delete_dish(self, dish_num):
        dish = self.find_dish(dish_num)
        if dish:
            # Проверка на использование в активных заказах
            used_in = []
            for order in self.orders:
                if order.state in [OrderState.WAITING, OrderState.ACCEPTED, OrderState.COOKING]:
                    for line in order.lines:
                        if line.dish.num == dish_num:
                            used_in.append(order.order_num)

            if used_in:
                messagebox.showwarning(
                    "Нельзя удалить",
                    f"Блюдо используется в заказах: {', '.join(map(str, used_in))}"
                )
                return False

            self.dishes.remove(dish)
            self.save()
            return True
        return False

    def find_dishes_by_group(self, group):
        return [dish for dish in self.dishes if dish.group.lower() == group.lower()]

    def new_client(self, full_name, phone_num, mail=""):
        client = self.find_client_by_phone(phone_num)
        if client:
            return client

        client = Client(self.next_client_num, full_name, phone_num, mail)
        self.clients.append(client)
        self.next_client_num += 1
        self.save()
        return client

    def find_client_by_phone(self, phone_num):
        for client in self.clients:
            if client.phone_num == phone_num:
                return client
        return None

    def find_client_by_id(self, client_id):
        for client in self.clients:
            if client.client_id == client_id:
                return client
        return None

    def create_order(self, client):
        order = Order(self.next_order_num, client)
        self.orders.append(order)
        client.add_order(order)
        self.next_order_num += 1
        self.save()
        return order

    def get_orders_by_state(self, state):
        return [order for order in self.orders if order.state == state]

    def get_client_orders(self, client):
        return client.orders

    def get_day_money(self, day=None):
        if day is None:
            day = datetime.now()

        day_orders = [order for order in self.orders
                      if order.date.date() == day.date()
                      and order.pay_state == PayState.PAID]

        return sum(order.total for order in day_orders)

    def get_menu_groups(self):
        groups = {}
        for dish in self.dishes:
            if dish.group not in groups:
                groups[dish.group] = []
            groups[dish.group].append(dish)
        return groups

    def save(self):
        data = {
            'dishes': [dish.to_json() for dish in self.dishes],
            'clients': [client.to_json() for client in self.clients],
            'orders': [order.to_json() for order in self.orders],
            'counters': {
                'order': self.next_order_num,
                'client': self.next_client_num,
                'dish': self.next_dish_num
            }
        }
        try:
            with open('cafe_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка: {e}")

    def load(self):
        try:
            with open('cafe_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.dishes = [Dish.from_json(dish_data) for dish_data in data['dishes']]
            self.clients = [Client.from_json(client_data) for client_data in data['clients']]

            for order_data in data['orders']:
                client = self.find_client_by_id(order_data['client_id'])
                if client:
                    order = Order(order_data['order_num'], client)
                    order.date = datetime.fromisoformat(order_data['date'])
                    order.state = OrderState[order_data['state']]
                    order.pay_state = PayState[order_data['pay_state']]
                    order.total = order_data['total']
                    order.comments = order_data['comments']

                    for line_data in order_data['lines']:
                        dish = self.find_dish(line_data['dish_num'])
                        if dish:
                            order.add_dish(dish, line_data['count'], line_data['comment'])

                    self.orders.append(order)
                    client.orders.append(order)

            self.next_order_num = data['counters']['order']
            self.next_client_num = data['counters']['client']
            self.next_dish_num = data['counters']['dish']

        except FileNotFoundError:
            self.create_test_data()
        except Exception as e:
            print(f"Ошибка: {e}")
            self.create_test_data()

    def create_test_data(self):
        self.new_dish("Пицца Пепперони", "Острая пицца", 480.0, "Пицца")
        self.new_dish("Спагетти Болоньезе", "Паста с мясом", 360.0, "Паста")
        self.new_dish("Греческий салат", "С оливками", 290.0, "Салаты")
        self.new_dish("Чизкейк", "Классический", 320.0, "Десерты")

        # Делаем одно блюдо неактивным
        dessert = self.dishes[-1]
        dessert.switch_active()


class CafeApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Учет заказов ресторана")
        self.window.geometry("1200x700")

        self.cafe = Cafe("Вкусная еда")

        self.tabs = ttk.Notebook(window)
        self.tabs.pack(fill='both', expand=True, padx=10, pady=10)

        self.setup_dishes_tab()
        self.setup_orders_tab()
        self.setup_clients_tab()
        self.setup_reports_tab()

    def setup_dishes_tab(self):
        self.dishes_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.dishes_tab, text="Меню")

        add_frame = ttk.LabelFrame(self.dishes_tab, text="Новое блюдо", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(add_frame, text="Название:").grid(row=0, column=0, sticky='w')
        self.dish_name = ttk.Entry(add_frame, width=30)
        self.dish_name.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Описание:").grid(row=1, column=0, sticky='w')
        self.dish_desc = ttk.Entry(add_frame, width=30)
        self.dish_desc.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Цена:").grid(row=2, column=0, sticky='w')
        self.dish_price = ttk.Entry(add_frame, width=30)
        self.dish_price.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(add_frame, text="Категория:").grid(row=3, column=0, sticky='w')
        self.dish_cat = ttk.Entry(add_frame, width=30)
        self.dish_cat.grid(row=3, column=1, padx=5, pady=2)

        ttk.Button(add_frame, text="Добавить", command=self.add_dish).grid(row=4, column=1, pady=10)

        list_frame = ttk.LabelFrame(self.dishes_tab, text="Список блюд", padding=10)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        cols = ('ID', 'Название', 'Цена', 'Категория', 'Статус')
        self.dishes_list = ttk.Treeview(list_frame, columns=cols, show='headings', height=15)

        for col in cols:
            self.dishes_list.heading(col, text=col)
            self.dishes_list.column(col, width=100)

        self.dishes_list.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill='x', pady=5)

        ttk.Button(btn_frame, text="Обновить", command=self.update_dishes).pack(side='left', padx=5)

        self.status_btn = ttk.Button(btn_frame, text="Закрыть позицию", command=self.change_status)
        self.status_btn.pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Удалить", command=self.delete_dish).pack(side='left', padx=5)

        self.update_dishes()

    def setup_orders_tab(self):
        self.orders_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.orders_tab, text="Заказы")

        left = ttk.Frame(self.orders_tab)
        left.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        client_frame = ttk.LabelFrame(left, text="Клиент", padding=10)
        client_frame.pack(fill='x', pady=5)

        ttk.Label(client_frame, text="Телефон:").grid(row=0, column=0, sticky='w')
        self.client_phone = ttk.Entry(client_frame, width=20)
        self.client_phone.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(client_frame, text="Имя:").grid(row=1, column=0, sticky='w')
        self.client_name = ttk.Entry(client_frame, width=20)
        self.client_name.grid(row=1, column=1, padx=5, pady=2)

        ttk.Button(client_frame, text="Найти/Создать", command=self.find_client).grid(row=2, column=1, pady=5)

        menu_frame = ttk.LabelFrame(left, text="Выбор блюд", padding=10)
        menu_frame.pack(fill='both', expand=True, pady=5)

        self.dish_select = ttk.Combobox(menu_frame, width=25)
        self.dish_select.grid(row=0, column=0, padx=5, pady=2)
        self.update_dish_select()

        ttk.Label(menu_frame, text="Кол-во:").grid(row=0, column=1, sticky='w')
        self.qty = ttk.Spinbox(menu_frame, from_=1, to=10, width=5)
        self.qty.grid(row=0, column=2, padx=5, pady=2)

        ttk.Button(menu_frame, text="Добавить", command=self.add_to_order).grid(row=0, column=3, padx=5)

        order_frame = ttk.LabelFrame(left, text="Текущий заказ", padding=10)
        order_frame.pack(fill='both', expand=True, pady=5)

        self.order_text = scrolledtext.ScrolledText(order_frame, height=10, width=50)
        self.order_text.pack(fill='both', expand=True)

        ttk.Button(left, text="Создать заказ", command=self.make_order).pack(pady=10)

        right = ttk.Frame(self.orders_tab)
        right.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        orders_frame = ttk.LabelFrame(right, text="Все заказы", padding=10)
        orders_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Клиент', 'Сумма', 'Статус', 'Оплата')
        self.orders_list = ttk.Treeview(orders_frame, columns=cols, show='headings', height=15)

        for col in cols:
            self.orders_list.heading(col, text=col)

        self.orders_list.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(orders_frame)
        btn_frame.pack(fill='x', pady=5)

        ttk.Button(btn_frame, text="Обновить", command=self.update_orders).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Детали", command=self.show_order).pack(side='left', padx=5)

        self.current_order = None
        self.current_client = None
        self.update_orders()

    def setup_clients_tab(self):
        self.clients_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.clients_tab, text="Клиенты")

        frame = ttk.LabelFrame(self.clients_tab, text="Клиенты", padding=10)
        frame.pack(fill='both', expand=True, padx=5, pady=5)

        cols = ('ID', 'Имя', 'Телефон', 'Email', 'Заказов')
        self.clients_list = ttk.Treeview(frame, columns=cols, show='headings', height=15)

        for col in cols:
            self.clients_list.heading(col, text=col)

        self.clients_list.pack(fill='both', expand=True)

        ttk.Button(frame, text="Обновить", command=self.update_clients).pack(pady=5)

        self.update_clients()

    def setup_reports_tab(self):
        self.reports_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.reports_tab, text="Отчеты")

        text_area = scrolledtext.ScrolledText(self.reports_tab, height=20, width=80)
        text_area.pack(fill='both', expand=True, padx=10, pady=10)

        self.show_stats(text_area)

    def show_stats(self, text_widget):
        stats = self.get_stats()
        text_widget.delete(1.0, tk.END)
        text_widget.insert(1.0, stats)

    def get_stats(self):
        orders_count = len(self.cafe.orders)
        clients_count = len(self.cafe.clients)
        money_today = self.cafe.get_day_money()

        status_count = {}
        for status in OrderState:
            status_count[status.value] = len(self.cafe.get_orders_by_state(status))

        text = f"""
     СТАТИСТИКА 

Всего заказов: {orders_count}
Всего клиентов: {clients_count}
Выручка за день: {money_today:.2f} руб.

Статусы заказов:
"""
        for status, count in status_count.items():
            text += f"  {status}: {count}\n"

        text += "\nЛучшие клиенты:\n"
        top_clients = sorted(self.cafe.clients, key=lambda c: c.orders_count(), reverse=True)[:5]

        for i, client in enumerate(top_clients, 1):
            text += f"  {i}. {client.full_name} - {client.orders_count()} заказов\n"

        return text

    def add_dish(self):
        try:
            name = self.dish_name.get()
            desc = self.dish_desc.get()
            price = float(self.dish_price.get())
            cat = self.dish_cat.get()

            if not all([name, desc, cat]):
                messagebox.showerror("Ошибка", "Заполните все поля")
                return

            self.cafe.new_dish(name, desc, price, cat)
            self.update_dishes()
            self.update_dish_select()

            self.dish_name.delete(0, tk.END)
            self.dish_desc.delete(0, tk.END)
            self.dish_price.delete(0, tk.END)
            self.dish_cat.delete(0, tk.END)

            messagebox.showinfo("Успех", "Блюдо добавлено")

        except ValueError:
            messagebox.showerror("Ошибка", "Цена должна быть числом")

    def update_dishes(self):
        for item in self.dishes_list.get_children():
            self.dishes_list.delete(item)

        for dish in self.cafe.dishes:
            status = "Открыта" if dish.active else "Закрыта"
            self.dishes_list.insert('', 'end', values=(
                dish.num, dish.title, f"{dish.cost} руб.", dish.group, status
            ))

    def update_dish_select(self):
        active_dishes = [f"{dish.num}. {dish.title} - {dish.cost} руб."
                         for dish in self.cafe.dishes if dish.active]
        self.dish_select['values'] = active_dishes
        if active_dishes:
            self.dish_select.set(active_dishes[0])

    def change_status(self):
        selection = self.dishes_list.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите блюдо")
            return

        dish_num = int(self.dishes_list.item(selection[0])['values'][0])
        dish = self.cafe.find_dish(dish_num)

        if dish:
            dish.switch_active()
            self.cafe.save()
            self.update_dishes()
            self.update_dish_select()

            if dish.active:
                self.status_btn.config(text="Закрыть позицию")
            else:
                self.status_btn.config(text="Открыть позицию")

    def delete_dish(self):
        selection = self.dishes_list.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите блюдо")
            return

        dish_num = int(self.dishes_list.item(selection[0])['values'][0])
        dish_name = self.dishes_list.item(selection[0])['values'][1]

        confirm = messagebox.askyesno("Подтверждение", f"Удалить '{dish_name}'?")

        if confirm:
            success = self.cafe.delete_dish(dish_num)
            if success:
                self.update_dishes()
                self.update_dish_select()
                messagebox.showinfo("Успех", "Блюдо удалено")

    def find_client(self):
        phone = self.client_phone.get()
        name = self.client_name.get()

        if not phone:
            messagebox.showerror("Ошибка", "Введите телефон")
            return

        client = self.cafe.find_client_by_phone(phone)

        if not client and name:
            client = self.cafe.new_client(name, phone)
            messagebox.showinfo("Успех", "Новый клиент")
        elif not client and not name:
            messagebox.showerror("Ошибка", "Введите имя для нового клиента")
            return

        self.current_client = client
        self.show_current_order()

    def add_to_order(self):
        if not self.current_client:
            messagebox.showerror("Ошибка", "Сначала найдите клиента")
            return

        selected = self.dish_select.get()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите блюдо")
            return

        try:
            dish_num = int(selected.split('.')[0])
            count = int(self.qty.get())

            dish = self.cafe.find_dish(dish_num)

            if not self.current_order:
                self.current_order = Order(0, self.current_client)

            self.current_order.add_dish(dish, count)
            self.show_current_order()

        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")

    def show_current_order(self):
        self.order_text.delete(1.0, tk.END)

        if self.current_client:
            self.order_text.insert(1.0, f"Клиент: {self.current_client.full_name}\n")
            self.order_text.insert(tk.END, f"Телефон: {self.current_client.phone_num}\n\n")

        if self.current_order and self.current_order.lines:
            self.order_text.insert(tk.END, "Заказ:\n")
            for line in self.current_order.lines:
                self.order_text.insert(tk.END, f"- {line}\n")
            self.order_text.insert(tk.END, f"\nВсего: {self.current_order.total} руб.")
        else:
            self.order_text.insert(tk.END, "Заказ пуст")

    def make_order(self):
        if not self.current_client:
            messagebox.showerror("Ошибка", "Сначала найдите клиента")
            return

        if not self.current_order or not self.current_order.lines:
            messagebox.showerror("Ошибка", "Добавьте блюда в заказ")
            return

        order = self.cafe.create_order(self.current_client)
        for line in self.current_order.lines:
            order.add_dish(line.dish, line.count)

        order.set_state(OrderState.WAITING)
        self.cafe.save()

        messagebox.showinfo("Успех", f"Заказ #{order.order_num} создан!")

        self.current_order = None
        self.show_current_order()
        self.update_orders()

    def update_orders(self):
        for item in self.orders_list.get_children():
            self.orders_list.delete(item)

        for order in self.cafe.orders:
            self.orders_list.insert('', 'end', values=(
                order.order_num,
                order.client.full_name,
                f"{order.total} руб.",
                order.state.value,
                order.pay_state.value
            ))

    def show_order(self):
        selection = self.orders_list.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ")
            return

        order_num = int(self.orders_list.item(selection[0])['values'][0])
        order = next((o for o in self.cafe.orders if o.order_num == order_num), None)

        if order:
            messagebox.showinfo(f"Заказ #{order_num}", order.get_info())

    def update_clients(self):
        for item in self.clients_list.get_children():
            self.clients_list.delete(item)

        for client in self.cafe.clients:
            self.clients_list.insert('', 'end', values=(
                client.client_id,
                client.full_name,
                client.phone_num,
                client.mail,
                client.orders_count()
            ))


def start_app():
    root = tk.Tk()
    app = CafeApp(root)
    root.mainloop()


if __name__ == "__main__":
    start_app()