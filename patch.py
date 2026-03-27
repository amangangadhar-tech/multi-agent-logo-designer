import sys

with open('d:/multi agent logo designer/multi-agent-logo-designer/logo-designer/agents/pdf_renderer.py', 'r', encoding='utf-8') as f:
    code = f.read()

# STEP 1
code = code.replace(
    '''    c.setFillColor(hex_to_color(palette['neutral_light']['hex']))
    c.rect(MARGIN, y_zone, LIVE_W, zone_h, fill=1, stroke=0)
    
    logo_path = "workspace/assets/logo_primary.png"''',
    '''    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.rect(MARGIN, y_zone, LIVE_W, zone_h, fill=1, stroke=0)
    
    logo_path = "workspace/assets/logo_white.png"'''
)

code = code.replace(
    '''    light_hex = palette['neutral_light']['hex']
    c.setFillColor(hex_to_color(light_hex))
    c.rect(PAGE_W/2, PAGE_H/2, PAGE_W/2, PAGE_H/2, fill=1, stroke=0)
    
    path_dark = "workspace/assets/logo_dark.png"''',
    '''    light_hex = palette['neutral_dark']['hex']
    c.setFillColor(hex_to_color(light_hex))
    c.rect(PAGE_W/2, PAGE_H/2, PAGE_W/2, PAGE_H/2, fill=1, stroke=0)
    
    path_dark = "workspace/assets/logo_white.png"'''
)

code = code.replace(
    '''    path_icon = "workspace/assets/icon_only.png"''',
    '''    c.setFillColor(hex_to_color(palette['neutral_dark']['hex']))
    c.rect(0, 0, PAGE_W, PAGE_H/2, fill=1, stroke=0)
    path_icon = "workspace/assets/logo_white.png"'''
)


# STEP 2
code = code.replace(
    '''        c.drawString(x + 15*mm, y + h_card_do - 10*mm, "Maintain clear space")''',
    '''        dos = [
            "Always use the approved logo",
            "Maintain minimum clear space",
            "Use Trusted Blue (#4567b7)",
            "Use the brand voice guide"
        ]
        dos2 = [
            "file \u2014 never recreate it",
            "1x icon height on all sides",
            "as primary colour on white",
            "friendly, reassuring, pro"
        ]
        c.drawString(x + 15*mm, y + h_card_do - 10*mm, dos[i])
        c.drawString(x + 15*mm, y + h_card_do - 15*mm, dos2[i])'''
)

code = code.replace(
    '''        c.drawString(x + 15*mm, y + h_card_do - 10*mm, "Do not distort logo")''',
    '''        donts = [
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
        c.drawString(x + 15*mm, y + h_card_do - 15*mm, donts2[i])'''
)

# STEP 3
code = code.replace(
    '''        c.setFont(typography['body_font']['family'], 8)
        c.drawString(x, y - 14*mm, f"RGB: {col.get('rgb', '')}")
        c.drawString(x, y - 18*mm, f"Use: {col.get('use', '')}")''',
    '''        c.setFont(typography['body_font']['family'], 8)
        c.drawString(x, y - 14*mm, f"RGB: {col.get('rgb', '')}")
        use_text = f"Use: {col.get('use', '')}"
        from reportlab.lib.utils import simpleSplit
        lines = simpleSplit(use_text, typography['body_font']['family'], 8, w_swatch + 5*mm)
        for j, line in enumerate(lines[:2]):
            c.drawString(x, y - 18*mm - (j*3*mm), line)'''
)

code = code.replace(
    '''    for trait in traits:
        c.setFillColor(hex_to_color(palette['accent']['hex']))
        c.rect(x_offset, y_pills, 35 * mm, 8 * mm, fill=1, stroke=0)''',
    '''    for trait in traits:
        c.setFillColor(hex_to_color(palette['primary']['hex']))
        c.rect(x_offset, y_pills, 35 * mm, 8 * mm, fill=1, stroke=0)'''
)

# STEP 4
code = code.replace(
    '''    y_h = PAGE_H - MARGIN - 50*mm
    c.setFont(typography['heading_font']['family'], 36)
    c.drawString(MARGIN, y_h, typography['heading_font']['family'])
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_h - 8*mm, "600 SemiBold  700 Bold  800 ExtraBold")
    
    y_b = y_h - 30*mm
    c.setFont(typography['body_font']['family'], 36)
    c.drawString(MARGIN, y_b, typography['body_font']['family'])
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_b - 8*mm, "400 Regular  500 Medium  700 Bold")''',
    '''    y_h = PAGE_H - MARGIN - 50*mm
    c.setFont("Helvetica-Bold", 36)
    c.drawString(MARGIN, y_h, "Helvetica Neue")
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_h - 8*mm, "Bold and SemiBold weights")
    
    y_b = y_h - 30*mm
    c.setFont(typography['body_font']['family'], 36)
    c.drawString(MARGIN, y_b, "Inter")
    c.setFont(typography['body_font']['family'], 10)
    c.drawString(MARGIN, y_b - 8*mm, "Regular and Medium weights")'''
)


# STEP 5
code = code.replace(
    '''def render_cover(c, page, brand_brief, palette, typography):
    cover_art_path = "workspace/assets/cover_art.png"
    if os.path.exists(cover_art_path):
        c.drawImage(cover_art_path, 0, 0, PAGE_W, PAGE_H, preserveAspectRatio=True, anchor='c')
    
    c.saveState()
    primary = hex_to_color(palette['primary']['hex'])
    primary.alpha = 0.4
    c.setFillColor(primary)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.restoreState()''',
    '''def render_cover(c, page, brand_brief, palette, typography):
    c.saveState()
    p = c.beginPath()
    p.rect(0, 0, PAGE_W, PAGE_H)
    c.clipPath(p, stroke=0)
    c.linearGradient(0, PAGE_H, 0, 0, [hex_to_color('#2e3d6b'), hex_to_color('#4567b7')])
    c.restoreState()'''
)

code = code.replace(
    '''    mood_path = "workspace/assets/mood_board.png"
    y_mood = PAGE_H - MARGIN - 60 * mm
    if os.path.exists(mood_path):
        c.drawImage(mood_path, MARGIN, y_mood, width=LIVE_W, height=55*mm, preserveAspectRatio=True, anchor='sw')''',
    '''    y_mood = PAGE_H - MARGIN - 60 * mm
    c.saveState()
    p = c.beginPath()
    p.rect(MARGIN, y_mood, LIVE_W, 55*mm)
    c.clipPath(p, stroke=0)
    c.linearGradient(MARGIN, y_mood + 55*mm, MARGIN, y_mood, [hex_to_color('#2e3d6b'), hex_to_color('#4567b7')])
    c.restoreState()'''
)

with open('d:/multi agent logo designer/multi-agent-logo-designer/logo-designer/agents/pdf_renderer.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied successfully.")
