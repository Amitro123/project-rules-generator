import os
from PIL import Image, ImageDraw, ImageFont

output = """> prg analyze .

🔍 Analyzing project-rules-generator...
Found README.md
Found pyproject.toml
Stack detected: python, typer, pydantic, pytest

🧠 No AI provider configured, falling back to offline analysis.
Generating rules based on directory structure and files...

✅ Generated .clinerules/rules.md
✅ Auto-generated 3 project skills.

Your AI context is ready. Run your agent!"""

lines = output.split("\n")

print("Rendering image...")
try:
    font = ImageFont.truetype("C:\\Windows\\Fonts\\consola.ttf", 16)
except IOError:
    font = ImageFont.load_default()

dummy_img = Image.new('RGB', (1, 1))
draw = ImageDraw.Draw(dummy_img)

max_width_actual = 0
total_height = 0
for line in lines:
    bbox = draw.textbbox((0, 0), line, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if w > max_width_actual: max_width_actual = w
    total_height += h + 4

padding = 20
img_width = max(max_width_actual + padding * 2, 600)
img_height = total_height + padding * 2

img = Image.new('RGB', (img_width, img_height), color=(30, 30, 30))
draw = ImageDraw.Draw(img)

y_text = padding
for i, line in enumerate(lines):
    fill_col = (200, 200, 200)
    if i == 0: fill_col = (100, 255, 100) # Green for command
    elif "Fail" in line or "Error" in line: fill_col = (255, 100, 100)
    elif "✅" in line or "Done" in line or "success" in line.lower(): fill_col = (100, 200, 255)
    
    draw.text((padding, y_text), line, font=font, fill=fill_col)
    bbox = draw.textbbox((0, 0), line, font=font)
    y_text += (bbox[3] - bbox[1]) + 4

os.makedirs("docs/assets", exist_ok=True)
img.save("docs/assets/prg-analyze-demo.png")
print("Saved docs/assets/prg-analyze-demo.png successfully.")
