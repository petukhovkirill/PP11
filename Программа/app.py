import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime


DB_CONFIG = {
    "host": "localhost",
    "database": "medstock_db",
    "user": "stock_app",
    "password": "AppPass789!"
}


class MedStockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MedStock - Система учета лекарств")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.user_data = None
        self.show_login_screen()

    def get_connection(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось подключиться к базе данных:\n{e}")
            return None

    def show_login_screen(self):
        self.clear_window()
        self.root.title("MedStock - Вход в систему")

        frame = tk.Frame(self.root, padx=40, pady=40)
        frame.pack(expand=True)

        tk.Label(frame, text="Вход в систему MedStock", font=("Arial", 16, "bold")).pack(pady=20)

        tk.Label(frame, text="Табельный номер:").pack(anchor="w", pady=(10, 0))
        self.entry_tab = tk.Entry(frame, width=30)
        self.entry_tab.pack(pady=5)
        self.entry_tab.focus_set()

        tk.Label(frame, text="Пароль:").pack(anchor="w", pady=(10, 0))
        self.entry_pass = tk.Entry(frame, width=30, show="*")
        self.entry_pass.pack(pady=5)
        self.entry_pass.bind("<Return>", lambda e: self.login())

        tk.Button(frame, text="Войти", command=self.login, bg="#4CAF50", fg="white",
                  width=20, height=2).pack(pady=20)

    def login(self):
        tab = self.entry_tab.get().strip()
        pwd = self.entry_pass.get().strip()

        if not tab or not pwd:
            messagebox.showwarning("Внимание", "Заполните все поля!")
            return

        conn = self.get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tab_number, full_name, position, department_id, has_potent_access
                FROM system_users
                WHERE tab_number = %s
                AND convert_from(
                    decrypt(decode(password_hash, 'hex'), 'MedStock_Super_Secret_Key_2026!1'::BYTEA, 'aes'),
                    'UTF8'
                ) = %s
            """, (tab, pwd))
            user = cursor.fetchone()
            cursor.close()

            if user:
                self.user_data = {
                    "tab": user[0],
                    "name": user[1],
                    "position": user[2],
                    "department_id": user[3],
                    "has_potent_access": bool(user[4]),
                }
                self.show_dashboard()
            else:
                messagebox.showerror("Ошибка", "Неверный табельный номер или пароль!")
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            conn.close()

    def show_dashboard(self):
        self.clear_window()
        self.root.title(f"MedStock - {self.user_data['position']} ({self.user_data['name']})")

        header = tk.Frame(self.root, bg="#2196F3", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text=f"Добро пожаловать, {self.user_data['name']}!",
                 bg="#2196F3", fg="white", font=("Arial", 14, "bold")).pack(side="left", padx=20, pady=15)
        tk.Button(header, text="Выйти", command=self.show_login_screen,
                  bg="#f44336", fg="white").pack(side="right", padx=20, pady=15)
        tk.Button(header, text="Обновить", command=self.refresh_dashboard,
                  bg="#FF9800", fg="white").pack(side="right", padx=5, pady=15)

        self.content_frame = tk.Frame(self.root, padx=20, pady=20)
        self.content_frame.pack(fill="both", expand=True)

        position = self.user_data['position']
        if position == 'Заведующий':
            self.build_manager_view(self.content_frame)
        elif position == 'Складской рабочий':
            self.build_warehouse_view(self.content_frame)
        elif position == 'Старшая медсестра':
            self.build_nurse_view(self.content_frame)
        else:
            tk.Label(self.content_frame,
                     text=f"Для должности «{position}» интерфейс не предусмотрен.",
                     font=("Arial", 12)).pack(pady=30)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_expired_warning(self):
        win = tk.Toplevel(self.root)
        win.title("ВЫДАЧА ЗАБЛОКИРОВАНА")
        win.configure(bg="#f44336")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        w, h = 620, 260
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

        tk.Label(win, text="⚠", bg="#f44336", fg="white",
                 font=("Arial", 48, "bold")).pack(pady=(20, 0))
        tk.Label(win, text="ВНИМАНИЕ: Выдача заблокирована!",
                 bg="#f44336", fg="white", font=("Arial", 18, "bold")).pack(pady=(5, 0))
        tk.Label(win, text="Срок годности препарата ИСТЕК!",
                 bg="#f44336", fg="white", font=("Arial", 16, "bold")).pack(pady=(5, 15))
        tk.Button(win, text="Понятно", command=win.destroy,
                  bg="white", fg="#f44336", font=("Arial", 12, "bold"),
                  width=16, height=1).pack(pady=5)

        win.bell()
        win.wait_window()

    def refresh_dashboard(self):
        if not hasattr(self, "content_frame") or not self.content_frame.winfo_exists():
            return
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        position = self.user_data['position']
        if position == 'Заведующий':
            self.build_manager_view(self.content_frame)
        elif position == 'Складской рабочий':
            self.build_warehouse_view(self.content_frame)
        elif position == 'Старшая медсестра':
            self.build_nurse_view(self.content_frame)

    REPORT_PERIODS = [
        ("За 30 дней (месяц)", 30),
        ("За 90 дней (квартал)", 90),
        ("За 180 дней (полугодие)", 180),
        ("За 365 дней (год)", 365),
        ("За всё время", None),
    ]

    def build_manager_view(self, frame):
        banner = tk.Frame(frame, bg="#1565C0")
        banner.pack(fill="x")
        tk.Label(banner, text="Аналитическая отчётность по отделениям",
                 bg="#1565C0", fg="white", font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(12, 2))
        tk.Label(banner, text="Полученные медикаменты и их суммарная стоимость — контроль перерасхода бюджета",
                 bg="#1565C0", fg="#BBDEFB", font=("Arial", 10)).pack(anchor="w", padx=20, pady=(0, 12))

        period_bar = tk.Frame(frame, bg="#E3F2FD")
        period_bar.pack(fill="x", pady=(0, 10))
        tk.Label(period_bar, text="Период отчёта:", bg="#E3F2FD",
                 font=("Arial", 10, "bold")).pack(side="left", padx=(20, 10), pady=8)

        self.report_period_var = tk.IntVar(value=90)
        for label, days in self.REPORT_PERIODS:
            val = days if days is not None else -1
            tk.Radiobutton(period_bar, text=label, variable=self.report_period_var, value=val,
                           bg="#E3F2FD", activebackground="#E3F2FD",
                           font=("Arial", 9), command=self.load_manager_report).pack(side="left", padx=4, pady=6)

        kpi_bar = tk.Frame(frame)
        kpi_bar.pack(fill="x", pady=(0, 10))

        self.kpi_total_lbl = self._make_kpi_card(kpi_bar, "ОБЩИЙ РАСХОД, руб", "0.00", "#1565C0")
        self.kpi_qty_lbl = self._make_kpi_card(kpi_bar, "ВСЕГО ЕДИНИЦ", "0", "#2E7D32")
        self.kpi_top_lbl = self._make_kpi_card(kpi_bar, "ЛИДЕР ПО РАСХОДУ", "—", "#C62828")

        table_wrap = tk.Frame(frame)
        table_wrap.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Manager.Treeview", rowheight=28, font=("Arial", 10))
        style.configure("Manager.Treeview.Heading", font=("Arial", 10, "bold"),
                        background="#1565C0", foreground="white")

        self.manager_tree = ttk.Treeview(table_wrap, columns=("rank", "dept", "qty", "total"),
                                         show="headings", height=12, style="Manager.Treeview")
        self.manager_tree.heading("rank", text="#")
        self.manager_tree.heading("dept", text="Отделение")
        self.manager_tree.heading("qty", text="Получено (ед.)")
        self.manager_tree.heading("total", text="Сумма (руб)")
        self.manager_tree.column("rank", width=50, anchor="center")
        self.manager_tree.column("dept", width=300, anchor="w")
        self.manager_tree.column("qty", width=160, anchor="center")
        self.manager_tree.column("total", width=200, anchor="e")
        self.manager_tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.manager_tree.yview)
        scroll.pack(side="right", fill="y")
        self.manager_tree.configure(yscrollcommand=scroll.set)

        self.manager_tree.tag_configure("odd", background="#FFFFFF")
        self.manager_tree.tag_configure("even", background="#F5F9FF")
        self.manager_tree.tag_configure("top", background="#FFF3E0", font=("Arial", 10, "bold"))
        self.manager_tree.tag_configure("zero", foreground="#9E9E9E")

        self.load_manager_report()

    def _make_kpi_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=color, padx=2, pady=2)
        card.pack(side="left", expand=True, fill="x", padx=8)
        inner = tk.Frame(card, bg="white")
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, bg="white", fg=color,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
        value_lbl = tk.Label(inner, text=value, bg="white", fg="#212121",
                             font=("Arial", 18, "bold"))
        value_lbl.pack(anchor="w", padx=12, pady=(0, 8))
        return value_lbl

    def load_manager_report(self):
        for item in self.manager_tree.get_children():
            self.manager_tree.delete(item)

        period_val = self.report_period_var.get()
        days = None if period_val == -1 else period_val

        if days is None:
            where_period = ""
            params = []
        else:
            where_period = "AND so.operation_date >= CURRENT_DATE - (%s || ' days')::INTERVAL"
            params = [str(days)]

        conn = self.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT d.name,
                       COALESCE(SUM(so.quantity), 0)   AS total_qty,
                       COALESCE(SUM(so.total_cost), 0) AS total_cost
                FROM departments d
                LEFT JOIN stock_operations so
                       ON so.department_id = d.id
                      AND so.operation_type = 'выдача'
                      {where_period}
                WHERE d.id != 1
                GROUP BY d.name
                ORDER BY total_cost DESC, d.name
            """, params)
            rows = cursor.fetchall()
            cursor.close()
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка", str(e))
            conn.close()
            return
        finally:
            conn.close()

        grand_total = 0.0
        grand_qty = 0
        top_dept = "—"
        for i, row in enumerate(rows):
            name = row[0]
            qty = int(row[1] or 0)
            total = float(row[2] or 0)
            grand_total += total
            grand_qty += qty
            if i == 0 and total > 0:
                top_dept = name

            tags = []
            if total == 0 and qty == 0:
                tags.append("zero")
            elif i == 0 and total > 0:
                tags.append("top")
            else:
                tags.append("even" if i % 2 == 0 else "odd")

            rank = "1" if (i == 0 and total > 0) else str(i + 1)
            self.manager_tree.insert("", "end",
                                     values=(rank, name, qty, f"{total:,.2f}"),
                                     tags=tuple(tags))

        self.kpi_total_lbl.config(text=f"{grand_total:,.2f}")
        self.kpi_qty_lbl.config(text=f"{grand_qty:,}")
        self.kpi_top_lbl.config(text=top_dept, font=("Arial", 14, "bold"))

    def build_warehouse_view(self, frame):
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True)

        tab_receive = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_receive, text="Приемка партии")
        self.build_receive_tab(tab_receive)

        tab_issue = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_issue, text="Выдача в отделения")
        self.build_direct_issue_tab(tab_issue)

        tab_requests = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_requests, text="Заявки от отделений")
        self.build_requests_tab(tab_requests)

        tab_writeoff = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_writeoff, text="Списание просрочки")
        self.build_writeoff_tab(tab_writeoff)

    def build_receive_tab(self, frame):
        tk.Label(frame, text="Приемка новой партии препаратов", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(frame, text="Отсканируйте товар или введите данные вручную",
                 fg="gray", font=("Arial", 10)).pack(pady=5)

        form = tk.Frame(frame)
        form.pack(pady=10)

        tk.Label(form, text="Медикамент:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_med = ttk.Combobox(form, width=60, state="readonly")
        self.combo_med.grid(row=0, column=1, pady=5)

        tk.Label(form, text="Номер серии (Честный Знак):").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_batch_num = tk.Entry(form, width=30)
        self.entry_batch_num.grid(row=1, column=1, pady=5)

        tk.Label(form, text="Дата производства (ГГГГ-ММ-ДД):").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_prod_date = tk.Entry(form, width=20)
        self.entry_prod_date.grid(row=2, column=1, pady=5)

        tk.Label(form, text="Срок годности (ГГГГ-ММ-ДД):").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_exp_date = tk.Entry(form, width=20)
        self.entry_exp_date.grid(row=3, column=1, pady=5)

        tk.Label(form, text="Цена закупки за ед.:").grid(row=4, column=0, sticky="w", pady=5)
        self.entry_price = tk.Entry(form, width=20)
        self.entry_price.grid(row=4, column=1, pady=5)

        tk.Label(form, text="Количество:").grid(row=5, column=0, sticky="w", pady=5)
        self.entry_qty = tk.Entry(form, width=20)
        self.entry_qty.grid(row=5, column=1, pady=5)

        self.med_ids = []
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, trade_name, inn, form FROM medicaments ORDER BY trade_name")
                meds = cursor.fetchall()
                self.med_ids = [m[0] for m in meds]
                self.combo_med['values'] = [f"{m[1]} ({m[2]}, {m[3]})" for m in meds]
                if meds:
                    self.combo_med.current(0)
                cursor.close()
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                conn.close()

        tk.Button(frame, text="Оформить приход", command=self.process_receive,
                  bg="#4CAF50", fg="white", width=25, height=2).pack(pady=20)

    def process_receive(self):
        try:
            med_idx = self.combo_med.current()
            if med_idx == -1:
                messagebox.showerror("Ошибка", "Выберите медикамент!")
                return
            med_id = self.med_ids[med_idx]

            batch_num = self.entry_batch_num.get().strip()
            prod_date = self.entry_prod_date.get().strip()
            exp_date = self.entry_exp_date.get().strip()

            if not batch_num or not prod_date or not exp_date:
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return

            price = float(self.entry_price.get())
            qty = int(self.entry_qty.get())

            if price < 0:
                messagebox.showerror("Ошибка", "Цена не может быть отрицательной!")
                return
            if qty <= 0:
                messagebox.showerror("Ошибка", "Количество должно быть больше 0!")
                return

        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность заполнения числовых полей и дат!")
            return

        conn = self.get_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO batches (medicament_id, batch_number, production_date, expiration_date,
                                     purchase_price, initial_quantity, current_quantity)
                VALUES (%s, %s, %s, %s, %s, %s, 0) RETURNING id
            """, (med_id, batch_num, prod_date, exp_date, price, qty))
            batch_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO stock_operations (batch_id, employee_id, department_id, operation_type,
                                              operation_date, quantity, total_cost)
                VALUES (%s, %s, 1, 'приход', CURRENT_TIMESTAMP, %s, 0)
            """, (batch_id, self.user_data['tab'], qty))

            conn.commit()
            messagebox.showinfo("Успех", f"Партия {batch_num} успешно принята на склад!")
            self.entry_batch_num.delete(0, tk.END)
            self.entry_prod_date.delete(0, tk.END)
            self.entry_exp_date.delete(0, tk.END)
            self.entry_price.delete(0, tk.END)
            self.entry_qty.delete(0, tk.END)
        except psycopg2.Error as e:
            conn.rollback()
            err_msg = str(e)
            if "unique constraint" in err_msg.lower() and "batch_number" in err_msg.lower():
                messagebox.showerror("Ошибка", "Партия с таким номером уже существует!")
            elif "Срок годности препарата ИСТЕК" in err_msg:
                messagebox.showerror("ВНИМАНИЕ", "Приемка заблокирована! Срок годности препарата ИСТЕК!")
            else:
                messagebox.showerror("Ошибка БД", err_msg)
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def build_direct_issue_tab(self, frame):
        tk.Label(frame, text="Прямая выдача препаратов в отделения", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(frame, text="Отсканируйте товар или введите данные вручную",
                 fg="gray", font=("Arial", 10)).pack(pady=5)

        form = tk.Frame(frame)
        form.pack(pady=10)

        tk.Label(form, text="Партия:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_direct_batch = ttk.Combobox(form, width=70, state="readonly")
        self.combo_direct_batch.grid(row=0, column=1, pady=5)

        tk.Label(form, text="Отделение-получатель:").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_direct_dept = ttk.Combobox(form, width=70, state="readonly")
        self.combo_direct_dept.grid(row=1, column=1, pady=5)

        tk.Label(form, text="Количество:").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_direct_qty = tk.Entry(form, width=20)
        self.entry_direct_qty.grid(row=2, column=1, pady=5)

        self.direct_dept_ids = []
        self.direct_batch_ids = []
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM departments WHERE id != 1 ORDER BY name")
                depts = cursor.fetchall()
                self.direct_dept_ids = [d[0] for d in depts]
                self.combo_direct_dept['values'] = [d[1] for d in depts]
                if depts:
                    self.combo_direct_dept.current(0)

                cursor.execute("""
                    SELECT b.id, m.trade_name, b.batch_number, b.current_quantity, b.expiration_date
                    FROM batches b JOIN medicaments m ON b.medicament_id = m.id
                    WHERE b.current_quantity > 0
                    ORDER BY m.trade_name, b.expiration_date
                """)
                batches = cursor.fetchall()
                self.direct_batch_ids = [b[0] for b in batches]
                self.combo_direct_batch['values'] = [
                    f"{b[1]} | Серия: {b[2]} | Ост: {b[3]} | Годен до: {b[4]}{' ⚠ ПРОСРОЧЕНА' if b[4] < datetime.now().date() else ''}"
                    for b in batches
                ]
                if batches:
                    self.combo_direct_batch.current(0)

                cursor.close()
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                conn.close()

        tk.Button(frame, text="Выдать препарат", command=self.process_direct_issue,
                  bg="#2196F3", fg="white", width=25, height=2).pack(pady=20)

    def process_direct_issue(self):
        batch_idx = self.combo_direct_batch.current()
        dept_idx = self.combo_direct_dept.current()

        if batch_idx == -1 or dept_idx == -1:
            messagebox.showerror("Ошибка", "Выберите партию и отделение!")
            return

        try:
            qty = int(self.entry_direct_qty.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное количество (больше 0)!")
            return

        batch_id = self.direct_batch_ids[batch_idx]
        dept_id = self.direct_dept_ids[dept_idx]

        conn = self.get_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stock_operations (batch_id, employee_id, department_id, operation_type,
                                              operation_date, quantity, total_cost)
                VALUES (%s, %s, %s, 'выдача', CURRENT_TIMESTAMP, %s, 0)
            """, (batch_id, self.user_data['tab'], dept_id, qty))

            conn.commit()
            messagebox.showinfo("Успех", "Препарат успешно выдан в отделение!")
            self.entry_direct_qty.delete(0, tk.END)
            self.refresh_dashboard()
        except psycopg2.Error as e:
            conn.rollback()
            err_msg = str(e)
            if "Срок годности препарата ИСТЕК" in err_msg:
                self.show_expired_warning()
            elif "Недостаточное количество" in err_msg:
                messagebox.showerror("Ошибка остатков", err_msg)
            else:
                messagebox.showerror("Ошибка БД", err_msg)
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def build_requests_tab(self, frame):
        tk.Label(frame, text="Заявки от отделений (сообщения о потребности в препаратах)",
                 font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(frame, text="Выберите новую заявку в таблице и нажмите «Заявка выполнена» "
                             "после фактической отправки препарата со склада.",
                 fg="gray", font=("Arial", 10)).pack(pady=5)

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, pady=10)

        self.requests_tree = ttk.Treeview(tree_frame, columns=("num", "med", "dept", "qty", "date", "status"),
                                          show="headings", height=12)
        self.requests_tree.heading("num", text="№ заявки")
        self.requests_tree.heading("med", text="Медикамент")
        self.requests_tree.heading("dept", text="Отделение")
        self.requests_tree.heading("qty", text="Количество")
        self.requests_tree.heading("date", text="Дата заявки")
        self.requests_tree.heading("status", text="Статус")
        self.requests_tree.column("num", width=90, anchor="center")
        self.requests_tree.column("med", width=230)
        self.requests_tree.column("dept", width=170)
        self.requests_tree.column("qty", width=110, anchor="center")
        self.requests_tree.column("date", width=160, anchor="center")
        self.requests_tree.column("status", width=120, anchor="center")
        self.requests_tree.pack(fill="both", expand=True)

        tk.Button(frame, text="Заявка выполнена",
                  command=self.process_request,
                  bg="#4CAF50", fg="white", width=30, height=2).pack(pady=10)

        self.request_ids = []
        self.load_requests()

    def load_requests(self):
        for item in self.requests_tree.get_children():
            self.requests_tree.delete(item)

        conn = self.get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.id, m.trade_name, d.name, r.quantity, r.request_date, r.status
                FROM requests r
                JOIN medicaments m ON r.medicament_id = m.id
                JOIN departments d ON r.department_id = d.id
                ORDER BY
                    CASE r.status
                        WHEN 'новая' THEN 1
                        WHEN 'выполнена' THEN 2
                        ELSE 3
                    END,
                    r.request_date DESC
            """)
            for row in cursor.fetchall():
                req_id, med, dept, qty, date, status = row
                date_str = date.strftime('%Y-%m-%d %H:%M') if date else '-'
                status_text = ("✓ " + status) if status == 'выполнена' else status
                self.requests_tree.insert("", "end", iid=str(req_id),
                                          values=(f"#{req_id}", med, dept, qty, date_str, status_text))
            cursor.close()
        except psycopg2.Error as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            conn.close()

    def process_request(self):
        selection = self.requests_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заявку в таблице!")
            return

        request_id = int(selection[0])

        values = self.requests_tree.item(selection[0], "values")
        current_status = values[5] if len(values) >= 6 else ""
        if "выполнена" in current_status:
            messagebox.showinfo("Информация", f"Заявка #{request_id} уже выполнена.")
            return

        if not messagebox.askyesno(
                "Подтверждение",
                f"Отметить заявку #{request_id} как ВЫПОЛНЕННУЮ?\n\n"
                f"Убедитесь, что препарат уже фактически отправлен со склада в отделение."):
            return

        conn = self.get_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE requests
                SET status = 'выполнена', completed_date = CURRENT_TIMESTAMP
                WHERE id = %s AND status = 'новая'
            """, (request_id,))
            if cursor.rowcount == 0:
                conn.rollback()
                messagebox.showinfo("Информация",
                                    f"Заявка #{request_id} не найдена среди новых (возможно, уже выполнена).")
                self.load_requests()
                return
            conn.commit()
            messagebox.showinfo("Успех", f"Заявка #{request_id} отмечена как выполненная.")
            self.load_requests()
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def build_writeoff_tab(self, frame):
        tk.Label(frame, text="Списание просроченных партий", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(frame, text="Отсканируйте товар или выберите из списка",
                 fg="gray", font=("Arial", 10)).pack(pady=5)

        info_label = tk.Label(frame, text="Выберите партию для списания (утилизации):",
                              fg="red", font=("Arial", 10))
        info_label.pack(pady=5)

        self.combo_batches = ttk.Combobox(frame, width=80, state="readonly")
        self.combo_batches.pack(pady=5)

        self.batch_ids = []
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.id, COALESCE(m.trade_name, 'Неизвестный препарат'), b.batch_number,
                           b.current_quantity, b.expiration_date,
                           CASE WHEN b.expiration_date < CURRENT_DATE THEN '⚠ ПРОСРОЧЕНА' ELSE '' END
                    FROM batches b
                    LEFT JOIN medicaments m ON b.medicament_id = m.id
                    WHERE b.current_quantity > 0
                    ORDER BY b.expiration_date ASC
                """)
                batches = cursor.fetchall()
                self.batch_ids = [b[0] for b in batches]

                values_list = []
                for b in batches:
                    values_list.append(
                        f"{b[1]} | Серия: {b[2]} | Ост: {b[3]} | Годен до: {b[4]} {b[5]}"
                    )

                self.combo_batches['values'] = values_list
                if batches:
                    self.combo_batches.current(0)
                cursor.close()
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                conn.close()

        tk.Button(frame, text="Списать партию (утилизация)", command=self.process_writeoff,
                  bg="#f44336", fg="white", width=25, height=2).pack(pady=20)

    def process_writeoff(self):
        if not self.combo_batches.get():
            messagebox.showwarning("Внимание", "Нет доступных партий для утилизации.")
            return

        idx = self.combo_batches.current()
        if idx == -1 or idx >= len(self.batch_ids):
            messagebox.showerror("Ошибка", "Выберите партию для списания!")
            return
        batch_id = self.batch_ids[idx]

        conn = self.get_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("CALL write_off_expired_batch(%s, %s)", (batch_id, self.user_data['tab']))
            conn.commit()
            messagebox.showinfo("Успех", "Партия успешно утилизирована!")
            self.refresh_dashboard()
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def build_nurse_view(self, frame):
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True)

        tab_request = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_request, text="Создать заявку")
        self.build_create_request_tab(tab_request)

        tab_my_requests = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_my_requests, text="Мои заявки")
        self.build_my_requests_tab(tab_my_requests)

        tab_received = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(tab_received, text="Поступления в моё отделение")
        self.build_received_tab(tab_received)

    def build_create_request_tab(self, frame):
        tk.Label(frame, text="Формирование заявки на получение препаратов",
                 font=("Arial", 12, "bold")).pack(pady=10)

        if not self.user_data.get('has_potent_access'):
            tk.Label(frame,
                     text="У вас нет допуска к ПКУ: препараты строгого учёта недоступны для заказа.",
                     fg="#c62828", font=("Arial", 9, "bold")).pack(pady=(0, 5))

        form = tk.Frame(frame)
        form.pack(pady=10)

        tk.Label(form, text="Медикамент:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_req_med = ttk.Combobox(form, width=60, state="readonly")
        self.combo_req_med.grid(row=0, column=1, pady=5)

        tk.Label(form, text="Отделение-получатель:").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_req_dept = ttk.Combobox(form, width=60, state="readonly")
        self.combo_req_dept.grid(row=1, column=1, pady=5)

        tk.Label(form, text="Количество:").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_req_qty = tk.Entry(form, width=20)
        self.entry_req_qty.grid(row=2, column=1, pady=5)

        self.req_med_ids = []
        self.req_dept_ids = []
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                if self.user_data.get('has_potent_access'):
                    cursor.execute("""
                        SELECT id, trade_name, inn FROM medicaments ORDER BY trade_name
                    """)
                else:
                    cursor.execute("""
                        SELECT id, trade_name, inn FROM medicaments
                        WHERE group_id != 2
                        ORDER BY trade_name
                    """)
                meds = cursor.fetchall()
                self.req_med_ids = [m[0] for m in meds]
                self.combo_req_med['values'] = [f"{m[1]} ({m[2]})" for m in meds]
                if meds:
                    self.combo_req_med.current(0)

                cursor.execute("SELECT id, name FROM departments WHERE id != 1 ORDER BY name")
                depts = cursor.fetchall()

                my_dept_id = self.user_data.get('department_id')
                my_dept_name = next((d[1] for d in depts if d[0] == my_dept_id), None)

                self.req_dept_ids = [my_dept_id]
                if my_dept_name:
                    dept_labels = [f"Моё отделение ({my_dept_name})"]
                else:
                    dept_labels = ["Моё отделение"]
                for d in depts:
                    self.req_dept_ids.append(d[0])
                    dept_labels.append(d[1])

                self.combo_req_dept['values'] = dept_labels
                self.combo_req_dept.current(0)

                cursor.close()
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                conn.close()

        tk.Button(frame, text="Отправить заявку на склад", command=self.process_create_request,
                  bg="#4CAF50", fg="white", width=25, height=2).pack(pady=20)

    def process_create_request(self):
        med_idx = self.combo_req_med.current()
        dept_idx = self.combo_req_dept.current()

        if med_idx == -1 or dept_idx == -1:
            messagebox.showerror("Ошибка", "Выберите медикамент и отделение!")
            return

        try:
            qty = int(self.entry_req_qty.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное количество (больше 0)!")
            return

        med_id = self.req_med_ids[med_idx]
        dept_id = self.req_dept_ids[dept_idx]

        conn = self.get_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()

            if not self.user_data.get('has_potent_access'):
                cursor.execute("SELECT group_id FROM medicaments WHERE id = %s", (med_id,))
                grp = cursor.fetchone()
                if grp and grp[0] == 2:
                    messagebox.showerror(
                        "Доступ запрещён",
                        "Заказ запрещён!\n\nУ вас нет допуска к препаратам строгого учёта (ПКУ).\n"
                        "Обратитесь к заведующему аптекой.")
                    return

            cursor.execute("""
                INSERT INTO requests (medicament_id, department_id, employee_id, quantity, status)
                VALUES (%s, %s, %s, %s, 'новая')
            """, (med_id, dept_id, self.user_data['tab'], qty))
            conn.commit()
            messagebox.showinfo("Успех", "Заявка успешно отправлена на склад! Ожидайте выполнения.")
            self.entry_req_qty.delete(0, tk.END)
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def build_my_requests_tab(self, frame):
        tk.Label(frame, text="Мои заявки и их статус", font=("Arial", 12, "bold")).pack(pady=10)

        tree = ttk.Treeview(frame, columns=("num", "med", "dept", "qty", "date", "status", "completed"),
                            show="headings", height=15)
        tree.heading("num", text="№ заявки")
        tree.heading("med", text="Медикамент")
        tree.heading("dept", text="Отделение")
        tree.heading("qty", text="Кол-во")
        tree.heading("date", text="Дата заявки")
        tree.heading("status", text="Статус")
        tree.heading("completed", text="Дата выполнения")
        tree.column("num", width=80, anchor="center")
        tree.column("med", width=230)
        tree.column("dept", width=170)
        tree.column("qty", width=90, anchor="center")
        tree.column("date", width=160, anchor="center")
        tree.column("status", width=110, anchor="center")
        tree.column("completed", width=160, anchor="center")
        tree.pack(fill="both", expand=True, pady=10)

        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT r.id, m.trade_name, d.name, r.quantity, r.request_date, r.status, r.completed_date
                    FROM requests r
                    JOIN medicaments m ON r.medicament_id = m.id
                    JOIN departments d ON r.department_id = d.id
                    WHERE r.employee_id = %s
                    ORDER BY r.request_date DESC
                """, (self.user_data['tab'],))
                for row in cursor.fetchall():
                    req_date = row[4].strftime('%Y-%m-%d %H:%M') if row[4] else '-'
                    completed = row[6].strftime('%Y-%m-%d %H:%M') if row[6] else '-'
                    tree.insert("", "end", values=(f"#{row[0]}", row[1], row[2], row[3],
                                                    req_date, row[5], completed))
                cursor.close()
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                conn.close()

    def build_received_tab(self, frame):
        tk.Label(frame, text="Поступления медикаментов в моё отделение",
                 font=("Arial", 12, "bold")).pack(pady=(10, 0))
        tk.Label(frame, text="Всего получено по каждому препарату за последние 90 дней (квартал)",
                 fg="gray", font=("Arial", 10)).pack(pady=(0, 10))

        tree = ttk.Treeview(frame, columns=("med", "inn", "form", "qty", "cost"),
                            show="headings", height=15)
        tree.heading("med", text="Препарат")
        tree.heading("inn", text="МНН")
        tree.heading("form", text="Форма")
        tree.heading("qty", text="Получено (ед.)")
        tree.heading("cost", text="Стоимость (руб)")
        tree.column("med", width=230)
        tree.column("inn", width=180)
        tree.column("form", width=130)
        tree.column("qty", width=120, anchor="center")
        tree.column("cost", width=140, anchor="center")
        tree.pack(fill="both", expand=True, pady=10)

        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT m.trade_name, m.inn, m.form,
                           SUM(so.quantity)   AS total_qty,
                           SUM(so.total_cost) AS total_cost
                    FROM stock_operations so
                    JOIN batches b     ON so.batch_id = b.id
                    JOIN medicaments m ON b.medicament_id = m.id
                    WHERE so.operation_type = 'выдача'
                      AND so.department_id = %s
                      AND so.operation_date >= CURRENT_DATE - INTERVAL '90 days'
                    GROUP BY m.trade_name, m.inn, m.form
                    ORDER BY total_qty DESC
                """, (self.user_data['department_id'],))
                rows = cursor.fetchall()
                grand_qty = 0
                grand_cost = 0
                for row in rows:
                    qty = row[3] or 0
                    cost = row[4] or 0
                    grand_qty += int(qty)
                    grand_cost += float(cost)
                    tree.insert("", "end", values=(row[0], row[1], row[2], qty, f"{cost:,.2f}"))
                cursor.close()

                if rows:
                    tk.Label(frame,
                             text=f"ИТОГО за 90 дней: {grand_qty} ед. на сумму {grand_cost:,.2f} руб",
                             font=("Arial", 12, "bold"), fg="#1565C0").pack(pady=10)
                else:
                    tk.Label(frame,
                             text="За последние 90 дней поступлений в ваше отделение не было.",
                             fg="gray", font=("Arial", 11)).pack(pady=10)
            except psycopg2.Error as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = MedStockApp(root)
    root.mainloop()
