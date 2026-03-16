import psycopg2
from psycopg2 import sql
import datetime

class BusinessProcesses:
    def __init__(self, connection):
        self.conn = connection
        self.cursor = connection.cursor()
    
    # КЛИЕНТ
    def client_view_catalog(self):
        print("\n" + "="*50)
        print("ПРОСМОТР КАТАЛОГА ТОВАРОВ")
        print("="*50)
        
        try:
            # категории товаров
            self.cursor.execute("""
                SELECT category_id, name 
                FROM Category 
                ORDER BY category_id
            """)
            categories = self.cursor.fetchall()
            
            if not categories:
                print(" ❗ Категории недоступны")
                return
            
            print("\nКАТЕГОРИИ ТОВАРОВ:")
            for cat_id, cat_name in categories:
                print(f"{cat_id}. {cat_name}")
            
            # выбор категории
            try:
                cat_choice = int(input("\nВыберите категорию (ID): "))
            except ValueError:
                print(" ❗ Неверный ввод")
                self.conn.rollback()
                return
            
            # товары выбранной категории
            self.cursor.execute("""
                SELECT p.product_id, p.name, p.price, p.measure_unit,
                       c.name as category_name
                FROM Product p
                JOIN Category c ON p.category = c.category_id
                WHERE p.category = %s
                ORDER BY p.product_id
            """, (cat_choice,))
            
            products = self.cursor.fetchall()
            
            if not products:
                print(" ❗ В этой категории нет товаров")
                return
            
            print(f"\nТОВАРЫ В КАТЕГОРИИ '{products[0][4]}':")
            print("-"*60)
            print(f"{'ID':<5} {'Название':<25} {'Цена':<10} {'Ед.изм.':<8}")
            print("-"*60)
            
            for product_id, name, price, unit, _ in products:
                print(f"{product_id:<5} {name:<25} {price:<10} {unit:<8}")
            
            # доступность товаров в филиалах
            print("\nДОСТУПНОСТЬ В ФИЛИАЛАХ:")
            print("-"*60)
            
            for product_id, name, _, _, _ in products:
                self.cursor.execute("""
                    SELECT b.address, bp.product_amount
                    FROM Branch_product bp
                    JOIN Branch b ON bp.branch = b.branch_id
                    WHERE bp.product = %s AND bp.product_amount > 0
                    ORDER BY b.address
                """, (product_id,))
                
                branches = self.cursor.fetchall()
                if branches:
                    print(f"\n{name}:")
                    for address, amount in branches:
                        print(f"  • {address}: {amount} шт.")
                else:
                    print(f"\n{name}: Нет в наличии")
        
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()
    
    # ПРОДАВЕЦ
    # идентификация продавца по ФИО
    def authenticate_seller(self):
        print("\nВведите свои данные для идентификации")
        last_name = input("Фамилия: ").strip()
        first_name = input("Имя: ").strip()
        middle_name = input("Отчество (Enter, если нет): ").strip() or None

        if not last_name or not first_name:
            print(" ❗ Фамилия и имя обязательны")
            return None

        self.cursor.execute("""
            SELECT 
                e.employee_id,
                e.first_name,
                e.last_name,
                e.middle_name,
                e.branch,
                b.address
            FROM Employee e
            JOIN Position p ON e.position = p.position_id
            JOIN Branch b ON e.branch = b.branch_id
            WHERE 
                e.last_name = %s 
                AND e.first_name = %s 
                AND (e.middle_name = %s OR (e.middle_name IS NULL AND %s IS NULL))
                AND p.name = 'Продавец'
        """, (last_name, first_name, middle_name, middle_name))

        row = self.cursor.fetchone()
        if row:
            return {
                'employee_id': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'middle_name': row[3],
                'branch_id': row[4],
                'branch_address': row[5]
            }
        else:
            print(" ❗ Сотрудник с такими ФИО не найден или на другой должности")
            return None

    # регистрация нового клиента
    def register_new_customer(self):
        print("\n" + "=" * 50)
        print("РЕГИСТРАЦИЯ НОВОГО КЛИЕНТА")
        print("=" * 50)

        try:
            print("\nЗаполните данные клиента:")
            print("-" * 40)

            # ФИО
            first_name = input("Имя: ").strip()
            if not first_name:
                print(" ❗ Имя обязательно")
                return None

            last_name = input("Фамилия: ").strip()
            if not last_name:
                print(" ❗ Фамилия обязательна")
                return None

            middle_name = input("Отчество (Enter, если нет): ").strip()
            middle_name = middle_name if middle_name else None

            # телефон
            while True:
                phone = input("Телефон: ").strip()
                if not phone:
                    print(" ❗ Телефон обязателен")
                    continue

                # проверка уникальности
                self.cursor.execute("""
                    SELECT customer_id FROM Customer WHERE phone_number = %s
                """, (phone,))

                if self.cursor.fetchone():
                    print(" ❗ Этот телефон уже зарегистрирован")
                    print("1. Ввести другой телефон")
                    print("2. Отменить регистрацию")
                    choice = input("Выберите: ")
                    if choice == '2':
                        return None
                    continue

                break

            # сохранение
            self.cursor.execute("""
                INSERT INTO Customer (
                    first_name, last_name, middle_name, phone_number
                ) VALUES (%s, %s, %s, %s)
                RETURNING customer_id
            """, (first_name, last_name, middle_name, phone))

            customer_id = self.cursor.fetchone()[0]
            self.conn.commit()

            print(f"\nКлиент успешно зарегистрирован!")
            print(f"   ID клиента: {customer_id}")
            print(f"   ФИО: {last_name} {first_name} {middle_name or ''}")
            print(f"   Телефон: {phone}")

            return customer_id

        except Exception as e:
            print(f" ❗ Ошибка при регистрации: {e}")
            self.conn.rollback()
            return None

    # выбор существующего клиента по телефону ИЛИ регистрация нового
    def select_or_create_customer(self):
        while True:
            phone = input("Телефон клиента (Enter, чтобы зарегистрировать нового): ").strip()
            if not phone:
                # регистрация нового клиента
                customer_id = self.register_new_customer()
                if customer_id is not None:
                    return customer_id
                else:
                    print(" ❗ Не удалось зарегистрировать клиента")
                    return None

            else:
                # поиск существующего клиента
                self.cursor.execute("""
                    SELECT customer_id, first_name, last_name 
                    FROM Customer 
                    WHERE phone_number = %s
                """, (phone,))
                result = self.cursor.fetchone()
                if result:
                    customer_id, first_name, last_name = result
                    print(f"Найден клиент: {last_name} {first_name} (ID: {customer_id})")
                    return customer_id
                else:
                    print(" ❗ Клиент с таким телефоном не найден")
                    choice = input("1. Ввести другой телефон\n2. Зарегистрировать нового клиента\nВаш выбор: ")
                    if choice == '2':
                        customer_id = self.register_new_customer()
                        if customer_id is not None:
                            return customer_id
                        else:
                            print(" ❗ Не удалось зарегистрировать клиента")
                            return None
                    elif choice != '1':
                        print(" Отмена")
                        return None

    # создание нового заказа
    def create_new_order(self, seller_info):
        print("\n" + "="*50)
        print("СОЗДАНИЕ НОВОГО ЗАКАЗА")
        print("="*50)
        
        employee_id = seller_info['employee_id']
        branch_id = seller_info['branch_id']
        branch_address = seller_info['branch_address']
        
        try:
            # выбор клиента
            print("\nВЫБОР КЛИЕНТА")
            print("-"*40)
            
            customer_id = self.select_or_create_customer()
            if not customer_id:
                return
            
            # создание заказа
            self.cursor.execute("""
                INSERT INTO "Order" (date, sum, customer, employee)
                VALUES (CURRENT_DATE, 0.01, %s, %s)
                RETURNING order_id
            """, (customer_id, employee_id))
            
            order_id = self.cursor.fetchone()[0]
            print(f" Создан заказ #{order_id}")
            
            # добавление товаров
            cart = []
            
            while True:
                print("\n" + "="*40)
                print(f"ЗАКАЗ #{order_id} - ДОБАВЛЕНИЕ ТОВАРОВ")
                print("="*40)
                
                # показать доступные товары
                self.cursor.execute("""
                    SELECT 
                        p.product_id,
                        p.name,
                        p.price,
                        p.measure_unit,
                        COALESCE(bp.product_amount, 0) as available,
                        c.name as category
                    FROM Product p
                    JOIN Category c ON p.category = c.category_id
                    LEFT JOIN Branch_product bp ON p.product_id = bp.product AND bp.branch = %s
                    WHERE COALESCE(bp.product_amount, 0) > 0
                    ORDER BY c.name, p.product_id
                """, (branch_id,))
                
                products = self.cursor.fetchall()
                
                if not products:
                    print(" ❗ В филиале нет товаров в наличии")
                    break
                
                print("\n ДОСТУПНЫЕ ТОВАРЫ:")
                current_category = None
                for prod_id, name, price, unit, available, category in products:
                    if category != current_category:
                        print(f"\n{category}:")
                        current_category = category
                    print(f"  ID:{prod_id:<3} {name:<25} {price:>6.2f} руб. ({available} {unit} в наличии)")
                
                print("\n1. Добавить товар по ID")
                print("2. Посмотреть корзину")
                print("3. Завершить оформление")
                print("0. Отменить заказ")
                
                choice = input("\nВыберите: ")
                
                if choice == '1':
                    try:
                        prod_id = int(input("ID товара: "))
                        from decimal import Decimal
                        quantity = Decimal(input("Количество: "))
                        
                        if quantity <= 0:
                            print(" ❗ Количество должно быть больше 0")
                            continue
                        
                        # находим товар
                        product = next((p for p in products if p[0] == prod_id), None)
                        if not product:
                            print(" ❗ Товар не найден")
                            continue
                        
                        prod_id, name, price, unit, available, category = product
                        
                        if quantity > available:
                            print(f" ❗ Недостаточно товара. В наличии: {available} {unit}")
                            continue
                        
                        # добавляем в корзину
                        existing = next((item for item in cart if item['product_id'] == prod_id), None)
                        if existing:
                            existing['quantity'] += quantity
                            existing['total'] = existing['quantity'] * price
                            print(f" Добавлено еще {quantity} {unit} {name}")
                        else:
                            cart.append({
                                'product_id': prod_id,
                                'name': name,
                                'price': price,
                                'unit': unit,
                                'quantity': quantity,
                                'total': quantity * price
                            })
                            print(f" Добавлено: {name} x{quantity} {unit}")
                        
                    except ValueError:
                        print(" ❗ Неверный формат данных")
                        self.conn.rollback()

                    input("\nНажмите Enter для продолжения...")

                elif choice == '2':
                    if not cart:
                        print("Корзина пуста")
                    else:
                        print("\n🛒 КОРЗИНА:")
                        total = 0
                        for i, item in enumerate(cart, 1):
                            print(f"{i}. {item['name']:<25} x{item['quantity']:<5} {item['unit']:<4} = {item['total']:>7.2f} руб.")
                            total += item['total']
                        print(f"ИТОГО: {total:>45.2f} руб.")

                    input("\nНажмите Enter для продолжения...")

                elif choice == '3':
                    if not cart:
                        print(" ❗ Корзина пуста! Добавьте товары.")
                        continue
                    
                    # Подтверждение и сохранение
                    total = sum(item['total'] for item in cart)
                    
                    print("\n" + "="*50)
                    print(f" ✔️ ПОДТВЕРЖДЕНИЕ ЗАКАЗА #{order_id}")
                    print("="*50)
                    print(f"Клиент ID: {customer_id}")
                    print(f"Сумма: {total:.2f} руб.")
                    print("-"*50)
                    
                    confirm = input("Оформить заказ? (да/нет): ").lower()
                    if confirm in ['да', 'д', 'yes', 'y']:
                        # Сохраняем товары
                        for item in cart:
                            self.cursor.execute("""
                                INSERT INTO Order_composition (order_id, product, product_amount)
                                VALUES (%s, %s, %s)
                            """, (order_id, item['product_id'], item['quantity']))
                        
                        # Обновляем сумму
                        self.cursor.execute("""
                            UPDATE "Order" SET sum = %s WHERE order_id = %s
                        """, (total, order_id))
                        
                        self.conn.commit()
                        
                        # Печать чека
                        print("\n" + "="*60)
                        print(" " * 20 + "ЧЕК")
                        print("="*60)
                        print(f"Номер: {order_id}")
                        print(f"Дата: {datetime.date.today()}")
                        print(f"Кассир: {seller_info['last_name']} {seller_info['first_name']}")
                        print(f"Филиал: {branch_address}")
                        print("-"*60)
                        for item in cart:
                            print(f"{item['name']:<25} {item['quantity']:>5} x {item['price']:>6.2f} = {item['total']:>8.2f}")
                        print("-"*60)
                        print(f"ИТОГО: {total:>48.2f} руб.")
                        print("="*60)
                        print(" ✔️ Заказ оформлен успешно!")
                        
                        break
                    else:
                        print("Продолжаем редактирование")
                
                    input("\nНажмите Enter для продолжения...")

                elif choice == '0':
                    confirm = input(" ❗ Отменить заказ? Все данные будут потеряны (да/нет): ").lower()
                    if confirm in ['да', 'д', 'yes', 'y']:
                        self.conn.rollback()
                        print(" ❗ Заказ отменен")
                        return
                    
                else:
                    print(" ❗ Неверный выбор")
        
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()  
    
    # МЕНЕДЖЕР
    # добавление нового товара
    def add_new_product(self):
        print("\nДОБАВЛЕНИЕ НОВОГО ТОВАРА")
        
        # выбор категории
        self.cursor.execute("SELECT category_id, name FROM Category ORDER BY category_id")
        categories = self.cursor.fetchall()
        
        print("\n Доступные категории:")
        for cat_id, cat_name in categories:
            print(f"{cat_id}. {cat_name}")
        
        try:
            category_id = int(input("\nВыберите категорию (ID): "))
            
            # ввод данных о товаре
            name = input("Название товара: ")
            price = float(input("Цена: "))
            
            print("\nЕдиницы измерения: шт, кг, г, мл")
            measure_unit = input("Единица измерения: ")
            
            self.cursor.execute("""
                INSERT INTO Product (name, category, measure_unit, price)
                VALUES (%s, %s, %s, %s)
                RETURNING product_id
            """, (name, category_id, measure_unit, price))
            
            product_id = self.cursor.fetchone()[0]
            print(f" ✔️ Товар '{name}' добавлен (ID: {product_id})")
            
            # добавление во все филиалы
            self.cursor.execute("SELECT branch_id FROM Branch")
            branches = self.cursor.fetchall()
            
            for (branch_id,) in branches:
                self.cursor.execute("""
                    INSERT INTO Branch_product (branch, product, product_amount)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (branch, product) DO NOTHING
                """, (branch_id, product_id, 0))
            
            # добавление состава
            add_ingredients = input("\nДобавить состав? (да/нет): ").lower()
            if add_ingredients in ['да', 'д', 'y', 'yes']:
                print("\nДОБАВЛЕНИЕ СОСТАВА ТОВАРА:")
                
                while True:
                    # показ ингредиентов
                    self.cursor.execute("SELECT ingredient_id, name FROM Ingredient ORDER BY ingredient_id")
                    ingredients = self.cursor.fetchall()
                    
                    print("\nДоступные ингредиенты:")
                    for ing_id, ing_name in ingredients:
                        print(f"{ing_id}. {ing_name}")
                    
                    try:
                        ingredient_id = int(input("\nВыберите ингредиент ID (0 - завершить): "))
                        if ingredient_id == 0:
                            break
                        
                        amount = float(input("Количество: "))
                        
                        self.cursor.execute("""
                            INSERT INTO Product_composition (product, ingredient, ingredient_amount)
                            VALUES (%s, %s, %s)
                        """, (product_id, ingredient_id, amount))
                        
                        print(" ✔️ Ингредиент добавлен")
                        
                    except ValueError:
                        print(" ❗ Неверный ввод")
            
            self.conn.commit()
            print(f"\n ✔️ Товар успешно добавлен!")
            
        except ValueError:
            print(" ❗ Неверный формат данных")
            self.conn.rollback()
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()
    
    # изменение цены товара
    def update_product_price(self):
        print("\nИЗМЕНЕНИЕ ЦЕНЫ ТОВАРА")
        
        # текущие товары
        self.cursor.execute("""
            SELECT p.product_id, p.name, p.price, c.name as category
            FROM Product p
            JOIN Category c ON p.category = c.category_id
            ORDER BY p.product_id
        """)
        
        products = self.cursor.fetchall()
        
        if not products:
            print(" ❗ Нет товаров в базе")
            return
        
        print(f"{'ID':<5} {'Название':<25} {'Цена':<10} {'Категория':<15}")
        print("-"*60)
        for prod_id, name, price, category in products:
            print(f"{prod_id:<5} {name:<25} {price:<10} {category:<15}")
        
        try:
            product_id = int(input("\nВыберите ID товара (0 - назад): "))
            
            if product_id == 0:
                print("Возврат в меню менеджера")
                return

            new_price = float(input("Новая цена: "))
            
            if new_price <= 0:
                print(" ❗ Цена должна быть больше 0")
                return
            
            self.cursor.execute("""
                UPDATE Product SET price = %s WHERE product_id = %s
            """, (new_price, product_id))
            
            self.conn.commit()
            print(f" ✔️ Цена товара обновлена")
            
        except ValueError:
            print(" ❗ Неверный формат данных")
            self.conn.rollback()
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()
    
    # просмотр отчета по популярным товарам
    def view_popular_products_report(self):
        print("\nОТЧЕТ ПО ПОПУЛЯРНЫМ ТОВАРАМ")
        
        try:
            days = int(input("За сколько дней показать отчет? (0 - за все время): "))
            
            start_date = None
            if days > 0:
                start_date = datetime.date.today() - datetime.timedelta(days=days)
            
            # используем функцию из бд
            self.cursor.execute("""
                SELECT * FROM get_popular_products(%s, NULL, 10)
            """, (start_date,))
            
            results = self.cursor.fetchall()
            
            if not results:
                print(" ❗ Нет данных за указанный период")
                return
            
            print("\n" + "="*70)
            print("ТОП-10 ПОПУЛЯРНЫХ ТОВАРОВ")
            print("="*70)
            print(f"{'Название':<25} {'Продано':<15} {'Выручка':<15} {'ID':<10}")
            print("-"*70)
            
            total_revenue = 0
            for product_id, name, sold, revenue in results:
                print(f"{name:<25} {sold:<15.2f} {revenue:<15.2f} {product_id:<10}")
                total_revenue += revenue
            
            print("-"*70)
            print(f"ОБЩАЯ ВЫРУЧКА: {total_revenue:>45.2f} руб.")
            print("="*70)
            
        except ValueError:
            print(" ❗ Неверный формат данных")
            self.conn.rollback()
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()
    
    # АДМИНИСТРАТОР
    # финансовый отчет за период
    def financial_report(self):
        print("\n ФИНАНСОВЫЙ ОТЧЕТ")
        
        try:
            start_date = input("Начальная дата (ГГГГ-ММ-ДД или Enter - за месяц): ")
            end_date = input("Конечная дата (ГГГГ-ММ-ДД или Enter - сегодня): ")
            
            if not start_date:
                start_date = datetime.date.today().replace(day=1)
            else:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            
            if not end_date:
                end_date = datetime.date.today()
            else:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            
            # общая выручка
            self.cursor.execute("""
                SELECT COALESCE(SUM(sum), 0) 
                FROM "Order" 
                WHERE date BETWEEN %s AND %s
            """, (start_date, end_date))
            
            total_revenue = self.cursor.fetchone()[0]
            
            # выручка по категориям
            self.cursor.execute("""
                SELECT c.name, SUM(o.sum) as revenue
                FROM "Order" o
                JOIN Order_composition oc ON o.order_id = oc.order_id
                JOIN Product p ON oc.product = p.product_id
                JOIN Category c ON p.category = c.category_id
                WHERE o.date BETWEEN %s AND %s
                GROUP BY c.category_id, c.name
                ORDER BY revenue DESC
            """, (start_date, end_date))
            
            category_revenue = self.cursor.fetchall()
            
            # количество заказов
            self.cursor.execute("""
                SELECT COUNT(*), COUNT(DISTINCT customer)
                FROM "Order" 
                WHERE date BETWEEN %s AND %s
            """, (start_date, end_date))
            
            order_count, unique_customers = self.cursor.fetchone()
            
            print("\n" + "="*60)
            print(f"ФИНАНСОВЫЙ ОТЧЕТ за период {start_date} - {end_date}")
            print("="*60)
            print(f"Общая выручка: {total_revenue:.2f} руб.")
            print(f"Количество заказов: {order_count}")
            print(f"Уникальных клиентов: {unique_customers}")
            print("-"*60)
            print("ВЫРУЧКА ПО КАТЕГОРИЯМ:")
            
            for category, revenue in category_revenue:
                percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
                print(f"  • {category}: {revenue:.2f} руб. ({percentage:.1f}%)")
            
            # средний чек
            avg_check = total_revenue / order_count if order_count > 0 else 0
            print(f"\nСредний чек: {avg_check:.2f} руб.")
            print("="*60)
            
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()
    
    # добавление нового сотрудника
    def add_new_employee(self):
        print("\n ДОБАВЛЕНИЕ НОВОГО СОТРУДНИКА")
        
        try:
            first_name = input("Имя: ")
            last_name = input("Фамилия: ")
            middle_name = input("Отчество (опционально): ") or None
            
            # выбор должности
            self.cursor.execute("SELECT position_id, name FROM Position ORDER BY position_id")
            positions = self.cursor.fetchall()
            
            print("\nДоступные должности:")
            for pos_id, pos_name in positions:
                print(f"{pos_id}. {pos_name}")
            
            position_id = int(input("Выберите должность (ID): "))
            
            # выбор филиала
            self.cursor.execute("SELECT branch_id, address FROM Branch ORDER BY branch_id")
            branches = self.cursor.fetchall()
            
            print("\nДоступные филиалы:")
            for branch_id, address in branches:
                print(f"{branch_id}. {address}")
            
            branch_id = int(input("Выберите филиал (ID): "))
            
            # добавление сотрудника
            self.cursor.execute("""
                INSERT INTO Employee (first_name, last_name, middle_name, position, branch, hire_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING employee_id
            """, (first_name, last_name, middle_name, position_id, branch_id, datetime.date.today()))
            
            employee_id = self.cursor.fetchone()[0]
            self.conn.commit()
            
            print(f" ✔️ Сотрудник добавлен (ID: {employee_id})")
            
        except ValueError:
            print(" ❗ Неверный формат данных")
            self.conn.rollback()
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()

    # история заказов клиента
    def customer_order_history(self):
        print("\n" + "="*50)
        print(" ИСТОРИЯ ЗАКАЗОВ КЛИЕНТА")
        print("="*50)
        
        try:
            # поиск клиента
            phone = input("Введите номер телефона клиента: ")
            
            self.cursor.execute("""
                SELECT customer_id, first_name, last_name 
                FROM Customer 
                WHERE phone_number = %s
            """, (phone,))
            
            customer = self.cursor.fetchone()
            
            if not customer:
                print(" ❗ Клиент не найден")
                return
            
            customer_id, first_name, last_name = customer
            print(f"\n Клиент: {last_name} {first_name} (ID: {customer_id})")
            
            # история заказов
            self.cursor.execute("""
                SELECT 
                    o.order_id,
                    o.date,
                    o.sum,
                    e.first_name || ' ' || e.last_name as seller,
                    b.address as branch
                FROM "Order" o
                JOIN Employee e ON o.employee = e.employee_id
                JOIN Branch b ON e.branch = b.branch_id
                WHERE o.customer = %s
                ORDER BY o.date DESC
            """, (customer_id,))
            
            orders = self.cursor.fetchall()
            
            if not orders:
                print(" У клиента нет заказов")
                return
            
            print(f"\n Всего заказов: {len(orders)}")
            print("="*90)
            print(f"{'ID':<6} {'Дата':<12} {'Сумма':<12} {'Продавец':<20} {'Филиал':<40}")
            print("-"*90)
            
            total_spent = 0
            for order_id, date, sum, seller, branch in orders:
                date_str = str(date)
                if len(branch) > 38:
                    branch = branch[:35] + "..."
                
                print(f"{order_id:<6} {date_str:<12} {sum:<12.2f} {seller:<20} {branch:<40}")
                total_spent += sum
            
            print("-"*90)
            print(f"Общая сумма покупок: {total_spent:>68.2f} руб.")
            
            print("\n ПОДРОБНОСТИ ЗАКАЗА:")
            try:
                order_id = int(input("Введите ID заказа для деталей (0 - пропустить): "))
                
                if order_id > 0:
                    self.cursor.execute("""
                        SELECT 
                            p.name,
                            oc.product_amount,
                            p.measure_unit,
                            p.price,
                            (oc.product_amount * p.price) as total
                        FROM Order_composition oc
                        JOIN Product p ON oc.product = p.product_id
                        WHERE oc.order_id = %s
                        ORDER BY p.name
                    """, (order_id,))
                    
                    items = self.cursor.fetchall()
                    
                    if items:
                        print(f"\n🧾 Состав заказа #{order_id}:")
                        print("-"*70)
                        print(f"{'Товар':<25} {'Кол-во':<8} {'Ед.':<4} {'Цена':<10} {'Сумма':<10}")
                        print("-"*70)
                        
                        order_total = 0
                        for name, amount, unit, price, total in items:
                            print(f"{name:<25} {amount:<8.2f} {unit:<4} {price:<10.2f} {total:<10.2f}")
                            order_total += total
                        
                        print("-"*70)
                        print(f"ИТОГО ЗА ЗАКАЗ: {order_total:>52.2f} руб.")
                    else:
                        print(f" ❗ Заказ #{order_id} не найден")
            except ValueError:
                print("Пропуск деталей")
                self.conn.rollback()
                
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()
    
    # отчет по использованию ингредиентов
    def ingredients_report(self):
        print("\n" + "="*50)
        print(" ОТЧЕТ ПО ИСПОЛЬЗОВАНИЮ ИНГРЕДИЕНТОВ")
        print("="*50)
        
        try:
            start_date = input("Начальная дата (ГГГГ-ММ-ДД или Enter - за месяц): ")
            end_date = input("Конечная дата (ГГГГ-ММ-ДД или Enter - сегодня): ")
            
            if not start_date:
                start_date = datetime.date.today().replace(day=1)
            else:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            
            if not end_date:
                end_date = datetime.date.today()
            else:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            
            # отчет по ингредиентам
            self.cursor.execute("""
                SELECT 
                    i.name as ingredient,
                    i.measure_unit,
                    SUM(pc.ingredient_amount * oc.product_amount) as total_used,
                    COUNT(DISTINCT o.order_id) as orders_count,
                    COUNT(DISTINCT p.product_id) as products_count
                FROM Order_composition oc
                JOIN "Order" o ON oc.order_id = o.order_id
                JOIN Product p ON oc.product = p.product_id
                JOIN Product_composition pc ON p.product_id = pc.product
                JOIN Ingredient i ON pc.ingredient = i.ingredient_id
                WHERE o.date BETWEEN %s AND %s
                GROUP BY i.ingredient_id, i.name, i.measure_unit
                ORDER BY total_used DESC
            """, (start_date, end_date))
            
            ingredients = self.cursor.fetchall()
            
            if not ingredients:
                print(" ❗ Нет данных за указанный период")
                return
            
            print(f"\n Период: {start_date} - {end_date}")
            print("="*80)
            print(f"{'Ингредиент':<25} {'Использовано':<15} {'Ед.изм.':<10} {'Заказов':<10} {'Товаров':<10}")
            print("-"*80)
            
            for ingredient, unit, used, orders, products in ingredients:
                print(f"{ingredient:<25} {used:<15.2f} {unit:<10} {orders:<10} {products:<10}")
            
            print("-"*80)
            print(f"Всего использовано ингредиентов: {len(ingredients)}")
            
        except ValueError:
            print(" ❗ Неверный формат даты")
            self.conn.rollback()
        except Exception as e:
            print(f" ❗ Ошибка: {e}")
            self.conn.rollback()