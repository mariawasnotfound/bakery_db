import sys
import os
from db import DatabaseConnection
from processes import BusinessProcesses

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 50)
    print("            ПЕКАРНЯ-КОНДИТЕРСКАЯ 🍰")
    print("=" * 50)

# определение типа пользователя по роли
def determine_user_type(db_user):
    role_map = {
        'client_role': 'покупатель',
        'seller_role': 'продавец',
        'manager_role': 'менеджер',
        'admin_role': 'администратор'
    }
    return role_map.get(db_user)

def main():
    db = DatabaseConnection()
    
    # авторизация
    clear_screen()
    print_header()
    print("\nВХОД В СИСТЕМУ")
    print("-" * 40)
    conn = db.connect_by_credentials()
    if not conn:
        print("\n ❗ Доступ запрещен")
        input("\nНажмите Enter для выхода...")
        return

    current_user = conn.get_dsn_parameters()['user']
    user_type = determine_user_type(current_user)
    if not user_type:
        print(" ❗ Неизвестная роль пользователя")
        db.disconnect()
        return

    bp = BusinessProcesses(conn)
    print(f"\n ✔️ Добро пожаловать! Вы вошли как {user_type.upper()}")

    session_active = True
    seller_info = None

    try:
        while session_active:
            clear_screen()
            print_header()
            print(f"\n Текущая роль: {user_type.upper()}")
            print("-" * 40)

            if user_type == 'покупатель':
                print("1.  Просмотр каталога")
                print("0.  Выйти")
                choice = input("\nВаш выбор: ")
                if choice == '1':
                    bp.client_view_catalog()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '0':
                    session_active = False
                else:
                    print(" ❗ Неверный выбор")
                    input("\nНажмите Enter...")

            elif user_type == 'продавец':
                if seller_info is None:
                    seller_info = bp.authenticate_seller()
                    if not seller_info:
                        print(" ❗ Не удалось идентифицировать продавца. Сессия завершена.")
                        session_active = False
                        continue

                print(f"\n Продавец: {seller_info['last_name']} {seller_info['first_name']}")
                print("-" * 40)
                print("1.  Зарегистрировать клиента")
                print("2.  Создать заказ")
                print("0.  Выйти")
                choice = input("\nВаш выбор: ")

                if choice == '1':
                    bp.register_new_customer()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '2':
                    bp.create_new_order(seller_info)
                    input("\nНажмите Enter для продолжения...")
                elif choice == '0':
                    session_active = False
                else:
                    print(" ❗ Неверный выбор")
                    input("\nНажмите Enter...")

            elif user_type == 'менеджер':
                print("1.  Добавить товар")
                print("2.  Изменить цену")
                print("3.  Отчет по популярным товарам")
                print("0.  Выйти")
                choice = input("\nВаш выбор: ")
                if choice == '1':
                    bp.add_new_product()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '2':
                    bp.update_product_price()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '3':
                    bp.view_popular_products_report()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '0':
                    session_active = False
                else:
                    print(" ❗ Неверный выбор")
                    input("\nНажмите Enter...")

            elif user_type == 'администратор':
                print("1.  Финансовый отчет")
                print("2.  Отчет по ингредиентам")
                print("3.  История клиента")
                print("4.  Добавить сотрудника")
                print("0.  Выйти")
                choice = input("\nВаш выбор: ")
                if choice == '1':
                    bp.financial_report()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '2':
                    bp.ingredients_report()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '3':
                    bp.customer_order_history()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '4':
                    bp.add_new_employee()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '0':
                    session_active = False
                else:
                    print(" ❗ Неверный выбор")
                    input("\nНажмите Enter...")

    except Exception as e:
        print(f"\n ❗ Критическая ошибка: {e}")
    finally:
        bp.cursor.close()
        db.disconnect()

    print("\n Конец сессии")
    input()

if __name__ == "__main__":
    main()