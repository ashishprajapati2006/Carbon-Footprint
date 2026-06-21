import logging
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger("ecopilot.pdf_svc")

class PDFService:
    @staticmethod
    def generate_report_pdf(report_data: dict) -> bytes:
        """
        Builds a professionally styled PDF document from a report data dictionary.
        Returns the PDF file contents as bytes.
        """
        logger.info(f"Generating PDF for report {report_data.get('_id', 'new')}")
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=54,
            bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        
        primary_color = colors.HexColor("#10b981")     # Emerald Green accent
        text_dark = colors.HexColor("#1e293b")         # Dark Slate body text
        bg_light = colors.HexColor("#f8fafc")          # slate-50 background for tables
        border_color = colors.HexColor("#e2e8f0")      # light border
        
        title_style = ParagraphStyle(
            name="ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=primary_color,
            spaceAfter=8
        )
        
        h1_style = ParagraphStyle(
            name="SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=text_dark,
            spaceBefore=14,
            spaceAfter=8,
            borderPadding=(0, 0, 2, 0),
            borderColor=primary_color,
            borderWidth=0.5
        )
        
        body_style = ParagraphStyle(
            name="BodyTextCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=text_dark,
            leading=13.5,
            spaceAfter=6
        )
        
        ai_summary_style = ParagraphStyle(
            name="AiSummaryText",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            textColor=colors.HexColor("#334155"),
            leading=14.5
        )
        
        story = []
        
        # --- HEADER SECTION ---
        report_type_str = report_data.get("report_type", "monthly").capitalize()
        story.append(Paragraph(f"EcoPilot AI - {report_type_str} Sustainability Report", title_style))
        
        # Metadata Block
        start_date = report_data.get("start_date")
        end_date = report_data.get("end_date")
        created_at = report_data.get("created_at")
        
        start_str = start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else str(start_date)[:10]
        end_str = end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else str(end_date)[:10]
        created_str = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else str(created_at)[:16]
        
        meta_data = [
            [
                Paragraph("<b>Report Period:</b>", body_style), Paragraph(f"{start_str} to {end_str}", body_style),
                Paragraph("<b>Generated On:</b>", body_style), Paragraph(created_str, body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[90, 170, 90, 190])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_light),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.25, border_color)
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))
        
        # --- AI EXECUTIVE SUMMARY ---
        story.append(Paragraph("🌱 AI Executive Summary", h1_style))
        ai_summary = report_data.get("ai_summary", "No AI analysis available for this period.")
        summary_p = Paragraph(ai_summary.replace("\n", "<br/>"), ai_summary_style)
        summary_table = Table([[summary_p]], colWidths=[540])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ecfdf5")), # Soft emerald tint
            ('PADDING', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINELEFT', (0,0), (0,-1), 3.0, primary_color), # Emerald accent line
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#d1fae5"))
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))
        
        # --- CARBON PERFORMANCE TRENDS ---
        story.append(Paragraph("📊 Carbon Emissions Trend", h1_style))
        trend = report_data.get("carbon_trend", {})
        total_co2 = trend.get("total_co2_kg", 0.0)
        prev_co2 = trend.get("previous_co2_kg", 0.0)
        pct_change = trend.get("percentage_change", 0.0)
        direction = trend.get("direction", "stable")
        
        dir_text = "increased 🔺" if direction == "up" else "decreased 🔻" if direction == "down" else "remained stable ➡️"
        trend_description = (
            f"Your total footprint for this period was <b>{total_co2:.2f} kg CO2e</b>. "
            f"Compared to the prior period (<b>{prev_co2:.2f} kg CO2e</b>), your emissions have {dir_text} "
            f"by <b>{pct_change:.1f}%</b>."
        )
        story.append(Paragraph(trend_description, body_style))
        story.append(Spacer(1, 10))
        
        # --- FUTURE EMISSIONS FORECAST ---
        story.append(Paragraph("🔮 3-Month Emissions Forecast", h1_style))
        predictions = report_data.get("predictions", [])
        
        pred_data = [["Month", "Forecasted Carbon (kg CO2e)"]]
        for pred in predictions:
            pred_data.append([pred.get("date", ""), f"{pred.get('co2_kg', 0.0):.2f} kg"])
            
        pred_table = Table(pred_data, colWidths=[270, 270])
        pred_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,1), (-1,-1), bg_light),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.25, border_color)
        ]))
        story.append(pred_table)
        story.append(Spacer(1, 10))
        
        # --- ACHIEVEMENTS & ECO ENGAGEMENT ---
        story.append(Paragraph("🏆 Achievements & Engagement", h1_style))
        ach = report_data.get("achievements", {})
        xp = ach.get("xp_earned", 0)
        badges = ach.get("badges_unlocked", [])
        badges_str = ", ".join(badges) if badges else "None"
        
        ach_data = [
            [Paragraph("<b>XP Points Earned:</b>", body_style), Paragraph(f"+{xp} XP", body_style)],
            [Paragraph("<b>Badges Unlocked:</b>", body_style), Paragraph(badges_str, body_style)]
        ]
        ach_table = Table(ach_data, colWidths=[140, 400])
        ach_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.25, border_color)
        ]))
        story.append(ach_table)
        story.append(Spacer(1, 10))
        
        # --- RECOMMENDED ECO-STEPS ---
        story.append(Paragraph("💡 Personalized Recommendations", h1_style))
        suggestions = report_data.get("suggestions", [])
        
        sug_data = [["Category", "Eco Action Recommendation", "Difficulty", "CO2 Reduction"]]
        for sug in suggestions:
            sug_data.append([
                sug.get("category", "").capitalize(),
                sug.get("recommendation", ""),
                sug.get("difficulty", "Easy"),
                sug.get("co2_reduction", "")
            ])
            
        sug_table = Table(sug_data, colWidths=[80, 280, 90, 90])
        sug_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#334155")), # Slate background
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.25, border_color)
        ]))
        story.append(sug_table)
        
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawString(36, 20, "EcoPilot AI Sustainability Performance Report")
            canvas.drawRightString(576, 20, f"Page {doc.page}")
            canvas.restoreState()
            
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
