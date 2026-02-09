# Restaurant menu data
MENU = {
    "appetizers": [
        {"id": "app1", "name": "Samosa", "price": 80, "description": "Crispy pastry with spiced potato filling"},
        {"id": "app2", "name": "Paneer Tikka", "price": 180, "description": "Grilled cottage cheese with spices"},
        {"id": "app3", "name": "Chicken 65", "price": 220, "description": "Spicy fried chicken appetizer"}
    ],
    "mains": [
        {"id": "main1", "name": "Butter Chicken", "price": 350, "description": "Creamy tomato curry with chicken"},
        {"id": "main2", "name": "Paneer Butter Masala", "price": 280, "description": "Cottage cheese in rich tomato gravy"},
        {"id": "main3", "name": "Biryani", "price": 320, "description": "Fragrant rice with chicken or vegetables"},
        {"id": "main4", "name": "Dal Makhani", "price": 240, "description": "Black lentils in creamy sauce"},
        {"id": "main5", "name": "Tandoori Chicken", "price": 380, "description": "Clay oven roasted chicken"}
    ],
    "breads": [
        {"id": "bread1", "name": "Naan", "price": 50, "description": "Soft leavened flatbread"},
        {"id": "bread2", "name": "Garlic Naan", "price": 60, "description": "Naan with garlic and butter"},
        {"id": "bread3", "name": "Roti", "price": 30, "description": "Whole wheat flatbread"}
    ],
    "desserts": [
        {"id": "des1", "name": "Gulab Jamun", "price": 80, "description": "Sweet milk dumplings in syrup"},
        {"id": "des2", "name": "Kulfi", "price": 90, "description": "Traditional Indian ice cream"},
        {"id": "des3", "name": "Rasmalai", "price": 100, "description": "Cottage cheese in sweet milk"}
    ],
    "drinks": [
        {"id": "drk1", "name": "Lassi", "price": 70, "description": "Sweet or salted yogurt drink"},
        {"id": "drk2", "name": "Masala Chai", "price": 40, "description": "Spiced Indian tea"},
        {"id": "drk3", "name": "Fresh Lime Soda", "price": 60, "description": "Sweet or salted lime drink"}
    ]
}

# Table availability - simplified schedule
# Format: {date: {time: available_tables}}
AVAILABILITY = {
    "2026-02-09": {
        "12:00": 5, "12:30": 4, "13:00": 3, "13:30": 2, "14:00": 4,
        "18:00": 3, "18:30": 2, "19:00": 1, "19:30": 0, "20:00": 2, "20:30": 4, "21:00": 5
    },
    "2026-02-10": {
        "12:00": 6, "12:30": 5, "13:00": 4, "13:30": 3, "14:00": 5,
        "18:00": 5, "18:30": 4, "19:00": 3, "19:30": 2, "20:00": 1, "20:30": 3, "21:00": 4
    },
    "2026-02-11": {
        "12:00": 5, "12:30": 4, "13:00": 3, "13:30": 2, "14:00": 4,
        "18:00": 4, "18:30": 3, "19:00": 2, "19:30": 1, "20:00": 0, "20:30": 2, "21:00": 3
    },
    "2026-02-12": {
        "12:00": 6, "12:30": 5, "13:00": 4, "13:30": 3, "14:00": 5,
        "18:00": 5, "18:30": 4, "19:00": 3, "19:30": 2, "20:00": 3, "20:30": 4, "21:00": 5
    },
    "2026-02-13": {
        "12:00": 5, "12:30": 4, "13:00": 3, "13:30": 2, "14:00": 4,
        "18:00": 4, "18:30": 3, "19:00": 2, "19:30": 1, "20:00": 2, "20:30": 3, "21:00": 4
    },
    "2026-02-14": {
        "12:00": 3, "12:30": 2, "13:00": 1, "13:30": 0, "14:00": 2,
        "18:00": 2, "18:30": 1, "19:00": 0, "19:30": 0, "20:00": 1, "20:30": 2, "21:00": 3
    },
    "2026-02-15": {
        "12:00": 6, "12:30": 5, "13:00": 4, "13:30": 3, "14:00": 5,
        "18:00": 5, "18:30": 4, "19:00": 3, "19:30": 2, "20:00": 3, "20:30": 4, "21:00": 5
    }
}

# In-memory storage for orders and reservations
ORDERS = {}
RESERVATIONS = []

TAX_RATE = 0.18  # 18% GST
