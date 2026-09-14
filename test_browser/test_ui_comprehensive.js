const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating to http://localhost:3000...');
  await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });

  // Wait a moment for rendering
  await new Promise(r => setTimeout(r, 2000));

  // 1. Test Language Dropdown
  console.log('Testing language dropdown...');
  // The language dropdown is a select element. Let's find it.
  // In LanguageSelector.tsx, it renders a `<select>` with value="en", "hi", etc.
  const selectHandle = await page.$('select');
  if (selectHandle) {
    await page.select('select', 'hi'); // Select Hindi
    await new Promise(r => setTimeout(r, 2000)); // wait for translation
    const pathHi = 'C:/Users/rohit/.gemini/antigravity-ide/brain/f15b9107-71d4-47b6-a219-9fc50a5167fc/scratch/ui_hindi.png';
    await page.screenshot({ path: pathHi, fullPage: true });
    console.log('Saved Hindi UI screenshot to', pathHi);

    await page.select('select', 'en'); // Switch back to English
    await new Promise(r => setTimeout(r, 1000));
  } else {
    console.log('Select dropdown not found!');
  }

  // 2. Test Action Chips
  console.log('Typing in chat...');
  await page.waitForSelector('textarea');
  await page.type('textarea', 'What is IS 13252?');
  
  console.log('Pressing Enter...');
  await page.keyboard.press('Enter');
  
  console.log('Waiting for chatbot to generate response with chips...');
  // Wait enough time for the RAG and LLM to respond
  await new Promise(r => setTimeout(r, 15000));
  
  // Find the chip containing "Scheme Guidance"
  console.log('Looking for Scheme Guidance chip...');
  const chips = await page.$$('button');
  let clicked = false;
  for (const chip of chips) {
    const text = await page.evaluate(el => el.textContent, chip);
    if (text.includes('Scheme Guidance') || text.includes('Explore IS')) {
      if (text.includes('Scheme Guidance')) {
        await chip.click();
        clicked = true;
        console.log('Clicked Scheme Guidance chip!');
        break;
      }
    }
  }

  if (clicked) {
    console.log('Waiting for final Scheme Guidance response...');
    await new Promise(r => setTimeout(r, 15000));
    
    const pathScheme = 'C:/Users/rohit/.gemini/antigravity-ide/brain/f15b9107-71d4-47b6-a219-9fc50a5167fc/scratch/ui_scheme.png';
    await page.screenshot({ path: pathScheme, fullPage: true });
    console.log('Saved Scheme response screenshot to', pathScheme);
  } else {
    console.log('Could not find Scheme Guidance chip.');
    const pathErr = 'C:/Users/rohit/.gemini/antigravity-ide/brain/f15b9107-71d4-47b6-a219-9fc50a5167fc/scratch/ui_error.png';
    await page.screenshot({ path: pathErr, fullPage: true });
  }

  await browser.close();
})();
