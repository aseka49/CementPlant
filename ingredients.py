from utils import execute_query, execute_query_with_validation, validate_and_normalize, validate_transaction_type


# Списание со склада
def deduct_stock(ingredient_name, quantity, reason):
    try:

        if not ingredient_name.strip() or not isinstance(ingredient_name, str):
            raise ValueError("Ошибка: Название ингредиента должно быть строкой и не может быть пустым.")

        quantity, transaction_type, reason = validate_and_normalize(quantity, 'расход', reason)

        ingredient_name = ingredient_name.lower()

        ingredient = execute_query_with_validation(
            "SELECT ingredient_id, stock_amount FROM ingredients WHERE LOWER(ingredient_name) = %s",
            (ingredient_name,),
            fetchone=True
        )

        if ingredient is None:
            print(f"Ингредиент '{ingredient_name}' не найден.")
            return False

        ingredient_id, current_stock = ingredient
        if quantity > current_stock:
            print(f"Недостаточно {ingredient_name} на складе для списания. Доступно: {current_stock}.")
            return False
        execute_query_with_validation(
            "UPDATE ingredients SET stock_amount = stock_amount - %s WHERE ingredient_id = %s",
            (quantity, ingredient_id),
            commit=True
        )
        execute_query_with_validation(
            "INSERT INTO stock_transactions (ingredient_id, transaction_date, transaction_type, quantity, reason) "
            "VALUES (%s, CURRENT_DATE, %s, %s, %s)",
            (ingredient_id, transaction_type, quantity, reason),
            commit=True
        )

        return f"Списано {quantity} кг {ingredient_name}."

    except ValueError as ve:
        return f"Ошибка валидации: {ve}"
    except Exception as e:
        return f"Произошла непредвиденная ошибка: {e}"


# Добавление прихода товара
def arrival_stock(ingredient_name, quantity, reason):
    transaction_type = 'приход'
    try:
        if not ingredient_name.strip() or not isinstance(ingredient_name, str):
            raise ValueError("Ошибка: Название ингредиента должно быть строкой и не может быть пустым.")

        quantity, transaction_type, reason = validate_and_normalize(quantity, transaction_type, reason)
        validate_transaction_type(transaction_type)

        ingredient = execute_query_with_validation(
            "SELECT ingredient_id FROM ingredients WHERE LOWER(ingredient_name) = %s",
            (ingredient_name,),
            fetchone=True
        )

        if ingredient is None:
            print(f"Ингредиент '{ingredient_name}' не найден.")
            return False

        ingredient_id = ingredient[0]

        execute_query_with_validation(
            "UPDATE ingredients SET stock_amount = stock_amount + %s WHERE ingredient_id = %s",
            (quantity, ingredient_id),
            commit=True
        )

        execute_query_with_validation(
            "INSERT INTO stock_transactions (ingredient_id, transaction_date, transaction_type, quantity, reason) "
            "VALUES (%s, CURRENT_DATE, %s, %s, %s)",
            (ingredient_id, transaction_type, quantity, reason),
            commit=True
        )

        return f"Добавлено {quantity} кг {ingredient_name}."
    except ValueError as ve:
        return f"Ошибка валидации: {ve}"
    except Exception as e:
        return f"Произошла непредвиденная ошибка: {e}"


# Добавление нового товара
def new_ingredient(name, unit, stock_amount):
    try:
        # Валидация данных
        name = name.strip().lower()
        if not name or not isinstance(name, str):
            raise ValueError("Ошибка: Название ингредиента должно быть строкой и не может быть пустым.")

        if not isinstance(unit, str) or not unit.strip():
            raise ValueError("Ошибка: Единица измерения должна быть строкой и не может быть пустой.")

        if not isinstance(stock_amount, (int, float)) or stock_amount < 0:
            raise ValueError("Ошибка: Количество должно быть положительным числом.")

        # Проверка, существует ли ингредиент в базе данных
        existing_ingredient = execute_query_with_validation(
            "SELECT ingredient_id, stock_amount FROM ingredients WHERE ingredient_name = %s",
            (name,),
            fetchone=True
        )

        if existing_ingredient:
            ingredient_id = existing_ingredient[0]
            # Обновление количества ингредиента
            execute_query_with_validation(
                "UPDATE ingredients SET stock_amount = stock_amount + %s WHERE ingredient_name = %s",
                (stock_amount, name),
                commit=True
            )
            transaction_type = 'приход'
            reason = 'Обновление существующего ингредиента'

        else:
            # Добавление нового ингредиента в базу данных
            ingredient_id = execute_query_with_validation(
                "INSERT INTO ingredients (ingredient_name, unit, stock_amount) VALUES (%s, %s, %s) RETURNING ingredient_id",
                (name, unit, stock_amount),
                commit=True,
                fetchone=True
            )[0]
            transaction_type = 'приход'
            reason = 'Добавление нового ингредиента'

        # Добавление записи в stock_transactions
        execute_query_with_validation(
            """
            INSERT INTO stock_transactions (ingredient_id, transaction_date, transaction_type, quantity, reason)
            VALUES (%s, CURRENT_DATE, %s, %s, %s)
            """,
            (ingredient_id, transaction_type, stock_amount, reason),
            commit=True
        )

        return f"Ингредиент '{name}' успешно добавлен или обновлен с количеством {stock_amount}."

    except ValueError as ve:
        return f"Ошибка валидации: {ve}"
    except Exception as e:
        print(f"Ошибка при добавлении/обновлении ингредиента: {e}")
        return f"Произошла ошибка: {e}"


# Удаление ингредиента
def delete_ingredient(name):
    name = name.strip().lower()
    if not name or not isinstance(name, str):
        raise ValueError("Ошибка: Название ингредиента должно быть строкой и не может быть пустым.")
    existing_ingredient = execute_query_with_validation(
        "SELECT ingredient_id, stock_amount FROM ingredients WHERE ingredient_name = %s",
        (name,),
        fetchone=True
    )

    if not existing_ingredient:
        return f'Ингредиент ({name}) не существует'

    ingredient_id = existing_ingredient[0]

    is_used_in_recipes = execute_query_with_validation(
        "SELECT COUNT(*) FROM recipe_ingredients WHERE ingredient_id = %s",
        (ingredient_id,),
        fetchone=True
    )[0]

    if is_used_in_recipes > 0:
        execute_query(
            "DELETE FROM recipe_ingredients WHERE ingredient_id = %s",
            (ingredient_id,),
            commit=True
        )

    execute_query(
        "DELETE FROM ingredients WHERE ingredient_id = %s",
        (ingredient_id,),
        commit=True
    )

    return f'Ингредиент ({name}) был успешно удален.'


def stock_status():
    ingredients = execute_query(
        "SELECT ingredient_name, unit, stock_amount FROM ingredients ORDER BY ingredient_name ASC")

    return ingredients

# Вывод ингредиентов с наименьшим кол-вом на складе
def ingredients_table(sort_type='alphabet'):
    query = "SELECT ingredient_name, unit, stock_amount FROM ingredients"

    if sort_type == 'alphabet':
        query += " ORDER BY ingredient_name ASC"
    elif sort_type == 'stock':
        query += " ORDER BY stock_amount ASC"


    return execute_query(query)

