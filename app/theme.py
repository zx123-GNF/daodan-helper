"""三角洲行动主题 QSS。

配色取自官方视觉：亮绿（logo 三角）、危险橙（hazard 条纹）、
深色战场底。侧栏与头部使用渐变 + 绿色描边。
"""

ACCENT_GREEN = "#17e97e"
ACCENT_GREEN_DIM = "#0eb060"
ACCENT_ORANGE = "#ff9f2e"
BG_DEEP = "#0a0e0c"
BG_PANEL = "#101713"
BG_CARD = "#141d17"
BG_FIELD = "#0b120e"
BORDER_GREEN = "#1f5c3d"
BORDER_SOFT = "#24382c"
TEXT_MAIN = "#eef4ef"
TEXT_SUB = "#9db8a6"


def build_qss(scale: float = 1.0) -> str:
    def px(value: int) -> int:
        return max(6, int(round(value * scale)))

    base = px(13)
    title = px(18)
    small = px(11)
    huge = px(18)
    stat = px(16)
    button = px(12)
    table = px(12)
    green = ACCENT_GREEN
    orange = ACCENT_ORANGE

    return f"""
* {{
    font-family: "Microsoft YaHei UI";
    font-size: {base}px;
    color: {TEXT_MAIN};
}}
QLabel {{
    color: {TEXT_MAIN};
    background: transparent;
}}
QScrollArea {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BG_DEEP}, stop:1 #0c1410);
    border: none;
}}
#pageRoot {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BG_DEEP}, stop:1 #0c1410);
}}
#settingsLabel {{
    color: #ffffff;
    font-weight: 600;
}}
QMainWindow, QWidget#root {{
    background: {BG_DEEP};
    color: {TEXT_MAIN};
}}
#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d1710, stop:1 {BG_PANEL});
    border-right: 2px solid {BORDER_GREEN};
}}
#sidebar QListWidget {{
    background: transparent;
    border: none;
    outline: 0;
}}
#sidebar QListWidget::item {{
    height: {px(52)}px;
    color: {TEXT_SUB};
    padding-left: {px(18)}px;
    border-left: {px(5)}px solid transparent;
}}
#sidebar QListWidget::item:selected {{
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #143324, stop:1 #10221800);
    border-left: {px(5)}px solid {green};
    font-weight: 600;
}}
#sidebar QListWidget::item:hover {{
    background: #12241a;
}}
#appTitle {{
    color: #ffffff;
    font-size: {huge}px;
    font-weight: 800;
}}
#appSubtitle {{
    color: {ACCENT_GREEN_DIM};
    font-size: {small}px;
    letter-spacing: 1px;
}}
#header {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {BG_PANEL}, stop:1 #101b14);
    border-bottom: 2px solid {BORDER_GREEN};
}}
#statusPill {{
    color: #cfe8d8;
    background: {BG_CARD};
    border: 2px solid {BORDER_SOFT};
    border-radius: {px(20)}px;
    padding: {px(6)}px {px(18)}px;
}}
#statusPill[active="true"] {{
    color: #04180d;
    background: {green};
    border-color: {green};
    font-weight: 700;
}}
#pageTitle {{
    font-size: {title}px;
    font-weight: 800;
    color: #ffffff;
}}
#pageHint {{
    color: {TEXT_SUB};
    font-size: {small}px;
}}
#accentLabel {{
    color: {green};
    font-weight: 700;
}}
#card {{
    background: {BG_CARD};
    border: 2px solid {BORDER_GREEN};
    border-radius: {px(12)}px;
}}
#cardTitle {{
    color: #d5e8db;
    font-size: {base}px;
    font-weight: 600;
}}
#statCard {{
    background: {BG_CARD};
    border: 2px solid {BORDER_SOFT};
    border-top: 3px solid {ACCENT_GREEN_DIM};
    border-radius: {px(12)}px;
}}
#statTitle {{
    color: {TEXT_SUB};
    font-size: {small}px;
}}
#statValue {{
    color: #ffffff;
    font-size: {stat}px;
    font-weight: 800;
}}
#heroBanner {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #123322, stop:0.55 #0f1f16, stop:1 {BG_CARD});
    border: 2px solid {BORDER_GREEN};
    border-left: {px(8)}px solid {green};
    border-radius: {px(12)}px;
}}
#heroTitle {{
    color: #ffffff;
    font-size: {stat}px;
    font-weight: 800;
}}
#heroSub {{
    color: {TEXT_SUB};
    font-size: {small}px;
}}
QPushButton {{
    background: #1c2f23;
    border: 2px solid #2f5340;
    border-radius: {px(8)}px;
    padding: {px(6)}px {px(12)}px;
    color: #ffffff;
    font-size: {button}px;
}}
QPushButton:hover {{
    background: #234030;
    border-color: {green};
}}
QPushButton:pressed {{
    background: #16281e;
}}
QPushButton#primaryButton {{
    background: {green};
    border-color: {green};
    color: #04180d;
    font-weight: 800;
}}
QPushButton#primaryButton:hover {{
    background: #5ff5a3;
    border-color: #5ff5a3;
}}
QPushButton#orangeButton {{
    background: {orange};
    border-color: {orange};
    color: #1d1204;
    font-weight: 800;
}}
QPushButton#orangeButton:hover {{
    background: #ffb95e;
    border-color: #ffb95e;
}}
QPushButton#dangerButton {{
    background: #8a2f2a;
    border-color: #b34038;
    color: #ffe3e0;
    font-weight: 700;
}}
QPushButton#dangerButton:hover {{
    background: #a83c34;
}}
QPushButton:disabled {{
    background: #16201a;
    border-color: #233128;
    color: #5c7263;
}}
QComboBox, QSpinBox, QLineEdit {{
    background: {BG_FIELD};
    border: 2px solid #2f5340;
    border-radius: {px(8)}px;
    padding: {px(8)}px {px(10)}px;
    color: #ffffff;
    font-size: {button}px;
    selection-background-color: {green};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: #1c2f23;
    border: 1px solid #2f5340;
    width: {px(22)}px;
}}
QSpinBox::up-arrow, QSpinBox::down-arrow {{
    width: {px(10)}px;
    height: {px(10)}px;
}}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 2px solid {BORDER_GREEN};
    selection-background-color: #143324;
    color: #ffffff;
}}
QCheckBox {{
    color: #d5e8db;
    font-size: {button}px;
    spacing: {px(8)}px;
}}
QCheckBox::indicator {{
    width: {px(20)}px;
    height: {px(20)}px;
    border: 2px solid #3f6b52;
    border-radius: {px(5)}px;
    background: {BG_FIELD};
}}
QCheckBox::indicator:checked {{
    background: {green};
    border-color: {green};
}}
QTableWidget::indicator {{
    width: {px(22)}px;
    height: {px(22)}px;
    border: 2px solid #3f6b52;
    border-radius: {px(5)}px;
    background: {BG_FIELD};
    margin-left: {px(8)}px;
}}
QTableWidget::indicator:checked {{
    background: {green};
    border-color: {green};
    image: none;
}}
QTableWidget {{
    background: {BG_FIELD};
    border: 2px solid {BORDER_GREEN};
    border-radius: {px(10)}px;
    gridline-color: #1c2f23;
    alternate-background-color: #0e1710;
    selection-background-color: #143324;
    font-size: {table}px;
}}
QTableWidget::item {{
    padding: {px(8)}px;
}}
QHeaderView::section {{
    background: #0f1c14;
    color: {TEXT_SUB};
    border: none;
    border-bottom: 2px solid {BORDER_GREEN};
    padding: {px(10)}px;
    font-size: {table}px;
    font-weight: 700;
}}
QPlainTextEdit {{
    background: #070b08;
    border: 2px solid {BORDER_GREEN};
    border-radius: {px(10)}px;
    color: #cfe8d8;
    font-family: "Consolas";
    font-size: {small}px;
}}
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_SUB};
    font-size: {small}px;
}}
QProgressBar {{
    background: {BG_FIELD};
    border: 2px solid {BORDER_GREEN};
    border-radius: {px(10)}px;
    height: {px(24)}px;
    text-align: center;
    color: #ffffff;
    font-size: {small}px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_GREEN_DIM}, stop:1 {green});
    border-radius: {px(8)}px;
}}
QScrollBar:vertical {{
    background: {BG_FIELD};
    width: {px(14)}px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #2f5340;
    border-radius: {px(7)}px;
    min-height: {px(40)}px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {BG_FIELD};
    height: {px(14)}px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #2f5340;
    border-radius: {px(7)}px;
    min-width: {px(40)}px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QMessageBox {{
    background: {BG_PANEL};
}}
QMessageBox QLabel {{
    color: {TEXT_MAIN};
    font-size: {button}px;
}}
QMessageBox QPushButton {{
    min-width: {px(72)}px;
    max-width: {px(110)}px;
    padding: {px(5)}px {px(10)}px;
}}
"""


DARK_QSS = build_qss(1.0)
