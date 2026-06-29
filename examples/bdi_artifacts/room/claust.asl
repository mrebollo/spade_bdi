/* Creencias */
// el estado inicial lo decine la clase Door


/* Planes */
+door(State) : State = locked <-
    .print("pide abrir");
    .send("porter@localhost",achieve,unlock).

+door(State) : State = unlocked.
