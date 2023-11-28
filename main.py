from datetime import date
import redis
from fastapi import FastAPI, HTTPException

from models import BillPayLoad, ItemPayLoad

app = FastAPI()

redis_client = redis.StrictRedis(host="0.0.0.0", port=6379, db=0, decode_responses=True)

# TODO: Route to add bill
@app.post("/bills/{bill_name}/{bill_totalamt}")
def add_bill(bill_name: str, bill_totalamt: float) -> dict[str, BillPayLoad]:
    if bill_totalamt <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    
    #Check if item already exists
    return {
        "bill": BillPayLoad(bill_id=1, bill_name=bill_name, bill_totalamt=bill_totalamt, bill_duedate=date.today(), bill_mindue=0)
    }

# TODO: Route to delete bill
# TODO: Route to update bill


# Route to add an item
@app.post("/items/{item_name}/{quantity}")
def add_item(item_name: str, quantity: int) -> dict[str, ItemPayLoad]:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0.")

    # Check if item already exists
    item_id_str: str | None = redis_client.hget("item_name_to_id", item_name)

    if item_id_str is not None:
        item_id = int(item_id_str)
        redis_client.hincrby(f"item_id:{item_id}", "quantity", quantity)
    else:
        # Generate an ID for the item
        item_id: int = redis_client.incr("item_ids")
        redis_client.hset(
            f"item_id:{item_id}",
            mapping={
                "item_id": item_id,
                "item_name": item_name,
                "quantity": quantity,
            },
        )
        # Create a set so we can search by name too
        redis_client.hset("item_name_to_id", item_name, item_id)

    return {
        "item": ItemPayLoad(item_id=item_id, item_name=item_name, quantity=quantity)
    }


# Route to list a specific item by ID but using Redis
@app.get("/items/{item_id}")
def list_item(item_id: int) -> dict[str, dict[str, str]]:
    if not redis_client.hexists(f"item_id:{item_id}", "item_id"):
        raise HTTPException(status_code=404, detail="Item not found.")
    else:
        return {"item": redis_client.hgetall(f"item_id:{item_id}")}


@app.get("/items")
def list_items() -> dict[str, list[ItemPayLoad]]:
    items: list[ItemPayLoad] = []
    stored_items: dict[str, str] = redis_client.hgetall("item_name_to_id")

    for name, id_str in stored_items.items():
        item_id: int = int(id_str)

        item_name_str: str | None = redis_client.hget(f"item_id:{item_id}", "item_name")
        if item_name_str is not None:
            item_name: str = item_name_str
        else:
            continue  # skip this item if it has no name

        item_quantity_str: str | None = redis_client.hget(
            f"item_id:{item_id}", "quantity"
        )
        if item_quantity_str is not None:
            item_quantity: int = int(item_quantity_str)
        else:
            item_quantity = 0

        items.append(
            ItemPayLoad(item_id=item_id, item_name=item_name, quantity=item_quantity)
        )

    return {"items": items}


# Route to delete a specific item by ID but using Redis
@app.delete("/items/{item_id}")
def delete_item(item_id: int) -> dict[str, str]:
    if not redis_client.hexists(f"item_id:{item_id}", "item_id"):
        raise HTTPException(status_code=404, detail="Item not found.")
    else:
        item_name: str | None = redis_client.hget(f"item_id:{item_id}", "item_name")
        redis_client.hdel("item_name_to_id", f"{item_name}")
        redis_client.delete(f"item_id:{item_id}")
        return {"result": "Item deleted."}


# Route to remove some quantity of a specific item by ID but using Redis
@app.delete("/items/{item_id}/{quantity}")
def remove_quantity(item_id: int, quantity: int) -> dict[str, str]:
    if not redis_client.hexists(f"item_id:{item_id}", "item_id"):
        raise HTTPException(status_code=404, detail="Item not found.")

    item_quantity: str | None = redis_client.hget(f"item_id:{item_id}", "quantity")

    # if quantity to be removed is higher or equal to item's quantity, delete the item
    if item_quantity is None:
        existing_quantity: int = 0
    else:
        existing_quantity: int = int(item_quantity)
    if existing_quantity <= quantity:
        item_name: str | None = redis_client.hget(f"item_id:{item_id}", "item_name")
        redis_client.hdel("item_name_to_id", f"{item_name}")
        redis_client.delete(f"item_id:{item_id}")
        return {"result": "Item deleted."}
    else:
        redis_client.hincrby(f"item_id:{item_id}", "quantity", -quantity)
        return {"result": f"{quantity} items removed."}