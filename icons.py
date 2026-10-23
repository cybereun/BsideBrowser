# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Cute 3D-Tactile Minimal Vector Icon Renderer
Generates crisp, well-proportioned QIcons / QPixmaps with subtle 3D elevation,
soft highlights, and clean minimal strokes so buttons never look tiny or jagged.
"""

from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QLinearGradient,
    QFont,
)
from PySide6.QtCore import Qt, QRectF, QPointF
import math
import os


def get_app_window_icon() -> QIcon:
    """
    Returns Image 1 (3D glowing globe + paper plane icon: `assets/app_icon.ico` / `app_icon.png`)
    for the Windows Taskbar, Desktop shortcut, and main window icon.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "assets", "app_icon.ico")
    png_path = os.path.join(base_dir, "assets", "app_icon.png")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    if os.path.exists(png_path):
        return QIcon(png_path)
    return QIcon(make_3d_badge_pixmap("🌐", "#38BDF8", "#4F46E5", size=64, radius=16))


def get_internal_title_icon_pixmap(size: int = 36) -> QPixmap:
    """
    Returns Image 2 (the 3D 'B' badge with orbit ring & star: `assets/internal_b_icon.png`)
    scaled smoothly for use exclusively in front of internal titles inside the app.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    b_path = os.path.join(base_dir, "assets", "internal_b_icon.png")
    if os.path.exists(b_path):
        pix = QPixmap(b_path)
        if not pix.isNull():
            return pix.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    return make_3d_badge_pixmap("B", top_color="#6366F1", bottom_color="#4338CA", size=size, radius=int(size * 0.28))


def make_provider_icon_pixmap(provider_or_model_id: str, size: int = 20) -> QPixmap:
    """
    Renders a crisp, tactile 3D company/brand emblem icon for each AI model provider:
    - OpenAI / Codex (`codex:...`, `openai-api`): Emerald-teal 3D badge with OpenAI 6-petal flower/knot emblem
    - Anthropic / Claude (`claude:...`, `claude-api`): Warm terracotta-orange 3D badge with Anthropic starburst/spark emblem
    - Google / Antigravity / Gemini (`antigravity:...`, `gemini-api`): Blue-violet 3D badge with 4-point Gemini/Antigravity star
    - Ollama / Local (`custom-local`): Charcoal-slate 3D badge with terminal/cube emblem
    - Bside Built-in (`bside-autonomous-v1`): Indigo 3D badge with Bside star
    """
    m = (provider_or_model_id or "").lower()
    if "codex" in m or "openai" in m or "gpt" in m:
        top_c, bot_c = "#10B981", "#047857"   # OpenAI Emerald Green
        brand = "openai"
    elif "claude" in m or "anthropic" in m:
        top_c, bot_c = "#EA580C", "#C2410C"   # Anthropic Claude Terracotta Orange
        brand = "claude"
    elif "antigravity" in m or "gemini" in m or "google" in m:
        top_c, bot_c = "#3B82F6", "#6366F1"   # Google Gemini / Antigravity Blue-Indigo
        brand = "gemini"
    elif "local" in m or "ollama" in m:
        top_c, bot_c = "#475569", "#1E293B"   # Local Ollama Slate
        brand = "ollama"
    else:
        top_c, bot_c = "#818CF8", "#4F46E5"   # Bside Indigo
        brand = "bside"

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    radius = max(5.0, size * 0.28)
    # 3D drop shadow
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 40))
    p.drawRoundedRect(QRectF(1.0, 1.8, size - 2.0, size - 2.2), radius, radius)

    # 3D gradient body
    body = QRectF(1.0, 0.8, size - 2.0, size - 2.4)
    grad = QLinearGradient(body.topLeft(), body.bottomLeft())
    grad.setColorAt(0.0, QColor(top_c))
    grad.setColorAt(1.0, QColor(bot_c))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(body, radius, radius)

    # Glossy inner top rim
    p.setPen(QPen(QColor(255, 255, 255, 85), 0.9))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(body.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)

    cx = body.center().x()
    cy = body.center().y()
    r = size * 0.27

    if brand == "openai":
        # OpenAI signature 6-lobed vortex / blossom + center hexagon
        pen = QPen(QColor("#FFFFFF"), max(1.4, size * 0.085), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(6):
            ang = math.radians(i * 60)
            px = cx + math.cos(ang) * (r * 0.48)
            py = cy + math.sin(ang) * (r * 0.48)
            p.drawEllipse(QPointF(px, py), r * 0.52, r * 0.52)

    elif brand == "claude":
        # Anthropic Claude signature 8-ray warm sunburst spark
        pen = QPen(QColor("#FFFFFF"), max(1.6, size * 0.095), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for i in range(8):
            ang = math.radians(i * 45 + 12)
            r_out = r * (1.08 if i % 2 == 0 else 0.78)
            p.drawLine(
                QPointF(cx + math.cos(ang) * (r * 0.18), cy + math.sin(ang) * (r * 0.18)),
                QPointF(cx + math.cos(ang) * r_out, cy + math.sin(ang) * r_out),
            )

    elif brand == "gemini":
        # Google Gemini / Antigravity 4-pointed curved star
        path = QPainterPath()
        outer_r = r * 1.18
        inner_r = r * 0.28
        pts = [
            QPointF(cx, cy - outer_r),
            QPointF(cx + inner_r, cy - inner_r),
            QPointF(cx + outer_r, cy),
            QPointF(cx + inner_r, cy + inner_r),
            QPointF(cx, cy + outer_r),
            QPointF(cx - inner_r, cy + inner_r),
            QPointF(cx - outer_r, cy),
            QPointF(cx - inner_r, cy - inner_r),
        ]
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawPath(path)

    elif brand == "ollama":
        # Cute terminal prompt `>_`
        pen = QPen(QColor("#FFFFFF"), max(1.5, size * 0.09), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(cx - r * 0.75, cy - r * 0.55)
        path.lineTo(cx - r * 0.10, cy)
        path.lineTo(cx - r * 0.75, cy + r * 0.55)
        p.drawPath(path)
        p.drawLine(QPointF(cx + r * 0.10, cy + r * 0.55), QPointF(cx + r * 0.75, cy + r * 0.55))

    else:
        # Bside emblem
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI Symbol", int(size * 0.45), QFont.Weight.Bold))
        p.drawText(body, Qt.AlignmentFlag.AlignCenter, "✦")

    p.end()
    return pix


def make_provider_icon(provider_or_model_id: str, size: int = 20) -> QIcon:
    return QIcon(make_provider_icon_pixmap(provider_or_model_id, size=size))


def make_status_chip_icon(kind: str, size: int = 22) -> QIcon:
    """
    Renders a crisp, colorful 3D badge icon for the permission (`perm_btn`) and context (`ctx_btn`)
    selector buttons and their dropdown menu items so the user can immediately see which option is active!
    Supported kinds:
    - 'perm_safe': 🛡️ Emerald green shield badge (자동 안전 제어)
    - 'perm_ask': ✋ Warm amber hand badge (매번 확인)
    - 'perm_full': ⚡ Electric indigo lightning badge (완전 자율 원격제어)
    - 'ctx_summary': 📝 Sky-blue document summary badge (현재 페이지 요약)
    - 'ctx_remote': 🕹️ Purple remote controller badge (원격 조작 도구)
    - 'ctx_visual': 📊 Emerald-teal bar chart badge (페이지 구조 시각화)
    - 'ctx_draft': ✉️ Rose-pink envelope/draft badge (공유 초안 카드)
    """
    badge_specs = {
        "perm_safe": ("#10B981", "#059669"),
        "perm_ask": ("#F59E0B", "#D97706"),
        "perm_full": ("#6366F1", "#4F46E5"),
        "ctx_summary": ("#3B82F6", "#2563EB"),
        "ctx_remote": ("#8B5CF6", "#6D28D9"),
        "ctx_visual": ("#14B8A6", "#0D9488"),
        "ctx_draft": ("#EC4899", "#DB2777"),
    }
    top_c, bot_c = badge_specs.get(kind, ("#64748B", "#475569"))

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    radius = max(5.5, size * 0.28)
    # 3D drop shadow
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 42))
    p.drawRoundedRect(QRectF(1.0, 1.8, size - 2.0, size - 2.2), radius, radius)

    # 3D gradient body
    body = QRectF(1.0, 0.8, size - 2.0, size - 2.4)
    grad = QLinearGradient(body.topLeft(), body.bottomLeft())
    grad.setColorAt(0.0, QColor(top_c))
    grad.setColorAt(1.0, QColor(bot_c))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(body, radius, radius)

    # Glossy inner top rim
    p.setPen(QPen(QColor(255, 255, 255, 90), 0.9))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(body.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)

    cx = body.center().x()
    cy = body.center().y()
    pen = QPen(QColor("#FFFFFF"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if kind == "perm_safe":
        # Crisp Shield + Checkmark
        sh = QPainterPath()
        sh.moveTo(cx, size * 0.22)
        sh.lineTo(size * 0.74, size * 0.30)
        sh.lineTo(size * 0.70, size * 0.56)
        sh.lineTo(cx, size * 0.76)
        sh.lineTo(size * 0.30, size * 0.56)
        sh.lineTo(size * 0.26, size * 0.30)
        sh.closeSubpath()
        p.drawPath(sh)
        p.drawLine(QPointF(size * 0.40, cy + 1), QPointF(cx - 1, size * 0.58))
        p.drawLine(QPointF(cx - 1, size * 0.58), QPointF(size * 0.62, size * 0.40))

    elif kind == "perm_ask":
        # Crisp Raised Hand (Palm + 4 distinct fingers)
        palm = QRectF(size * 0.30, size * 0.46, size * 0.40, size * 0.28)
        p.drawRoundedRect(palm, 3.5, 3.5)
        for fx in (0.34, 0.44, 0.54, 0.64):
            p.drawLine(QPointF(size * fx, size * 0.46), QPointF(size * fx, size * 0.24))

    elif kind == "perm_full":
        # Crisp Lightning Bolt
        bolt = QPainterPath()
        bolt.moveTo(size * 0.56, size * 0.20)
        bolt.lineTo(size * 0.32, size * 0.52)
        bolt.lineTo(size * 0.50, size * 0.52)
        bolt.lineTo(size * 0.44, size * 0.78)
        bolt.lineTo(size * 0.68, size * 0.46)
        bolt.lineTo(size * 0.50, size * 0.46)
        bolt.closeSubpath()
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(bolt)

    elif kind == "ctx_summary":
        # Crisp Document Lines
        doc = QRectF(size * 0.28, size * 0.22, size * 0.44, size * 0.54)
        p.drawRoundedRect(doc, 3.0, 3.0)
        p.drawLine(QPointF(size * 0.36, size * 0.36), QPointF(size * 0.64, size * 0.36))
        p.drawLine(QPointF(size * 0.36, size * 0.48), QPointF(size * 0.64, size * 0.48))
        p.drawLine(QPointF(size * 0.36, size * 0.60), QPointF(size * 0.54, size * 0.60))

    elif kind == "ctx_remote":
        # Crisp Cursor / Remote Pointer
        ptr = QPainterPath()
        ptr.moveTo(size * 0.32, size * 0.24)
        ptr.lineTo(size * 0.32, size * 0.72)
        ptr.lineTo(size * 0.46, size * 0.58)
        ptr.lineTo(size * 0.60, size * 0.74)
        ptr.lineTo(size * 0.68, size * 0.66)
        ptr.lineTo(size * 0.54, size * 0.50)
        ptr.lineTo(size * 0.70, size * 0.50)
        ptr.closeSubpath()
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(ptr)

    elif kind == "ctx_visual":
        # Crisp 3-Bar Chart
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(size * 0.26, size * 0.50, size * 0.12, size * 0.24), 2.0, 2.0)
        p.drawRoundedRect(QRectF(size * 0.44, size * 0.34, size * 0.12, size * 0.40), 2.0, 2.0)
        p.drawRoundedRect(QRectF(size * 0.62, size * 0.24, size * 0.12, size * 0.50), 2.0, 2.0)

    elif kind == "ctx_draft":
        # Crisp Envelope
        env = QRectF(size * 0.24, size * 0.30, size * 0.52, size * 0.38)
        p.drawRoundedRect(env, 3.0, 3.0)
        flap = QPainterPath()
        flap.moveTo(size * 0.26, size * 0.32)
        flap.lineTo(cx, size * 0.52)
        flap.lineTo(size * 0.74, size * 0.32)
        p.drawPath(flap)

    p.end()
    return QIcon(pix)


def make_3d_badge_pixmap(
    glyph: str,
    top_color: str = "#6366F1",
    bottom_color: str = "#4338CA",
    fg_color: str = "#FFFFFF",
    size: int = 34,
    radius: int = 10,
) -> QPixmap:
    """
    Creates a tactile 3D rounded badge pixmap with a subtle top specular highlight,
    gradient fill, and crisp centered vector/symbol glyph (like Image 4's blue globe badge).
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    # Subtle bottom shadow layer for 3D depth
    shadow_rect = QRectF(1.5, 2.5, size - 3, size - 3)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 45))
    painter.drawRoundedRect(shadow_rect, radius, radius)

    # Main 3D gradient body
    body_rect = QRectF(1.5, 1.0, size - 3, size - 3.5)
    grad = QLinearGradient(body_rect.topLeft(), body_rect.bottomLeft())
    grad.setColorAt(0.0, QColor(top_color))
    grad.setColorAt(1.0, QColor(bottom_color))
    painter.setBrush(QBrush(grad))
    painter.drawRoundedRect(body_rect, radius, radius)

    # Top inner glossy highlight rim
    rim_pen = QPen(QColor(255, 255, 255, 90), 1.1)
    painter.setPen(rim_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(body_rect.adjusted(0.6, 0.6, -0.6, -0.6), radius - 0.5, radius - 0.5)

    # Draw crisp glyph or vector shape
    painter.setPen(QColor(fg_color))
    font = QFont("Segoe UI Symbol", int(size * 0.42), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(body_rect, Qt.AlignmentFlag.AlignCenter, glyph)

    painter.end()
    return pix


def make_nav_icon(
    kind: str,
    fg_hex: str = "#3A3A40",
    accent_hex: str = "#4F46E5",
    size: int = 24,
) -> QIcon:
    """
    Draws clean, large, rounded-stroke minimal vector icons with a subtle 3D drop shadow
    matching the clean aesthetic of Image 2, 3, and 4:
    - 'back': left arrow ←
    - 'forward': right arrow →
    - 'reload': circular refresh arrow ↻
    - 'home': cute minimal house ⌂
    - 'new_chat': rounded square with edit pencil (Image 3)
    - 'sidebar': split-panel sidebar icon (Image 3)
    - 'plus': plus icon +
    - 'send': upward arrow / send icon
    - 'remote': remote cursor / AI control icon
    - 'star_off' / 'star_on': bookmark star
    - 'settings': minimal sliders / gear
    - 'vault': lock icon
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    fg = QColor(fg_hex)
    shadow = QColor(0, 0, 0, 32)
    accent = QColor(accent_hex)

    def draw_shape(pen_color: QColor, dy: float = 0.0):
        pen = QPen(pen_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        c = size / 2.0
        if kind == "back":
            p.drawLine(QPointF(size * 0.74, c + dy), QPointF(size * 0.26, c + dy))
            path = QPainterPath()
            path.moveTo(size * 0.46, size * 0.28 + dy)
            path.lineTo(size * 0.25, c + dy)
            path.lineTo(size * 0.46, size * 0.72 + dy)
            p.drawPath(path)

        elif kind == "forward":
            p.drawLine(QPointF(size * 0.26, c + dy), QPointF(size * 0.74, c + dy))
            path = QPainterPath()
            path.moveTo(size * 0.54, size * 0.28 + dy)
            path.lineTo(size * 0.75, c + dy)
            path.lineTo(size * 0.54, size * 0.72 + dy)
            p.drawPath(path)

        elif kind == "reload":
            rect = QRectF(size * 0.24, size * 0.24 + dy, size * 0.52, size * 0.52)
            p.drawArc(rect, 35 * 16, 290 * 16)
            # Arrowhead at top-right
            path = QPainterPath()
            path.moveTo(size * 0.56, size * 0.19 + dy)
            path.lineTo(size * 0.74, size * 0.26 + dy)
            path.lineTo(size * 0.65, size * 0.43 + dy)
            p.drawPath(path)

        elif kind == "home":
            path = QPainterPath()
            # Roof + House body (cute rounded minimal house like Image 2)
            path.moveTo(size * 0.24, size * 0.48 + dy)
            path.lineTo(c, size * 0.24 + dy)
            path.lineTo(size * 0.76, size * 0.48 + dy)
            path.lineTo(size * 0.76, size * 0.76 + dy)
            path.lineTo(size * 0.24, size * 0.76 + dy)
            path.closeSubpath()
            p.drawPath(path)

        elif kind == "new_chat":
            # Rounded box with diagonal pencil (Image 3)
            box = QRectF(size * 0.22, size * 0.24 + dy, size * 0.52, size * 0.52)
            p.drawRoundedRect(box, 4.5, 4.5)
            p.drawLine(QPointF(size * 0.48, size * 0.52 + dy), QPointF(size * 0.78, size * 0.22 + dy))

        elif kind == "sidebar":
            # Rounded rectangle with right vertical divider (Image 3)
            box = QRectF(size * 0.20, size * 0.24 + dy, size * 0.60, size * 0.52)
            p.drawRoundedRect(box, 4.5, 4.5)
            p.drawLine(QPointF(size * 0.58, size * 0.25 + dy), QPointF(size * 0.58, size * 0.75 + dy))

        elif kind == "plus":
            p.drawLine(QPointF(c, size * 0.27 + dy), QPointF(c, size * 0.73 + dy))
            p.drawLine(QPointF(size * 0.27, c + dy), QPointF(size * 0.73, c + dy))

        elif kind == "send":
            p.drawLine(QPointF(c, size * 0.74 + dy), QPointF(c, size * 0.26 + dy))
            path = QPainterPath()
            path.moveTo(size * 0.30, size * 0.45 + dy)
            path.lineTo(c, size * 0.25 + dy)
            path.lineTo(size * 0.70, size * 0.45 + dy)
            p.drawPath(path)

        elif kind == "remote":
            # Cute cursor / magic wand icon
            path = QPainterPath()
            path.moveTo(size * 0.28, size * 0.24 + dy)
            path.lineTo(size * 0.28, size * 0.72 + dy)
            path.lineTo(size * 0.44, size * 0.58 + dy)
            path.lineTo(size * 0.58, size * 0.78 + dy)
            path.lineTo(size * 0.66, size * 0.72 + dy)
            path.lineTo(size * 0.52, size * 0.52 + dy)
            path.lineTo(size * 0.72, size * 0.52 + dy)
            path.closeSubpath()
            p.drawPath(path)

        elif kind in ("star_off", "star_on"):
            if kind == "star_on":
                p.setBrush(QBrush(QColor("#F59E0B")))
                p.setPen(QPen(QColor("#D97706"), 1.8))
            path = QPainterPath()
            path.moveTo(c, size * 0.20 + dy)
            path.lineTo(size * 0.60, size * 0.40 + dy)
            path.lineTo(size * 0.82, size * 0.43 + dy)
            path.lineTo(size * 0.65, size * 0.58 + dy)
            path.lineTo(size * 0.70, size * 0.79 + dy)
            path.lineTo(c, size * 0.68 + dy)
            path.lineTo(size * 0.30, size * 0.79 + dy)
            path.lineTo(size * 0.35, size * 0.58 + dy)
            path.lineTo(size * 0.18, size * 0.43 + dy)
            path.lineTo(size * 0.40, size * 0.40 + dy)
            path.closeSubpath()
            p.drawPath(path)

        elif kind == "vault":
            # Key icon matching uploaded reference image (circle head at top-right, diagonal shaft to bottom-left with teeth)
            p.drawEllipse(QPointF(size * 0.62, size * 0.36 + dy), size * 0.16, size * 0.16)
            path = QPainterPath()
            path.moveTo(size * 0.50, size * 0.48 + dy)
            path.lineTo(size * 0.24, size * 0.74 + dy)
            path.lineTo(size * 0.32, size * 0.80 + dy)
            path.lineTo(size * 0.40, size * 0.70 + dy)
            path.lineTo(size * 0.46, size * 0.74 + dy)
            path.lineTo(size * 0.56, size * 0.54 + dy)
            p.drawPath(path)

        elif kind == "extension":
            # Chrome Extension Puzzle Piece icon matching uploaded reference image (top knob, right indentation)
            path = QPainterPath()
            path.moveTo(size * 0.25, size * 0.34 + dy)
            path.lineTo(size * 0.41, size * 0.34 + dy)
            # Top knob protruding up
            path.arcTo(QRectF(size * 0.41, size * 0.18 + dy, size * 0.18, size * 0.18), 180, -180)
            path.lineTo(size * 0.75, size * 0.34 + dy)
            # Right side with inward notch
            path.lineTo(size * 0.75, size * 0.45 + dy)
            path.arcTo(QRectF(size * 0.65, size * 0.45 + dy, size * 0.18, size * 0.18), 90, 180)
            path.lineTo(size * 0.75, size * 0.76 + dy)
            # Bottom & Left
            path.lineTo(size * 0.25, size * 0.76 + dy)
            path.closeSubpath()
            p.drawPath(path)

        elif kind == "media":
            # Media lines + musical note icon matching uploaded reference image
            p.drawLine(QPointF(size * 0.22, size * 0.32 + dy), QPointF(size * 0.50, size * 0.32 + dy))
            p.drawLine(QPointF(size * 0.22, size * 0.46 + dy), QPointF(size * 0.50, size * 0.46 + dy))
            p.drawLine(QPointF(size * 0.22, size * 0.60 + dy), QPointF(size * 0.42, size * 0.60 + dy))
            # Note stem & flag
            p.drawLine(QPointF(size * 0.64, size * 0.68 + dy), QPointF(size * 0.64, size * 0.30 + dy))
            p.drawLine(QPointF(size * 0.64, size * 0.30 + dy), QPointF(size * 0.78, size * 0.30 + dy))
            p.setBrush(QBrush(pen_color))
            p.drawEllipse(QPointF(size * 0.57, size * 0.68 + dy), size * 0.08, size * 0.07)
            p.setBrush(Qt.BrushStyle.NoBrush)

        elif kind == "settings":
            p.drawEllipse(QPointF(c, c + dy), size * 0.16, size * 0.16)
            p.drawEllipse(QPointF(c, c + dy), size * 0.28, size * 0.28)

        elif kind == "hand":
            # Open palm / hand icon matching bottom-left of Image 1 & 3
            palm = QRectF(size * 0.28, size * 0.44 + dy, size * 0.42, size * 0.34)
            p.drawRoundedRect(palm, 5.0, 5.0)
            for fx in (0.32, 0.43, 0.54, 0.65):
                p.drawLine(QPointF(size * fx, size * 0.44 + dy), QPointF(size * fx, size * 0.22 + dy))

        elif kind == "layers":
            # Stacked context/history icon matching second icon in bottom bar of Image 1 & 3
            p.drawLine(QPointF(size * 0.32, size * 0.24 + dy), QPointF(size * 0.68, size * 0.24 + dy))
            p.drawLine(QPointF(size * 0.26, size * 0.36 + dy), QPointF(size * 0.74, size * 0.36 + dy))
            tray = QRectF(size * 0.22, size * 0.48 + dy, size * 0.56, size * 0.28)
            p.drawRoundedRect(tray, 4.0, 4.0)

        elif kind == "sparkle":
            # AI Model emblem icon matching bottom bar of Image 1, 2, 3
            p.drawEllipse(QPointF(c, c + dy), size * 0.28, size * 0.28)
            p.drawLine(QPointF(c, size * 0.30 + dy), QPointF(c, size * 0.70 + dy))
            p.drawLine(QPointF(size * 0.30, c + dy), QPointF(size * 0.70, c + dy))

        elif kind == "mic":
            # Microphone / Send icon inside dark circle in Image 3
            cap = QRectF(size * 0.38, size * 0.22 + dy, size * 0.24, size * 0.34)
            p.drawRoundedRect(cap, 4.0, 4.0)
            arc_r = QRectF(size * 0.28, size * 0.34 + dy, size * 0.44, size * 0.32)
            p.drawArc(arc_r, 180 * 16, 180 * 16)
            p.drawLine(QPointF(c, size * 0.66 + dy), QPointF(c, size * 0.78 + dy))

        elif kind == "enter":
            # Crisp Enter / Return key icon (↵)
            path = QPainterPath()
            path.moveTo(size * 0.72, size * 0.28 + dy)
            path.lineTo(size * 0.72, size * 0.56 + dy)
            path.lineTo(size * 0.28, size * 0.56 + dy)
            p.drawPath(path)
            arr = QPainterPath()
            arr.moveTo(size * 0.44, size * 0.40 + dy)
            arr.lineTo(size * 0.26, size * 0.56 + dy)
            arr.lineTo(size * 0.44, size * 0.72 + dy)
            p.drawPath(arr)

        elif kind == "stop":
            # Recording stop square icon
            p.setBrush(QBrush(pen_color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(size * 0.32, size * 0.32 + dy, size * 0.36, size * 0.36), 3.0, 3.0)
            p.setBrush(Qt.BrushStyle.NoBrush)

    # 1. Soft 3D drop shadow
    draw_shape(shadow, dy=1.0)
    # 2. Foreground crisp stroke
    draw_shape(fg if kind != "remote" else accent, dy=0.0)

    p.end()
    return QIcon(pix)


def make_pushpin_icon(pinned: bool = False, size: int = 20) -> QIcon:
    """
    Renders the Chrome Extension Pushpin (압핀) icon matching Image 1:
    - When `pinned=True`: Solid/active blue-indigo or charcoal pushpin (고정됨 -> 툴바에 아이콘 표시)
    - When `pinned=False`: Outline pushpin with diagonal slash in magenta/rose (`#E11D48` / `#EC4899`)
      matching Image 1's crossed-out pushpin icon!
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    color = QColor("#2563EB") if pinned else QColor("#DB2777")
    pen = QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    # Top horizontal bar of pushpin
    p.drawLine(QPointF(size * 0.30, size * 0.22), QPointF(size * 0.70, size * 0.22))

    # Body of pushpin tapering down to a wider flange
    body = QPainterPath()
    body.moveTo(size * 0.36, size * 0.22)
    body.lineTo(size * 0.36, size * 0.44)
    body.lineTo(size * 0.26, size * 0.56)
    body.lineTo(size * 0.74, size * 0.56)
    body.lineTo(size * 0.64, size * 0.44)
    body.lineTo(size * 0.64, size * 0.22)
    body.closeSubpath()

    if pinned:
        p.setBrush(QBrush(QColor(37, 99, 235, 65)))
    else:
        p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(body)

    # Bottom needle point
    p.drawLine(QPointF(size * 0.50, size * 0.56), QPointF(size * 0.50, size * 0.82))

    # Diagonal slash when unpinned (exactly like Image 1's pink crossed-out pin)
    if not pinned:
        slash_pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(slash_pen)
        p.drawLine(QPointF(size * 0.20, size * 0.20), QPointF(size * 0.80, size * 0.80))

    p.end()
    return QIcon(pix)


def make_more_dots_icon(fg_hex: str = "#52525B", size: int = 20) -> QIcon:
    """Renders the vertical 3-dots (`⋮`) menu icon matching Image 1."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(fg_hex))
    cx = size * 0.5
    r = max(1.5, size * 0.08)
    for ry in (0.26, 0.50, 0.74):
        p.drawEllipse(QPointF(cx, size * ry), r, r)
    p.end()
    return QIcon(pix)

