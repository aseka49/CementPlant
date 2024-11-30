from utils import execute_query


# Функция расчета ингредиентов на n-ное количество блюд
def calculate_total_ingredients(recipe_servings, calculation_date):
    total_ingredients = {}

    print("Блюда и количество порций:")
    for recipe_name, servings in recipe_servings:
        print(f"- {recipe_name}: {servings} порций")

        recipe = execute_query(
            "SELECT recipe_id FROM recipes WHERE recipe_name = %s",
            (recipe_name,),
            fetchone=True
        )
        if not recipe:
            print(f"Рецепт '{recipe_name}' не найден.")
            continue

        recipe_id = recipe[0]

        ingredients = execute_query(
            """
            SELECT i.ingredient_id, i.ingredient_name, ri.amount_per_serving
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
            WHERE ri.recipe_id = %s
            """,
            (recipe_id,)
        )

        for ingredient_id, ingredient_name, amount_per_serving in ingredients:
            total_amount = amount_per_serving * servings
            if ingredient_name in total_ingredients:
                total_ingredients[ingredient_name]['quantity'] += total_amount
            else:
                total_ingredients[ingredient_name] = {'id': ingredient_id, 'quantity': total_amount}

    for ingredient_name, data in total_ingredients.items():
        ingredient_id = data['id']
        total_amount = data['quantity']

        current_stock = execute_query(
            "SELECT stock_amount FROM ingredients WHERE ingredient_id = %s",
            (ingredient_id,),
            fetchone=True
        )

        if current_stock is None:
            print(f"Ингредиент '{ingredient_name}' не найден в базе данных.")
            return None  # Прерываем выполнение, если ингредиент не найден

        current_stock = current_stock[0]

        if total_amount > current_stock:
            print(
                f"Ошибка: Недостаточно {ingredient_name}. Требуется {total_amount} кг, а на складе только {current_stock} кг.")
            return None

    for ingredient_name, data in total_ingredients.items():
        ingredient_id = data['id']
        total_amount = data['quantity']

        execute_query(
            "UPDATE ingredients SET stock_amount = stock_amount - %s WHERE ingredient_id = %s",
            (total_amount, ingredient_id),
            commit=True
        )

        execute_query(
            """
            INSERT INTO stock_transactions (ingredient_id, transaction_date, transaction_type, quantity, reason)
            VALUES (%s, %s, 'расход', %s, 'Приготовление блюд')
            """,
            (ingredient_id, calculation_date, total_amount),
            commit=True
        )

    return total_ingredients


# Функция по добавлению новых рецептов
def new_recipe(recipe_name, ingredients, category_name):
    try:
        recipe_name = recipe_name.strip().lower()

        if not recipe_name or not isinstance(recipe_name, str):
            raise ValueError("Ошибка: Название рецепта должно быть строкой и не может быть пустым.")
        if len(recipe_name) < 3:
            raise ValueError("Ошибка: Название рецепта должно быть не менее 3 символов.")

        if not category_name or not isinstance(category_name, str):
            raise ValueError("Ошибка: Название категории должно быть строкой и не может быть пустым.")

        # Получение ID категории
        category_id = execute_query(
            "SELECT category_id FROM categories WHERE category_name = %s",
            (category_name,),
            fetchone=True
        )
        if not category_id:
            raise ValueError(f"Ошибка: Категория '{category_name}' не существует.")
        category_id = category_id[0]  # Извлечение значения

        # Проверка существующего рецепта
        existing_recipe = execute_query(
            "SELECT recipe_name FROM recipes WHERE LOWER(recipe_name) = %s",
            (recipe_name,),
            fetchone=True
        )
        if existing_recipe:
            raise ValueError(f"Ошибка: Рецепт с названием '{recipe_name.title()}' уже существует.")

        # Нормализация ингредиентов
        normalized_ingredients = []
        for i in ingredients:
            if isinstance(i, tuple) and len(i) == 2 and isinstance(i[0], str) and isinstance(i[1], (int, float)) and i[1] > 0:
                normalized_ingredients.append((i[0].strip().lower(), i[1]))
            else:
                raise ValueError("Ошибка: Ингредиенты должны быть списком кортежей (название, количество).")

        # Добавление рецепта
        recipe_id = execute_query(
            "INSERT INTO recipes (recipe_name, category_id) VALUES (%s, %s) RETURNING recipe_id",
            (recipe_name, category_id),
            commit=True,
            fetchone=True
        )[0]

        # Добавление ингредиентов
        for ingredient_name, amount_per_serving in normalized_ingredients:
            ingredient = execute_query(
                "SELECT ingredient_id FROM ingredients WHERE LOWER(ingredient_name) = %s",
                (ingredient_name,),
                fetchone=True
            )
            if ingredient is None:
                raise ValueError(f"Ошибка: Ингредиент '{ingredient_name}' не найден.")
            ingredient_id = ingredient[0]

            execute_query(
                """
                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount_per_serving)
                VALUES (%s, %s, %s)
                """,
                (recipe_id, ingredient_id, amount_per_serving),
                commit=True
            )

        return f"Рецепт '{recipe_name.title()}' успешно добавлен с ингредиентами в категорию '{category_name}'."

    except ValueError as ve:
        print(f"Ошибка валидации: {ve}")
    except Exception as e:
        print(f"Произошла ошибка при добавлении рецепта: {e}")


# Вывод всех нынешних рецептов
def actual_recipes():
    recipes = execute_query("SELECT recipe_name FROM recipes ORDER BY recipe_name ASC")
    return recipes


# Функция по удалению рецепта
def delete_recipe(recipe_name):
    try:
        if not recipe_name or not isinstance(recipe_name, str) or not recipe_name.strip():
            raise ValueError("Ошибка: Название рецепта должно быть строкой и не может быть пустым.")

        if len(recipe_name.strip()) < 2:
            raise ValueError("Ошибка: Название рецепта должно быть не менее 2 символов.")

        result = execute_query(
            "SELECT recipe_id FROM recipes WHERE recipe_name = %s",
            (recipe_name.strip(),),
            fetchone=True
        )

        if result is None:
            print(f"Рецепт с названием '{recipe_name}' не найден.")
            return

        recipe_id = result[0]
        execute_query(
            "DELETE FROM recipe_ingredients WHERE recipe_id = %s",
            (recipe_id,),
            commit=True
        )

        execute_query(
            "DELETE FROM recipes WHERE recipe_id = %s",
            (recipe_id,),
            commit=True
        )
        return f"Рецепт '{recipe_name}' и связанные ингредиенты успешно удалены."

    except ValueError as ve:
        return f"Ошибка валидации: {ve}"
    except Exception as e:
        return f"Произошла ошибка при удалении рецепта: {e}"


def update_recipe(recipe_name, new_recipe_name=None, updated_ingredients=None, removed_ingredients=None):
    try:
        # Проверка входных данных
        recipe_name = recipe_name.strip().lower()
        if not recipe_name or len(recipe_name) < 2:
            raise ValueError("Ошибка: Название рецепта должно быть строкой и не может быть пустым.")
        recipe_id_result = execute_query(
            "SELECT recipe_id FROM recipes WHERE recipe_name = %s",
            (recipe_name,),
            fetchone=True
        )
        if recipe_id_result is None:
            raise ValueError("Рецепта не существует")
        recipe_id = recipe_id_result[0]

        # Обновление названия рецепта
        if new_recipe_name:
            new_recipe_name = new_recipe_name.strip().lower()
            if len(new_recipe_name) < 2:
                raise ValueError("Новое название рецепта должно состоять больше чем из 2 символов")

            execute_query(
                "UPDATE recipes SET recipe_name = %s WHERE recipe_id = %s",
                (new_recipe_name, recipe_id),
                commit=True
            )

        # Обновление ингредиентов
        if updated_ingredients:
            for ingredient_name, amount in updated_ingredients:
                if not isinstance(ingredient_name, str) or not isinstance(amount, (int, float)) or amount <= 0:
                    raise ValueError("Ошибка: Ингредиенты должны быть строками с положительным количеством.")

                ingredient_result = execute_query(
                    "SELECT ingredient_id FROM ingredients WHERE LOWER(ingredient_name) = %s",
                    (ingredient_name.strip().lower(),),
                    fetchone=True
                )

                if ingredient_result is None:
                    print(f"Ингредиент '{ingredient_name}' не найден. Он будет пропущен.")
                    continue

                ingredient_id = ingredient_result[0]

                recipe_ingredient_result = execute_query(
                    """
                    SELECT * FROM recipe_ingredients
                    WHERE recipe_id = %s AND ingredient_id = %s
                    """,
                    (recipe_id, ingredient_id),
                    fetchone=True
                )

                if recipe_ingredient_result:
                    execute_query(
                        """
                        UPDATE recipe_ingredients
                        SET amount_per_serving = %s
                        WHERE recipe_id = %s AND ingredient_id = %s
                        """,
                        (amount, recipe_id, ingredient_id),
                        commit=True
                    )
                else:
                    execute_query(
                        """
                        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount_per_serving)
                        VALUES (%s, %s, %s)
                        """,
                        (recipe_id, ingredient_id, amount),
                        commit=True
                    )

        # Удаление ингредиентов
        if removed_ingredients:
            for ingredient_name in removed_ingredients:
                if not isinstance(ingredient_name, str):
                    raise ValueError("Ошибка: Название ингредиента должно быть строкой.")

                ingredient_result = execute_query(
                    "SELECT ingredient_id FROM ingredients WHERE LOWER(ingredient_name) = %s",
                    (ingredient_name.strip().lower(),),
                    fetchone=True
                )

                if ingredient_result is None:
                    print(f"Ингредиент '{ingredient_name}' не найден.")
                    continue

                ingredient_id = ingredient_result[0]

                execute_query(
                    "DELETE FROM recipe_ingredients WHERE recipe_id = %s AND ingredient_id = %s",
                    (recipe_id, ingredient_id),
                    commit=True
                )

        return f"Рецепт '{recipe_name.title()}' успешно обновлен."

    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Произошла ошибка при обновлении рецепта: {e}"


def show_recipe_ingredient(recipe_name):
    # Получаем ID рецепта по названию
    recipe_id_result = execute_query(
        "SELECT recipe_id FROM recipes WHERE recipe_name = %s",
        (recipe_name,),
        fetchone=True
    )
    if recipe_id_result is None:
        return None  # Рецепт с таким названием не найден

    recipe_id = recipe_id_result[0]

    # Получаем ингредиенты для рецепта по его ID
    ingredients_from_recipe = execute_query(
        """
        SELECT i.ingredient_name, ri.amount_per_serving
        FROM recipe_ingredients ri
        JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
        WHERE ri.recipe_id = %s
        """,
        (recipe_id,),
        fetchone=False
    )

    return ingredients_from_recipe


def table_recipes(sort_type='name'):
    query = "SELECT r.recipe_name, c.category_name FROM recipes r LEFT JOIN categories c ON r.category_id = c.category_id"
    if sort_type == 'name':
        query += " ORDER BY recipe_name ASC"
    elif sort_type == 'category':
        query += " ORDER BY category_name ASC"
    return execute_query(query)
