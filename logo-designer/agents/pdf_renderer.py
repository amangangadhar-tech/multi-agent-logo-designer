import os
import io
import json
import base64
import pathlib
import datetime
import requests

from PIL import Image, ImageDraw, ImageFont
import cairosvg

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.platypus import Image as RLImage

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
LIVE_W = PAGE_W - 2 * MARGIN

def hex_to_color(hex_str: str) -> colors.Color:
    h = hex_str.lstrip('#')
    return colors.Color(*[int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)])

def load_all_data() -> dict:
    with open("workspace/brand_brief.json", "r", encoding="utf-8") as f:
        brand_brief = json.load(f)
    with open("workspace/colour_palette.json", "r", encoding="utf-8") as f:
        colour_palette = json.load(f)
    with open("workspace/typography.json", "r", encoding="utf-8") as f:
        typography = json.load(f)
    with open("workspace/guideline_pages.json", "r", encoding="utf-8") as f:
        guideline_pages = json.load(f)
        
    return {
        "brand_brief": brand_brief,
        "colour_palette": colour_palette,
        "typography": typography,
        "guideline_pages": guideline_pages
    }

def svg_to_png(svg_path: str, output_png: str, width_px: int = 600):
    try:
        cairosvg.svg2png(url=svg_path, write_to=output_png, output_width=width_px)
    except Exception as e:
        print(f"Warning: Failed to convert {svg_path} to PNG: {e}")
        try:
            img = Image.new('RGB', (600, 200), color=(180, 180, 180))
            d = ImageDraw.Draw(img)
            d.text((280, 90), "Logo", fill=(0, 0, 0))
            img.save(output_png)
        except Exception:
            pass

def _create_placeholder_logo(output_path: str, company_name: str):
    """
    Fallback: creates a minimal coloured rectangle with company initials.
    Called only if a logo PNG is missing entirely (e.g. Flux + gradient both failed).
    """
    is_icon = "icon" in os.path.basename(output_path)
    width, height = (512, 512) if is_icon else (1200, 600)
    bg_colour = (30, 58, 138)        # safe brand-neutral deep blue
    img  = Image.new("RGB", (width, height), bg_colour)
    draw = ImageDraw.Draw(img)
    initials = (company_name[:2] if len(company_name) >= 2 else company_name).upper()
    # Draw initials centred — no custom font needed, PIL default is fine for a fallback
    draw.text(
        (width // 2, height // 2),
        initials,
        fill=(255, 255, 255),
        anchor="mm"
    )
    img.save(output_path, "PNG")
    print(f"WARNING: placeholder logo created for {output_path}")

def _logo_display_dims(logo_path: str, desired_width_mm: float):
    """Returns (width_mm, height_mm) preserving the image's aspect ratio."""
    from PIL import Image as PILImage
    img = PILImage.open(logo_path)
    logo_w, logo_h = img.size
    aspect = logo_w / logo_h
    return desired_width_mm, desired_width_mm / aspect

def register_google_fonts(typography: dict):
    os.makedirs("workspace/assets/fonts", exist_ok=True)
    for font_type in ['heading_font', 'body_font', 'accent_font']:
        if font_type not in typography or typography[font_type] is None:
            continue
            
        family = typography[font_type]['family']
        slug = family.lower().replace(' ', '')
        filename = family.replace(' ', '') + "-Regular"
        path = f"workspace/assets/fonts/{filename}.ttf"
        
        if not os.path.exists(path):
            success = False
            for v in range(35, 5, -1):
                url = f"https://fonts.gstatic.com/s/{slug}/v{v}/{filename}.ttf"
                try:
                    r = requests.get(url, timeout=3)
                    if r.status_code == 200:
                        with open(path, "wb") as f:
                            f.write(r.content)
                        success = True
                        break
                except Exception:
                    continue
            
            if not success:
                print(f"Warning: Failed to download {family}, using Helvetica as fallback.")
                typography[font_type]['family'] = "Helvetica"
                continue
                
        try:
            pdfmetrics.registerFont(TTFont(family, path))
        except Exception as e:
            print(f"Warning: Failed to register {family}: {e}")
            typography[font_type]['family'] = "Helvetica"

def render_cover(c, page, brand_brief, palette, typography):
    c.saveState()
    p = c.beginPath()
    p.rect(0, 0, PAGE_W, PAGE_H)
    c.clipPath(p, stroke=0)
    c.linearGradient(0, PAGE_H, 0, 0, [hex_to_color('#2e3d6b'), hex_to_color('#4567b7')])
    c.restoreState()
    
    logo_path = "workspace/assets/logo_white.png"
    if os.path.exists(logo_path):
        try:
            with Image.open(logo_path) as img:
                logo_h = 70.5 * mm * img.height / img.width
        except:
            logo_h = 30 * mm
        c.drawImage(logo_path, (PAGE_W - 70.5*mm) / 2, PAGE_H / 2, width=70.5*mm, height=logo_h, preserveAspectRatio=True, anchor='c')
    
    c.setFillColor(colors.white)
    c.setFont(typography['heading_font']['family'], 40)
    c.drawCentredString(PAGE_W / 2, 115 * mm, brand_brief.get('company_name', ''))
    
    white_70 = colors.Color(1, 1, 1, alpha=0.7)
    c.setFillColor(white_70)
    try:
        accent_family = typography['accent_font']['family']
    except:
        accent_family = typography['heading_font']['family']
    c.setFont(accent_family, 18)
    c.drawCentredString(PAGE_W / 2, 100 * mm, brand_brief.get('tagline', ''))
    
    c.setFillColor(colors.white)
    c.setFont(typography['body_font']['family'], 8)
    c.drawString(MARGIN, MARGIN, "Brand Guidelines v1.0")

def render_about(c, page, brand_brief, palette, typography):
    c.setFillColor(hex_to_color(palette['accent']['hex']))
    c.setFont(typography['heading_font']['family'], 9)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN, brand_brief.get('company_name', ''))
    
    y_mood = PAGE_H - MARGIN - 60 * mm
    c.saveState()
    p = c.beginPath()
    p.rect(MARGIN, y_mood, LIVE_W, 55*mm)
    c.clipPath(p, stroke=0)
    c.linearGradient(MARGIN, y_mood + 55*mm, MARGIN, y_mood, [hex_to_color('#2e3d6b'), hex_to_color('#4567b7')])
    c.restoreState()
        
    y_title = PAGE_H - MARGIN - 80 * mm
    c.setFillColor(hex_to_color(palette['primary']['hex']))
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, y_title, "About the Brand")
    
    styles = getSampleStyleSheet()
    desc_style = ParagraphStyle(
        'Desc',
        parent=styles['Normal'],
        fontName=typography['body_font']['family'],
        fontSize=11,
        textColor=hex_to_color(palette['neutral_dark']['hex']),
        leading=16
    )
    p = Paragraph(brand_brief.get('company_description', ''), desc_style)
    w, h = p.wrap(LIVE_W, 100 * mm)
    y_desc = y_title - 10 * mm - h
    p.drawOn(c, MARGIN, y_desc)
    
    y_badge = y_desc - 20 * mm
    c.setFillColor(hex_to_color(palette['primary']['hex']))
    c.rect(MARGIN, y_badge, 120 * mm, 12 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(typography['heading_font']['family'], 11)
    arch = brand_brief.get('brand_archetype', '')
    c.drawString(MARGIN + 5*mm, y_badge + 8*mm, f"Brand Archetype: {arch}")
    
    y_pills = y_badge - 15 * mm
    traits = brand_brief.get('personality_traits', [])[:3]
    x_offset = MARGIN
    for trait in traits:
        c.setFillColor(hex_to_color(palette['primary']['hex']))
        c.rect(x_offset, y_pills, 35 * mm, 8 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(typography['body_font']['family'], 9)
        c.drawCentredString(x_offset + 17.5*mm, y_pills + 3*mm, str(trait))
        x_offset += 40 * mm
        
    y_tone = y_pills - 20 * mm
    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.setFont(typography['body_font']['family'], 11)
    c.drawString(MARGIN, y_tone, f"Tone of Voice: {brand_brief.get('tone_of_voice', '')}")

def render_logo_primary(c, page, brand_brief, palette, typography):
    c.setFillColor(hex_to_color(palette['primary']['hex']))
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 20*mm, "The Logo")
    
    zone_h = 100 * mm
    y_zone = PAGE_H / 2 - zone_h / 2
    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.rect(MARGIN, y_zone, LIVE_W, zone_h, fill=1, stroke=0)
    
    logo_path = "workspace/assets/logo_white.png"
    logo_w = 120 * mm
    if os.path.exists(logo_path):
        try:
            with Image.open(logo_path) as img:
                logo_h = logo_w * img.height / img.width
        except:
            logo_h = 40 * mm
        if logo_h > 80 * mm:
            logo_h = 80 * mm
            logo_w = logo_h * (img.width / img.height)
            
        x_logo = MARGIN + (LIVE_W - logo_w) / 2
        y_logo = y_zone + (zone_h - logo_h) / 2
        c.drawImage(logo_path, x_logo, y_logo, width=logo_w, height=logo_h, preserveAspectRatio=True, anchor='c')
        
        c.setStrokeColor(hex_to_color(palette['primary']['hex']))
        c.setLineWidth(1)
        c.setDash(4, 4)
        safe = 8.5 * mm
        c.rect(x_logo - safe, y_logo - safe, logo_w + 2*safe, logo_h + 2*safe, fill=0, stroke=1)
        c.setDash()
        
    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.setFont(typography['body_font']['family'], 9)
    c.drawString(MARGIN, y_zone - 10*mm, "Clear space: minimum 1x icon height on all sides")
    c.drawString(MARGIN, y_zone - 15*mm, "Minimum print: 30mm | Digital: 120px")
    
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_zone - 25*mm, brand_brief.get('tagline', ''))

def render_logo_variants(c, page, brand_brief, palette):
    dark_hex = palette['neutral_dark']['hex']
    c.setFillColor(hex_to_color(dark_hex))
    c.rect(0, PAGE_H/2, PAGE_W/2, PAGE_H/2, fill=1, stroke=0)
    
    logo_w = PAGE_W/2 * 0.6
    path_white = "workspace/assets/logo_white.png"
    if os.path.exists(path_white):
        c.drawImage(path_white, PAGE_W/4 - logo_w/2, PAGE_H*0.75 - 15*mm, width=logo_w, height=30*mm, preserveAspectRatio=True, anchor='c')
        
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W/4, PAGE_H/2 + 20*mm, "On Dark Backgrounds")
    
    light_bg = (248, 248, 250)
    c.setFillColor(colors.Color(light_bg[0]/255, light_bg[1]/255, light_bg[2]/255))
    c.rect(PAGE_W/2, PAGE_H/2, PAGE_W/2, PAGE_H/2, fill=1, stroke=0)
    
    path_dark = "workspace/assets/logo_dark.png"
    if os.path.exists(path_dark):
        disp_w, disp_h = _logo_display_dims(path_dark, logo_w / mm)
        c.drawImage(path_dark, PAGE_W*0.75 - logo_w/2, PAGE_H*0.75 - (disp_h*mm)/2, width=disp_w*mm, height=disp_h*mm, preserveAspectRatio=True, mask='auto')
        
    c.setFillColor(hex_to_color(dark_hex))
    c.drawCentredString(PAGE_W*0.75, PAGE_H/2 + 20*mm, "On Light Backgrounds")
    
    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.rect(0, 0, PAGE_W, PAGE_H/2, fill=1, stroke=0)
    path_icon = "workspace/assets/icon_only.png"
    if os.path.exists(path_icon):
        icon_w = 40 * mm
        c.drawImage(path_icon, PAGE_W/2 - icon_w/2, PAGE_H/4, width=icon_w, height=icon_w, preserveAspectRatio=True, mask='auto')
    
    c.drawCentredString(PAGE_W/2, PAGE_H/4 - 30*mm, "Favicon | App Icon | Stamp")

def render_colour_palette(c, page, palette, typography):
    c.setFillColor(hex_to_color(palette['primary']['hex']))
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 20*mm, "Colour Palette")
    
    keys = ['primary', 'secondary', 'accent', 'neutral_dark', 'neutral_light', 'white', 'black']
    x_start = MARGIN
    y_start = PAGE_H - MARGIN - 60*mm
    w_swatch = 55 * mm
    h_swatch = 28 * mm
    x_gap = 10 * mm
    y_gap = 25 * mm
    
    for i, k in enumerate(keys):
        col = palette.get(k)
        if not col: continue
        row = i // 4
        col_idx = i % 4
        x = x_start + col_idx * (w_swatch + x_gap)
        y = y_start - row * (h_swatch + y_gap + 20*mm)
        
        c.setFillColor(hex_to_color(col['hex']))
        c.rect(x, y, w_swatch, h_swatch, fill=1, stroke=1)
        
        c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
        c.setFont(typography['heading_font']['family'], 9)
        c.drawString(x, y - 5*mm, col.get('name', k.title()))
        
        c.setFont(typography['body_font']['family'], 9)
        c.drawString(x, y - 10*mm, col.get('hex', ''))
        
        c.setFont(typography['body_font']['family'], 8)
        c.drawString(x, y - 14*mm, f"RGB: {col.get('rgb', '')}")
        use_text = f"Use: {col.get('use', '')}"
        from reportlab.lib.utils import simpleSplit
        lines = simpleSplit(use_text, typography['body_font']['family'], 8, w_swatch + 5*mm)
        for j, line in enumerate(lines[:2]):
            c.drawString(x, y - 18*mm - (j*3*mm), line)
        
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, MARGIN + 10*mm, "All values are print-ready. For digital, use hex values.")

def render_typography(c, page, typography):
    c.setFillColor(colors.black)
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 20*mm, "Typography")
    
    y_h = PAGE_H - MARGIN - 50*mm
    c.setFont("Helvetica-Bold", 36)
    c.drawString(MARGIN, y_h, "Helvetica Neue")
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_h - 8*mm, "Bold and SemiBold weights")
    
    y_b = y_h - 30*mm
    c.setFont(typography['body_font']['family'], 36)
    c.drawString(MARGIN, y_b, "Inter")
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_b - 8*mm, "Regular and Medium weights")
    
    y_t = y_b - 30*mm
    data = [
        ['Name', 'Size', 'Sample'],
        ['H1', '48px', 'Aa Bb Cc 123'],
        ['H2', '36px', 'Aa Bb Cc 123'],
        ['H3', '28px', 'Aa Bb Cc 123'],
        ['Body', '16px', 'Aa Bb Cc 123'],
        ['Caption', '12px', 'Aa Bb Cc 123']
    ]
    t = Table(data, colWidths=[30*mm, 30*mm, 80*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), typography['body_font']['family']),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    t.wrapOn(c, LIVE_W, y_t)
    t.drawOn(c, MARGIN, y_t - 60*mm)
    
    c.setFont(typography['body_font']['family'], 11)
    c.drawString(MARGIN, MARGIN + 20*mm, "These typefaces have been selected for optimal readability and brand alignment.")
    c.drawString(MARGIN, MARGIN + 15*mm, "They ensure a consistent visual voice across all digital and print mediums.")

def render_usage_rules(c, page, typography):
    c.setFillColor(colors.black)
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 20*mm, "Do's & Don'ts")
    
    y_do = PAGE_H - MARGIN - 40*mm
    c.setFillColor(hex_to_color('#22c55e'))
    c.setFont(typography['heading_font']['family'], 18)
    c.drawString(MARGIN, y_do, "Do's")
    
    c.setStrokeColor(hex_to_color('#22c55e'))
    c.setLineWidth(2)
    w_card_do = 78*mm; h_card_do = 45*mm
    for i in range(4):
        col = i % 2; row = i // 2
        x = MARGIN + col*(w_card_do + 10*mm)
        y = y_do - 15*mm - row*(h_card_do + 10*mm) - h_card_do
        c.rect(x, y, w_card_do, h_card_do, fill=0, stroke=1)
        c.drawString(x + 5*mm, y + h_card_do - 10*mm, "\u2713")
        c.setFont(typography['body_font']['family'], 10)
        c.setFillColor(colors.black)
        dos = [
            "Always use the approved logo",
            "Maintain minimum clear space",
            "Use Trusted Blue (#4567b7)",
            "Use the brand voice guide"
        ]
        dos2 = [
            "file — never recreate it",
            "1x icon height on all sides",
            "as primary colour on white",
            "friendly, reassuring, pro"
        ]
        c.drawString(x + 15*mm, y + h_card_do - 10*mm, dos[i])
        c.drawString(x + 15*mm, y + h_card_do - 15*mm, dos2[i])
        c.setFillColor(hex_to_color('#22c55e'))
    
    y_dont = y_do - 2*h_card_do - 40*mm
    c.setFillColor(hex_to_color('#ef4444'))
    c.setFont(typography['heading_font']['family'], 18)
    c.drawString(MARGIN, y_dont, "Don'ts")
    
    c.setStrokeColor(hex_to_color('#ef4444'))
    c.setLineWidth(2)
    for i in range(4):
        col = i % 2; row = i // 2
        x = MARGIN + col*(w_card_do + 10*mm)
        y = y_dont - 15*mm - row*(h_card_do + 10*mm) - h_card_do
        c.rect(x, y, w_card_do, h_card_do, fill=0, stroke=1)
        c.drawString(x + 5*mm, y + h_card_do - 10*mm, "\u2717")
        c.setFont(typography['body_font']['family'], 10)
        c.setFillColor(colors.black)
        donts = [
            "Do not stretch, skew, or",
            "Do not place the logo on busy",
            "Do not use unapproved colours",
            "Do not use the tagline without"
        ]
        donts2 = [
            "rotate the logo",
            "photographic backgrounds",
            "or font substitutions",
            "the logo in formal contexts"
        ]
        c.drawString(x + 15*mm, y + h_card_do - 10*mm, donts[i])
        c.drawString(x + 15*mm, y + h_card_do - 15*mm, donts2[i])
        c.setFillColor(hex_to_color('#ef4444'))

def render_brand_voice(c, page, brand_brief, palette, typography):
    c.setFillColor(colors.black)
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 20*mm, "Brand Voice")
    
    c.setFillColor(hex_to_color(palette['accent']['hex']))
    c.setFont(typography['heading_font']['family'], 28)
    quote = brand_brief.get('tone_of_voice', 'Professional and Clear')
    c.drawString(MARGIN, PAGE_H - MARGIN - 50*mm, f'"{quote}"')
    
    y_tab = PAGE_H - MARGIN - 80*mm
    data = [
        ["We say", "We don't say"],
        ['Welcome to our platform', 'Click here now'],
        ['Discover our solutions', 'Buy our stuff'],
        ['We believe in quality', 'We are the best']
    ]
    t = Table(data, colWidths=[LIVE_W/2, LIVE_W/2])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), hex_to_color(palette['primary']['hex'])),
        ('TEXTCOLOR', (0,0), (1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), typography['body_font']['family']),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, hex_to_color(palette['neutral_light']['hex'])]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12)
    ]))
    t.wrapOn(c, LIVE_W, y_tab)
    t.drawOn(c, MARGIN, y_tab - 60*mm)
    
    y_copy = y_tab - 80*mm
    c.setFillColor(colors.black)
    c.setFont(typography['heading_font']['family'], 16)
    c.drawString(MARGIN, y_copy, "We write:")
    c.drawString(PAGE_W/2 + 10*mm, y_copy, "Not:")
    
    c.setFont(typography['body_font']['family'], 11)
    c.drawString(MARGIN, y_copy - 10*mm, "A thoughtful, user-centric message.")
    c.drawString(PAGE_W/2 + 10*mm, y_copy - 10*mm, "A pushy sales pitch.")

def render_design_system(c, page, typography):
    c.setFillColor(colors.black)
    c.setFont(typography['heading_font']['family'], 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 20*mm, "Design System")
    
    c.setFont(typography['body_font']['family'], 12)
    y_grid = PAGE_H - MARGIN - 40*mm
    c.drawString(MARGIN, y_grid, "8-column grid, 8px base unit, 16px gutters")
    
    y_sp = y_grid - 20*mm
    scales = [(8, '8px'), (16, '16px'), (24, '24px'), (32, '32px'), (48, '48px'), (64, '64px')]
    for v, lbl in scales:
        c.setFillColor(hex_to_color('#cbd5e1'))
        c.rect(MARGIN + 20*mm, y_sp, v*mm, 5*mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont(typography['body_font']['family'], 10)
        c.drawString(MARGIN, y_sp + 1*mm, lbl)
        y_sp -= 10*mm
        
    y_rad = y_sp - 20*mm
    c.setFont(typography['heading_font']['family'], 16)
    c.drawString(MARGIN, y_rad, "Corner Radius")
    
    y_box = y_rad - 30*mm
    c.setStrokeColor(colors.black)
    c.rect(MARGIN, y_box, 30*mm, 20*mm, fill=0, stroke=1) # 4px
    c.roundRect(MARGIN + 40*mm, y_box, 30*mm, 20*mm, 4*mm, fill=0, stroke=1) # 8px
    c.roundRect(MARGIN + 80*mm, y_box, 30*mm, 20*mm, 8*mm, fill=0, stroke=1) # 16px
    
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_box - 5*mm, "4px (sharp)")
    c.drawString(MARGIN + 40*mm, y_box - 5*mm, "8px (medium)")
    c.drawString(MARGIN + 80*mm, y_box - 5*mm, "16px (rounded)")
    
    y_shad = y_box - 25*mm
    c.setFont(typography['heading_font']['family'], 16)
    c.drawString(MARGIN, y_shad, "Shadows")
    
    y_sbox = y_shad - 30*mm
    c.setFillColor(hex_to_color('#f1f5f9'))
    c.rect(MARGIN, y_sbox, 30*mm, 15*mm, fill=1, stroke=0)
    c.rect(MARGIN + 40*mm, y_sbox, 30*mm, 15*mm, fill=1, stroke=0)
    c.rect(MARGIN + 80*mm, y_sbox, 30*mm, 15*mm, fill=1, stroke=0)
    
    c.setFillColor(colors.black)
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_sbox - 5*mm, "Soft 0 2px 8px")
    c.drawString(MARGIN + 40*mm, y_sbox - 5*mm, "Medium 0 4px 16px")
    c.drawString(MARGIN + 80*mm, y_sbox - 5*mm, "Strong 0 8px 32px")
    
    c.drawString(MARGIN, MARGIN + 10*mm, "Iconography: Use 24x24px grid, 2px stroke weight, rounded caps")

def render_closing(c, page, brand_brief, palette):
    c.setFillColor(hex_to_color(palette['accent']['hex']))
    c.rect(0, PAGE_H - 35*mm, PAGE_W, 35*mm, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 32)
    try: 
        c.setFont(typography['heading_font']['family'], 32)
    except: pass

    c.drawCentredString(PAGE_W/2, PAGE_H - 25*mm, brand_brief.get('company_name', ''))
    
    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.setFont('Helvetica', 14)
    try: 
        c.setFont(typography['body_font']['family'], 14)
    except: pass
    c.drawCentredString(PAGE_W/2, PAGE_H - 55*mm, brand_brief.get('tagline', ''))
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    c.setFont('Helvetica', 11)
    try: 
        c.setFont(typography['body_font']['family'], 11)
    except: pass
    c.drawCentredString(PAGE_W/2, PAGE_H/2, f"Brand Guidelines v1.0 - {today}")
    
    slug = brand_brief.get('company_name', 'company').lower().replace(' ', '')
    c.setFont('Helvetica', 10)
    try: 
        c.setFont(typography['body_font']['family'], 10)
    except: pass
    c.drawCentredString(PAGE_W/2, PAGE_H/2 - 10*mm, f"For brand enquiries: brand@{slug}.com")
    
    c.setFillColor(hex_to_color(palette['primary']['hex']))
    c.rect(0, 0, PAGE_W, 8*mm, fill=1, stroke=0)

def render_page_number(c, page_num, total, accent_hex):
    c.setFillColor(hex_to_color(accent_hex))
    c.setFont('Helvetica', 9)
    c.drawRightString(PAGE_W-MARGIN, MARGIN-8*mm, f'{page_num} / {total}')

def main():
    data = load_all_data()
    os.makedirs('workspace/assets', exist_ok=True)
    register_google_fonts(data['typography'])
    
    # Logos are now PNG files generated directly by Flux + Pillow.
    # svg_to_png() is no longer called for logos.
    logo_files = [
        "workspace/assets/logo_primary.png",
        "workspace/assets/logo_white.png",
        "workspace/assets/logo_dark.png",
        "workspace/assets/icon_only.png"
    ]
    for lf in logo_files:
        if not os.path.exists(lf) or os.path.getsize(lf) == 0:
            _create_placeholder_logo(lf, data['brand_brief']['company_name'])
            
    c = canvas.Canvas('workspace/brand_guidelines.pdf', pagesize=A4)
    PAGE_RENDERERS = {
        1: render_cover, 2: render_about, 3: render_logo_primary,
        4: render_logo_variants, 5: render_colour_palette, 6: render_typography,
        7: render_usage_rules, 8: render_brand_voice, 9: render_design_system,
        10: render_closing
    }
    
    pages = sorted(data.get('guideline_pages', {}).get('pages', []), key=lambda p: p.get('page_number', 0))
    if not pages:
        for i in range(1, 11):
            pages.append({'page_number': i})
            
    accent_hex = data['colour_palette']['accent']['hex']
    for page in pages:
        page_num = page['page_number']
        fn = PAGE_RENDERERS.get(page_num)
        if fn:
            if page_num == 1: fn(c, page, data['brand_brief'], data['colour_palette'], data['typography'])
            elif page_num == 2: fn(c, page, data['brand_brief'], data['colour_palette'], data['typography'])
            elif page_num == 3: fn(c, page, data['brand_brief'], data['colour_palette'], data['typography'])
            elif page_num == 4: fn(c, page, data['brand_brief'], data['colour_palette'])
            elif page_num == 5: fn(c, page, data['colour_palette'], data['typography'])
            elif page_num == 6: fn(c, page, data['typography'])
            elif page_num == 7: fn(c, page, data['typography'])
            elif page_num == 8: fn(c, page, data['brand_brief'], data['colour_palette'], data['typography'])
            elif page_num == 9: fn(c, page, data['typography'])
            elif page_num == 10: fn(c, page, data['brand_brief'], data['colour_palette'])
            
            if page_num not in (1, 10):
                render_page_number(c, page_num, 10, accent_hex)
            c.showPage()
            
    c.save()
    
    try:
        size_kb = os.path.getsize('workspace/brand_guidelines.pdf') // 1024
        print(f'✅ PDF written: workspace/brand_guidelines.pdf ({size_kb} KB)')
    except Exception as e:
        pass
        
    with open('workspace/agent_log.txt', 'a', encoding='utf-8') as f:
        f.write('pdf_renderer — STATUS: DONE\\n')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        with open('workspace/agent_log.txt', 'a', encoding='utf-8') as f:
            f.write(f'pdf_renderer — STATUS: ERROR — {e}\\n')
        exit(1)
