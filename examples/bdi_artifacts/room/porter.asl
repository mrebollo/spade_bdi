/* Creencias */
// el estado inicial lo decine la clase Door

/* Planes */

// recibe petición lock 
+!lock 
    <-
    .print("cerrando heridas");
    .lock.

// recibe petición unlock
+!unlock 
    <-
    .print("abriendo puerta");
    .unlock.

