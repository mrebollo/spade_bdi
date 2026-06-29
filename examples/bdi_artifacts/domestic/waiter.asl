/* waiter.asl */

limit(beer, 7).
too_much(beer) :-
    .date(YY,MM,DD) & 
    .count(consumed(YY,MM,DD,_,_,_,beer), QtdB) & 
    limit(beer, Limit) & 
    QtdB >= Limit.

at(robot, fridge).

+!has(Ow, B) : available(beer, fridge) & not too_much(beer)
    <- .print("I am getting a ", B, " for ", Ow);
       !at(robot, fridge);
       +serving(Ow, B);
       .open(fridge);
       .get(B);
       .close(fridge);
       !finish_service(Ow, B).

// Si se pudo coger una cerveza, la entregamos
+!finish_service(Ow, B) : serving(Ow, B) & holding(beer)
    <- -serving(Ow, B);
       !at(robot, owner);
       .hand_in(Ow);
       // register that another beer will be consumed
       .date(YY,MM,DD); .time(HH,NN,SS);
       +consumed(YY,MM,DD,HH,NN,SS,beer);
       .print("Enjoy your beer, ", Ow).

// Si no había cerveza realmente disponible al coger, dejamos pedido pendiente
+!finish_service(Ow, B) : serving(Ow, B) & not holding(beer)
    <- .print("Looking inside... there are 0 beers.");
       -serving(Ow, B);
       +pedido_pendiente(Ow, B).

+!has(Ow, B) : not available(beer, fridge) & not too_much(beer)
    <- .print("Stock is empty. I will serve you as soon as it arrives.");
       +pedido_pendiente(Ow, B).

+available(beer, fridge) : pedido_pendiente(Ow, B)
    <- .print("Stock is back! Serving pending order for ", Ow);
       -pedido_pendiente(Ow, B);
       !has(Ow, B).

+!has(Ow, B) : too_much(beer)
    <- ?limit(beer, L);
       .concat("The Department of Health does not allow me to give you more than ", L, " beers a day!", M);
       .print(M);
       .send("owner@localhost", tell, msg(M));
       .print("Refusing to serve more beer to ", Ow).

+!at(robot, P) : at(robot, P) <- true.

+!at(robot, P) : not at(robot, P) 
    <- .print("Going to ", P);
       .move_towards(P);
       !at(robot, P).
