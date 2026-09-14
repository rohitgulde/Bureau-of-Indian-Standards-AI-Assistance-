import json
import os
import asyncio
from googletrans import Translator

# en.json path
en_path = r"c:\Users\rohit\OneDrive\Desktop\sih\bis-frontend\public\locales\en.json"
locales_dir = r"c:\Users\rohit\OneDrive\Desktop\sih\bis-frontend\public\locales"

# List of target language codes
# Note: googletrans uses 'or' for Odia? Google Translate API code is 'or' or 'od'. Let's check googletrans.
# 'bn', 'mr', 'ta', 'ur', 'gu', 'ml', 'kn', 'pa', 'hi', 'or'
langs = ['hi', 'bn', 'mr', 'ta', 'ur', 'gu', 'ml', 'kn', 'or', 'pa']

async def translate_dict(translator, data, lang):
    translated_data = {}
    for k, v in data.items():
        if isinstance(v, str):
            # Try to avoid translating HTML tags like <1> and </1> if possible, or fix them post-translation
            res = await translator.translate(v, dest=lang)
            translated_data[k] = res.text
        else:
            translated_data[k] = v
    return translated_data

async def main():
    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)

    translator = Translator()

    for lang in langs:
        file_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            print(f"Skipping {lang}, already exists.")
            continue
            
        print(f"Translating for {lang}...")
        try:
            translated_data = await translate_dict(translator, en_data, lang)
            # Fix up specific tags that might be mangled
            if "hero_desc" in translated_data:
                desc = translated_data["hero_desc"]
                desc = desc.replace("< 1 >", "<1>").replace("< / 1 >", "</1>").replace("<1 >", "<1>").replace("</ 1>", "</1>")
                translated_data["hero_desc"] = desc
                
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
            print(f"Saved {lang}.json")
        except Exception as e:
            print(f"Failed for {lang}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
