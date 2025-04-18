import sys
import sqlite3
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QMessageBox, QInputDialog, QComboBox
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns

# init
global_df = pd.DataFrame()  # Глобальная переменная для сохранения таблицы в DataFrame

class TableEditor(QMainWindow): # Первоначальные таблица с данными
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Исходные данные")
        self.setGeometry(100, 100, 769, 400)

        # Создаю виджет таблицы
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setHorizontalHeaderLabels(["Показатели", "Долговые_обязательства", "Собственный_капитал", "Внеоборотные_активы", "Заемный_капитал", "Валюта_баланса"])

        # Подключаемся к базе данных
        self.conn = sqlite3.connect('financial_data.db')
        self.cursor = self.conn.cursor()

        # Создаем таблицу, если она не существует
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_data (
                year TEXT,
                debt INTEGER,
                equity INTEGER,
                non_current_assets INTEGER,
                borrowed_capital INTEGER,
                balance_currency INTEGER
            )
        ''')
        self.conn.commit()


        # Создайте словарь для сопоставления имен столбцов
        self.column_mapping = {
            "Показатели": "year",
            "Долговые_обязательства": "debt",
            "Собственный_капитал": "equity",
            "Внеоборотные_активы": "non_current_assets",
            "Заемный_капитал": "borrowed_capital",
            "Валюта_баланса": "balance_currency"
        }


        # Загружаю начальные данные из базы данных
        self.load_initial_data()

        # Выравниваю ширину столбцов по содержимому
        self.table_widget.resizeColumnsToContents()

        # Создаю кнопки
        self.add_button = QPushButton("Добавить")
        self.edit_button = QPushButton("Изменить")
        self.delete_button = QPushButton("Удалить")
        self.save_button = QPushButton("Сохранить в DataFrame")

        # Подключаю обработчики событий
        self.add_button.clicked.connect(self.add_row)
        self.edit_button.clicked.connect(self.edit_cell)
        self.delete_button.clicked.connect(self.delete_cell)
        self.save_button.clicked.connect(self.save_to_dataframe)

        # Создаю компоновку
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.save_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.table_widget)
        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def load_initial_data(self):
        # Загружаем данные из базы данных
        self.cursor.execute("SELECT * FROM financial_data")
        rows = self.cursor.fetchall()

        self.table_widget.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_data in enumerate(row_data):
                self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(cell_data)))

    def add_row(self): # Добавление строки
        # Добавление новой строчки в базу данных
        year = QInputDialog.getText(self, "Добавить строку", "Введите год:")[0]
        if year:
            self.cursor.execute("INSERT INTO financial_data (year, debt, equity, non_current_assets, borrowed_capital, balance_currency) VALUES (?, ?, ?, ?, ?, ?)",
                                 (year, 0, 0, 0, 0, 0))
            self.conn.commit()
            self.load_initial_data()

    def edit_cell(self): # Изменение ячейки 
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Выберите ячейку для изменения.")
            return

        for item in selected_items:
            text, ok = QInputDialog.getText(self, "Изменить ячейку", "Введите новое значение:", text=item.text())
            if ok and text:
                row = self.table_widget.row(item)
                col = self.table_widget.column(item)
                column_name = self.table_widget.horizontalHeaderItem(col).text()

                # Используйте словарь для получения имени столбца в базе данных
                db_column_name = self.column_mapping.get(column_name)
                if db_column_name is None:
                    QMessageBox.warning(self, "Ошибка", f"Неизвестное имя столбца: {column_name}")
                    continue

                year = self.table_widget.item(row, 0).text()

                self.cursor.execute(f"UPDATE financial_data SET {db_column_name} = ? WHERE year = ?", (text, year))
                self.conn.commit()
                item.setText(text)

    def delete_cell(self): # Кнопка удаления строки
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Выберите ячейку для удаления.")
            return

        for item in selected_items:
            row = self.table_widget.row(item)
            year = self.table_widget.item(row, 0).text()
            self.cursor.execute("DELETE FROM financial_data WHERE year = ?", (year,))
            self.conn.commit()
            self.table_widget.removeRow(row)

    def save_to_dataframe(self): # Кнопка сохранения в dataframe -> благодаря такому формату, получается удачно работать с данными.
        global global_df

        # Извлекаем данные из таблицы
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()
        data = []

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table_widget.item(row, col)
                row_data.append(item.text() if item is not None else "")
            data.append(row_data)

        # Создаем DataFrame
        global_df = pd.DataFrame(data, columns=[self.table_widget.horizontalHeaderItem(col).text() for col in range(cols)])
        print("DataFrame сохранен.")

        self.close()

        # Открываем новое окно с результатами. Если введён только 1 год, то выйдет ошибка.
        if len(global_df) == 1:
            QMessageBox.warning(self, "Предупреждение", "Слишком мало данных.")
            self.close()
        else: 
            self.result_window = ResultWindow(global_df)
            self.result_window.show()


class ResultWindow(QMainWindow): # Окно результирования 
    def __init__(self, dataframe):
        super().__init__()

        self.setWindowTitle("Результаты")
        self.setGeometry(100, 100, 1200, 600)

        # Подсчет значений
        global finance # Глобальная переменная для дальнейших расчетов в графиках

        fin_risk = [round(int(dataframe["Долговые_обязательства"][i]) / int(dataframe["Собственный_капитал"][i]), 2) for i in range(len(dataframe))]
        manuvr = [round((int(dataframe["Собственный_капитал"][i]) - int(dataframe["Внеоборотные_активы"][i])) / int(dataframe["Собственный_капитал"][i]), 2) for i in range(len(dataframe))]
        finance = [round(int(dataframe["Собственный_капитал"][i]) / int(dataframe["Заемный_капитал"][i]), 2) for i in range(len(dataframe))]
        nezav = [round(int(dataframe["Собственный_капитал"][i]) / int(dataframe["Валюта_баланса"][i]), 2) for i in range(len(dataframe))]
        fin_stable = [round((int(dataframe["Долговые_обязательства"][i]) + int(dataframe["Собственный_капитал"][i])) / int(dataframe["Валюта_баланса"][i]), 2) for i in range(len(dataframe))]

        self.names = [fin_risk, manuvr, finance, nezav, fin_stable]
        self.coefficients = ["Коэффициент Финансового риска", "Коэффициент Маневренности", "Коэффициент Финансирования", "Коэффициент Независимости", "Коэффициент Финансовой устойчивости"]

        def get_otn_change(iter): # Функция для нахождения относительных изменений
            otn_changes = ((self.names[iter][-1] - self.names[iter][0]) / self.names[iter][-1]) * 100
            return f"{round(otn_changes, 3)}%"

        def get_abs_change(iter): # Функция для нахождения абсолютных изменений
            abs_changes = self.names[iter][-1] - self.names[iter][0]
            return round(abs_changes, 3)

        def otn_izm_list(): # Возвращает список относитльных изменений В МОДУЛЕ! (т.к. значения < 0 не воспроизводятся на графике)
            res = []
            for iter in range(len(self.names)):
                res.append(abs(round(((self.names[iter][-1] - self.names[iter][0]) / self.names[iter][-1]) * 100, 2)))
            return res

        global gl_vals, graph_names
        gl_vals = otn_izm_list()
        graph_names = [fin_risk, manuvr, finance, nezav, fin_stable]

        # Создаем виджет таблицы для результатов
        self.result_table_widget = QTableWidget()
        self.result_table_widget.setColumnCount(len(dataframe) + 3)
        self.result_table_widget.setRowCount(5)
        self.result_table_widget.setHorizontalHeaderLabels(["Показатели", *[i for i in dataframe["Показатели"]], "Относительное изм.", "Абсолютное изм."])

        # Заполняем таблицу названиями показателей
        for row_idx, coefficient in enumerate(self.coefficients):
            self.result_table_widget.setItem(row_idx, 0, QTableWidgetItem(coefficient))

        # Выравнивание по центру для названий показателей
        for row in range(5):
            item = self.result_table_widget.item(row, 0)
            item.setTextAlignment(Qt.AlignCenter)

        # Заполняем таблицу результатами
        for row_idx, name in enumerate(self.names):
            for col_idx, value in enumerate(name):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.result_table_widget.setItem(row_idx, col_idx + 1, item)

        # Добавляем относительные и абсолютные изменения
        for row_idx in range(len(self.names)):
            item_otn = QTableWidgetItem(get_otn_change(row_idx))
            item_otn.setTextAlignment(Qt.AlignCenter)
            self.result_table_widget.setItem(row_idx, len(dataframe) + 1, item_otn)

            item_abs = QTableWidgetItem(str(get_abs_change(row_idx)))
            item_abs.setTextAlignment(Qt.AlignCenter)
            self.result_table_widget.setItem(row_idx, len(dataframe) + 2, item_abs)

        # Выравниваю ширину столбцов по содержимому
        self.result_table_widget.resizeColumnsToContents()

        # Задаю ширину столбца "Показатели"
        for i in range(1, len(dataframe["Показатели"]) + 1):
            self.result_table_widget.setColumnWidth(i, 50)

        # Создаю выпадающий список для выбора коэффициента
        self.coefficient_combo = QComboBox()
        self.coefficient_combo.addItems(self.coefficients)
        self.coefficient_combo.addItem("(выберите коэффициент)")
        self.coefficient_combo.currentIndexChanged.connect(self.plot_graph)

        self.coefficient_combo.setCurrentIndex(5)

        # Создаю кнопки для построения графиков
        self.pie_chart_button = QPushButton("Круговая диаграмма")
        self.bar_chart_button = QPushButton("Гистограмма (Первых 4-х лет)")

        self.pie_chart_button.clicked.connect(self.plot_pie_chart)
        self.bar_chart_button.clicked.connect(self.plot_bar_chart)

        # Создаем компоновку для левой части
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.result_table_widget)
        left_layout.addWidget(self.coefficient_combo)
        left_layout.addWidget(self.pie_chart_button)
        left_layout.addWidget(self.bar_chart_button)

        # Создаем виджет для графиков
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Создаем компоновку для правой части
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.canvas)

        # Общая компоновка
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 43)
        main_layout.addLayout(right_layout, 57)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        if len(global_df) == 1:
            QMessageBox.warning(self, "Предупреждение", "Слишком мало данных.")
            self.close()

    def plot_graph(self): # Диаграмма показателй по выбранному коэффициенту
        selected_index = self.coefficient_combo.currentIndex()
        if selected_index == 5:
            return

        selected_coefficient = self.names[selected_index]

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        x = [i for i in global_df["Показатели"]]
        y = [i for i in selected_coefficient]

        ax.bar(x, y, label='Значение коэффициента', alpha=0.5)
        ax.plot(x, y, color='red', marker='o', markersize=7)

        ax.set_xlabel('Год')
        ax.set_ylabel(f'{self.coefficients[selected_index]}')
        ax.set_title(f"Динамика изменений {self.coefficients[selected_index]}")

        ax.legend()
        self.canvas.draw()

    def plot_pie_chart(self): # Круговая диаграмма
        explode = (0, 0, 0.1, 0, 0)
        labels = ["Финансовый риск", "Маневренность", "Финансирование", "Независимость", "Фин. устойчивость"]

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.pie(gl_vals, labels=labels, autopct="%1.1f%%", explode=explode)
        ax.set_title("Относительные изменения за весь период")

        self.canvas.draw()

    def plot_bar_chart(self): # Диаграмма изменений показателей (за первые 4 года)!
        palette = sns.color_palette("husl", 5)
        x = ["Фин. риск", "Маневр.", "Незав.", "Фин. уст."]

        self.figure.clear()

        match len(global_df["Показатели"]):

            case 2: # Построение 2-х графиков
                ax = self.figure.subplots(2, 1)
                self.figure.suptitle("Гистограммы коэффициентов за 2 года")

                for i, year in enumerate(global_df["Показатели"][:2]):
                    row, col = divmod(i, 1)
                    ax[row].set_title(f"{year}-й Год")
                    ax[row].bar(x, [coef[i] for coef in graph_names if coef != finance], width=0.9, color=palette)

                self.canvas.draw()

            case 3: # Построение 3-х графиков
                ax = self.figure.subplots(3, 1)
                self.figure.suptitle("Гистограммы коэффициентов за 3 года")

                for i, year in enumerate(global_df["Показатели"][:3]):
                    row, col = divmod(i, 1)
                    ax[row].set_title(f"{year}-й Год")
                    ax[row].bar(x, [coef[i] for coef in graph_names if coef != finance], width=0.9, color=palette)

                self.canvas.draw()

            case _: # Построение 4-х и более графиков
                ax = self.figure.subplots(2, 2)
                self.figure.suptitle("Гистограммы коэффициентов за первые 4 года")

                for i, year in enumerate(global_df["Показатели"][:4]):
                    row, col = divmod(i, 2)
                    ax[row, col].set_title(f"{year}-й Год")
                    ax[row, col].bar(x, [coef[i] for coef in graph_names if coef != finance], width=0.9, color=palette)

                self.canvas.draw()


        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TableEditor()
    window.show()
    sys.exit(app.exec())
