const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating to http://localhost:3000...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });

  // Wait for the language dropdown to be available (assuming it is part of the layout or ChatWindow)
  // The layout has a language dropdown usually, or it's in the QuickChats/ChatWindow.
  // We can just type a query in the chat window.
  
  console.log('Typing in chat...');
  // The input is a textarea with placeholder 'Type in your language...' or similar
  await page.waitForSelector('textarea');
  await page.type('textarea', 'What are the guidelines for IS 13252?');
  
  console.log('Pressing Enter...');
  await page.keyboard.press('Enter');
  
  console.log('Waiting for response...');
  // Wait for the chatbot to render a response containing 'guidelines' or wait a few seconds
  await new Promise(r => setTimeout(r, 6000));
  
  const artifactPath = 'C:/Users/rohit/.gemini/antigravity-ide/brain/f15b9107-71d4-47b6-a219-9fc50a5167fc/scratch/screenshot_test.png';
  await page.screenshot({ path: artifactPath, fullPage: true });
  console.log('Saved screenshot to', artifactPath);

  await browser.close();
})();
