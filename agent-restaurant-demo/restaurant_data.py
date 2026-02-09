# Restaurant menu data
MENU = {
    "appetizers": [
        {"id": "app1", "name": "Spring Rolls", "price": 8.50, "description": "Crispy vegetable spring rolls"},
        {"id": "app2", "name": "Garlic Bread", "price": 6.00, "description": "Toasted bread with garlic butter"},
        {"id": "app3", "name": "Bruschetta", "price": 9.50, "description": "Tomato and basil on toasted bread"}
    ],
    "mains": [
        {"id": "main1", "name": "Margherita Pizza", "price": 16.00, "description": "Classic tomato and mozzarella"},
        {"id": "main2", "name": "Spaghetti Carbonara", "price": 18.50, "description": "Creamy pasta with bacon"},
        {"id": "main3", "name": "Grilled Salmon", "price": 24.00, "description": "Atlantic salmon with vegetables"},
        {"id": "main4", "name": "Chicken Parmesan", "price": 20.00, "description": "Breaded chicken with marinara"},
        {"id": "main5", "name": "Vegetarian Lasagna", "price": 17.50, "description": "Layered pasta with vegetables"}
    ],
    "desserts": [
        {"id": "des1", "name": "Tiramisu", "price": 9.00, "description": "Classic Italian dessert"},
        {"id": "des2", "name": "Chocolate Cake", "price": 8.50, "description": "Rich chocolate layer cake"},
        {"id": "des3", "name": "Gelato", "price": 7.00, "description": "Italian ice cream, various flavors"}
    ],
    "drinks": [
        {"id": "drk1", "name": "Soft Drink", "price": 3.50, "description": "Coke, Sprite, or Fanta"},
        {"id": "drk2", "name": "Fresh Juice", "price": 5.00, "description": "Orange or apple juice"},
        {"id": "drk3", "name": "Coffee", "price": 4.50, "description": "Espresso, cappuccino, or latte"}
    ]
}

# Table availability - simplified schedule
# Format: {date: {time: available_tables}}
AVAILABILITY = {
    "2026-02-09": {
        "18:00": 3, "18:30": 2, "19:00": 1, "19:30": 0, "20:00": 2, "20:30": 4
    },
    "2026-02-10": {
        "18:00": 5, "18:30": 4, "19:00": 3, "19:30": 2, "20:00": 1, "20:30": 3
    },
    "2026-02-11": {
        "18:00": 4, "18:30": 3, "19:00": 2, "19:30": 1, "20:00": 0, "20:30": 2
    }
}

# In-memory storage for orders and reservations
ORDERS = {}
RESERVATIONS = []

TAX_RATE = 0.10  # 10% tax
