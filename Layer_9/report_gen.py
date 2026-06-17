"""
DatasheetAI — Layer 9: Engineering PDF Report Generator
════════════════════════════════════════════════════════
Uses ReportLab to compile publication-quality industrial camera analysis
and recommendation reports from physics constraints and scoring outputs.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Custom canvas to generate dynamic footer page numbers (Page X of Y)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B")) # Slate 500
        
        # Header (on pages after page 1)
        if self._pageNumber > 1:
            self.drawString(40, 755, "DatasheetAI — Engineering Recommendation Report")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(40, 748, 572, 748)
            
        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 35, footer_text)
        self.drawString(40, 35, "CONFIDENTIAL — FOR INTERNAL USE ONLY")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 48, 572, 48)
        
        self.restoreState()


def generate_pdf_report(requirements, results, filepath):
    """
    Generate a professional industrial PDF report.
    
    Args:
        requirements: dict containing conveyor constraints
        results: list of scored camera dicts
        filepath: str, output destination path
    """
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Define Palette (Slate Blue / Modern Industrial Tech theme)
    c_primary = colors.HexColor("#0F172A")    # Dark Slate 900
    c_secondary = colors.HexColor("#3B82F6")  # Accent Blue 500
    c_text_dark = colors.HexColor("#1E293B")  # Slate 800
    c_text_muted = colors.HexColor("#64748B") # Slate 500
    c_border = colors.HexColor("#CBD5E1")     # Slate 300
    c_light_bg = colors.HexColor("#F8FAFC")   # Slate 50
    c_alert_green = colors.HexColor("#15803D")# Green 700
    
    # Custom Typography Styles
    style_title = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    
    style_subtitle = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_text_muted,
        spaceAfter=15
    )
    
    style_h2 = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_primary,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    style_body = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text_dark,
    )
    
    style_body_bold = ParagraphStyle(
        'ReportBodyBold',
        parent=style_body,
        fontName='Helvetica-Bold'
    )
    
    style_bullet = ParagraphStyle(
        'ReportBullet',
        parent=style_body,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )

    story = []
    
    # ── HEADER BLOCK ──
    story.append(Paragraph("DatasheetAI — Technical Analysis & Recommendation Report", style_title))
    date_str = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated on {date_str}  │  Project Context: Machine Vision Inspection", style_subtitle))
    
    # ── SECTION 1: REQUIREMENTS & PHYSICS THRESHOLDS ──
    story.append(Paragraph("1. Physics Requirements & Thresholds", style_h2))
    story.append(Paragraph(
        "Based on the input operating speed and minimum defect sizes, the physical thresholds "
        "required to guarantee reliable image acquisition are computed as follows:", style_body
    ))
    story.append(Spacer(1, 8))
    
    # Calculate thresholds for display
    conveyor_speed = requirements.get("conveyor_speed_ms", 3.0)
    object_size = requirements.get("object_size_mm", 50.0)
    crack_size = requirements.get("crack_size_mm", requirements.get("defect_size_mm", 0.05))
    
    min_fps = (conveyor_speed * 1000) / object_size
    min_pixels = (object_size / crack_size) * 2
    max_exposure_ms = (crack_size / (conveyor_speed * 1000)) * 1000
    
    # Parameters Table
    param_data = [
        [Paragraph("<b>Operating Constraint</b>", style_body_bold), 
         Paragraph("<b>Input Value</b>", style_body_bold), 
         Paragraph("<b>Engineering Threshold Formula</b>", style_body_bold), 
         Paragraph("<b>Computed Target</b>", style_body_bold)],
        [Paragraph("Conveyor Speed", style_body), f"{conveyor_speed} m/s", "—", "—"],
        [Paragraph("Smallest Defect size", style_body), f"{crack_size} mm", "—", "—"],
        [Paragraph("Target Object Size", style_body), f"{object_size} mm", "—", "—"],
        [Paragraph("<b>Minimum Frame Rate</b>", style_body_bold), "—", "(Speed × 1000) / Obj Size", f"<b>{min_fps:.1f} fps</b>"],
        [Paragraph("<b>Minimum Resolution (Horizontal)</b>", style_body_bold), "—", "(Obj Size / Defect Size) × 2", f"<b>{min_pixels:.0f} px</b>"],
        [Paragraph("<b>Maximum Exposure Time</b>", style_body_bold), "—", "Defect Size / (Speed × 1000)", f"<b>{max_exposure_ms:.4f} ms</b>"]
    ]
    
    t_params = Table(param_data, colWidths=[160, 90, 160, 120])
    t_params.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_light_bg),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('LINEBELOW', (0,3), (-1,3), 1.5, c_primary),
    ]))
    story.append(t_params)
    story.append(Spacer(1, 15))
    
    # ── SECTION 2: RECOMMENDATION OVERVIEW ──
    story.append(Paragraph("2. Scored Camera Recommendations", style_h2))
    
    passing = [c for c in results if c["passed"]]
    failing = [c for c in results if not c["passed"]]
    
    story.append(Paragraph(
        f"The engine evaluated the database and identified <b>{len(passing)} passing</b> models and "
        f"<b>{len(failing)} excluded</b> models based on resolution and FPS constraints:", style_body
    ))
    story.append(Spacer(1, 8))
    
    # Recommendation List Table
    rec_headers = [
        Paragraph("<b>Rank</b>", style_body_bold),
        Paragraph("<b>Camera Model</b>", style_body_bold),
        Paragraph("<b>Manufacturer</b>", style_body_bold),
        Paragraph("<b>Frame Rate</b>", style_body_bold),
        Paragraph("<b>Resolution</b>", style_body_bold),
        Paragraph("<b>Score</b>", style_body_bold),
        Paragraph("<b>Status</b>", style_body_bold)
    ]
    
    rec_table_data = [rec_headers]
    for idx, c in enumerate(passing, 1):
        rec_table_data.append([
            str(idx),
            Paragraph(f"<b>{c['product_name']}</b>", style_body),
            c['manufacturer'],
            c['frame_rate'],
            c['resolution'],
            f"{c['score']}/100",
            Paragraph("<font color='green'><b>PASS</b></font>", style_body)
        ])
        
    for c in failing:
        rec_table_data.append([
            "—",
            c['product_name'],
            c['manufacturer'],
            c['frame_rate'],
            c['resolution'],
            "0/100",
            Paragraph("<font color='red'><b>EXCLUDED</b></font>", style_body)
        ])
        
    t_rec = Table(rec_table_data, colWidths=[40, 130, 90, 80, 100, 50, 42])
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), c_light_bg),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]
    
    # Apply row shading for readability
    for i in range(1, len(rec_table_data)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8FAFC")))
            
    t_rec.setStyle(TableStyle(t_style))
    story.append(t_rec)
    story.append(Spacer(1, 15))
    
    # ── SECTION 3: TOP RECOMMENDED DETAILED ANALYSIS ──
    if passing:
        story.append(Paragraph("3. Detailed Evaluation (Top Matches)", style_h2))
        
        # Display top 3 models details
        for i, c in enumerate(passing[:3], 1):
            cam_story = []
            cam_story.append(Paragraph(f"<b>Match #{i}: {c['product_name']}</b> (Score: {c['score']}/100)", style_body_bold))
            cam_story.append(Spacer(1, 4))
            
            # Key specs bullet points
            cam_story.append(Paragraph(f"• <b>Manufacturer:</b> {c['manufacturer']}", style_bullet))
            cam_story.append(Paragraph(f"• <b>Resolution:</b> {c['resolution']}  │  <b>Max FPS:</b> {c['frame_rate']}", style_bullet))
            cam_story.append(Paragraph(f"• <b>Connection interface:</b> {c['interface']}  │  <b>Weight:</b> {c['weight']}", style_bullet))
            
            # Suitability reasons
            reasons_text = " │ ".join(c.get("reasons", []))
            cam_story.append(Paragraph(f"• <b>Fit Rationale:</b> {reasons_text}", style_bullet))
            cam_story.append(Spacer(1, 8))
            
            story.append(KeepTogether(cam_story))
            
    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    return True


if __name__ == "__main__":
    # Test report compile
    test_req = {"conveyor_speed_ms": 3.0, "object_size_mm": 50.0, "crack_size_mm": 0.05}
    test_results = [
        {
            "product_name": "acA2040-90um",
            "manufacturer": "Basler",
            "frame_rate": "90 fps",
            "resolution": "2048 x 2048 pixels",
            "interface": "USB 3.0",
            "weight": "65 g",
            "score": 90,
            "reasons": ["✅ FPS: 90 fps (perfect fit)", "✅ Resolution: 2048px (perfect fit)", "✅ Interface: USB 3.0"],
            "penalties": [],
            "passed": True
        },
        {
            "product_name": "BFS-U3-51S5C",
            "manufacturer": "FLIR",
            "frame_rate": "75 fps",
            "resolution": "2448 x 2048 pixels",
            "interface": "USB 3.0",
            "weight": "72 g",
            "score": 85,
            "reasons": ["✅ FPS: 75 fps (good fit)", "✅ Resolution: 2448px (perfect fit)", "✅ Interface: USB 3.0"],
            "penalties": [],
            "passed": True
        },
        {
            "product_name": "XCG-CG510",
            "manufacturer": "Sony",
            "frame_rate": "23 fps",
            "resolution": "2448 x 2048 pixels",
            "interface": "GigE",
            "weight": "90 g",
            "score": 0,
            "reasons": [],
            "penalties": ["❌ FPS too low: 23 fps < 60 fps needed"],
            "passed": False
        }
    ]
    
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_report.pdf")
    generate_pdf_report(test_req, test_results, out)
    print(f"Test PDF generated at: {out}")
