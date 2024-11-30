from utils import execute_query, execute_query_with_validation, validate_and_normalize, validate_transaction_type


# Хоз.товары на складе
def household_items():
    items = execute_query("SELECT item_name, unit, stock_amount FROM household_items ORDER BY item_name ASC")
    return items


# Списание хоз.товаров
def deduct_items(item_name, quantity, reason):
    try:
        # Проверка и нормализация данных
        if not item_name.strip() or not isinstance(item_name, str):
            raise ValueError("Ошибка: Название хоз. товара должно быть строкой и не может быть пустым.")

        if not isinstance(quantity, (int, float)) or quantity <= 0:
            raise ValueError("Ошибка: Количество должно быть положительным числом.")

        if not reason.strip() or not isinstance(reason, str):
            raise ValueError("Ошибка: Причина списания должна быть строкой и не может быть пустой.")

        # Приведение к нижнему регистру
        item_name = item_name.lower()

        # Проверка наличия товара и текущего запаса
        item = execute_query_with_validation(
            "SELECT item_id, stock_amount FROM household_items WHERE LOWER(item_name) = %s",
            (item_name,),
            fetchone=True
        )

        if item is None:
            print(f"Товар '{item_name}' не найден.")
            return

        item_id, current_stock = item

        # Проверка, достаточно ли товара для списания
        if quantity > current_stock:
            print(f"Недостаточно {item_name} на складе для списания. Доступно: {current_stock}.")
            return

        # Обновляем количество на складе
        execute_query_with_validation(
            "UPDATE household_items SET stock_amount = stock_amount - %s WHERE item_id = %s",
            (quantity, item_id),
            commit=True
        )

        # Вносим запись в stock_transaction_houseitems
        transaction_type = 'расход'
        execute_query_with_validation(
            """
            INSERT INTO stock_transaction_houseitems (item_id, transaction_date, transaction_type, quantity, reason)
            VALUES (%s, CURRENT_DATE, %s, %s, %s)
            """,
            (item_id, transaction_type, quantity, reason),
            commit=True
        )

        print(f"Списано {quantity} шт {item_name}.")

    except ValueError as ve:
        print(f"Ошибка валидации: {ve}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

    return f"Списано {quantity} шт {item_name}."


# Приход хоз.товаров
def arrival_items(item_name, quantity, reason):
    transaction_type = 'приход'
    try:
        if not item_name.strip() or not isinstance(item_name, str):
            raise ValueError("Ошибка: Название хоз.товара должно быть строкой и не может быть пустым.")

        quantity, transaction_type, reason = validate_and_normalize(quantity, transaction_type, reason)
        validate_transaction_type(transaction_type)

        # Находим item_id по имени ингредиента
        item = execute_query_with_validation(
            "SELECT item_id FROM household_items WHERE LOWER(item_name) = %s",
            (item_name,),
            fetchone=True
        )
        if item is None:
            print(f"Хоз.товар '{item_name}' не найден.")
            return

        item_id = item[0]

        # Обновляем количество на складе
        execute_query_with_validation(
            "UPDATE household_items SET stock_amount = stock_amount + %s WHERE item_id = %s",
            (quantity, item_id),
            commit=True
        )

        # Вносим запись в stock_transactions
        execute_query_with_validation(
            "INSERT INTO stock_transaction_houseitems (item_id, transaction_date, transaction_type, quantity, reason) "
            "VALUES (%s, CURRENT_DATE, %s, %s, %s)",
            (item_id, transaction_type, quantity, reason),
            commit=True
        )

        print(f"Добавлено {quantity} кг {item_name}.")
    except ValueError as ve:
        print(f"Ошибка валидации: {ve}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


# Новый хоз.товар
def new_item(item_name, unit, stock_amount):
    try:
        item_name = item_name.strip().lower()
        if not item_name or not isinstance(item_name, str):
            raise ValueError("Ошибка: Название хоз.товара должно быть строкой и не может быть пустым.")

        if not isinstance(unit, str) or not unit.strip():
            raise ValueError("Ошибка: Единица измерения должна быть строкой и не может быть пустой.")

        if not isinstance(stock_amount, (int, float)) or stock_amount < 0:
            raise ValueError("Ошибка: Количество должно быть положительным числом.")

        # Проверка, существует ли товар
        existing_item = execute_query_with_validation(
            "SELECT item_id, stock_amount FROM household_items WHERE item_name = %s",
            (item_name,),
            fetchone=True
        )
        print(f"Результат запроса на существующий товар: {existing_item}")

        if existing_item:
            item_id = existing_item[0]
            # Обновление количества товара
            execute_query_with_validation(
                "UPDATE household_items SET stock_amount = stock_amount + %s WHERE item_name = %s",
                (stock_amount, item_name),
                commit=True
            )
            transaction_type = 'приход'
            reason = 'Обновление существующего хоз.товара'
            print(f"Товар {item_name} обновлен.")
        else:
            # Добавление нового хоз.товара
            item_id = execute_query_with_validation(
                "INSERT INTO household_items (item_name, unit, stock_amount) VALUES (%s, %s, %s) RETURNING item_id",
                (item_name, unit, stock_amount),
                commit=True,
                fetchone=True
            )[0]
            transaction_type = 'приход'
            reason = 'Добавление нового хоз.товара'
            print(f"Товар {item_name} добавлен.")

        # Добавление записи в stock_transaction_houseitems
        execute_query_with_validation(
            """
            INSERT INTO stock_transaction_houseitems (item_id, transaction_date, transaction_type, quantity, reason)
            VALUES (%s, CURRENT_DATE, %s, %s, %s)
            """,
            (item_id, transaction_type, stock_amount, reason),
            commit=True
        )
        print(f"Транзакция для товара {item_name} добавлена.")

        return f"Хоз.товар '{item_name}' успешно добавлен или обновлен с количеством {stock_amount}."

    except ValueError as ve:
        return f"Ошибка валидации: {ve}"
    except Exception as e:
        return f"Произошла ошибка: {e}"


# Удаление хоз.товара
def delete_item(item_name):
    item_name = item_name.strip().lower()
    if not item_name or not isinstance(item_name, str):
        raise ValueError("Ошибка: Название товара должно быть строкой и не может быть пустым.")

    existing_item = execute_query(
        "SELECT item_id, stock_amount FROM household_items WHERE item_name =%s",
        (item_name,),
        fetchone=True
    )
    if existing_item:
        item_id = existing_item[0]
        execute_query(
            "DELETE FROM household_items WHERE item_id =%s",
            (item_id,),
            commit=True
        )
        return f'Товар {item_name} был успешно удален'
    else:
        return f'Товара {item_name} не существует'

