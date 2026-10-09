import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto("http://localhost:8501")
        await page.wait_for_timeout(3000)

        # Click "Plotar Bases" button in sidebar to create points
        plot_btn = page.get_by_role("button", name="Plotar Bases")
        await plot_btn.click()
        await page.wait_for_timeout(3000)

        # Take screenshot with points plotted
        await page.screenshot(path="test_map_points.png")

        # Find map iframe
        iframe_element = await page.wait_for_selector("iframe")
        frame = await iframe_element.content_frame()

        # Switch to Vector Clean
        vec_btn = await frame.wait_for_selector("#btn-vector")
        await vec_btn.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path="test_map_vector.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
