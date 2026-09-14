import re
with open('c:/Users/rohit/OneDrive/Desktop/sih/bis-frontend/app/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace any weird characters before `<div className="min-h-screen`
content = re.sub(r'return\s*\(\s*.*?<div className=\"min-h-screen', 'return (\n    <div className=\"min-h-screen', content, flags=re.DOTALL)

with open('c:/Users/rohit/OneDrive/Desktop/sih/bis-frontend/app/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
