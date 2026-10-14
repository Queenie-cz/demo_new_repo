"""俄罗斯方块 (Tetris) - 基于 pygame

操作说明:
    ← / →   左右移动
    ↓       加速下落
    ↑ / X   顺时针旋转
    Z       逆时针旋转
    空格     直接落到底
    P       暂停 / 继续
    R       重新开始
    ESC     退出
"""

import random
import sys

import pygame

CELL = 30
COLS, ROWS = 10, 20
SIDE_WIDTH = 200
WIDTH = COLS * CELL + SIDE_WIDTH
HEIGHT = ROWS * CELL
FPS = 60

BLACK = (0, 0, 0)
GRID_COLOR = (40, 40, 40)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)

SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}

COLORS = {
    "I": (0, 240, 240),
    "O": (240, 240, 0),
    "T": (160, 0, 240),
    "S": (0, 240, 0),
    "Z": (240, 0, 0),
    "J": (0, 0, 240),
    "L": (240, 160, 0),
}

LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}


def rotate_cw(matrix):
    return [list(row) for row in zip(*matrix[::-1])]


def rotate_ccw(matrix):
    return [list(row) for row in zip(*matrix)][::-1]


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.shape = [row[:] for row in SHAPES[kind]]
        self.color = COLORS[kind]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def cells(self, shape=None, x=None, y=None):
        shape = shape if shape is not None else self.shape
        x = self.x if x is None else x
        y = self.y if y is None else y
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    yield x + c, y + r


class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.current = self.new_piece()
        self.next = self.new_piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.fall_timer = 0

    def new_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    @property
    def fall_interval(self):
        return max(80, 800 - (self.level - 1) * 70)

    def valid(self, piece, shape=None, x=None, y=None):
        for cx, cy in piece.cells(shape, x, y):
            if cx < 0 or cx >= COLS or cy >= ROWS:
                return False
            if cy >= 0 and self.board[cy][cx] is not None:
                return False
        return True

    def move(self, dx, dy):
        if self.valid(self.current, x=self.current.x + dx, y=self.current.y + dy):
            self.current.x += dx
            self.current.y += dy
            return True
        return False

    def rotate(self, clockwise=True):
        new_shape = rotate_cw(self.current.shape) if clockwise else rotate_ccw(self.current.shape)
        for kick in (0, -1, 1, -2, 2):
            if self.valid(self.current, shape=new_shape, x=self.current.x + kick):
                self.current.shape = new_shape
                self.current.x += kick
                return

    def hard_drop(self):
        dropped = 0
        while self.move(0, 1):
            dropped += 1
        self.score += dropped * 2
        self.lock_piece()

    def ghost_y(self):
        y = self.current.y
        while self.valid(self.current, y=y + 1):
            y += 1
        return y

    def lock_piece(self):
        for cx, cy in self.current.cells():
            if cy < 0:
                self.game_over = True
                return
            self.board[cy][cx] = self.current.color
        self.clear_lines()
        self.current = self.next
        self.next = self.new_piece()
        if not self.valid(self.current):
            self.game_over = True

    def clear_lines(self):
        remaining = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(remaining)
        if cleared:
            self.board = [[None] * COLS for _ in range(cleared)] + remaining
            self.lines += cleared
            self.score += LINE_SCORES[cleared] * self.level
            self.level = self.lines // 10 + 1

    def update(self, dt):
        if self.game_over or self.paused:
            return
        self.fall_timer += dt
        if self.fall_timer >= self.fall_interval:
            self.fall_timer = 0
            if not self.move(0, 1):
                self.lock_piece()


def load_font(size):
    for name in ("pingfang", "pingfangsc", "heitisc", "stheitimedium", "arialunicode", "microsoftyahei", "simhei"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_cell(surface, x, y, color, alpha=255):
    rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
    if alpha < 255:
        overlay = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        overlay.fill((*color, alpha))
        surface.blit(overlay, rect)
    else:
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)


def draw(screen, game, font, small_font):
    screen.fill(BLACK)

    for r in range(ROWS):
        for c in range(COLS):
            pygame.draw.rect(screen, GRID_COLOR, (c * CELL, r * CELL, CELL, CELL), 1)
            if game.board[r][c]:
                draw_cell(screen, c, r, game.board[r][c])

    if not game.game_over:
        gy = game.ghost_y()
        for cx, cy in game.current.cells(y=gy):
            if cy >= 0:
                draw_cell(screen, cx, cy, game.current.color, alpha=60)
        for cx, cy in game.current.cells():
            if cy >= 0:
                draw_cell(screen, cx, cy, game.current.color)

    side_x = COLS * CELL + 20
    pygame.draw.line(screen, GRAY, (COLS * CELL, 0), (COLS * CELL, HEIGHT), 2)

    screen.blit(font.render("下一个", True, WHITE), (side_x, 20))
    for r, row in enumerate(game.next.shape):
        for c, val in enumerate(row):
            if val:
                rect = pygame.Rect(side_x + c * CELL, 60 + r * CELL, CELL, CELL)
                pygame.draw.rect(screen, game.next.color, rect)
                pygame.draw.rect(screen, WHITE, rect, 1)

    info = [f"分数: {game.score}", f"行数: {game.lines}", f"等级: {game.level}"]
    for i, text in enumerate(info):
        screen.blit(font.render(text, True, WHITE), (side_x, 160 + i * 40))

    help_lines = ["← → 移动", "↑ / X 旋转", "Z 反向旋转", "↓ 加速", "空格 落底", "P 暂停", "R 重开", "ESC 退出"]
    for i, text in enumerate(help_lines):
        screen.blit(small_font.render(text, True, GRAY), (side_x, 300 + i * 26))

    if game.paused or game.game_over:
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        title = "游戏结束" if game.game_over else "暂停中"
        hint = "按 R 重新开始" if game.game_over else "按 P 继续"
        t = font.render(title, True, WHITE)
        h = small_font.render(hint, True, WHITE)
        screen.blit(t, t.get_rect(center=(COLS * CELL // 2, HEIGHT // 2 - 20)))
        screen.blit(h, h.get_rect(center=(COLS * CELL // 2, HEIGHT // 2 + 20)))

    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("俄罗斯方块")
    clock = pygame.time.Clock()
    font = load_font(28)
    small_font = load_font(18)
    pygame.key.set_repeat(170, 50)

    game = Tetris()

    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == pygame.K_r:
                game.reset()
                continue
            if event.key == pygame.K_p and not game.game_over:
                game.paused = not game.paused
                continue
            if game.game_over or game.paused:
                continue
            if event.key == pygame.K_LEFT:
                game.move(-1, 0)
            elif event.key == pygame.K_RIGHT:
                game.move(1, 0)
            elif event.key == pygame.K_DOWN:
                if game.move(0, 1):
                    game.score += 1
                    game.fall_timer = 0
            elif event.key in (pygame.K_UP, pygame.K_x):
                game.rotate(clockwise=True)
            elif event.key == pygame.K_z:
                game.rotate(clockwise=False)
            elif event.key == pygame.K_SPACE:
                game.hard_drop()

        game.update(dt)
        draw(screen, game, font, small_font)


if __name__ == "__main__":
    main()
