from pygame import *
import socket
import json
from threading import Thread

# --- Налаштування вікна Pygame ---
WIDTH, HEIGHT = 800, 600
init()
screen = display.set_mode((WIDTH, HEIGHT))
clock = time.Clock()
display.set_caption("Пінг-Понг")

# --- Підключення до сервера ---
def connect_to_server():
    """
    Підключається до сервера і отримує:
    - socket клієнта
    - свій ідентифікатор (0 або 1) від сервера
    - початковий буфер для обробки пакетів
    - словник для зберігання стану гри
    """
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('localhost', 8080))  # Підключення до сервера
            buffer = ""  # Буфер для збирання пакетів
            game_state = {}  # Поточний стан гри
            my_id = int(client.recv(24).decode())  # Отримуємо свій ID від сервера
            return my_id, game_state, buffer, client
        except:
            # Якщо сервер недоступний — пробуємо знову
            pass


def receive():
    """
    Постійно приймає дані від сервера в окремому потоці.
    Збирає шматки пакетів у буфер, розділяє по '\n' і парсить JSON у game_state.
    """
    global buffer, game_state, game_over
    while not game_over:
        try:
            data = client.recv(1024).decode()
            buffer += data
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                if packet.strip():
                    game_state = json.loads(packet)
        except:
            # Якщо зв’язок втрачено — ставимо переможця як -1 (гра закінчена)
            game_state["winner"] = -1
            break


# --- Шрифти ---
font_win = font.Font(None, 72)
font_main = font.Font(None, 36)

# --- Ігрові змінні ---
game_over = False
winner = None
you_winner = None

# --- Підключення до сервера ---
my_id, game_state, buffer, client = connect_to_server()
Thread(target=receive, daemon=True).start()  # Потік для отримання даних від сервера

# --- Головний цикл гри ---
while True:
    for e in event.get():
        if e.type == QUIT:
            exit()

    # --- Етап відліку перед стартом гри ---
    if "countdown" in game_state and game_state["countdown"] > 0:
        screen.fill((0, 0, 0))
        countdown_text = font.Font(None, 72).render(str(game_state["countdown"]), True, (255, 255, 255))
        screen.blit(countdown_text, (WIDTH // 2 - 20, HEIGHT // 2 - 30))
        display.update()
        continue  # Чекаємо завершення відліку, гру ще не малюємо

    # --- Перевірка на завершення гри ---
    if "winner" in game_state and game_state["winner"] is not None:
        screen.fill((20, 20, 20))

        if you_winner is None:  # Визначаємо тільки один раз, чи ми перемогли
            if game_state["winner"] == my_id:
                you_winner = True
            else:
                you_winner = False

        if you_winner:
            text = "Ти переміг!"
        else:
            text = "Пощастить наступним разом!"

        win_text = font_win.render(text, True, (255, 215, 0))
        text_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(win_text, text_rect)

        text = font_win.render('К - рестарт', True, (255, 215, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120))
        screen.blit(text, text_rect)

        display.update()
        continue  # Блокуємо оновлення гри після перемоги

    # --- Малювання об’єктів гри ---
    if game_state:
        screen.fill((30, 30, 30))

        # Платформа гравця 0 (зелена)
        draw.rect(screen, (0, 255, 0), (20, game_state['paddles']['0'], 20, 100))

        # Платформа гравця 1 (рожева)
        draw.rect(screen, (255, 0, 255), (WIDTH - 40, game_state['paddles']['1'], 20, 100))

        # М'яч (білий круг)
        draw.circle(screen, (255, 255, 255), (game_state['ball']['x'], game_state['ball']['y']), 10)

        # Рахунок
        score_text = font_main.render(f"{game_state['scores'][0]} : {game_state['scores'][1]}", True, (255, 255, 255))
        screen.blit(score_text, (WIDTH // 2 - 25, 20))

        # Звукові події (поки заглушки)
        if game_state['sound_event']:
            if game_state['sound_event'] == 'wall_hit':
                # Тут можна вставити звук відбиття м'яча від стіни
                pass
            if game_state['sound_event'] == 'platform_hit':
                # Тут можна вставити звук відбиття м'яча від платформи
                pass

    else:
        # Якщо ще немає стану гри — чекаємо підключення гравців
        wating_text = font_main.render(f"Очікування гравців...", True, (255, 255, 255))
        screen.blit(wating_text, (WIDTH // 2 - 25, 20))

    display.update()
    clock.tick(60)

    # --- Керування гравцем ---
    keys = key.get_pressed()
    if keys[K_w]:
        client.send(b"UP")
    elif keys[K_s]:
        client.send(b"DOWN")
