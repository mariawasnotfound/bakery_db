import psycopg2
import getpass

class DatabaseConnection:
    def __init__(self):
        self.connection = None

    # запрашиваем логин и пароль, подключаемся к бд
    def connect_by_credentials(self):
        role = input("Роль (логин): ").strip()
        if not role:
            print(" Логин не может быть пустым!")
            return None

        password = getpass.getpass("Пароль: ")

        try:
            db_params = {
                'dbname': 'bakery_susu',
                'user': role,
                'password': password,
                'host': 'localhost',
                'port': '5432'
            }
            self.connection = psycopg2.connect(**db_params)
            self.connection.autocommit = False
            print(f"Успешный вход как {role}")
            return self.connection
        except Exception as e:
            print(f"Ошибка входа: {e}")
            return None

    def disconnect(self):
        if self.connection:
            self.connection.close()
            print("Соединение прервано")