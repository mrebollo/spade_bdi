/* Creencias */
// el estado inicial lo decine la clase Door

/* Planes */
+door(unlocked) <-
    .print("pide cerrar");
    .send("porter@localhost",achieve,lock).