import json
import os
import asyncio
from deep_translator import GoogleTranslator

# en.json path
en_path = r"c:\Users\rohit\OneDrive\Desktop\sih\bis-frontend\public\locales\en.json"
locales_dir = r"c:\Users\rohit\OneDrive\Desktop\sih\bis-frontend\public\locales"

# 'bn', 'mr', 'ta', 'ur', 'gu', 'ml', 'kn', 'pa', 'hi', 'or'
langs = ['hi', 'bn', 'mr', 'ta', 'ur', 'gu', 'ml', 'kn', 'or', 'pa']

def translate_dict(data, lang):
    import time
    translated_data = {}
    translator = GoogleTranslator(source='en', target=lang)
    for k, v in data.items():
        if isinstance(v, str):
            success = False
            for attempt in range(5):
                try:
                    res = translator.translate(v)
                    translated_data[k] = res
                    success = True
                    break
                except Exception as e:
                    time.sleep(1)
            if not success:
                translated_data[k] = v # fallback
        else:
            translated_data[k] = v
    return translated_data

def main():
    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)

    for lang in langs:
        file_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            print(f"Skipping {lang}, already exists.", flush=True)
            continue
            
        print(f"Translating for {lang}...", flush=True)
        try:
            translated_data = translate_dict(en_data, lang)
            # Fix up specific tags that might be mangled
            if "hero_desc" in translated_data:
                desc = translated_data["hero_desc"]
                desc = desc.replace("< 1 >", "<1>").replace("< / 1 >", "</1>").replace("<1 >", "<1>").replace("</ 1>", "</1>")
                translated_data["hero_desc"] = desc
                
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
            print(f"Saved {lang}.json", flush=True)
        except Exception as e:
            print(f"Failed for {lang}: {e}", flush=True)

if __name__ == "__main__":
    main()
