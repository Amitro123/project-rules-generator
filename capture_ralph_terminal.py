import os
from PIL import Image, ImageDraw, ImageFont

output = """> prg ralph "add a --verbose flag to prg analyze"

🤖 Starting Ralph Autonomous Loop
[System] Checked out branch: feature/add-verbose-flag-prg-analyze
[System] Loaded context: .clinerules/rules.md, constitution.md

[Iteration 1/5]
🔍 Agent is reading target file: prg/cli.py
✍️  Agent is modifying prg/cli.py (Adding --verbose boolean option to analyze command)
🧪 Agent is running self-review... 
   > Running tests: pytest prg/tests/test_cli.py
   > Output: 2 passed in 0.05s
✅ Self-review passed.

🏁 Feature implementation complete!
Ralph has finished executing the feature loop.
The code is thoroughly self-tested and ready for human review.

[Action Required] Run `prg ralph approve` to merge, or `prg ralph reject` to revert.
"""

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
img_width = max(max_width_actual + padding * 2, 700)
img_height = total_height + padding * 2

img = Image.new('RGB', (img_width, img_height), color=(30, 30, 30))
draw = ImageDraw.Draw(img)

y_text = padding
for i, line in enumerate(lines):
    fill_col = (200, 200, 200)
    if "prg ralph" in line and i == 0: fill_col = (100, 255, 100) # Green for command
    elif "[System]" in line: fill_col = (150, 150, 150)
    elif "🤖" in line: fill_col = (200, 200, 255)
    elif "✅" in line: fill_col = (100, 255, 100)
    elif "🏁" in line: fill_col = (255, 200, 100)
    elif "Action Required" in line: fill_col = (255, 150, 150)
    elif "Agent is" in line: fill_col = (200, 220, 255)
    elif "Running tests" in line or "Output:" in line: fill_col = (150, 150, 150)
    
    draw.text((padding, y_text), line, font=font, fill=fill_col)
    bbox = draw.textbbox((0, 0), line, font=font)
    y_text += (bbox[3] - bbox[1]) + 4

os.makedirs("docs/assets", exist_ok=True)
img.save("docs/assets/ralph-demo.png")
print("Saved docs/assets/ralph-demo.png successfully.")
