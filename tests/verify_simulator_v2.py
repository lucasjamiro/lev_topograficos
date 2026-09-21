import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async_playwright_instance = await async_playwright().start()
    browser = await async_playwright_instance.chromium.launch()
    page = await browser.new_page()

    # Increase timeout for streamlit
    page.set_default_timeout(60000)

    await page.goto("http://localhost:8501")
    await page.wait_for_selector("text=Simulador de Levantamentos Topográficos")
    print("Page loaded")

    # 1. Test Linked Traverse (Poligonal Enquadrada)
    # Select Poligonação (it's default)
    # Select Enquadrada
    # The radio buttons are "Fechada" and "Enquadrada". Index 0 is Fechada, Index 1 is Enquadrada.
    await page.get_by_text("Enquadrada").click()
    await page.wait_for_timeout(1000)

    # Click "Gerar Coordenadas Aleatórias"
    await page.get_by_text("Gerar Coordenadas Aleatórias").click()
    await page.wait_for_timeout(2000)

    # Click "Simular Observações de Campo"
    # There are two buttons with this text potentially? No, one is inside a column.
    await page.get_by_text("Simular Observações de Campo").click()
    await page.wait_for_timeout(2000)

    # Scroll down to results
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    await page.screenshot(path="traverse_linked_results.png", full_page=True)
    print("Traverse Linked results captured")

    # 2. Test Leveling (Nivelamento)
    # Change to Leveling
    # The first selectbox is "Tipo de Levantamento"
    await page.get_by_test_id("stSelectbox").first.click()
    await page.keyboard.press("ArrowDown")
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2000)

    # Click "Gerar Trajeto de Nivelamento"
    await page.get_by_text("Gerar Trajeto de Nivelamento").click()
    await page.wait_for_timeout(2000)

    # Click "Simular Observações de Campo"
    await page.get_by_text("Simular Observações de Campo").click()
    await page.wait_for_timeout(3000)

    # Scroll down to ASCII Rod
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    await page.screenshot(path="leveling_rod_results.png", full_page=True)
    print("Leveling rod results captured")

    # 3. Test Challenge Mode
    await page.get_by_test_id("stCheckbox").first.click() # Modo Desafio
    await page.wait_for_timeout(1000)
    await page.screenshot(path="challenge_mode.png", full_page=True)
    print("Challenge mode captured")

    await browser.close()
    await async_playwright_instance.stop()

if __name__ == "__main__":
    asyncio.run(run())
