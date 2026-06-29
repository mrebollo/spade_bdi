/* owner.asl */

/* initial intention */
!get(beer).

// Pedir una cerveza
+!get(beer)
    <- .print("Asking for a beer");
       .send("waiter@localhost", achieve, has(owner, beer)).


// Coger la cerveza de la mesa
+table(occupied)
    <- .print("Beer is on the table, taking it");
       .take.


// Si tengo una cerveza la bebo
+has(owner, beer)
    <- !drink(beer).


// Si no tengo la cerveza la pido
-has(owner,beer) : true
    <- 
    .print("I drank the beer, I have no more beers! :(");
    .wait(1000);
    !get(beer).

// Proceso para beber cerveza dando tragos
+!drink(beer) : has(owner,beer) //& focused(beer)
    <- .sip(beer);
       .wait(100);
       !drink(beer).

// Fin de la recursion: no queda cerveza
+!drink(beer) : not has(owner,beer).


// Reaccionar a mensajes del camarero
+msg(M)[source(Ag)] 
    <- .print("Message from ", Ag, ": ", M);
       -msg(M).