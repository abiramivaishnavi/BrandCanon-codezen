"""Generates the demo content for the fictional AuroraBrew brand into ./demo
Run from the project root:  python scripts/make_demo_files.py"""
import os
import pymupdf
import docx
from docx.shared import Inches
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo")
os.makedirs(OUT, exist_ok=True)


def font(size, bold=True):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def poster(name, bg, accent, lines):
    img = Image.new("RGB", (900, 1100), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 900, 150], fill=accent)
    y = 45
    for text, size, color in lines:
        d.text((60, y), text, font=font(size), fill=color)
        y += size + 40
    img.save(os.path.join(OUT, name))


# 1. Instagram caption with several seeded problems
open(os.path.join(OUT, "01_instagram_caption.txt"), "w", encoding="utf-8").write(
    "Aurora Brew's Morning Ember is India's best coffee! Hurry, only Rs 499 for a 250g pack. "
    "Our Winter offer gives you 25% off at every outlet until 31 Jan. "
    "Customers who drink it daily will find that it boosts immunity and burns fat. DON'T MISS OUT!!!\n")

# 2. Off-brand poster: wrong colours (blue/purple), wrong discount, wrong price
POSTER_TEXT = "AURORA BREW\nWINTER WARMERS\n25% OFF\nMorning Ember now Rs 499\nOffer ends 31 Jan"
poster("02_winter_poster_offbrand.png", "#2B3A8C", "#7B2CBF",
       [("AURORA BREW", 54, "#FFFFFF"), ("WINTER", 120, "#FFFFFF"), ("WARMERS", 120, "#FFFFFF"),
        ("25% OFF", 150, "#FFD60A"), ("Morning Ember now Rs 499", 44, "#FFFFFF"), ("Offer ends 31 Jan", 44, "#FFFFFF")])
open(os.path.join(OUT, "02_winter_poster_offbrand_TEXT.txt"), "w", encoding="utf-8").write(POSTER_TEXT + "\n")

# 2b. Corrected poster: approved colours and facts
poster("02b_winter_poster_fixed.png", "#F5EBDD", "#4A2C2A",
       [("AURORABREW", 54, "#F5EBDD"), ("WINTER", 120, "#4A2C2A"), ("WARMERS", 120, "#4A2C2A"),
        ("20% OFF", 150, "#E2703A"), ("Morning Ember now Rs 549", 44, "#4A2C2A"), ("Offer ends 31 Jan", 44, "#4A2C2A")])
open(os.path.join(OUT, "02b_winter_poster_fixed_TEXT.txt"), "w", encoding="utf-8").write(
    "AuroraBrew\nWINTER WARMERS\n20% OFF\nMorning Ember now Rs 549\nOffer ends 31 Jan\n")

# 3. Brochure PDF: offer facts are right, company facts are wrong
doc = pymupdf.open()
page = doc.new_page()
body = ("AuroraBrew Winter Warmers\n\n"
        "Warm up your winter with 20% off Morning Ember, now Rs 549 for a 250g pack. Offer ends 31 Jan.\n\n"
        "Since 2015, AuroraBrew has grown to 40 cafés across South India. "
        "Every batch is small-batch roasted in Bengaluru using Fair-Trade certified beans.\n\n"
        "Try Velvet Night, our decaf blend, at Rs 599. It is the finest decaf you will ever taste.")
page.insert_textbox(pymupdf.Rect(60, 60, 540, 780), body, fontsize=13, fontname="helv")
doc.save(os.path.join(OUT, "03_winter_brochure.pdf"))

# 4. HR job post (DOCX) with an image that has no alt text
d = docx.Document()
d.add_heading("We are hiring baristas!", level=1)
d.add_paragraph("Aurorabrew is the No.1 place to work in Bengaluru. Join our coffee shop team at any of our 38 cafés.")
d.add_paragraph("Candidates must be young, energetic and willing to work long hours without complaining. "
                "Apply now, limited stock of positions!")
Image.new("RGB", (400, 200), "#E2703A").save(os.path.join(OUT, "_tmp.png"))
d.add_picture(os.path.join(OUT, "_tmp.png"), width=Inches(3))
os.remove(os.path.join(OUT, "_tmp.png"))
d.save(os.path.join(OUT, "04_hiring_post.docx"))

# 5. A clean caption: should produce no findings
open(os.path.join(OUT, "05_clean_caption.txt"), "w", encoding="utf-8").write(
    "Cold mornings call for something warm. This winter, enjoy 20% off Morning Ember at your nearest AuroraBrew café. "
    "A 250g pack is Rs 549, small-batch roasted in Bengaluru. Offer ends 31 Jan.\n")

# 6. Extra guideline document for the admin upload demo
g = docx.Document()
g.add_heading("Social media", level=1)
for line in ["Use no more than three hashtags in one post and always include #AuroraBrew.",
             "Do not use more than two emojis in a caption because they reduce readability for screen readers.",
             "Reply to customer complaints politely and never argue with a customer in public comments."]:
    g.add_paragraph(line, style="List Bullet")
g.save(os.path.join(OUT, "06_social_media_guidelines_addendum.docx"))

print("Demo files written to", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)
