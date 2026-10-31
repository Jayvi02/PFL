"""Light theme with navy accents (Qt style sheet)."""

NAVY = "#1F3A68"
NAVY_DARK = "#162B4E"
BLUE = "#2F6FED"
BLUE_SOFT = "#E8F0FE"
BG = "#F4F6FA"
SURFACE = "#FFFFFF"
BORDER = "#E1E6EF"
TEXT = "#1B2433"
MUTED = "#6B778C"
SUCCESS = "#1E8E5A"
SUCCESS_SOFT = "#E3F5EC"
WARNING = "#B7791F"
WARNING_SOFT = "#FDF3E1"
DANGER = "#C53030"
DANGER_SOFT = "#FDECEC"

STYLESHEET = f"""
* {{
    font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    color: {TEXT};
}}
QMainWindow, QDialog, #Workspace {{ background: {BG}; }}
QToolTip {{ background: {NAVY_DARK}; color: white; border: none; padding: 6px 8px; border-radius: 6px; }}

/* Sidebar */
#Sidebar {{ background: {NAVY}; }}
#Sidebar QLabel#Brand {{ color: white; font-size: 12.5pt; font-weight: 600; }}
#Sidebar QLabel#BrandSub {{ color: #9FB3D6; font-size: 8.5pt; }}
#Sidebar QPushButton {{
    color: #D6E0F2; background: transparent; border: none; text-align: left;
    padding: 9px 14px; border-radius: 8px; font-size: 10pt;
}}
#Sidebar QPushButton:hover {{ background: rgba(255,255,255,0.08); color: white; }}
#Sidebar QPushButton:checked {{ background: rgba(255,255,255,0.16); color: white; font-weight: 600; }}
#Sidebar QLabel#Version {{ color: #7F93B8; font-size: 8pt; }}

/* Header */
#Header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
#Header QLabel#PageTitle {{ font-size: 15pt; font-weight: 600; }}
#Header QLabel#UserLabel {{ color: {MUTED}; }}
QLineEdit#GlobalSearch {{ min-width: 280px; border-radius: 16px; padding: 6px 12px; background: {BG}; }}

/* Cards */
#Card, QFrame#Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel#CardTitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#StatValue {{ font-size: 19pt; font-weight: 600; color: {NAVY}; }}
QLabel#StatLabel {{ color: {MUTED}; font-size: 9pt; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#SectionTitle {{ font-size: 10.5pt; font-weight: 600; color: {NAVY}; padding-top: 4px; }}
QLabel#BigNumber {{ font-size: 22pt; font-weight: 700; color: {NAVY}; }}

/* Inputs */
QLineEdit, QComboBox, QSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 7px; padding: 6px 9px;
    selection-background-color: {BLUE};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border: 1px solid {BLUE}; }}
QLineEdit[invalid="true"] {{ border: 1px solid {DANGER}; background: {DANGER_SOFT}; }}
QLineEdit:read-only {{ background: {BG}; color: {MUTED}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ border: 1px solid {BORDER}; selection-background-color: {BLUE_SOFT}; selection-color: {TEXT}; }}
QLabel#FieldError {{ color: {DANGER}; font-size: 8.5pt; }}

/* Buttons */
QPushButton {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 7px; padding: 7px 14px; font-weight: 500;
}}
QPushButton:hover {{ background: #F0F3F9; border-color: #CBD3E1; }}
QPushButton:pressed {{ background: #E6EBF4; }}
QPushButton:disabled {{ color: #A6B0C0; background: #F6F7FA; }}
QPushButton[variant="primary"] {{ background: {BLUE}; border: 1px solid {BLUE}; color: white; }}
QPushButton[variant="primary"]:hover {{ background: #255FD6; }}
QPushButton[variant="primary"]:disabled {{ background: #A9C2F5; border-color: #A9C2F5; }}
QPushButton[variant="danger"] {{ color: {DANGER}; }}
QPushButton[variant="danger"]:hover {{ background: {DANGER_SOFT}; border-color: #F2C4C4; }}
QPushButton::menu-indicator {{ subcontrol-position: right center; right: 8px; }}

/* Tables */
QTableView {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; gridline-color: transparent;
    selection-background-color: {BLUE_SOFT}; selection-color: {TEXT}; alternate-background-color: #FAFBFD;
}}
QTableView::item {{ padding: 4px 8px; border-bottom: 1px solid #EEF1F6; }}
QHeaderView::section {{
    background: #F7F9FC; color: {MUTED}; font-weight: 600; font-size: 9pt; border: none;
    border-bottom: 1px solid {BORDER}; padding: 7px 8px;
}}
QTableCornerButton::section {{ background: #F7F9FC; border: none; }}

QListWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 4px; }}
QListWidget::item {{ padding: 9px 10px; border-radius: 7px; }}
QListWidget::item:selected {{ background: {BLUE_SOFT}; color: {TEXT}; }}
QListWidget::item:hover {{ background: #F3F6FB; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; padding: 8px 16px; color: {MUTED}; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {NAVY}; border-bottom: 2px solid {BLUE}; font-weight: 600; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #CDD5E2; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #CDD5E2; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

QMenu {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {BLUE_SOFT}; color: {TEXT}; }}

QCheckBox::indicator {{ width: 16px; height: 16px; }}

/* Status chips */
QLabel[chip="draft"] {{ background: {WARNING_SOFT}; color: {WARNING}; border-radius: 9px; padding: 2px 10px; font-weight: 600; font-size: 8.5pt; }}
QLabel[chip="finalized"] {{ background: {SUCCESS_SOFT}; color: {SUCCESS}; border-radius: 9px; padding: 2px 10px; font-weight: 600; font-size: 8.5pt; }}
QLabel[chip="error"] {{ background: {DANGER_SOFT}; color: {DANGER}; border-radius: 9px; padding: 2px 10px; font-weight: 600; font-size: 8.5pt; }}
QLabel[chip="ok"] {{ background: {SUCCESS_SOFT}; color: {SUCCESS}; border-radius: 9px; padding: 2px 10px; font-weight: 600; font-size: 8.5pt; }}

QFrame#Banner[level="warning"] {{ background: {WARNING_SOFT}; border: 1px solid #F3D9A6; border-radius: 8px; }}
QFrame#Banner[level="error"] {{ background: {DANGER_SOFT}; border: 1px solid #F2C4C4; border-radius: 8px; }}
QFrame#Banner[level="ok"] {{ background: {SUCCESS_SOFT}; border: 1px solid #BDE5CF; border-radius: 8px; }}

/* Login */
#LoginPanel {{ background: {NAVY}; }}
#LoginPanel QLabel {{ color: white; }}
#LoginPanel QLabel#LoginSub {{ color: #A9BBDB; }}
"""
