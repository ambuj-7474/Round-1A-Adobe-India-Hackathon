#!/usr/bin/env python3
"""
Create multilingual PDF samples for testing

This script creates sample PDF files with multilingual text (English, Japanese, Hindi)
to test the PDF Outline Extractor's multilingual capabilities.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register fonts for multilingual support
def register_fonts():
    # Use built-in fonts that support various scripts
    # No need to register custom fonts, we'll use the built-in ones
    pass

# Create a sample PDF with the given language content
def create_sample_pdf(output_path, title, headings, content, lang):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles for multilingual text
    # Use existing styles and modify them instead of adding new ones
    title_style = styles['Title']
    title_style.fontName = 'Helvetica-Bold'
    title_style.fontSize = 18
    title_style.alignment = TA_CENTER
    title_style.spaceAfter = 12
    
    heading1_style = styles['Heading1']
    heading1_style.fontName = 'Helvetica-Bold'
    heading1_style.fontSize = 16
    heading1_style.alignment = TA_LEFT
    heading1_style.spaceAfter = 10
    
    heading2_style = styles['Heading2']
    heading2_style.fontName = 'Helvetica-Bold'
    heading2_style.fontSize = 14
    heading2_style.alignment = TA_LEFT
    heading2_style.spaceAfter = 8
    
    normal_style = styles['Normal']
    normal_style.fontName = 'Helvetica'
    normal_style.fontSize = 10
    normal_style.alignment = TA_LEFT
    normal_style.spaceAfter = 10
    
    # Build the document
    story = []
    
    # Add title
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))
    
    # Add headings and content
    for i, (heading, subheadings, text) in enumerate(zip(headings, content['subheadings'], content['paragraphs'])):
        story.append(Paragraph(heading, styles['Heading1']))
        story.append(Spacer(1, 8))
        
        story.append(Paragraph(text[0], styles['Normal']))
        story.append(Spacer(1, 10))
        
        for j, subheading in enumerate(subheadings):
            story.append(Paragraph(subheading, styles['Heading2']))
            story.append(Spacer(1, 6))
            
            if j < len(text) - 1:
                story.append(Paragraph(text[j+1], styles['Normal']))
                story.append(Spacer(1, 10))
    
    # Build the PDF
    doc.build(story)
    print(f"Created {lang} sample PDF: {output_path}")

def main():
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
    os.makedirs(output_dir, exist_ok=True)
    
    # English sample
    create_sample_pdf(
        os.path.join(output_dir, "sample_english.pdf"),
        "Sample English Document",
        ["Chapter 1: Introduction", "Chapter 2: Content", "Chapter 3: Conclusion"],
        {
            "subheadings": [
                [],
                ["2.1 Heading Detection", "2.2 Hierarchical Structure"],
                []
            ],
            "paragraphs": [
                ["This is a sample English document to test the PDF Outline Extractor."],
                ["This chapter contains information about the content of the document.", 
                 "This section discusses how headings are detected in the document.",
                 "This section explains the hierarchical structure of the document."],
                ["This chapter concludes the document."]
            ]
        },
        "English"
    )
    
    # Japanese sample
    create_sample_pdf(
        os.path.join(output_dir, "sample_japanese_new.pdf"),
        "日本語サンプル文書",
        ["第1章 はじめに", "第2章 テスト内容", "第3章 まとめ"],
        {
            "subheadings": [
                [],
                ["2.1 見出しの検出", "2.2 階層構造"],
                []
            ],
            "paragraphs": [
                ["これは日本語のサンプル文書です。PDF アウトライン抽出ツールをテストするために使用します。"],
                ["この章では、文書の内容に関する情報を提供します。", 
                 "このセクションでは、文書内の見出しがどのように検出されるかについて説明します。",
                 "このセクションでは、文書の階層構造について説明します。"],
                ["この章では文書をまとめます。"]
            ]
        },
        "Japanese"
    )
    
    # Hindi sample
    create_sample_pdf(
        os.path.join(output_dir, "sample_hindi_new.pdf"),
        "हिंदी नमूना दस्तावेज़",
        ["अध्याय 1: परिचय", "अध्याय 2: परीक्षण सामग्री", "अध्याय 3: निष्कर्ष"],
        {
            "subheadings": [
                [],
                ["2.1 शीर्षक का पता लगाना", "2.2 पदानुक्रम संरचना"],
                []
            ],
            "paragraphs": [
                ["यह PDF आउटलाइन एक्सट्रैक्टर का परीक्षण करने के लिए एक हिंदी नमूना दस्तावेज़ है।"],
                ["इस अध्याय में दस्तावेज़ की सामग्री के बारे में जानकारी है।", 
                 "इस खंड में बताया गया है कि दस्तावेज़ में शीर्षक कैसे पता लगाए जाते हैं।",
                 "इस खंड में दस्तावेज़ की पदानुक्रम संरचना के बारे में बताया गया है।"],
                ["इस अध्याय में दस्तावेज़ का निष्कर्ष है।"]
            ]
        },
        "Hindi"
    )

if __name__ == "__main__":
    register_fonts()
    main()