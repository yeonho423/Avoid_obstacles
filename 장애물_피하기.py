import os
import random
import tkinter as tk

# 🎵 음악 재생을 위한 pygame 모듈 로드
try:
    import pygame

    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    print(
        "⚠️ pygame 모듈이 설치되지 않아 음악이 재생되지 않습니다. 'pip"
        " install pygame'을 실행해보세요!"
    )


class DodgeGameApp:

    def __init__(self, root):
        self.root = root
        self.root.title("장애물 피하기 - 상점 & 미니게임 & 무적 쉴드")
        self.root.configure(bg="#1E1E2E")

        # --- 전체 화면 설정 ---
        self.is_fullscreen = True
        self.root.attributes("-fullscreen", True)

        # 화면 크기 계산
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # 전체 화면 단축키 바인딩 (F11: 토글, Escape: 창모드 복귀)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # --- 재화 및 레벨 데이터 ---
        self.total_points = 0  # 기본 포인트
        self.red_coins = 0  # 레드 코인
        self.purple_coins = 0  # 퍼플 코인 (외딴섬 전용)
        self.current_level = 1  # 선택된 현재 레벨 (1~20)
        self.max_unlocked_level = 1  # 해금된 최고 레벨

        # 외딴섬 히든 플래그
        self.island_unlocked = False
        self.has_shown_ending = False

        # --- BGM 관리 변수 ---
        self.current_bgm_track = None

        # --- 일반 업그레이드 (포인트 사용 - 영구 유지) ---
        self.upgrades = {
            "width": {
                "name": "📏 바 길이 늘리기",
                "level": 1,
                "max_level": 5,
                "base_cost": 50,
                "cost_mult": 1.8,
                "desc": "플레이어 바의 길이가 늘어납니다.",
            },
            "speed": {
                "name": "⚡ 이동 속도 증가",
                "level": 1,
                "max_level": 5,
                "base_cost": 40,
                "cost_mult": 1.7,
                "desc": "플레이어 이동 속도가 상승합니다.",
            },
            "score": {
                "name": "💰 점수 보너스",
                "level": 1,
                "max_level": 5,
                "base_cost": 60,
                "cost_mult": 2.0,
                "desc": "장애물을 피할 때 얻는 점수가 증가합니다.",
            },
        }

        # --- 레드 코인 전용 업그레이드 (이번 게임 전용 1회용 소모품) ---
        self.red_upgrades = {
            "lives": {
                "name": "❤️ 추가 목숨 (이번 판 전용)",
                "level": 0,
                "max_level": 3,
                "cost": 5,
                "desc": "이번 게임 동안 충돌 시 목숨을 1개 소모하고 부활합니다.",
            },
            "shield": {
                "name": "🛡️ 무적 쉴드 (이번 판 전용)",
                "level": 0,
                "max_level": 5,
                "cost": 5,
                "desc": "이번 게임에서 S키로 발동하며, 다음 판으로 넘어가지 않습니다.",
            },
        }

        # --- 🏝️ 외딴섬 마을 전용 업그레이드 (퍼플 코인 구매) ---
        self.island_upgrades = {
            "tp_pulse": {
                "name": "🌀 순간이동 펄스 (D키 사용)",
                "level": 0,
                "max_level": 3,
                "cost": 3,
                "desc": "위기 시 D키를 눌러 화면 내 모든 장애물을 즉시 밀어냅니다! (판당 충전식)",
            },
            "slow_battery": {
                "name": "⏱️ 슬로우 모션 배터리",
                "level": 0,
                "max_level": 5,
                "cost": 2,
                "desc": "외딴섬의 극심한 중력을 완화해 장애물 속도를 영구 6% 감소시킵니다.",
            },
            "island_talisman": {
                "name": "👑 섬의 수호령 부적",
                "level": 0,
                "max_level": 5,
                "cost": 4,
                "desc": "11레벨 이상의 극심한 점수 패널티를 완화하여 회피 점수를 추가 보정합니다.",
            },
        }

        # 프레임 레벨 컨테이너
        self.current_frame = None
        self.show_main_menu()

    # ==========================================
    # 🎯 레벨별 목표 점수 계산 함수 (11~20레벨 극악 난이도)
    # ==========================================
    def get_target_score(self, level):
        if level <= 6:
            return 100 + (level * 20)
        hard_scores = {
            7: 500,
            8: 1000,
            9: 2000,
            10: 5000,
            11: 6000,
            12: 8000,
            13: 11000,
            14: 15000,
            15: 20000,
            16: 25000,
            17: 30000,
            18: 36000,
            19: 42000,
            20: 50000,
        }
        return hard_scores.get(level, 50000)

    # ==========================================
    # 🖥️ 전체화면 전환 함수
    # ==========================================
    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        if not self.is_fullscreen:
            self.root.geometry("600x800")

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.root.attributes("-fullscreen", False)
        self.root.geometry("600x800")

    # ==========================================
    # 🎵 BGM 음악 재생 모듈
    # ==========================================
    def play_bgm(self, filename):
        if not HAS_PYGAME:
            return

        if self.current_bgm_track == filename:
            return

        if os.path.exists(filename):
            try:
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play(-1)
                self.current_bgm_track = filename
            except Exception as e:
                print(f"🎵 음악 재생 오류 ({filename}): {e}")
        else:
            print(f"📁 음악 파일을 찾을 수 없습니다: {filename}")

    def stop_bgm(self):
        if HAS_PYGAME:
            pygame.mixer.music.stop()
            self.current_bgm_track = None

    def clear_frame(self):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.root.unbind("<KeyPress-Left>")
        self.root.unbind("<KeyRelease-Left>")
        self.root.unbind("<KeyPress-Right>")
        self.root.unbind("<KeyRelease-Right>")
        self.root.unbind("<s>")
        self.root.unbind("<S>")
        self.root.unbind("<d>")
        self.root.unbind("<D>")

    # ==========================================
    # 1. 메인 홈 화면 (Main Menu)
    # ==========================================
    def show_main_menu(self):
        self.clear_frame()
        self.play_bgm("main_bgm.mp3")

        # 10레벨 클리어 후 첫 메인 복귀 시 엔딩 팝업
        if self.max_unlocked_level >= 11 and not self.has_shown_ending:
            self.has_shown_ending = True
            self.island_unlocked = True
            self.show_ending_screen()
            return

        self.current_frame = tk.Frame(self.root, bg="#1E1E2E")
        self.current_frame.pack(fill="both", expand=True)

        hint_label = tk.Label(
            self.current_frame,
            text="[ F11: 전체화면 토글 | ESC: 창모드 ]",
            font=("Arial", 9),
            fg="#6C7086",
            bg="#1E1E2E",
        )
        hint_label.pack(pady=(15, 0))

        title_label = tk.Label(
            self.current_frame,
            text="🎮 장애물 피하기 🎮",
            font=("Arial", 26, "bold"),
            fg="#A6E3A1",
            bg="#1E1E2E",
        )
        title_label.pack(pady=(10, 4))

        subtitle_label = tk.Label(
            self.current_frame,
            text="장애물을 피하고, 미니게임으로 레드코인을 모아보세요!",
            font=("Arial", 11),
            fg="#BAC2DE",
            bg="#1E1E2E",
        )
        subtitle_label.pack(pady=(0, 10))

        point_card = tk.Frame(self.current_frame, bg="#313244", padx=25, pady=10)
        point_card.pack(pady=6)

        point_val = tk.Label(
            point_card,
            text=(
                f"🪙 포인트: {self.total_points:,} P\n🔴 레드코인:"
                f" {self.red_coins:,} RC"
            ),
            font=("Arial", 15, "bold"),
            fg="#F9E2AF",
            bg="#313244",
            justify="center",
        )
        point_val.pack()

        target_score = self.get_target_score(self.current_level)

        # 레벨 선택 프레임 (기본 1~10레벨)
        level_frame = tk.LabelFrame(
            self.current_frame,
            text=f"⭐ 본토 레벨 선택 (현재 Lv 목표: {target_score:,}점)",
            font=("Arial", 10, "bold"),
            fg="#89B4FA",
            bg="#313244",
            padx=15,
            pady=8,
        )
        level_frame.pack(pady=8)

        level_btn_box = tk.Frame(level_frame, bg="#313244")
        level_btn_box.pack()

        for row, (start_lvl, end_lvl) in enumerate([(1, 6), (6, 11)]):
            row_box = tk.Frame(level_btn_box, bg="#313244")
            row_box.pack(pady=3)
            for lvl in range(start_lvl, end_lvl):
                is_unlocked = lvl <= self.max_unlocked_level
                is_selected = lvl == self.current_level

                if is_selected:
                    bg_col = "#A6E3A1"
                    fg_col = "#11111B"
                elif is_unlocked:
                    bg_col = "#89B4FA"
                    fg_col = "#11111B"
                else:
                    bg_col = "#45475A"
                    fg_col = "#A6ADC8"

                state_val = "normal" if is_unlocked else "disabled"

                btn = tk.Button(
                    row_box,
                    text=f"L{lvl}",
                    font=("Arial", 10, "bold"),
                    width=5,
                    bg=bg_col,
                    fg=fg_col,
                    state=state_val,
                    cursor="hand2" if is_unlocked else "arrow",
                    command=lambda l=lvl: self.select_level(l),
                )
                btn.pack(side="left", padx=3)

        self.level_desc_lbl = tk.Label(
            level_frame,
            text="",
            font=("Arial", 9, "bold"),
            fg="#FAB387",
            bg="#313244",
        )
        self.level_desc_lbl.pack(pady=(6, 0))
        self.update_level_desc()

        btn_style = {
            "font": ("Arial", 12, "bold"),
            "width": 24,
            "height": 2,
            "bd": 0,
            "cursor": "hand2",
        }

        start_btn = tk.Button(
            self.current_frame,
            text=f"▶ {self.current_level}레벨 플레이 시작",
            bg="#A6E3A1",
            fg="#11111B",
            activebackground="#94E2D5",
            command=self.start_game,
            **btn_style,
        )
        start_btn.pack(pady=(12, 5))

        shop_btn = tk.Button(
            self.current_frame,
            text="🛒 상점 & 미니게임",
            bg="#89B4FA",
            fg="#11111B",
            activebackground="#B4BEFE",
            command=self.show_shop,
            **btn_style,
        )
        shop_btn.pack(pady=5)

        help_btn = tk.Button(
            self.current_frame,
            text="📖 게임 설명",
            bg="#F9E2AF",
            fg="#11111B",
            activebackground="#FAE3B0",
            command=self.show_instructions,
            **btn_style,
        )
        help_btn.pack(pady=5)

        exit_btn = tk.Button(
            self.current_frame,
            text="❌ 종료",
            bg="#F38BA8",
            fg="#11111B",
            activebackground="#EBA0AC",
            command=self.root.quit,
            **btn_style,
        )
        exit_btn.pack(pady=5)

    # ==========================================
    # 🎬 10레벨 클리어 기념 엔딩 화면
    # ==========================================
    def show_ending_screen(self):
        self.clear_frame()
        self.stop_bgm()

        self.current_frame = tk.Frame(self.root, bg="#11111B")
        self.current_frame.pack(fill="both", expand=True, padx=40, pady=40)

        congrats_lbl = tk.Label(
            self.current_frame,
            text="🏆 CONGRATULATIONS! 🏆",
            font=("Arial", 28, "bold"),
            fg="#F9E2AF",
            bg="#11111B",
        )
        congrats_lbl.pack(pady=(20, 15))

        story_txt = (
            "당신은 온갖 역경과 번개 폭풍을 뚫고\n"
            "마침내 본토의 모든 시련(10레벨)을 정복했습니다!\n\n"
            "평화가 찾아온 듯했으나...\n"
            "먼 바다 안개 너머에서 들려오는 거대한 파도 소리.\n\n"
            "수수께끼의 안개에 싸인 전설의 '외딴섬 마을'로 가는 길이 열렸습니다.\n"
            "그곳엔 지금껏 본 적 없는 극한의 시련이 기다리고 있습니다."
        )

        story_lbl = tk.Label(
            self.current_frame,
            text=story_txt,
            font=("Arial", 13),
            fg="#CDD6F4",
            bg="#11111B",
            justify="center",
            pady=20,
        )
        story_lbl.pack()

        notice_box = tk.Label(
            self.current_frame,
            text="✨ [상점]의 가장 아래에 '외딴섬 마을로 떠나기'가 해금되었습니다!",
            font=("Arial", 12, "bold"),
            fg="#A6E3A1",
            bg="#181825",
            padx=20,
            pady=12,
        )
        notice_box.pack(pady=15)

        cont_btn = tk.Button(
            self.current_frame,
            text="모험 계속하기 ➔",
            font=("Arial", 12, "bold"),
            bg="#89B4FA",
            fg="#11111B",
            height=2,
            width=20,
            bd=0,
            cursor="hand2",
            command=self.show_main_menu,
        )
        cont_btn.pack(pady=20)

    # ==========================================
    # 🏝️ 외딴섬 마을 전용 화면 (11 ~ 20 레벨 허브 & 전용 상점)
    # ==========================================
    def show_island_village(self):
        self.clear_frame()
        self.play_bgm("island_bgm.mp3")

        # 외딴섬 전용 몽환적/어두운 심해 테마 배경
        self.current_frame = tk.Frame(self.root, bg="#0D1117")
        self.current_frame.pack(fill="both", expand=True, padx=35, pady=20)

        header_label = tk.Label(
            self.current_frame,
            text="🏝️ 외딴섬 마을 (11 ~ 20 Lv) 🌊",
            font=("Arial", 22, "bold"),
            fg="#7EE787",
            bg="#0D1117",
        )
        header_label.pack(pady=(5, 2))

        cur_target = self.get_target_score(self.current_level)
        sub_lbl = tk.Label(
            self.current_frame,
            text=f"🪙 {self.total_points:,} P | 🟣 {self.purple_coins:,} PC  (현재 선택 Lv 목표: {cur_target:,}점)",
            font=("Arial", 12, "bold"),
            fg="#D2A8FF",
            bg="#0D1117",
        )
        sub_lbl.pack(pady=(0, 10))

        # 외딴섬 레벨 선택 (11~20레벨)
        level_frame = tk.LabelFrame(
            self.current_frame,
            text="🌌 외딴섬 극악 레벨 선택 (11~20)",
            font=("Arial", 10, "bold"),
            fg="#58A6FF",
            bg="#161B22",
            padx=10,
            pady=6,
        )
        level_frame.pack(fill="x", pady=4)

        level_box = tk.Frame(level_frame, bg="#161B22")
        level_box.pack()

        for row, (start_lvl, end_lvl) in enumerate([(11, 16), (16, 21)]):
            row_box = tk.Frame(level_box, bg="#161B22")
            row_box.pack(pady=2)
            for lvl in range(start_lvl, end_lvl):
                is_unlocked = lvl <= self.max_unlocked_level
                is_selected = lvl == self.current_level

                if is_selected:
                    bg_col = "#7EE787"
                    fg_col = "#0D1117"
                elif is_unlocked:
                    bg_col = "#58A6FF"
                    fg_col = "#0D1117"
                else:
                    bg_col = "#21262D"
                    fg_col = "#8B949E"

                state_val = "normal" if is_unlocked else "disabled"

                btn = tk.Button(
                    row_box,
                    text=f"L{lvl}",
                    font=("Arial", 9, "bold"),
                    width=5,
                    bg=bg_col,
                    fg=fg_col,
                    state=state_val,
                    cursor="hand2" if is_unlocked else "arrow",
                    command=lambda l=lvl: self.select_island_level(l),
                )
                btn.pack(side="left", padx=2)

        # 게임 시작 버튼
        start_btn = tk.Button(
            self.current_frame,
            text=f"⚔️ {self.current_level}레벨 외딴섬 탐사 시작",
            font=("Arial", 12, "bold"),
            bg="#7EE787",
            fg="#0D1117",
            activebackground="#56D364",
            height=2,
            bd=0,
            cursor="hand2",
            command=self.start_game,
        )
        start_btn.pack(fill="x", pady=8)

        # 외딴섬 전용 상점 아이템 리스트 (퍼플 코인 사용)
        island_shop_frame = tk.LabelFrame(
            self.current_frame,
            text="🔮 외딴섬 고대 상점 (퍼플 코인 구매)",
            font=("Arial", 10, "bold"),
            fg="#D2A8FF",
            bg="#161B22",
            padx=10,
            pady=6,
        )
        island_shop_frame.pack(fill="both", expand=True, pady=4)

        for key, item in self.island_upgrades.items():
            cost = item["cost"] * (item["level"] + 1)
            is_max = item["level"] >= item["max_level"]

            card = tk.Frame(island_shop_frame, bg="#21262D", padx=10, pady=5)
            card.pack(fill="x", pady=3)

            info_f = tk.Frame(card, bg="#21262D")
            info_f.pack(side="left", anchor="w")

            t_lbl = tk.Label(
                info_f,
                text=f"{item['name']} (Lv.{item['level']}/{item['max_level']})",
                font=("Arial", 9, "bold"),
                fg="#D2A8FF",
                bg="#21262D",
            )
            t_lbl.pack(anchor="w")

            d_lbl = tk.Label(
                info_f,
                text=item["desc"],
                font=("Arial", 8),
                fg="#8B949E",
                bg="#21262D",
            )
            d_lbl.pack(anchor="w")

            btn_txt = "MAX" if is_max else f"{cost:,} PC"
            btn_state = "disabled" if (is_max or self.purple_coins < cost) else "normal"
            btn_bg = "#30363D" if is_max else ("#D2A8FF" if self.purple_coins >= cost else "#21262D")

            buy_btn = tk.Button(
                card,
                text=btn_txt,
                font=("Arial", 9, "bold"),
                bg=btn_bg,
                fg="#0D1117" if btn_bg == "#D2A8FF" else "#C9D1D9",
                width=8,
                state=btn_state,
                cursor="hand2" if btn_state == "normal" else "arrow",
                command=lambda k=key: self.buy_island_upgrade(k),
            )
            buy_btn.pack(side="right")

        # 본토로 돌아가기 버튼
        back_btn = tk.Button(
            self.current_frame,
            text="⛵ 본토(메인 화면)로 복귀",
            font=("Arial", 11, "bold"),
            bg="#30363D",
            fg="#C9D1D9",
            activebackground="#484F58",
            cursor="hand2",
            height=1,
            bd=0,
            command=self.show_main_menu,
        )
        back_btn.pack(fill="x", side="bottom", pady=4)

    def select_island_level(self, lvl):
        self.current_level = lvl
        self.show_island_village()

    def buy_island_upgrade(self, key):
        item = self.island_upgrades[key]
        cost = item["cost"] * (item["level"] + 1)
        if self.purple_coins >= cost and item["level"] < item["max_level"]:
            self.purple_coins -= cost
            item["level"] += 1
            self.show_island_village()

    def select_level(self, lvl):
        self.current_level = lvl
        self.show_main_menu()

    def update_level_desc(self):
        target_score = self.get_target_score(self.current_level)
        if self.current_level == 1:
            txt = f"1레벨: 클리어 목표 {target_score:,}점! 단일 장애물 위주로 여유롭게 🌿"
        elif self.current_level <= 4:
            txt = f"{self.current_level}레벨: 클리어 목표 {target_score:,}점! 속도가 빨라집니다. 🙂"
        elif self.current_level <= 5:
            txt = f"{self.current_level}레벨: 클리어 목표 {target_score:,}점! 장애물이 쏟아집니다! ⚡"
        elif self.current_level <= 9:
            txt = f"{self.current_level}레벨: 클리어 목표 {target_score:,}점! 점수 획득량 감소 & 번개 폭풍! 💥"
        elif self.current_level == 10:
            txt = f"10레벨: 클리어 목표 {target_score:,}점! 점수 감소 + 순발력 극강 시험! 🔥"
        elif self.current_level <= 15:
            txt = f"{self.current_level}레벨: [외딴섬] 클리어 목표 {target_score:,}점! 퍼플코인 50% 획득 🌊"
        else:
            txt = f"{self.current_level}레벨: [외딴섬 심연] 클리어 목표 {target_score:,}점! 퍼플코인 25% 극소량 획득 🌌"

        self.level_desc_lbl.config(text=txt)

    # ==========================================
    # 2. 게임 설명 화면 (Instructions - 외딴섬 언급 X)
    # ==========================================
    def show_instructions(self):
        self.clear_frame()
        self.play_bgm("main_bgm.mp3")

        self.current_frame = tk.Frame(self.root, bg="#1E1E2E")
        self.current_frame.pack(fill="both", expand=True, padx=40, pady=30)

        header_label = tk.Label(
            self.current_frame,
            text="📖 게임 설명 📖",
            font=("Arial", 22, "bold"),
            fg="#F9E2AF",
            bg="#1E1E2E",
        )
        header_label.pack(pady=(5, 15))

        info_card = tk.Frame(self.current_frame, bg="#313244", padx=25, pady=20)
        info_card.pack(fill="both", expand=True)

        desc_text = (
            "🎮 [ 조작 방법 ]\n"
            "• 좌/우 화살표 (◀ ▶) : 플레이어 이동\n"
            "• S 키 : 무적 쉴드 아이템 발동\n"
            "• R 키 / M 키 : 게임 오버 시 다시하기 / 메인메뉴\n"
            "• F11 / ESC : 전체 화면 토글 / 창 모드로 전환\n\n"
            "⭐ [ 레벨 & 클리어 규칙 ]\n"
            "• 1~6레벨: 120점부터 레벨당 +20점씩 증가 (워밍업 구간)\n"
            "• 🔥 7레벨부터 목표 점수 대폭 상승! (7Lv: 500P / 8Lv: 1,000P / 9Lv: 2,000P / 10Lv: 5,000P)\n"
            "• 목표 점수를 달성하면 상단에 [ CLEAR! ] 가 표시되며, 게임 오버 시 다음 레벨이 해금됩니다.\n"
            "• ⚠️ 6레벨부터는 난이도 상승으로 인해 장애물 회피 점수가 20% 감소합니다! (80%만 적용)\n\n"
            "🛒 [ 상점 & 미니게임 ]\n"
            "• 포인트(P): 장애물 피하기 성공 시 획득 (영구 스탯 강화)\n"
            "• 레드코인(RC): 미니게임으로 획득 (이번 게임 전용 쉴드/목숨 구매)\n"
            "  ※ 주의: 무적 쉴드와 추가 목숨은 이번 게임(1판)에서만 적용되며 다음 판으로 넘어가지 않습니다!\n"
            "• 럭키 복권: 5P를 사용해 포인트를 뽑을 수 있습니다."
        )

        desc_label = tk.Label(
            info_card,
            text=desc_text,
            font=("Arial", 11),
            fg="#CDD6F4",
            bg="#313244",
            justify="left",
            anchor="nw",
        )
        desc_label.pack(fill="both", expand=True)

        back_btn = tk.Button(
            self.current_frame,
            text="🏠 메인 화면으로 돌아가기",
            font=("Arial", 12, "bold"),
            bg="#585B70",
            fg="#CDD6F4",
            activebackground="#6C7086",
            cursor="hand2",
            height=2,
            bd=0,
            command=self.show_main_menu,
        )
        back_btn.pack(fill="x", side="bottom", pady=(15, 0))

    # ==========================================
    # 3. 상점 & 미니게임 화면 (Shop)
    # ==========================================
    def show_shop(self):
        self.clear_frame()
        self.play_bgm("main_bgm.mp3")

        self.current_frame = tk.Frame(self.root, bg="#1E1E2E")
        self.current_frame.pack(fill="both", expand=True, padx=40, pady=15)

        header_label = tk.Label(
            self.current_frame,
            text="🛒 상점 & 미니게임 🎰",
            font=("Arial", 20, "bold"),
            fg="#89B4FA",
            bg="#1E1E2E",
        )
        header_label.pack(pady=(2, 2))

        self.shop_point_label = tk.Label(
            self.current_frame,
            text=f"🪙 {self.total_points:,} P  |  🔴 {self.red_coins:,} RC",
            font=("Arial", 12, "bold"),
            fg="#F9E2AF",
            bg="#1E1E2E",
        )
        self.shop_point_label.pack(pady=(0, 6))

        # 미니게임 영역
        mini_frame = tk.LabelFrame(
            self.current_frame,
            text="🎰 레드 코인 뽑기 미니게임 (비용: 20 P)",
            font=("Arial", 9, "bold"),
            fg="#FAB387",
            bg="#313244",
            padx=8,
            pady=4,
        )
        mini_frame.pack(fill="x", pady=(0, 4))

        btn_box = tk.Frame(mini_frame, bg="#313244")
        btn_box.pack(pady=2)

        for num in range(1, 6):
            btn = tk.Button(
                btn_box,
                text=str(num),
                font=("Arial", 10, "bold"),
                width=4,
                bg="#89B4FA",
                fg="#11111B",
                cursor="hand2",
                command=lambda n=num: self.play_minigame(n),
            )
            btn.pack(side="left", padx=4)

        self.mini_result_lbl = tk.Label(
            mini_frame,
            text="1~5 중 선택! 맞추면 🔴 3 RC",
            font=("Arial", 8, "bold"),
            fg="#A6E3A1",
            bg="#313244",
        )
        self.mini_result_lbl.pack()

        # 복권 영역
        lottery_frame = tk.LabelFrame(
            self.current_frame,
            text="🎟️ 럭키 포인트 복권 (비용: 5 P)",
            font=("Arial", 9, "bold"),
            fg="#F9E2AF",
            bg="#313244",
            padx=8,
            pady=4,
        )
        lottery_frame.pack(fill="x", pady=(0, 4))

        lottery_inner = tk.Frame(lottery_frame, bg="#313244")
        lottery_inner.pack(fill="x")

        lottery_btn = tk.Button(
            lottery_inner,
            text="🎲 복권 (5P)",
            font=("Arial", 9, "bold"),
            bg="#F9E2AF",
            fg="#11111B",
            cursor="hand2",
            command=self.play_lottery,
        )
        lottery_btn.pack(side="left", padx=6)

        self.lottery_result_lbl = tk.Label(
            lottery_inner,
            text="최대 10P 당첨!",
            font=("Arial", 8),
            fg="#BAC2DE",
            bg="#313244",
        )
        self.lottery_result_lbl.pack(side="left", padx=5)

        # 일반 업그레이드
        for key, item in self.upgrades.items():
            cost = int(item["base_cost"] * (item["cost_mult"] ** (item["level"] - 1)))
            is_max = item["level"] >= item["max_level"]

            card = tk.Frame(self.current_frame, bg="#313244", padx=10, pady=3)
            card.pack(fill="x", pady=2)

            info_frame = tk.Frame(card, bg="#313244")
            info_frame.pack(side="left", anchor="w")

            lbl_title = tk.Label(
                info_frame,
                text=f"{item['name']} (Lv.{item['level']}/{item['max_level']})",
                font=("Arial", 9, "bold"),
                fg="#CDD6F4",
                bg="#313244",
            )
            lbl_title.pack(anchor="w")

            btn_txt = "MAX" if is_max else f"{cost:,} P"
            btn_state = "disabled" if (is_max or self.total_points < cost) else "normal"
            btn_bg = "#585B70" if is_max else ("#A6E3A1" if self.total_points >= cost else "#45475A")

            buy_btn = tk.Button(
                card,
                text=btn_txt,
                font=("Arial", 9, "bold"),
                bg=btn_bg,
                fg="#11111B" if btn_bg == "#A6E3A1" else "#CDD6F4",
                width=8,
                state=btn_state,
                cursor="hand2" if btn_state == "normal" else "arrow",
                command=lambda k=key: self.buy_upgrade(k),
            )
            buy_btn.pack(side="right")

        # 레드 코인 전용 업그레이드
        for key, item in self.red_upgrades.items():
            cost = item["cost"] * (item["level"] + 1) if item["level"] > 0 else item["cost"]
            is_max = item["level"] >= item["max_level"]

            card = tk.Frame(self.current_frame, bg="#45475A", padx=10, pady=3)
            card.pack(fill="x", pady=2)

            info_frame = tk.Frame(card, bg="#45475A")
            info_frame.pack(side="left", anchor="w")

            lbl_title = tk.Label(
                info_frame,
                text=f"{item['name']} (Lv.{item['level']}/{item['max_level']})",
                font=("Arial", 9, "bold"),
                fg="#F38BA8",
                bg="#45475A",
            )
            lbl_title.pack(anchor="w")

            btn_txt = "MAX" if is_max else f"{cost} RC"
            btn_state = "disabled" if (is_max or self.red_coins < cost) else "normal"
            btn_bg = "#585B70" if is_max else ("#F38BA8" if self.red_coins >= cost else "#313244")

            buy_btn = tk.Button(
                card,
                text=btn_txt,
                font=("Arial", 9, "bold"),
                bg=btn_bg,
                fg="#11111B" if btn_bg == "#F38BA8" else "#CDD6F4",
                width=8,
                state=btn_state,
                cursor="hand2" if btn_state == "normal" else "arrow",
                command=lambda k=key: self.buy_red_upgrade(k),
            )
            buy_btn.pack(side="right")

        # 🌟 상점 맨 밑: 외딴섬 마을로 이동 버튼 (10레벨 클리어 시 노출)
        if self.island_unlocked or self.max_unlocked_level >= 11:
            island_btn = tk.Button(
                self.current_frame,
                text="🏝️ 외딴섬 마을로 떠나기 (11~20Lv) ➔",
                font=("Arial", 11, "bold"),
                bg="#A6E3A1",
                fg="#11111B",
                activebackground="#94E2D5",
                cursor="hand2",
                height=2,
                bd=0,
                command=self.show_island_village,
            )
            island_btn.pack(fill="x", pady=(6, 4))

        back_btn = tk.Button(
            self.current_frame,
            text="🏠 메인 화면으로 돌아가기",
            font=("Arial", 10, "bold"),
            bg="#585B70",
            fg="#CDD6F4",
            activebackground="#6C7086",
            cursor="hand2",
            height=1,
            bd=0,
            command=self.show_main_menu,
        )
        back_btn.pack(fill="x", side="bottom", pady=4)

    def play_lottery(self):
        cost = 5
        if self.total_points < cost:
            self.lottery_result_lbl.config(
                text="❌ 포인트 부족!", fg="#F38BA8"
            )
            return

        self.total_points -= cost
        rand_val = random.random()

        if rand_val < 0.20:
            reward = 10
            msg = "💎 대박! +10 P!"
            color = "#A6E3A1"
        elif rand_val < 0.50:
            reward = 5
            msg = "🥇 본전! +5 P!"
            color = "#F9E2AF"
        elif rand_val < 0.80:
            reward = 3
            msg = "🥈 소소! +3 P!"
            color = "#89B4FA"
        else:
            reward = 0
            msg = "🥉 꽝!"
            color = "#F38BA8"

        self.total_points += reward
        self.show_shop()
        self.lottery_result_lbl.config(text=msg, fg=color)

    def play_minigame(self, user_choice):
        cost = 20
        if self.total_points < cost:
            self.mini_result_lbl.config(
                text="❌ 포인트 부족 (20P)", fg="#F38BA8"
            )
            return

        self.total_points -= cost
        answer = random.randint(1, 5)

        if user_choice == answer:
            self.red_coins += 3
            self.mini_result_lbl.config(
                text=f"🎉 정답 [{answer}]! 🔴 +3 RC!",
                fg="#A6E3A1",
            )
        else:
            self.mini_result_lbl.config(
                text=f"😅 오답! 정답은 [{answer}]", fg="#F9E2AF"
            )

        self.show_shop()

    def buy_upgrade(self, key):
        item = self.upgrades[key]
        cost = int(item["base_cost"] * (item["cost_mult"] ** (item["level"] - 1)))

        if self.total_points >= cost and item["level"] < item["max_level"]:
            self.total_points -= cost
            item["level"] += 1
            self.show_shop()

    def buy_red_upgrade(self, key):
        item = self.red_upgrades[key]
        cost = item["cost"] * (item["level"] + 1) if item["level"] > 0 else item["cost"]

        if self.red_coins >= cost and item["level"] < item["max_level"]:
            self.red_coins -= cost
            item["level"] += 1
            self.show_shop()

    # ==========================================
    # 4. 인게임 화면 (In-Game Canvas)
    # ==========================================
    def start_game(self):
        self.clear_frame()

        level_bgm_file = f"level_{self.current_level}.mp3"
        self.play_bgm(level_bgm_file)

        is_island_stage = self.current_level >= 11
        # 외딴섬 전용 인게임 배경색 vs 본토 배경색
        canvas_bg = "#0B0E14" if is_island_stage else "#1E1E2E"
        top_bar_bg = "#030712" if is_island_stage else "#181825"

        self.current_frame = tk.Frame(self.root, bg=canvas_bg)
        self.current_frame.pack(fill="both", expand=True)

        top_bar = tk.Frame(self.current_frame, bg=top_bar_bg, padx=15, pady=10)
        top_bar.pack(fill="x")

        self.target_score = self.get_target_score(self.current_level)

        w_lvl = self.upgrades["width"]["level"]
        s_lvl = self.upgrades["speed"]["level"]
        sc_lvl = self.upgrades["score"]["level"]

        self.lives = self.red_upgrades["lives"]["level"]
        self.red_upgrades["lives"]["level"] = 0

        shield_lvl = self.red_upgrades["shield"]["level"]
        self.red_upgrades["shield"]["level"] = 0

        # 외딴섬 전용 펄스 아이템 충전 (외딴섬 스테이지에서만 사용 가능)
        self.tp_charges = self.island_upgrades["tp_pulse"]["level"] if is_island_stage else 0

        self.has_shield_item = shield_lvl > 0
        self.shield_max_sec = 5 + max(0, shield_lvl - 1) * 2 if shield_lvl > 0 else 0

        self.shield_active = False
        self.shield_timer = 0

        self.current_score = 0
        self.game_over = False

        self.game_score_label = tk.Label(
            top_bar,
            text="",
            font=("Arial", 13, "bold"),
            fg="#7EE787" if is_island_stage else "#A6E3A1",
            bg=top_bar_bg,
        )
        self.game_score_label.pack(side="left", padx=10)

        coin_display = f"🟣 {self.purple_coins:,} PC" if is_island_stage else f"🪙 {self.total_points:,} P"
        self.game_total_label = tk.Label(
            top_bar,
            text=f"{'🏝️' if is_island_stage else '⭐'} Lv.{self.current_level} | {coin_display}",
            font=("Arial", 13, "bold"),
            fg="#D2A8FF" if is_island_stage else "#F9E2AF",
            bg=top_bar_bg,
        )
        self.game_total_label.pack(side="right", padx=10)

        self.update_top_bar_ui()

        self.canvas_width = self.root.winfo_screenwidth()
        self.canvas_height = self.root.winfo_screenheight() - 60
        self.canvas = tk.Canvas(
            self.current_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg=canvas_bg,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.player_width = 70 + (w_lvl * 15)
        self.player_height = 20
        self.player_x = (self.canvas_width - self.player_width) / 2
        self.player_y = self.canvas_height - 90

        self.player_speed_x = 0.0
        self.accel = 1.2 + (s_lvl * 0.25)
        self.max_speed = 9.0 + (s_lvl * 1.8)
        self.friction = 0.84

        self.score_multiplier = 1.0 + (sc_lvl - 1) * 0.5

        # 플레이어 생성
        p_color = "#58A6FF" if is_island_stage else "#A6E3A1"
        self.player = self.canvas.create_rectangle(
            self.player_x,
            self.player_y,
            self.player_x + self.player_width,
            self.player_y + self.player_height,
            fill=p_color,
            outline="",
        )

        self.obstacles = []
        # 슬로우 배터리 적용 및 기본 속도 (외딴섬 스테이지에서만 슬로우 배터리 감속 적용)
        slow_factor = 1.0 - (self.island_upgrades["slow_battery"]["level"] * 0.06) if is_island_stage else 1.0
        self.base_obstacle_speed = (3.6 + (self.current_level - 1) * 0.45) * slow_factor

        self.keys = {"Left": False, "Right": False}
        self.root.bind("<KeyPress-Left>", self.on_key_press)
        self.root.bind("<KeyRelease-Left>", self.on_key_release)
        self.root.bind("<KeyPress-Right>", self.on_key_press)
        self.root.bind("<KeyRelease-Right>", self.on_key_release)
        self.root.bind("<s>", self.use_shield)
        self.root.bind("<S>", self.use_shield)
        self.root.bind("<d>", self.use_tp_pulse)
        self.root.bind("<D>", self.use_tp_pulse)
        self.root.bind("<r>", self.on_shortcut_key)
        self.root.bind("<R>", self.on_shortcut_key)
        self.root.bind("<m>", self.on_shortcut_key)
        self.root.bind("<M>", self.on_shortcut_key)

        self.spawn_obstacle_wave()
        self.update_game()

    def update_top_bar_ui(self):
        shield_str = ""
        if self.shield_active:
            sec_left = max(1, self.shield_timer // 60)
            shield_str = f" | 🛡️ 사용중({sec_left}초)"
        elif self.has_shield_item:
            shield_str = f" | 🛡️ 가능[S]({self.shield_max_sec}초)"

        tp_str = f" | 🌀펄스[D]x{self.tp_charges}" if self.tp_charges > 0 else ""
        clear_str = " 🎉 [ CLEAR! ]" if self.current_score >= self.target_score else ""

        unit_str = "점"
        self.game_score_label.config(
            text=(
                f"점수: {self.current_score:,}/{self.target_score:,}{unit_str}{clear_str} |"
                f" ❤️x{self.lives}{shield_str}{tp_str}"
            )
        )

    def use_tp_pulse(self, event=None):
        """외딴섬 전용 D키 펄스 스킬: 모든 장애물 제거 (11레벨 이상 외딴섬에서만 작동)"""
        if self.current_level >= 11 and self.tp_charges > 0 and not self.game_over:
            self.tp_charges -= 1
            for obs in self.obstacles:
                self.canvas.delete(obs["id"])
            self.obstacles.clear()
            self.update_top_bar_ui()

    def use_shield(self, event=None):
        if self.has_shield_item and not self.shield_active and not self.game_over:
            self.has_shield_item = False
            self.shield_active = True
            self.shield_timer = self.shield_max_sec * 60
            self.canvas.itemconfig(self.player, fill="#D2A8FF")
            self.update_top_bar_ui()

    def on_key_press(self, event):
        if event.keysym in self.keys:
            self.keys[event.keysym] = True

    def on_key_release(self, event):
        if event.keysym in self.keys:
            self.keys[event.keysym] = False

    def on_shortcut_key(self, event):
        if self.game_over:
            if event.keysym in ["r", "R"]:
                self.start_game()
            elif event.keysym in ["m", "M"]:
                if self.current_level >= 11:
                    self.show_island_village()
                else:
                    self.show_main_menu()

    def spawn_obstacle_wave(self):
        if self.current_level <= 4:
            multi_chance = 0.15 + (self.current_level - 1) * 0.08
        else:
            multi_chance = 0.45 + (self.current_level - 1) * 0.04

        count = 1
        if random.random() < multi_chance:
            max_count = 3 if self.current_level < 5 else (5 if self.current_level >= 11 else 4)
            count = random.randint(2, max_count)

        electric_chance = 0.04 + (self.current_level - 1) * 0.03

        for _ in range(count):
            # 13레벨 이상일 경우 플레이어 위치 주변으로 낙하 범위 집중
            if self.current_level >= 13 and hasattr(self, "player_x"):
                p_center = self.player_x + (self.player_width / 2)
                offset = random.randint(-180, 180)
                target_x = int(p_center + offset)
                x = max(20, min(self.canvas_width - 60, target_x))
            else:
                x = random.randint(20, max(50, self.canvas_width - 60))

            is_electric = random.random() < electric_chance

            if is_electric:
                speed_mult = random.uniform(1.3, 1.8)
                speed = self.base_obstacle_speed * speed_mult

                points = [
                    x + 22, 0,
                    x + 6, 24,
                    x + 18, 24,
                    x, 48,
                    x + 30, 18,
                    x + 16, 18,
                    x + 34, 0,
                ]
                obj_color = "#FFA657" if self.current_level >= 11 else "#FFFF00"
                obj = self.canvas.create_polygon(
                    points, fill=obj_color, outline="#FF7B72", width=2
                )
            else:
                min_mult = 0.85 if self.current_level <= 3 else 0.95
                max_mult = 1.25 if self.current_level <= 3 else 1.55
                speed_mult = random.uniform(min_mult, max_mult)
                speed = self.base_obstacle_speed * speed_mult

                obs_col = "#79C0FF" if self.current_level >= 11 else "#FAB387"
                obj = self.canvas.create_rectangle(
                    x, 0, x + 40, 40, fill=obs_col, outline=""
                )

            self.obstacles.append(
                {"id": obj, "is_electric": is_electric, "speed": speed}
            )

    def update_player_physics(self):
        if self.keys["Left"]:
            self.player_speed_x -= self.accel
        if self.keys["Right"]:
            self.player_speed_x += self.accel

        self.player_speed_x *= self.friction

        if self.player_speed_x > self.max_speed:
            self.player_speed_x = self.max_speed
        elif self.player_speed_x < -self.max_speed:
            self.player_speed_x = -self.max_speed

        self.player_x += self.player_speed_x

        if self.player_x < 0:
            self.player_x = 0
            self.player_speed_x = 0
        elif self.player_x > self.canvas_width - self.player_width:
            self.player_x = self.canvas_width - self.player_width
            self.player_speed_x = 0

        self.canvas.coords(
            self.player,
            self.player_x,
            self.player_y,
            self.player_x + self.player_width,
            self.player_y + self.player_height,
        )

    def check_collision(self, p, o):
        min_x = min(o[0::2])
        max_x = max(o[0::2])
        min_y = min(o[1::2])
        max_y = max(o[1::2])
        return not (p[2] < min_x or p[0] > max_x or p[3] < min_y or p[1] > max_y)

    def update_game(self):
        if self.game_over:
            return

        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer % 30 == 0:
                self.update_top_bar_ui()

            if self.shield_timer <= 0:
                self.shield_active = False
                p_color = "#58A6FF" if self.current_level >= 11 else "#A6E3A1"
                self.canvas.itemconfig(self.player, fill=p_color)
                self.update_top_bar_ui()

        self.update_player_physics()

        player_pos = self.canvas.coords(self.player)
        obstacles_to_remove = []

        for obs in self.obstacles:
            if obs["is_electric"]:
                obs["speed"] += 0.12

            self.canvas.move(obs["id"], 0, obs["speed"])
            obs_pos = self.canvas.coords(obs["id"])
            max_obs_y = max(obs_pos[1::2])

            # 장애물 회피 성공
            if max_obs_y >= self.canvas_height:
                obstacles_to_remove.append(obs)
                base_reward = 40 if obs["is_electric"] else 10

                # ⭐ 점수 획득 배율 (11~15Lv: 25%, 16~20Lv: 15% + 부적 보정)
                if self.current_level >= 16:
                    talisman_boost = self.island_upgrades["island_talisman"]["level"] * 0.04
                    level_multiplier = 0.15 + talisman_boost
                elif self.current_level >= 11:
                    talisman_boost = self.island_upgrades["island_talisman"]["level"] * 0.06
                    level_multiplier = 0.25 + talisman_boost
                elif self.current_level >= 6:
                    level_multiplier = 0.80
                else:
                    level_multiplier = 1.0

                earned = int(base_reward * self.score_multiplier * level_multiplier)
                earned = max(1, earned)

                self.current_score += earned
                self.base_obstacle_speed += 0.03
                self.update_top_bar_ui()

            # 충돌 발생
            elif self.check_collision(player_pos, obs_pos):
                obstacles_to_remove.append(obs)
                if self.shield_active:
                    pass
                elif self.lives > 0:
                    self.lives -= 1
                    self.update_top_bar_ui()
                else:
                    self.game_over = True
                    is_island = self.current_level >= 11

                    # ⭐ 외딴섬 레벨별 퍼플 코인 차등 지급
                    if self.current_level >= 16:
                        # 16~20레벨: 획득 점수의 25%만 지급
                        earned_pc = max(1, self.current_score // 4) if self.current_score > 0 else 0
                        self.purple_coins += earned_pc
                        self.last_earned_reward = earned_pc
                    elif self.current_level >= 11:
                        # 11~15레벨: 획득 점수의 50%만 지급
                        earned_pc = max(1, self.current_score // 2) if self.current_score > 0 else 0
                        self.purple_coins += earned_pc
                        self.last_earned_reward = earned_pc
                    else:
                        self.total_points += self.current_score
                        self.last_earned_reward = self.current_score

                    if (
                        self.current_score >= self.target_score
                        and self.current_level == self.max_unlocked_level
                        and self.max_unlocked_level < 20
                    ):
                        self.max_unlocked_level += 1

                    self.root.unbind("<KeyPress-Left>")
                    self.root.unbind("<KeyRelease-Left>")
                    self.root.unbind("<KeyPress-Right>")
                    self.root.unbind("<KeyRelease-Right>")
                    self.root.unbind("<s>")
                    self.root.unbind("<S>")
                    self.root.unbind("<d>")
                    self.root.unbind("<D>")

                    self.show_game_over_ui()
                    return

        for obs in obstacles_to_remove:
            self.canvas.delete(obs["id"])
            if obs in self.obstacles:
                self.obstacles.remove(obs)

        if not self.obstacles:
            self.spawn_obstacle_wave()

        self.root.after(16, self.update_game)

    def show_game_over_ui(self):
        cx = self.canvas_width / 2
        cy = self.canvas_height / 2
        is_island = self.current_level >= 11

        self.canvas.create_rectangle(
            cx - 200,
            cy - 160,
            cx + 200,
            cy + 160,
            fill="#181825",
            outline="#F38BA8",
            width=2,
        )

        self.canvas.create_text(
            cx,
            cy - 110,
            text="GAME OVER",
            fill="#F38BA8",
            font=("Arial", 28, "bold"),
        )

        unlock_msg = ""
        if (
            self.current_score >= self.target_score
            and self.current_level == self.max_unlocked_level - 1
            and self.max_unlocked_level <= 20
        ):
            unlock_msg = f"\n🎉 다음 레벨({self.max_unlocked_level}Lv) 해금 성공!"

        unit_str = "PC" if is_island else "P"
        reward_amount = getattr(self, "last_earned_reward", self.current_score)
        
        self.canvas.create_text(
            cx,
            cy - 50,
            text=f"달성 점수: {self.current_score:,}점\n획득 재화: +{reward_amount:,} {unit_str}{unlock_msg}",
            fill="#7EE787" if is_island else "#A6E3A1",
            font=("Arial", 13, "bold"),
            justify="center",
        )

        total_txt = f"총 보유 퍼플코인: {self.purple_coins:,} PC" if is_island else f"총 보유 포인트: {self.total_points:,} P"
        self.canvas.create_text(
            cx,
            cy + 15,
            text=total_txt,
            fill="#D2A8FF" if is_island else "#F9E2AF",
            font=("Arial", 13),
        )

        btn_frame = tk.Frame(self.current_frame, bg="#181825")

        replay_btn = tk.Button(
            btn_frame,
            text="🔄 다시 하기 [R]",
            font=("Arial", 11, "bold"),
            bg="#A6E3A1",
            fg="#11111B",
            width=14,
            height=2,
            bd=0,
            cursor="hand2",
            command=self.start_game,
        )
        replay_btn.pack(side="left", padx=6)

        main_dest = self.show_island_village if self.current_level >= 11 else self.show_main_menu
        main_text = "🏝️ 섬으로 [M]" if self.current_level >= 11 else "🏠 메인 화면 [M]"

        main_btn = tk.Button(
            btn_frame,
            text=main_text,
            font=("Arial", 11, "bold"),
            bg="#89B4FA",
            fg="#11111B",
            width=14,
            height=2,
            bd=0,
            cursor="hand2",
            command=main_dest,
        )
        main_btn.pack(side="right", padx=6)

        self.canvas.create_window(cx, cy + 90, window=btn_frame)


if __name__ == "__main__":
    root = tk.Tk()
    app = DodgeGameApp(root)
    root.mainloop()
