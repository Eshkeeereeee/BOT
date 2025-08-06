import random
import string


async def generate_qk_code(db):
    """Генерирует уникальный qK-код"""
    while True:
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = ''.join(random.choices(string.digits, k=7))

        code_parts = []
        num_index = 0

        for i in range(len(letters) + len(numbers)):
            if random.random() < 0.3 and len(code_parts) < len(letters) + len(numbers):
                if any(c.isalpha() for c in code_parts):
                    if num_index < len(numbers):
                        code_parts.append(numbers[num_index])
                        num_index += 1
                else:
                    code_parts.append(letters[0])
                    letters = letters[1:]
            else:
                if num_index < len(numbers):
                    code_parts.append(numbers[num_index])
                    num_index += 1
                elif letters:
                    code_parts.append(letters[0])
                    letters = letters[1:]

        qk_code = f"qK-{''.join(code_parts)}"

        if not await db.qk_exists(qk_code):
            return qk_code