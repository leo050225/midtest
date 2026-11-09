import sys
import os
import pygame
import requests

# 關鍵修正：強制略過本機代理，防止 macOS / Conda 將 127.0.0.1 請求導向 Proxy
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

API_BASE_URL = "http://127.0.0.1:8000"

COLOR_BG = (18, 18, 19)
COLOR_SIDEBAR_BG = (24, 24, 27)
COLOR_DIVIDER = (70, 70, 75)
COLOR_TEXT = (255, 255, 255)
COLOR_MUTED = (160, 160, 160)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色

pygame.init()
# 任務三：視窗寬度從 500 擴大為 700
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")

font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
history_font = pygame.font.SysFont("Courier New", 22, bold=True)


class WordleGame:
    def __init__(self):
        # 建立專屬 session 避免系統代理干擾
        self.session = requests.Session()
        self.session.trust_env = False  # 忽略系統環境變數中的 HTTP_PROXY

        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.message = "Press ENTER to submit, R to restart, H to toggle Hard Mode"
        
        # 任務三 & 四：歷史紀錄、勝率統計與硬核模式
        self.history = []
        self.hard_mode = False
        self.stats = {"total_games": 0, "wins": 0, "win_rate": 0.0}
        
        self.start_new_game()

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局 """
        try:
            payload = {"hard_mode": self.hard_mode}
            res = self.session.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.history = []
                if "stats" in data:
                    self.stats = data["stats"]
                self.message = "New game started!"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException as e:
            print("[Client Error] start_new_game failed:", repr(e))
            self.message = "Cannot connect to FastAPI server!"

    def toggle_hard_mode(self):
        """ 任務四：切換硬核模式開關並重新開始新遊戲 """
        self.hard_mode = not self.hard_mode
        self.start_new_game()

    def submit_guess(self):
        """ 將當前行單字發送至 FastAPI 驗證 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = self.session.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=10)

            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]

                # 依據後端回傳更新格子顏色
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                # 任務三：側邊欄記錄已猜測單字
                self.history.append(guess_word)

                if "stats" in data:
                    self.stats = data["stats"]

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        # 任務一：6 次機會用盡失敗時揭曉答案
                        target = data.get("target_word", "")
                        self.message = f"Game Over! The word was {target}. Press R to restart."
                        self.game_over = True
                    else:
                        # 任務一：顯示剩餘次數
                        tries_left = 6 - self.row
                        self.message = f"Keep guessing! ({tries_left} tries left)"
            else:
                # 任務二 & 任務四：不在字典或違反硬核模式，不消耗次數
                detail = res.json().get("detail", "Error processing guess")
                if "Word not in dictionary" in detail:
                    self.message = "Not in word list!"
                else:
                    self.message = detail
        except requests.exceptions.RequestException as e:
            print("[Client Error] submit_guess failed:", repr(e))
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        ctrl_held = (event.mod & pygame.KMOD_CTRL) or (event.mod & pygame.KMOD_META)

        # 遊戲結束時：按 R 重開，按 H 切換模式
        if self.game_over:
            if event.key == pygame.K_r:
                self.start_new_game()
                return
            elif event.key == pygame.K_h:
                self.toggle_hard_mode()
                return

        # 進行中：按 Ctrl+R 或 Ctrl+H 可隨時重開或切換模式
        if ctrl_held:
            if event.key == pygame.K_r:
                self.start_new_game()
                return
            elif event.key == pygame.K_h:
                self.toggle_hard_mode()
                return

        # 當前行未輸入任何字母時（self.col == 0），按 H 切換模式
        if self.col == 0 and event.key == pygame.K_h:
            self.toggle_hard_mode()
            return

        # 退格鍵 Backspace
        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
            return

        # 送出鍵 Enter
        if event.key == pygame.K_RETURN:
            self.submit_guess()
            return

        # 一般英文字母輸入（包含 R 與 H，不再衝突）
        if event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)

        # 繪製 6x5 網格
        margin_x, margin_y = 75, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)

                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 任務一：畫底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(250, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)

        # 任務三：繪製側邊欄 (x: 500-700) 與分隔線
        pygame.draw.line(surface, COLOR_DIVIDER, (500, 0), (500, HEIGHT), 2)
        pygame.draw.rect(surface, COLOR_SIDEBAR_BG, pygame.Rect(502, 0, 198, HEIGHT))

        # 任務四：右上角顯示目前模式
        mode_text = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_surface = small_font.render(mode_text, True, (240, 80, 80) if self.hard_mode else COLOR_MUTED)
        surface.blit(mode_surface, (515, 15))

        # 任務三：側邊欄統計資訊
        total = self.stats.get("total_games", 0)
        wins = self.stats.get("wins", 0)
        rate = self.stats.get("win_rate", 0.0)
        stats_line = small_font.render(f"Total: {total} | Wins: {wins}", True, COLOR_TEXT)
        rate_line = small_font.render(f"Win Rate: {rate}%", True, COLOR_TEXT)
        surface.blit(stats_line, (515, 45))
        surface.blit(rate_line, (515, 68))

        pygame.draw.line(surface, COLOR_DIVIDER, (505, 95), (695, 95), 1)

        # 任務三：側邊欄歷史紀錄面板
        history_title = small_font.render("--- History ---", True, COLOR_MUTED)
        surface.blit(history_title, (515, 105))

        for idx, word in enumerate(self.history):
            item_surface = history_font.render(f"{idx + 1}. {word}", True, COLOR_TEXT)
            surface.blit(item_surface, (515, 135 + idx * 35))


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()