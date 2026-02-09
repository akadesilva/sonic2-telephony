# Restaurant Order Agent - Bella Italia

A voice-based restaurant ordering agent built with **Strands BidiAgent** and Amazon Bedrock Nova Sonic 2 for telephony integration.

## Architecture

- **Framework**: Strands Agents (built-in OTEL instrumentation)
- **Model**: Amazon Nova Sonic 2 (bidirectional streaming)
- **Observability**: AWS Distro for OpenTelemetry (ADOT)
- **Server**: FastAPI WebSocket
- **Integration**: Vonage Voice API

## Features

- **Dine-in Reservations**: Check availability and book tables
- **Takeaway Orders**: Take orders, calculate bills with tax
- **Menu Management**: Browse menu by category
- **Order Tracking**: Create, modify, and complete orders
- **Full Observability**: Automatic logging of all tool calls and model interactions

## Menu

- **Appetizers**: Spring Rolls, Garlic Bread, Bruschetta
- **Mains**: Margherita Pizza, Spaghetti Carbonara, Grilled Salmon, Chicken Parmesan, Vegetarian Lasagna
- **Desserts**: Tiramisu, Chocolate Cake, Gelato
- **Drinks**: Soft Drinks, Fresh Juice, Coffee

## Tools

1. `get_current_datetime` - Get current date/time
2. `get_menu` - Retrieve menu (full or by category)
3. `check_availability` - Check table availability
4. `create_reservation` - Book a table
5. `create_order` - Start new order
6. `add_item_to_order` - Add items to order
7. `calculate_bill` - Calculate total with tax
8. `complete_order` - Finalize order
9. `reject_order` - Cancel order

## Running

```bash
cd /home/ec2-user/work/demos/Bedrock/agents/agentcore/sonic2-telephony/agent-restaurant-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

## Demo Scenarios

### Scenario 1: Dine-in Reservation
- Customer wants to dine in
- Check availability for date/time
- Create reservation with customer details

### Scenario 2: Takeaway Order
- Customer wants takeaway
- Browse menu
- Add items to order
- Calculate and confirm total

## Evaluation Metrics

- Order accuracy (correct items, quantities)
- Bill calculation correctness
- Reservation details accuracy
- Conversation flow naturalness
- Error handling
