"""Quick test of Moodle connection."""
import asyncio
import os
from dotenv import load_dotenv
from src.mcp.protocol import MoodleClient

load_dotenv()


async def test():
    url = os.getenv("MOODLE_URL")
    token = os.getenv("MOODLE_TOKEN")

    if not url or not token:
        print(" Error: MOODLE_URL y MOODLE_TOKEN deben estar en .env")
        return

    print(f" Conectando a: {url}")

    client = MoodleClient(url, token)

    try:
        courses = await client.get_courses()
        print(f" Éxito! Encontrados {len(courses)} cursos:")

        for course in courses[:5]:  # Mostrar primeros 5
            print(f"📚 {course.get('fullname')} (ID: {course.get('id')})")

    except ValueError as e:
        print(f" Error de Moodle: {e}")
    except Exception as e:
        print(f" Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test())