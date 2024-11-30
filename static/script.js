function toggleTable() {
    const table = document.getElementById('itemsTable');
    table.style.display = table.style.display === 'none' ? 'block' : 'none';
}
function refreshPage() {
    location.reload();
}


function addRecipeInput() {
    const newInput = document.createElement('div');
    newInput.classList.add('recipe-input');
    newInput.innerHTML = `
        <label for="recipe">Блюдо:</label>
        <select name="recipes[]" required>
            {% for recipe in recipes %}
            <option value="{{ recipe }}">{{ recipe }}</option>
            {% endfor %}
        </select>
        <label for="quantity">Количество:</label>
        <input type="number" name="quantities[]" min="1" required>
    `;
    document.getElementById('recipeInputs').appendChild(newInput);
}


