import re
with open('c:/Users/rohit/OneDrive/Desktop/sih/bis-frontend/app/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

good_content = '''  const STATS = [
    { icon: BookOpen,    label: t("stat_1_label"),       value: t("stat_1_value") },
    { icon: FlaskConical,label: t("stat_2_label"),     value: t("stat_2_value") },
    { icon: Award,       label: t("stat_3_label"),  value: t("stat_3_value")    },
    { icon: Shield,      label: t("stat_4_label"),    value: t("stat_4_value")     },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-background dark:via-background dark:to-background flex flex-col relative overflow-hidden">
      {/* ── Global Decorative Blobs (Premium feel in light mode) ── */}'''

start_idx = content.find('  const STATS = [')
end_idx = content.find('      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">')

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + good_content + '\n' + content[end_idx:]
    with open('c:/Users/rohit/OneDrive/Desktop/sih/bis-frontend/app/page.tsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Fixed!')
else:
    print('Not found')
