/* stocker.asl */

!start.

+!start 
    <- .print("Booting up. Checking fridge snapshot...");
       .open(fridge);
       .close(fridge).

// Reacciona al resultado del chequeo (o a cualquier cambio futuro)
+stock(beer, 0)
    <- .print("Confirmed: stock is empty. Ordering more...");
       .send("market@localhost", achieve, order(beer, 5)).

+stock(beer, Q) : Q > 0
    <- .print("Confirmed: I see ", Q, " beers. All good.").

+delivered(beer, Qtd, OrderId)[source(Ag)]
    <- 
    .print("Order ", OrderId, " arrived from ", Ag); 
    .print("Restocking fridge...");
    .restock(Qtd).
    //-delivered(beer, Qtd, OrderId).
