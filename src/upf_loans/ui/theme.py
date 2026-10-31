"""Dark "liquid glass" theme: translucent panels over a softly lit backdrop, lime accent.

Qt style sheets can't blur what is behind a widget, so the glass effect comes from
layered translucent fills, light top-edge borders and the painted backdrop in
``widgets/backdrop.py``. Pop-ups (menus, drop-down lists, dialogs, tooltips) are
separate windows, so they get solid colours to stay readable.
"""

from PySide6.QtGui import QColor, QFont, QPalette

# Base colours
BG = "#0D0F14"
BG_RAISED = "#171A21"       # solid surface for pop-ups and dialogs
BG_POPUP = "#1D2129"
TEXT = "#F3F5F8"
TEXT_SOFT = "#C9CED8"
MUTED = "#8B93A3"
FAINT = "#5E6676"

# Accent
LIME = "#C8F03C"
LIME_HOVER = "#D6F86A"
LIME_DARK = "#9DC21C"
ON_LIME = "#10140A"

# Status
SUCCESS = "#7BE495"
WARNING = "#F5C25B"
DANGER = "#FF6B6B"
INFO = "#7DB4FF"

# Glass layers (rgba strings for QSS)
GLASS = "rgba(255,255,255,0.055)"
GLASS_HI = "rgba(255,255,255,0.09)"
GLASS_HOVER = "rgba(255,255,255,0.12)"
GLASS_BORDER = "rgba(255,255,255,0.10)"
GLASS_EDGE = "rgba(255,255,255,0.18)"
LINE = "rgba(255,255,255,0.07)"

MONO = '"Cascadia Mono", "JetBrains Mono", "SF Mono", Consolas, "DejaVu Sans Mono", monospace'
# Source Serif 4 is bundled (assets/fonts, SIL Open Font License) for the calm, bookish reading feel.
SERIF = '"Source Serif 4", Georgia, "Times New Roman", serif'
SANS = SERIF
DISPLAY = SERIF

# Kept for code that colours single values (negative amounts, highlighted caps).
NEGATIVE = DANGER
HIGHLIGHT = LIME

_CHIP = "border-radius: 10px; padding: 3px 11px; font-weight: 600; font-size: 8.5pt;"

STYLESHEET = f"""
* {{
    font-family: {SANS};
    font-size: 10.5pt;
    color: {TEXT};
    outline: 0;
}}
QMainWindow {{ background: {BG}; }}
QDialog, QMessageBox {{ background: {BG_RAISED}; }}
QDialog QLabel, QMessageBox QLabel {{ background: transparent; }}
#Workspace, #Transparent {{ background: transparent; }}
#qt_scrollarea_viewport {{ background: transparent; }}
QToolTip {{ background: {BG_POPUP}; color: {TEXT}; border: 1px solid {GLASS_EDGE}; padding: 6px 9px; border-radius: 8px; }}

/* ---------- Shell ---------- */
#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.10), stop:1 rgba(255,255,255,0.04));
    border: 1px solid {GLASS_BORDER}; border-top-color: {GLASS_EDGE}; border-radius: 26px;
}}
#Sidebar QLabel {{ background: transparent; }}
#Sidebar QLabel#Brand {{ font-family: {DISPLAY}; font-size: 12.5pt; font-weight: 700; }}
#Sidebar QLabel#BrandSub {{ color: {MUTED}; font-size: 8.5pt; }}
#Sidebar QLabel#Logo {{ background: {LIME}; border-radius: 13px; }}
#Sidebar QPushButton {{
    color: {TEXT_SOFT}; background: transparent; border: 1px solid transparent; text-align: left;
    padding: 10px 14px; border-radius: 16px; font-size: 10pt;
}}
#Sidebar QPushButton:hover {{ background: {GLASS_HI}; color: {TEXT}; }}
#Sidebar QPushButton:checked, #Sidebar QPushButton:checked:hover {{ background: transparent; color: {ON_LIME}; font-weight: 700; }}
#Sidebar QFrame#NavIndicator {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {LIME_HOVER}, stop:1 {LIME});
    border: 1px solid rgba(255,255,255,0.35); border-radius: 16px;
}}
#Sidebar QLabel#Version {{ color: {MUTED}; font-family: {MONO}; font-size: 8pt; }}
#Sidebar QLabel#VersionDate {{ color: {FAINT}; font-size: 8pt; }}
#Sidebar QFrame#VersionBox {{ background: rgba(0,0,0,0.22); border: 1px solid {LINE}; border-radius: 14px; }}

#Shell {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.075), stop:1 rgba(255,255,255,0.03));
    border: 1px solid {GLASS_BORDER}; border-top-color: {GLASS_EDGE}; border-radius: 32px;
}}
#Header {{ background: transparent; }}
#Header QLabel {{ background: transparent; }}
#Header QLabel#PageTitle {{ font-family: {DISPLAY}; font-size: 24pt; font-weight: 700; }}
#Header QLabel#PageSub {{ color: {MUTED}; font-size: 10.5pt; }}
QLineEdit#GlobalSearch {{
    min-width: 300px; border-radius: 17px; padding: 8px 16px; background: rgba(0,0,0,0.25);
    border: 1px solid {GLASS_BORDER};
}}
QLineEdit#GlobalSearch:focus {{ border: 1px solid {LIME}; }}

/* ---------- Cards ---------- */
QFrame#Card {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.085), stop:1 rgba(255,255,255,0.035));
    border: 1px solid {GLASS_BORDER}; border-top-color: {GLASS_EDGE}; border-radius: 22px;
}}
QFrame#Card[accent="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {LIME_HOVER}, stop:1 {LIME_DARK});
    border: 1px solid rgba(255,255,255,0.35);
}}
QFrame#Card QLabel, QFrame#Card QCheckBox {{ background: transparent; }}
QFrame#Card[accent="true"] QLabel {{ color: {ON_LIME}; }}
QFrame#Card[accent="true"] QLabel#StatLabel {{ color: rgba(16,20,10,0.70); }}
QLabel#CardTitle {{ font-family: {DISPLAY}; font-size: 12pt; font-weight: 700; }}
QLabel#StatValue {{ font-family: {MONO}; font-size: 16pt; font-weight: 600; }}
QLabel#StatLabel {{ color: {MUTED}; font-size: 9pt; }}
QLabel#Badge {{ background: rgba(200,240,60,0.14); border: 1px solid rgba(200,240,60,0.25); border-radius: 14px; }}
QFrame#Card[accent="true"] QLabel#Badge {{ background: rgba(16,20,10,0.12); border: 1px solid rgba(16,20,10,0.15); }}
QLabel#Muted {{ color: {MUTED}; background: transparent; }}
QLabel#SectionTitle {{ font-size: 9pt; font-weight: 700; color: {LIME}; padding-top: 6px; letter-spacing: 1px; background: transparent; }}
QLabel#TotalValue {{ font-family: {MONO}; font-size: 13pt; font-weight: 600; }}
QLabel#BigNumber {{ font-family: {MONO}; font-size: 18pt; font-weight: 600; }}
QLabel#Hero {{ font-family: {DISPLAY}; font-size: 20pt; font-weight: 700; }}
QLabel#Negative, QLabel[negative="true"] {{ color: {DANGER}; }}
QLabel#Highlight {{ color: {LIME}; font-weight: 700; }}
QLabel#Strong {{ font-weight: 700; }}
QLabel#Amount {{ }}

/* ---------- Inputs ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{
    background: rgba(0,0,0,0.22); border: 1px solid {GLASS_BORDER}; border-radius: 12px; padding: 7px 11px;
    color: {TEXT}; selection-background-color: {LIME}; selection-color: {ON_LIME};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: rgba(255,255,255,0.20); }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {LIME}; }}
QLineEdit[invalid="true"] {{ border: 1px solid {DANGER}; background: rgba(255,107,107,0.10); }}
QLineEdit:read-only {{ background: rgba(255,255,255,0.03); color: {MUTED}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {FAINT}; }}
QComboBox {{ padding-right: 30px; combobox-popup: 0; }}
QComboBox::drop-down {{ border: none; width: 28px; subcontrol-origin: padding; subcontrol-position: center right; }}
QComboBox::down-arrow {{ image: url(upf:chevron.svg); width: 12px; height: 12px; }}

/* Drop-down lists are their own windows: solid background, light text. */
QComboBox QAbstractItemView, QListView#ComboPopup, QCompleter QAbstractItemView {{
    background: {BG_POPUP}; color: {TEXT}; border: 1px solid {GLASS_EDGE}; border-radius: 10px;
    padding: 4px; selection-background-color: {LIME}; selection-color: {ON_LIME};
}}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 4px 10px; border-radius: 7px; color: {TEXT}; background: transparent; }}
QComboBox QAbstractItemView::item:hover {{ background: {GLASS_HOVER}; color: {TEXT}; }}
QComboBox QAbstractItemView::item:selected {{ background: {LIME}; color: {ON_LIME}; }}
QComboBox QFrame {{ background: {BG_POPUP}; border: none; }}

QLabel#FieldError {{ color: {DANGER}; font-size: 8.5pt; background: transparent; }}

/* ---------- Buttons ---------- */
QPushButton {{
    background: {GLASS_HI}; border: 1px solid {GLASS_BORDER}; border-top-color: {GLASS_EDGE};
    border-radius: 14px; padding: 8px 16px; font-weight: 600; color: {TEXT};
}}
QPushButton:hover {{ background: {GLASS_HOVER}; border-color: rgba(255,255,255,0.22); }}
QPushButton:pressed {{ background: rgba(255,255,255,0.06); }}
QPushButton:disabled {{ color: {FAINT}; background: rgba(255,255,255,0.03); border-color: {LINE}; }}
QPushButton[variant="primary"] {{ background: {LIME}; border: 1px solid {LIME_HOVER}; color: {ON_LIME}; }}
QPushButton[variant="primary"]:hover {{ background: {LIME_HOVER}; }}
QPushButton[variant="primary"]:pressed {{ background: {LIME_DARK}; }}
QPushButton[variant="primary"]:disabled {{ background: rgba(200,240,60,0.25); border-color: transparent; color: rgba(16,20,10,0.6); }}
QPushButton[variant="danger"] {{ color: {DANGER}; }}
QPushButton[variant="danger"]:hover {{ background: rgba(255,107,107,0.14); border-color: rgba(255,107,107,0.35); }}
QPushButton[variant="pill"] {{ border-radius: 15px; padding: 7px 16px; }}
QPushButton::menu-indicator {{ subcontrol-position: right center; right: 10px; image: none; width: 0; }}

/* ---------- Tables and lists ---------- */
QTableView {{
    background: rgba(0,0,0,0.18); border: 1px solid {LINE}; border-radius: 16px; gridline-color: transparent;
    selection-background-color: rgba(200,240,60,0.20); selection-color: {TEXT}; alternate-background-color: rgba(255,255,255,0.025);
    color: {TEXT};
}}
QTableView::item {{ padding: 5px 8px; border-bottom: 1px solid {LINE}; }}
QTableView::item:hover {{ background: rgba(255,255,255,0.04); }}
QTableView::item:selected {{ background: rgba(200,240,60,0.20); color: {TEXT}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: transparent; color: {MUTED}; font-weight: 600; font-size: 8.5pt; border: none;
    border-bottom: 1px solid {GLASS_BORDER}; padding: 9px 8px;
}}
QHeaderView::section:hover {{ color: {TEXT}; }}
QTableCornerButton::section {{ background: transparent; border: none; }}

QListWidget {{ background: rgba(0,0,0,0.18); border: 1px solid {LINE}; border-radius: 16px; padding: 6px; color: {TEXT}; }}
QListWidget::item {{ padding: 10px 10px; border-radius: 12px; margin: 1px 0; }}
QListWidget::item:hover {{ background: {GLASS_HI}; }}
QListWidget::item:selected {{ background: rgba(200,240,60,0.18); color: {TEXT}; border: 1px solid rgba(200,240,60,0.35); }}

/* ---------- Tabs: segmented glass pills ---------- */
QTabWidget::pane {{ border: none; background: transparent; top: 6px; }}
QTabWidget::tab-bar {{ left: 0; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: {GLASS}; color: {TEXT_SOFT}; padding: 8px 18px; margin-right: 6px; border-radius: 14px;
    border: 1px solid {LINE};
}}
QTabBar::tab:hover {{ background: {GLASS_HOVER}; color: {TEXT}; }}
QTabBar::tab:selected {{ background: rgba(255,255,255,0.16); color: {TEXT}; border: 1px solid {GLASS_EDGE}; font-weight: 700; }}

/* ---------- Scroll bars ---------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.16); border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.28); }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 4px; }}
QScrollBar::handle:horizontal {{ background: rgba(255,255,255,0.16); border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- Menus ---------- */
QMenu {{ background: {BG_POPUP}; border: 1px solid {GLASS_EDGE}; border-radius: 12px; padding: 6px; color: {TEXT}; }}
QMenu::item {{ padding: 8px 22px 8px 12px; border-radius: 8px; color: {TEXT}; background: transparent; }}
QMenu::item:selected {{ background: {LIME}; color: {ON_LIME}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 8px; }}
QMenu::icon {{ padding-left: 8px; }}

QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 6px; border: 1px solid {GLASS_EDGE}; background: rgba(0,0,0,0.25); }}
QCheckBox::indicator:checked {{ background: {LIME}; border-color: {LIME}; image: url(upf:check-dark.svg); }}

QProgressBar {{ background: rgba(0,0,0,0.3); border: 1px solid {LINE}; border-radius: 9px; height: 18px; text-align: center; color: {TEXT}; font-size: 8.5pt; }}
QProgressBar::chunk {{ background: {LIME}; border-radius: 8px; }}

QFormLayout QLabel, QGroupBox {{ background: transparent; }}

/* ---------- Status chips ---------- */
QLabel[chip="draft"] {{ background: rgba(245,194,91,0.16); color: {WARNING}; border: 1px solid rgba(245,194,91,0.30); {_CHIP} }}
QLabel[chip="finalized"] {{ background: rgba(123,228,149,0.15); color: {SUCCESS}; border: 1px solid rgba(123,228,149,0.30); {_CHIP} }}
QLabel[chip="error"] {{ background: rgba(255,107,107,0.15); color: {DANGER}; border: 1px solid rgba(255,107,107,0.30); {_CHIP} }}
QLabel[chip="ok"] {{ background: rgba(123,228,149,0.15); color: {SUCCESS}; border: 1px solid rgba(123,228,149,0.30); {_CHIP} }}
QLabel[chip="lime"] {{ background: rgba(200,240,60,0.15); color: {LIME}; border: 1px solid rgba(200,240,60,0.30); {_CHIP} }}

QFrame#Banner {{ border-radius: 14px; }}
QFrame#Banner QLabel {{ background: transparent; }}
QFrame#Banner[level="warning"] {{ background: rgba(245,194,91,0.12); border: 1px solid rgba(245,194,91,0.30); }}
QFrame#Banner[level="error"] {{ background: rgba(255,107,107,0.12); border: 1px solid rgba(255,107,107,0.32); }}
QFrame#Banner[level="ok"] {{ background: rgba(123,228,149,0.10); border: 1px solid rgba(123,228,149,0.28); }}
"""


def palette() -> QPalette:
    """A dark palette so anything the style sheet doesn't reach (native bits, pop-up frames) matches."""
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG_RAISED,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: BG_POPUP,
        QPalette.ColorRole.AlternateBase: "#222731",
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: "#252A33",
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.ToolTipBase: BG_POPUP,
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.PlaceholderText: FAINT,
        QPalette.ColorRole.Highlight: LIME,
        QPalette.ColorRole.HighlightedText: ON_LIME,
        QPalette.ColorRole.BrightText: "#FFFFFF",
        QPalette.ColorRole.Link: LIME,
        QPalette.ColorRole.Light: "#3A404C",
        QPalette.ColorRole.Midlight: "#2C313B",
        QPalette.ColorRole.Mid: "#232730",
        QPalette.ColorRole.Dark: "#0A0C10",
        QPalette.ColorRole.Shadow: "#000000",
    }
    for role, colour in roles.items():
        p.setColor(role, QColor(colour))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(FAINT))
    return p


def apply(app) -> None:
    """Fusion style + dark palette + style sheet. The palette is set explicitly so a Windows
    dark/light system setting can't leave dark text on dark drop-down rows."""
    from . import resources

    resources.register()
    app.setStyle("Fusion")
    font = QFont("Source Serif 4")
    font.setStyleHint(QFont.StyleHint.Serif)
    font.setPointSizeF(10.5)
    app.setFont(font)
    app.setPalette(palette())
    app.setStyleSheet(STYLESHEET)
