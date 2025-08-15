import socket
import json
import threading
import time
import random

# Константи гри
WIDTH, HEIGHT = 800, 600       # Розмір поля
BALL_SPEED = 5                 # Початкова швидкість м'яча
PADDLE_SPEED = 10              # Швидкість руху платформ
COUNTDOWN_START = 3            # Зворотний відлік перед грою


class GameServer:
    def __init__(self, host='localhost', port=8080):
        """Ініціалізація сервера, створення сокета, змін гри та блокування"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)  # Очікуємо 2 гравців
        print("🎮 Server started")

        # Структури даних для клієнтів
        self.clients = {0: None, 1: None}       # Підключення гравців
        self.connected = {0: False, 1: False}   # Статус підключення
        self.lock = threading.Lock()            # Блокування для синхронізації потоків

        self.reset_game_state()  # Встановлюємо початковий стан гри
        self.sound_event = None  # Для передачі звукових подій клієнтам

    def reset_game_state(self):
        """Скидає позиції платформ, м'яча та рахунок до початкового стану"""
        self.paddles = {0: 250, 1: 250}  # Позиції платформ (по вертикалі)
        self.scores = [0, 0]             # Рахунок обох гравців
        self.ball = {                    # Параметри м'яча
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }
        self.countdown = COUNTDOWN_START  # Зворотний відлік перед стартом
        self.game_over = False
        self.winner = None

    def handle_client(self, pid):
        """Обробляє команди від конкретного гравця"""
        conn = self.clients[pid]
        try:
            while True:
                data = conn.recv(64).decode()  # Читаємо команду
                with self.lock:  # Блокуємо доступ до спільних змінних
                    if data == "UP":
                        self.paddles[pid] = max(60, self.paddles[pid] - PADDLE_SPEED)
                    elif data == "DOWN":
                        self.paddles[pid] = min(HEIGHT - 100, self.paddles[pid] + PADDLE_SPEED)
        except:
            # При розриві з'єднання — кінець гри
            with self.lock:
                self.connected[pid] = False
                self.game_over = True
                self.winner = 1 - pid
                print(f"Гравець {pid} відключився. Переміг гравець {1 - pid}.")

    def broadcast_state(self):
        """Відправляє поточний стан гри всім клієнтам"""
        state = json.dumps({
            "paddles": self.paddles,
            "ball": self.ball,
            "scores": self.scores,
            "countdown": max(self.countdown, 0),
            "winner": self.winner if self.game_over else None,
            "sound_event": self.sound_event
        }) + "\n"
        for pid, conn in self.clients.items():
            if conn:
                try:
                    conn.sendall(state.encode())
                except:
                    self.connected[pid] = False

    def ball_logic(self):
        """Оновлює положення м'яча, перевіряє зіткнення та рахунок"""
        # Перед грою — зворотний відлік
        while self.countdown > 0:
            time.sleep(1)
            with self.lock:
                self.countdown -= 1
                self.broadcast_state()

        # Основний цикл руху м'яча
        while not self.game_over:
            with self.lock:
                # Рух м'яча
                self.ball['x'] += self.ball['vx']
                self.ball['y'] += self.ball['vy']

                # Відбиття від верхньої та нижньої меж
                if self.ball['y'] <= 60 or self.ball['y'] >= HEIGHT:
                    self.ball['vy'] *= -1
                    self.sound_event = "wall_hit"

                # Відбиття від платформ
                if (self.ball['x'] <= 40 and self.paddles[0] <= self.ball['y'] <= self.paddles[0] + 100) or \
                   (self.ball['x'] >= WIDTH - 40 and self.paddles[1] <= self.ball['y'] <= self.paddles[1] + 100):
                    self.ball['vx'] *= -1
                    self.sound_event = 'platform_hit'

                # Голи
                if self.ball['x'] < 0:
                    self.scores[1] += 1
                    self.reset_ball()
                elif self.ball['x'] > WIDTH:
                    self.scores[0] += 1
                    self.reset_ball()

                # Переможець
                if self.scores[0] >= 10:
                    self.game_over = True
                    self.winner = 0
                elif self.scores[1] >= 10:
                    self.game_over = True
                    self.winner = 1

                self.broadcast_state()
                self.sound_event = None

            time.sleep(0.016)  # ~60 FPS

    def reset_ball(self):
        """Повертає м'яч у центр з випадковим напрямком"""
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }

    def accept_players(self):
        """Чекає підключення двох гравців та запускає обробку їх команд"""
        for pid in [0, 1]:
            print(f"Очікуємо гравця {pid}...")
            conn, _ = self.server.accept()
            self.clients[pid] = conn
            conn.sendall((str(pid) + "\n").encode())  # Надсилаємо ID гравця
            self.connected[pid] = True
            print(f"Гравець {pid} приєднався")
            threading.Thread(target=self.handle_client, args=(pid,), daemon=True).start()

    def run(self):
        """Запускає гру та перезапускає її після завершення"""
        while True:
            self.accept_players()
            self.reset_game_state()
            threading.Thread(target=self.ball_logic, daemon=True).start()

            while not self.game_over and all(self.connected.values()):
                time.sleep(0.1)

            print(f"Гравець {self.winner} переміг!")
            time.sleep(5)  # Пауза перед новою грою

            # Закриваємо старі з'єднання
            for pid in [0, 1]:
                try:
                    self.clients[pid].close()
                except:
                    pass
                self.clients[pid] = None
                self.connected[pid] = False


# Запуск сервера
GameServer().run()
